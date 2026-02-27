#!/usr/bin/env python3
"""
Token Telemetry Module voor OpenClaw Server Status

Verzamelt en analyzeert token-verbruik en kosten-data van de software-architect
token_usage.db database. Geeft gedetailleerde rapportage per aanbieder, model,
en project. Includes timeline analysis per model (dag/week/maand).

Module gebruiking:
    from lib.token_telemetry import TokenTelemetry, TokenTimelineAnalyzer
    
    telemetry = TokenTelemetry()
    stats = telemetry.get_monthly_stats()
    
    timeline = TokenTimelineAnalyzer()
    daily = timeline.get_daily_model_tokens()

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
    - Totaal token-verbruik per aanbieder (Anthropic, OpenAI, Google, Ollama)
    - Kosten per model en per project
    - Budget utilization per provider
    - EUR bedragen ALTIJD op 2 decimalen
    
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
            "mistral-small3.1:24b": {"input": 0.0, "output": 0.0},
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
        
        EUR bedragen ALTIJD op 2 decimalen.
        
        Args:
            year: Jaar (standaard: huidge jaar)
            month: Maand (standaard: huidge maand)
        
        Returns:
            Dict met:
                - total_tokens: Totaal input + output tokens
                - total_cost_usd: Totaal kosten in USD (2 decimalen)
                - total_cost_eur: Totaal kosten in EUR (2 decimalen)
                - by_provider: Breakdown per aanbieder (Anthropic, OpenAI, Google, Ollama)
                - by_model: Breakdown per model
                - by_project: Breakdown per project
                - budget_remaining: Resterende budget (2 decimalen)
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
            "calls": 0,
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
            by_provider[provider]["calls"] += row['call_count']
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
        
        # Round EUR naar 2 decimalen
        total_cost_eur = round(total_cost_eur, 2)
        
        return {
            "period": f"{year:04d}-{month:02d}",
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost_eur / self.USD_TO_EUR, 2),
            "total_cost_eur": total_cost_eur,
            "by_provider": dict(by_provider),
            "by_model": dict(by_model),
            "by_project": dict(by_project),
            "budget_remaining_eur": round(self._calculate_budget_remaining(total_cost_eur), 2)
        }
    
    def get_daily_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Haal dagelijkse trend op (laatste N dagen).
        
        EUR bedragen op 2 decimalen.
        
        Args:
            days: Aantal dagen terug (default: 30)
        
        Returns:
            List van dicts per dag met tokens en kosten
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
                "cost_eur": round(row['cost'] or 0.0, 2),
                "calls": row['calls'] or 0
            }
            for row in rows
        ]
    
    def format_report(self, stats: Dict[str, Any]) -> str:
        """
        Format statistieken als leesbare Nederlands rapport.
        
        EUR bedragen ALTIJD op 2 decimalen.
        
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
        report.append(f"\n🔌 PER AANBIEDER (Anthropic, OpenAI, Google, Ollama):")
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
                report.append(f"      • {model}: €{model_data['cost_eur']:.2f}")
        
        # Per project (top 10)
        report.append(f"\n📦 TOP PROJECTEN:")
        for i, (project, data) in enumerate(
            sorted(stats['by_project'].items(), 
                   key=lambda x: x[1]['cost_eur'], 
                   reverse=True)[:10],
            1
        ):
            report.append(f"  {i:2d}. {project:<25s} €{data['cost_eur']:>8,.2f}")
        
        # Budget
        budget_remaining = stats.get('budget_remaining_eur', 0)
        if budget_remaining >= 0:
            report.append(f"\n💳 BUDGET REMAINING: €{budget_remaining:.2f}")
        
        report.append("\n" + "="*60 + "\n")
        
        return "\n".join(report)
    
    def _calculate_budget_remaining(self, spent_eur: float) -> float:
        """
        Calculate remaining budget (helper method).
        
        EUR op 2 decimalen.
        
        Args:
            spent_eur: Bedrag uitgegeven in EUR deze maand
        
        Returns:
            Resterende budget (€0 als geen limiet, 2 decimalen)
        """
        # Read from config if available
        config_path = Path(__file__).parent.parent / "config" / "server_status.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    monthly_budget = config.get("budget", {}).get("monthly_limit_eur", 0)
                    if monthly_budget > 0:
                        return max(0, round(monthly_budget - spent_eur, 2))
            except:
                pass
        
        return 0.0


