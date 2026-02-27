#!/usr/bin/env python3
"""
OpenClaw Server Status — Main Script

Centrale orchestrator voor systeemmonitoring:
- Verzamelt realtime metrics
- Analyzeert via lokale Mistral
- Genereert Nederlands rapport met token-telemetrie
- Queued naar Telegram

Gebruiking:
    python3 scripts/server_status.py --now
    python3 scripts/server_status.py --now --verbose

Author: OpenClaw Server Status
License: MIT
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.metrics_collector import MetricsCollector
from lib.token_telemetry import TokenTelemetry


def load_config(config_path: str = None) -> dict:
    """
    Laad configuratie vanuit JSON bestand.
    
    Args:
        config_path: Optioneel pad naar config. 
                    Default: config/server_status.json
    
    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "server_status.json"
    
    if Path(config_path).exists():
        with open(config_path) as f:
            return json.load(f)
    
    # Default config
    return {
        "report_interval_hours": 6,
        "telegram_chat_id": 8106588289,
        "chromadb_path": "/Users/bonzen/.openclaw/workspace/openclaw_rag/index_data",
        "budget": {"monthly_limit_eur": 100}
    }


def generate_report(metrics: dict, token_stats: dict, verbose: bool = False) -> str:
    """
    Genereer Nederlands rapport met metrics en token-telemetrie.
    
    Args:
        metrics: Systeemmetrics van MetricsCollector
        token_stats: Token statistieken van TokenTelemetry
        verbose: Alle details tonen
    
    Returns:
        Geformateerde rapport string
    """
    ram_percent = metrics['ram']['percent']
    cpu_load = metrics['cpu']['load_1min']
    
    # Status bepalen
    if ram_percent > 90:
        status = "🔴 CRITICAL"
    elif ram_percent > 75:
        status = "🟠 CAUTION"
    else:
        status = "🟢 HEALTHY"
    
    report = []
    report.append(f"\n{'='*60}")
    report.append(f"📊 SERVER STATUS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"{'='*60}")
    
    # Systeemstatus
    report.append(f"\n{status}")
    report.append(f"RAM:  {ram_percent:6.1f}% ({metrics['ram']['used_gb']:5.1f}GB / {metrics['ram']['total_gb']:5.1f}GB)")
    report.append(f"CPU:  {cpu_load:6.2f} load (4 cores)")
    report.append(f"Swap: {metrics['swap']['percent']:6.1f}% ({metrics['swap']['used_gb']:5.1f}GB / {metrics['swap']['total_gb']:5.1f}GB)")
    report.append(f"Disk: {metrics['disk']['percent_used']:6.1f}% ({metrics['disk']['free_gb']:5.1f}GB free)")
    
    # Temps
    if 'cpu_temp_c' in metrics['temperature']:
        report.append(f"Temp: {metrics['temperature']['cpu_temp_c']:6.1f}°C")
    
    # Services
    report.append(f"\nSERVICES:")
    report.append(f"  Ollama:    {metrics['ollama']['model_count']} models ({metrics['ollama']['total_memory_gb']:.1f}GB)")
    report.append(f"  ChromaDB:  {metrics['chromadb']['doc_count']} docs ({metrics['chromadb']['size_mb']:.1f}MB)")
    
    # Token Telemetry
    report.append(f"\n💰 TOKEN TELEMETRIE ({token_stats['period']}):")
    report.append(f"  Totaal Tokens:  {token_stats['total_tokens']:>12,d}")
    report.append(f"  Totaal Kosten:  €{token_stats['total_cost_eur']:>11,.2f}")
    
    # Per provider
    report.append(f"\n  Per aanbieder:")
    for provider, data in sorted(
        token_stats['by_provider'].items(),
        key=lambda x: x[1]['cost_eur'],
        reverse=True
    ):
        if data['cost_eur'] > 0:  # Only show if cost > 0
            report.append(f"    {provider:12s}: €{data['cost_eur']:>8,.2f} ({data['tokens']:>8,d} tokens)")
            
            # Models
            if data['models']:
                for model, mdata in sorted(
                    data['models'].items(),
                    key=lambda x: x[1]['cost_eur'],
                    reverse=True
                ):
                    if mdata['cost_eur'] > 0:
                        report.append(f"      • {model:<25s}: €{mdata['cost_eur']:.2f}")
    
    # Budget
    budget_remaining = token_stats.get('budget_remaining_eur', 0)
    if budget_remaining > 0:
        report.append(f"\n  Budget Remaining: €{budget_remaining:.2f}")
    
    # Recommendations
    report.append(f"\n⚙️ AANBEVELINGEN:")
    if ram_percent > 85:
        report.append(f"  ⚠️  RAM approaching limit — close Safari/Chrome")
    elif ram_percent > 70:
        report.append(f"  ℹ️  RAM usage moderate — monitor")
    else:
        report.append(f"  ✅ RAM usage healthy")
    
    if metrics['swap']['percent'] > 50:
        report.append(f"  ⚠️  Swap usage: {metrics['swap']['percent']:.0f}% — consider RAM upgrade")
    
    if metrics['disk']['percent_used'] > 90:
        report.append(f"  🚨 Disk nearly full — cleanup needed")
    
    report.append(f"\n{'='*60}\n")
    
    return "\n".join(report)


def main():
    """
    Main entry point.
    
    Argumenten:
        --now: Onmiddellijk rapport genereren
        --verbose: Alle details
        --format: Output format (text/json)
    """
    parser = argparse.ArgumentParser(description="OpenClaw Server Status Monitor")
    parser.add_argument("--now", action="store_true", help="Generate report immediately")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--format", default="text", choices=["text", "json"],
                       help="Output format")
    
    args = parser.parse_args()
    
    try:
        # Verzamel metrics
        print("📊 Verzamelen metrics...", file=sys.stderr)
        collector = MetricsCollector()
        metrics = collector.collect()
        
        # Verzamel token telemetrie
        print("💰 Verzamelen token telemetrie...", file=sys.stderr)
        telemetry = TokenTelemetry()
        token_stats = telemetry.get_monthly_stats()
        
        # Genereer rapport
        if args.format == "text":
            report = generate_report(metrics, token_stats, args.verbose)
            print(report)
        else:
            # JSON output
            output = {
                "timestamp": metrics['timestamp'],
                "metrics": metrics,
                "tokens": token_stats
            }
            print(json.dumps(output, indent=2))
        
        print("✅ Done", file=sys.stderr)
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
