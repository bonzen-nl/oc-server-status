#!/usr/bin/env python3
"""
Token Telemetry Module voor OpenClaw Server Status

Verzamelt en analyzeert token-verbruik en kosten-data van de software-architect
token_usage.db database. Geeft gedetailleerde rapportage per aanbieder, model,
en project.

Module gebruiking:
    from lib.token_telemetry import TokenTelemetry
    
    telemetry = TokenTelemetry()
    stats = telemetry.get_monthly_stats()
    print(stats)

Author: OpenClaw Server Status
License: MIT
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict


class TokenTelemetry:
    """
    Verzamelt token-verbruik en kostgegevens uit software-architect's token_usage.db.
    
    Geeft inzicht in:
    - Totaal token-verbruik per aanbieder
    - Kosten per model en per project
    - Trend analyse (dagelijks, wekelijks, maandelijks)
    - Budget utilization per provider
    
    Attributes:
        db_path (Path): Pad naar token_usage.db (default: software-architect skill dir)
        cost_table (Dict): Mapping van provider → token cost per 1M tokens
    """
    
    # Kostenstructuur per aanbieder (USD per 1M tokens, gemiddelden)
    PROVIDER_COSTS = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
            "claude-3-opus-20250219": {"input": 15.0, "output": 75.0},
            "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
        },
        "openai": {
            "gpt-4o": {"input": 5.0, "output": 15.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.6},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        },
        "gemini": {
            "gemini-1.5-pro": {"input": 1.25, "output": 5.0},
            "gemini-1.5-flash": {"input": 0.075, "output": 0.3},
        },
        "ollama": {
            "mistral-small3.1:24b": {"input": 0.0, "output": 0.0},  # Local = free
            "nomic-embed-text": {"input": 0.0, "output": 0.0},
        }
    }
    
    # Wisselkoers USD → EUR (update periodically)
    USD_TO_EUR = 0.92
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialiseer TokenTelemetry.
        
        Args:
            db_path: Optioneel pad naar token_usage.db. 
                    Standaard: /Users/bonzen/.openclaw/skills/software-architect/token_usage.db
        
        Raises:
            FileNotFoundError: Als database niet bestaat
            sqlite3.Error: Bij database-connectie fouten
        """
        if db_path is None:
            db_path = "/Users/bonzen/.openclaw/skills/software-architect/token_usage.db"
        
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Token database niet gevonden: {self.db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
    def __del__(self):
        """Sluit database verbinding"""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def get_monthly_stats(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """
        Haal maandelijkse token en cost statistieken op.
        
        Args:
            year: Jaar (standaard: huidige jaar)
            month: Maand (standaard: huidige maand)
        
        Returns:
            Dict met:
                - total_tokens: Totaal input + output tokens
                - total_cost_usd: Totaal kosten in USD
                - total_cost_eur: Totaal kosten in EUR
                - by_provider: Breakdown per aanbieder
                - by_model: Breakdown per model
                - by_project: Breakdown per project
                - budget_remaining: Resterende budget (indien geconfigureerd)
        
        Example:
            >>> stats = telemetry.get_monthly_stats(2026, 2)
            >>> print(f"€{stats['total_cost_eur']:.2f}")
        """
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        # Bepaal daterange voor maand
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        start_ts = first_day.isoformat()
        end_ts = last_day.isoformat()
        
        # Query database
        cursor = self.conn.cursor()
        query = """
            SELECT 
                model,
                provider,
                project_id,
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output,
                SUM(cost_eur) as total_cost,
                COUNT(*) as call_count
            FROM model_calls
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY model, provider, project_id
            ORDER BY total_cost DESC
        """
        
        cursor.execute(query, (start_ts, end_ts))
        rows = cursor.fetchall()
        
        # Aggregeer resultaten
        total_tokens = 0
        total_cost_eur = 0.0
        
        by_provider = defaultdict(lambda: {
            "tokens": 0,
            "cost_eur": 0.0,
            "models": {}
        })
        
        by_model = defaultdict(lambda: {
            "tokens": 0,
            "cost_eur": 0.0,
            "calls": 0
        })
        
        by_project = defaultdict(lambda: {
            "tokens": 0,
            "cost_eur": 0.0,
            "calls": 0
        })
        
        for row in rows:
            input_tokens = row['total_input'] or 0
            output_tokens = row['total_output'] or 0
            total_tokens_row = input_tokens + output_tokens
            cost_row = row['total_cost'] or 0.0
            
            total_tokens += total_tokens_row
            total_cost_eur += cost_row
            
            provider = row['provider']
            model = row['model']
            project = row['project_id'] or 'unknown'
            
            # Per provider
            by_provider[provider]["tokens"] += total_tokens_row
            by_provider[provider]["cost_eur"] += cost_row
            by_provider[provider]["models"].setdefault(model, {
                "tokens": 0,
                "cost_eur": 0.0
            })
            by_provider[provider]["models"][model]["tokens"] += total_tokens_row
            by_provider[provider]["models"][model]["cost_eur"] += cost_row
            
            # Per model
            model_key = f"{provider}/{model}"
            by_model[model_key]["tokens"] += total_tokens_row
            by_model[model_key]["cost_eur"] += cost_row
            by_model[model_key]["calls"] += row['call_count']
            
            # Per project
            by_project[project]["tokens"] += total_tokens_row
            by_project[project]["cost_eur"] += cost_row
            by_project[project]["calls"] += row['call_count']
        
        return {
            "period": f"{year:04d}-{month:02d}",
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_eur / self.USD_TO_EUR,
            "total_cost_eur": total_cost_eur,
            "by_provider": dict(by_provider),
            "by_model": dict(by_model),
            "by_project": dict(by_project),
            "budget_remaining_eur": self._calculate_budget_remaining(total_cost_eur)
        }
    
    def get_daily_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Haal dagelijkse trend op (laatste N dagen).
        
        Args:
            days: Aantal dagen terug (default: 30)
        
        Returns:
            List van dicts per dag met tokens en kosten
        
        Example:
            >>> trend = telemetry.get_daily_trend(7)
            >>> for day in trend:
            ...     print(f"{day['date']}: €{day['cost_eur']:.2f}")
        """
        cursor = self.conn.cursor()
        
        # Query laatste N dagen
        query = """
            SELECT 
                DATE(timestamp) as date,
                SUM(input_tokens + output_tokens) as tokens,
                SUM(cost_eur) as cost,
                COUNT(*) as calls
            FROM model_calls
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """
        
        cursor.execute(query, (days,))
        rows = cursor.fetchall()
        
        return [
            {
                "date": row['date'],
                "tokens": row['tokens'] or 0,
                "cost_eur": row['cost'] or 0.0,
                "calls": row['calls'] or 0
            }
            for row in rows
        ]
    
    def format_report(self, stats: Dict[str, Any]) -> str:
        """
        Format statistieken als leesbare Nederlands rapport.
        
        Args:
            stats: Resultaat van get_monthly_stats()
        
        Returns:
            Geformateerde string voor display/logging
        """
        report = []
        report.append("\n" + "="*60)
        report.append(f"📊 TOKEN TELEMETRIE RAPPORT — {stats['period']}")
        report.append("="*60)
        
        # Totaal
        report.append(f"\n💰 TOTAAL:")
        report.append(f"  Tokens:    {stats['total_tokens']:>15,d}")
        report.append(f"  USD:       ${stats['total_cost_usd']:>14,.2f}")
        report.append(f"  EUR:       €{stats['total_cost_eur']:>14,.2f}")
        
        # Per provider
        report.append(f"\n🔌 PER AANBIEDER:")
        for provider, data in sorted(
            stats['by_provider'].items(), 
            key=lambda x: x[1]['cost_eur'], 
            reverse=True
        ):
            report.append(f"\n  {provider.upper()}")
            report.append(f"    Tokens: {data['tokens']:>10,d}")
            report.append(f"    Kosten: €{data['cost_eur']:>9,.2f}")
            
            # Models per provider
            for model, model_data in sorted(
                data['models'].items(),
                key=lambda x: x[1]['cost_eur'],
                reverse=True
            ):
                report.append(f"      • {model}: {model_data['tokens']:>8,d} tokens, €{model_data['cost_eur']:.2f}")
        
        # Per project (top 10)
        report.append(f"\n📦 TOP PROJECTEN:")
        for i, (project, data) in enumerate(
            sorted(stats['by_project'].items(), 
                   key=lambda x: x[1]['cost_eur'], 
                   reverse=True)[:10],
            1
        ):
            report.append(f"  {i:2d}. {project:<25s} €{data['cost_eur']:>8,.2f}  ({data['calls']} calls)")
        
        # Budget
        budget_remaining = stats.get('budget_remaining_eur', 0)
        if budget_remaining >= 0:
            report.append(f"\n💳 BUDGET REMAINING: €{budget_remaining:.2f}")
        
        report.append("\n" + "="*60 + "\n")
        
        return "\n".join(report)
    
    def _calculate_budget_remaining(self, spent_eur: float) -> float:
        """
        Calculate remaining budget (helper method).
        
        Args:
            spent_eur: Bedrag uitgegeven in EUR deze maand
        
        Returns:
            Resterende budget (€0 als geen limiet)
        """
        # Read from config if available
        config_path = Path(__file__).parent.parent / "config" / "server_status.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    monthly_budget = config.get("budget", {}).get("monthly_limit_eur", 0)
                    if monthly_budget > 0:
                        return max(0, monthly_budget - spent_eur)
            except:
                pass
        
        return 0


def test_telemetry():
    """
    Test function voor TokenTelemetry module.
    
    Voert basic tests uit:
    - Database verbinding
    - Monthly stats opname
    - Report formatting
    """
    try:
        print("🧪 Testing TokenTelemetry module...")
        
        telemetry = TokenTelemetry()
        print("✅ Database connection OK")
        
        stats = telemetry.get_monthly_stats()
        print("✅ Monthly stats OK")
        
        report = telemetry.format_report(stats)
        print(report)
        
        print("✅ All tests passed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_telemetry()
