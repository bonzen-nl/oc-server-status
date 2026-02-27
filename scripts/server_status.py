#!/usr/bin/env python3
"""
OpenClaw Server Status — Unified Report

Centrale orchestrator voor systeemmonitoring:
- Realtime system metrics (RAM, CPU, Disk, Temp, Ollama, ChromaDB)
- Gedetailleerde token analysis (alle providers + models)
- Token timeline per model: dag/week/maand breakdown (INGEBOUWD)
- Budget forecasting
- Comprehensive Dutch reporting

SAMENVOEGDE RAPPORTAGE:
  Server Status + Token Telemetry + Token Timeline (dag/week/maand)
  in ÉÉN geïntegreerd rapport

Gebruiking:
    python3 scripts/server_status.py --now
    python3 scripts/server_status.py --now --format json

Alle bedragen in EUR op 2 decimalen.
Alle output in Nederlands.

Author: OpenClaw Server Status
License: MIT
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.metrics_collector import MetricsCollector
from lib.token_telemetry import TokenTelemetry, TokenTimelineAnalyzer, format_token_timeline_section


def generate_unified_report(metrics: dict, token_stats: dict, 
                           timeline_data: dict) -> str:
    """
    Genereer UNIFIED rapport: System Metrics + Token Telemetry + Token Timeline.
    
    Alles in ÉÉN rapport, chronologisch:
    1. Server status (RAM, CPU, Disk, Services)
    2. Token telemetrie (totalen, per provider, per model)
    3. Token timeline per model (dag/week/maand)
    4. Aanbevelingen
    
    Args:
        metrics: System metrics van MetricsCollector
        token_stats: Token stats van TokenTelemetry
        timeline_data: Dict met daily/weekly/monthly token breakdown
    
    Returns:
        Geformateerd unified rapport string
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
    
    # ========== SYSTEM STATUS ==========
    report.append(f"\n{'='*80}")
    report.append(f"📊 OPENСLAW SERVER STATUS — {datetime.now().strftime('%Y-%m-%d %H:%M CET')}")
    report.append(f"{'='*80}")
    
    report.append(f"\n{status}")
    report.append(f"{'─'*80}")
    report.append(f"RAM:  {ram_percent:>6.1f}% ({metrics['ram']['used_gb']:>5.1f}GB / {metrics['ram']['total_gb']:>5.1f}GB)")
    report.append(f"CPU:  {cpu_load:>6.2f} load (4 cores)")
    report.append(f"Swap: {metrics['swap']['percent']:>6.1f}% ({metrics['swap']['used_gb']:>5.1f}GB / {metrics['swap']['total_gb']:>5.1f}GB)")
    report.append(f"Disk: {metrics['disk']['percent_used']:>6.1f}% ({metrics['disk']['free_gb']:>5.1f}GB free)")
    
    if 'cpu_temp_c' in metrics['temperature']:
        report.append(f"Temp: {metrics['temperature']['cpu_temp_c']:>6.1f}°C")
    
    report.append(f"\nSERVICES:")
    report.append(f"  Ollama:    {metrics['ollama']['model_count']} models ({metrics['ollama']['total_memory_gb']:.1f}GB)")
    report.append(f"  ChromaDB:  {metrics['chromadb']['doc_count']} docs ({metrics['chromadb']['size_mb']:.1f}MB)")
    
    # ========== TOKEN TELEMETRY ==========
    report.append(f"\n{'='*80}")
    report.append(f"💰 TOKEN TELEMETRIE — {token_stats.get('period', 'N/A')}")
    report.append(f"{'='*80}")
    
    report.append(f"\n📊 TOTAAL:")
    report.append(f"  Tokens:    {token_stats.get('total_tokens', 0):>15,d}")
    report.append(f"  Kosten:    €{token_stats.get('total_cost_eur', 0):>14,.2f}")
    
    report.append(f"\n🔌 PER AANBIEDER (Anthropic, OpenAI, Google, Ollama):")
    for provider, data in sorted(
        token_stats.get('by_provider', {}).items(),
        key=lambda x: x[1]['cost_eur'],
        reverse=True
    ):
        if data['tokens'] > 0:
            # EUR op 2 decimalen
            cost_eur = data['cost_eur']
            report.append(f"  {provider:15s} | €{cost_eur:>8,.2f} | {data['tokens']:>10,d} tokens")
    
    # Top models (alle providers)
    report.append(f"\n🏆 TOP MODELLEN (alle providers):")
    all_models = []
    for provider, data in token_stats.get('by_provider', {}).items():
        if isinstance(data, dict) and 'models' in data:
            for model, model_data in data.get('models', {}).items():
                all_models.append({
                    'provider': provider,
                    'model': model,
                    'tokens': model_data.get('tokens', 0),
                    'cost_eur': model_data.get('cost_eur', 0.0)
                })
    
    all_models.sort(key=lambda x: x['cost_eur'], reverse=True)
    
    for i, item in enumerate(all_models[:10], 1):
        # EUR op 2 decimalen
        report.append(f"  {i:2d}. {item['provider']:12s}/{item['model']:<30s} €{item['cost_eur']:>8,.2f}")
    
    # Budget
    budget_remaining = token_stats.get('budget_remaining_eur', 0)
    total_budget = 100
    spent = total_budget - budget_remaining if budget_remaining >= 0 else total_budget
    pct = (spent / total_budget * 100) if total_budget > 0 else 0
    
    report.append(f"\n💳 BUDGET:")
    report.append(f"  Monthly:   €{total_budget:>10,.2f}")
    report.append(f"  Spent:     €{spent:>10,.2f}  ({pct:>5.1f}%)")
    report.append(f"  Remaining: €{budget_remaining:>10,.2f}")
    
    if pct > 75:
        report.append(f"  ⚠️  Hoog verbruik")
    else:
        report.append(f"  ✅ Gezond")
    
    # ========== TOKEN TIMELINE (INGEBOUWD) ==========
    if timeline_data:
        timeline_text = format_token_timeline_section(
            timeline_data.get('daily', {}),
            timeline_data.get('weekly', {}),
            timeline_data.get('monthly', {})
        )
        report.append(timeline_text)
    
    # ========== RECOMMENDATIONS ==========
    report.append(f"{'='*80}")
    report.append(f"⚙️  AANBEVELINGEN:")
    
    if ram_percent > 85:
        report.append(f"  🚨 RAM critical — sluit apps")
    elif ram_percent > 70:
        report.append(f"  ⚠️  RAM matig — controleer")
    else:
        report.append(f"  ✅ RAM gezond")
    
    if metrics['swap']['percent'] > 80:
        report.append(f"  ⚠️  Swap hoog — upgrade RAM?")
    
    if metrics['disk']['percent_used'] > 90:
        report.append(f"  🚨 Disk vol — opschonen nodig")
    
    if pct > 75:
        report.append(f"  💰 Budget hoog — optimaliseer")
    
    report.append(f"\n{'='*80}\n")
    
    return "\n".join(report)