class TokenTimelineAnalyzer:
    """
    Analyzeert token-verbruik PER MODEL over dag/week/maand periodes.
    
    Geeft gedetailleerde inzicht in welke modellen hoeveel tokens verbruiken:
    - Dagelijks: model breakdown voor afgelopen 3 dagen
    - Wekelijks: trends per week per model
    - Maandelijks: vergelijking vorige 3 maanden per model
    
    EUR bedragen ALTIJD op 2 decimalen.
    Onderdeel van unified server status rapport.
    
    Attributes:
        db_path (Path): Pad naar token_usage.db (software-architect skill)
        conn (sqlite3.Connection): Database verbinding
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialiseer analyzer.
        
        Args:
            db_path: Database pad (default: software-architect/token_usage.db)
        
        Raises:
            FileNotFoundError: Als database niet bestaat
        """
        if db_path is None:
            db_path = "/Users/bonzen/.openclaw/skills/software-architect/token_usage.db"
        
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database niet gevonden: {self.db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
    
    def __del__(self):
        """Sluit verbinding"""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def get_daily_model_tokens(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Haal dagelijks token-verbruik per model op.
        
        EUR bedragen op 2 decimalen.
        
        Returns: {datum: {model: {tokens, cost_eur, calls}}}
        
        Args:
            year: Jaar (default: huidge)
            month: Maand (default: huidge)
        
        Returns:
            Dict met dagelijkse model-statistieken
        """
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        start_ts = first_day.isoformat()
        end_ts = last_day.isoformat()
        
        cursor = self.conn.cursor()
        query = """
            SELECT 
                DATE(timestamp) as date,
                model,
                provider,
                SUM(input_tokens + output_tokens) as tokens,
                SUM(cost_eur) as cost,
                COUNT(*) as calls
            FROM model_calls
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY DATE(timestamp), model, provider
            ORDER BY date DESC, cost DESC
        """
        
        cursor.execute(query, (start_ts, end_ts))
        rows = cursor.fetchall()
        
        result = defaultdict(dict)
        
        for row in rows:
            date = row['date']
            model_key = f"{row['provider']}/{row['model']}"
            
            result[date][model_key] = {
                "tokens": row['tokens'] or 0,
                "cost_eur": round(row['cost'] or 0.0, 2),
                "calls": row['calls'] or 0
            }
        
        return dict(result)
    
    def get_weekly_model_tokens(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Haal wekelijks token-verbruik per model op.
        
        EUR bedragen op 2 decimalen.
        
        Returns: {week: {model: {tokens, cost_eur, calls, days_active}}}
        
        Args:
            year: Jaar
            month: Maand
        
        Returns:
            Dict met wekelijkse statistieken per model
        """
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        start_ts = first_day.isoformat()
        end_ts = last_day.isoformat()
        
        cursor = self.conn.cursor()
        query = """
            SELECT 
                strftime('%Y-W%W', timestamp) as week,
                model,
                provider,
                SUM(input_tokens + output_tokens) as tokens,
                SUM(cost_eur) as cost,
                COUNT(*) as calls,
                COUNT(DISTINCT DATE(timestamp)) as days_active
            FROM model_calls
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY strftime('%Y-W%W', timestamp), model, provider
            ORDER BY week DESC, cost DESC
        """
        
        cursor.execute(query, (start_ts, end_ts))
        rows = cursor.fetchall()
        
        result = defaultdict(dict)
        
        for row in rows:
            week = row['week']
            model_key = f"{row['provider']}/{row['model']}"
            
            result[week][model_key] = {
                "tokens": row['tokens'] or 0,
                "cost_eur": round(row['cost'] or 0.0, 2),
                "calls": row['calls'] or 0,
                "days_active": row['days_active'] or 0
            }
        
        return dict(result)
    
    def get_monthly_model_tokens(self, months_back: int = 3) -> Dict[str, Dict[str, Any]]:
        """
        Vergelijk model-tokens over maanden (trend).
        
        EUR bedragen op 2 decimalen.
        
        Args:
            months_back: Aantal maanden terug
        
        Returns:
            Dict: {maand: {model: {tokens, cost_eur, calls}}}
        """
        cursor = self.conn.cursor()
        result = {}
        
        for i in range(months_back):
            month_date = datetime.now() - timedelta(days=30*i)
            year = month_date.year
            month = month_date.month
            
            first_day = datetime(year, month, 1)
            if month == 12:
                last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1) - timedelta(days=1)
            
            start_ts = first_day.isoformat()
            end_ts = last_day.isoformat()
            
            query = """
                SELECT 
                    model,
                    provider,
                    SUM(input_tokens + output_tokens) as tokens,
                    SUM(cost_eur) as cost,
                    COUNT(*) as calls
                FROM model_calls
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY model, provider
                ORDER BY cost DESC
            """
            
            cursor.execute(query, (start_ts, end_ts))
            rows = cursor.fetchall()
            
            month_key = f"{year:04d}-{month:02d}"
            result[month_key] = {}
            
            for row in rows:
                model_key = f"{row['provider']}/{row['model']}"
                result[month_key][model_key] = {
                    "tokens": row['tokens'] or 0,
                    "cost_eur": round(row['cost'] or 0.0, 2),
                    "calls": row['calls'] or 0
                }
        
        return result


def format_token_timeline_section(daily: Dict, weekly: Dict, monthly: Dict) -> str:
    """
    Format token timeline als rapport-sectie.
    
    Toont model-verbruik per dag, week, maand in leesbaar format.
    EUR bedragen ALTIJD op 2 decimalen.
    
    Args:
        daily: Van get_daily_model_tokens()
        weekly: Van get_weekly_model_tokens()
        monthly: Van get_monthly_model_tokens()
    
    Returns:
        Geformateerde string voor in het rapport
    """
    section = []
    
    section.append(f"\n{'='*70}")
    section.append(f"📈 TOKEN VERBRUIK PER MODEL — Dag / Week / Maand")
    section.append(f"{'='*70}")
    
    # Dagelijks
    if daily:
        section.append(f"\n📅 DAGELIJKS (meest recent):")
        for date in sorted(daily.keys(), reverse=True)[:3]:
            section.append(f"\n  {date}:")
            models = daily[date]
            for model, data in sorted(models.items(), key=lambda x: x[1]['cost_eur'], reverse=True):
                # EUR op 2 decimalen
                section.append(f"    {model:<35s} | {data['tokens']:>8,d} tokens | €{data['cost_eur']:>7,.2f}")
    
    # Wekelijks
    if weekly:
        section.append(f"\n\n📊 WEKELIJKS:")
        for week in sorted(weekly.keys(), reverse=True)[:2]:
            section.append(f"\n  Week {week}:")
            models = weekly[week]
            for model, data in sorted(models.items(), key=lambda x: x[1]['cost_eur'], reverse=True):
                # EUR op 2 decimalen
                section.append(f"    {model:<35s} | {data['tokens']:>8,d} tokens | €{data['cost_eur']:>7,.2f} ({data['days_active']}d)")
    
    # Maandelijks
    if monthly:
        section.append(f"\n\n📈 MAANDELIJKS (trend):")
        
        # Top modellen
        all_models = set()
        for month_data in monthly.values():
            all_models.update(month_data.keys())
        
        # Top 3 modellen
        top_models = set()
        for month_key in sorted(monthly.keys(), reverse=True)[0:1]:
            for model in list(monthly[month_key].keys())[:3]:
                top_models.add(model)
        
        for model in sorted(top_models):
            section.append(f"\n  {model}:")
            for month in sorted(monthly.keys(), reverse=True):
                if model in monthly[month]:
                    data = monthly[month][model]
                    # EUR op 2 decimalen
                    section.append(f"    {month}: {data['tokens']:>8,d} tokens | €{data['cost_eur']:>7,.2f}")
    
    section.append(f"\n{'='*70}\n")
    
    return "\n".join(section)