def main():
    """
    Main entry point.
    
    Commandline argumenten:
        --now: Genereer onmiddellijk
        --format: Output format (text/json, default: text)
    """
    parser = argparse.ArgumentParser(description="OpenClaw Server Status — Unified Report")
    parser.add_argument("--now", action="store_true", help="Genereer onmiddellijk")
    parser.add_argument("--format", default="text", choices=["text", "json"], help="Output format")
    
    args = parser.parse_args()
    
    try:
        print("📊 Verzamelen system metrics...", file=sys.stderr)
        collector = MetricsCollector()
        metrics = collector.collect()
        
        print("💰 Verzamelen token telemetrie (alle providers)...", file=sys.stderr)
        telemetry = TokenTelemetry()
        token_stats = telemetry.get_monthly_stats()
        
        print("📈 Verzamelen token timeline (per model, dag/week/maand)...", file=sys.stderr)
        timeline = TokenTimelineAnalyzer()
        timeline_data = {
            "daily": timeline.get_daily_model_tokens(),
            "weekly": timeline.get_weekly_model_tokens(),
            "monthly": timeline.get_monthly_model_tokens()
        }
        
        if args.format == "text":
            report = generate_unified_report(metrics, token_stats, timeline_data)
            print(report)
        else:
            output = {
                "timestamp": metrics['timestamp'],
                "metrics": metrics,
                "tokens": token_stats,
                "timeline": timeline_data
            }
            print(json.dumps(output, indent=2))
        
        print("✅ Rapport gegenereerd", file=sys.stderr)
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
