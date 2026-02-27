# Token Telemetry Integration

## Overzicht

OpenClaw Server Status bevat nu volledige token-telemetrie integratie. Wanneer de status wordt gegenereerd, wordt automatisch een overzicht van token-verbruik en kosten per aanbieder en model getoond.

### Wat is opgenomen?

#### 💰 Token Statistieken
- **Totaal tokens**: Alles input + output tokens deze maand
- **Totaal kosten**: In EUR (omgerekend van USD)
- **Per aanbieder**: Ophaling per provider (Anthropic, OpenAI, Gemini, Ollama)
- **Per model**: Costbreakdown per specifiek model
- **Per project**: Cost tracking per project-ID

#### 📊 Report Output

Elke status-rapport bevat nu:

```
📊 SERVER STATUS — 2026-02-27 22:35
============================================================

🟢 HEALTHY
RAM:     45.2% (  4.9GB /  10.9GB)
CPU:       1.23 load (4 cores)
Swap:     38.5% (  2.7GB /   7.0GB)
Disk:     42.1% (  12.3GB free)
Temp:     52.5°C

SERVICES:
  Ollama:    2 models (6.5GB)
  ChromaDB:  99 docs (2.5MB)

💰 TOKEN TELEMETRIE (2026-02):
  Totaal Tokens:        125,450
  Totaal Kosten:        €15.70

  Per aanbieder:
    anthropic   : €12.50 (  95,000 tokens)
      • claude-3-5-sonnet-20241022: €12.50
    openai      :  €2.80 (  23,450 tokens)
      • gpt-4o-mini: €2.80
    gemini      :  €0.40 (   7,000 tokens)
      • gemini-1.5-flash: €0.40
    ollama      :  €0.00 (   0 tokens)

  Budget Remaining: €84.30

⚙️ AANBEVELINGEN:
  ✅ RAM usage healthy
  ℹ️  Swap usage moderate
  ✅ Disk space healthy

============================================================
```

## Implementatie Details

### Module: `lib/token_telemetry.py`

Centrale TokenTelemetry klasse:

```python
from lib.token_telemetry import TokenTelemetry

# Initialiseer
telemetry = TokenTelemetry()

# Get monthly stats
stats = telemetry.get_monthly_stats(year=2026, month=2)
# Returns: {
#   "period": "2026-02",
#   "total_tokens": 125450,
#   "total_cost_eur": 15.70,
#   "by_provider": {...},
#   "by_model": {...},
#   "by_project": {...},
#   "budget_remaining_eur": 84.30
# }

# Get daily trend
trend = telemetry.get_daily_trend(days=7)

# Format as report
report = telemetry.format_report(stats)
print(report)
```

### Data Source

Token-telemetry wordt ingelezen uit:
```
/Users/bonzen/.openclaw/skills/software-architect/token_usage.db
```

Deze SQLite database bevat:
- `model_calls` — Elke API call (timestamp, model, tokens, cost)
- `projects` — Project summaries
- `budget_tracking` — Monthly budget tracking

### Kostenstructuur

Kosten worden berekend per provider/model:

```python
PROVIDER_COSTS = {
    "anthropic": {
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},  # USD/M tokens
        "claude-3-opus-20250219": {"input": 15.0, "output": 75.0},
        "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
    },
    "openai": {
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    },
    # ... meer providers
}
```

## Usage

### Direct Script Run

```bash
# Generate report immediately
python3 scripts/server_status.py --now

# Verbose output
python3 scripts/server_status.py --now --verbose

# JSON output
python3 scripts/server_status.py --now --format json
```

### In Code

```python
from lib.metrics_collector import MetricsCollector
from lib.token_telemetry import TokenTelemetry

# Metrics
collector = MetricsCollector()
metrics = collector.collect()

# Tokens
telemetry = TokenTelemetry()
tokens = telemetry.get_monthly_stats()

# Report
report = generate_report(metrics, tokens)
print(report)
```

## Files Toegevoegd/Gewijzigd

### Nieuwe Files
- `lib/token_telemetry.py` — Token tracking module (300+ lines, fully documented)
- `lib/metrics_collector.py` — System metrics collection (250+ lines, fully documented)
- `scripts/server_status.py` — Main orchestrator script (200+ lines, fully documented)
- `config/server_status.json` — Configuration template
- `requirements.txt` — Python dependencies

### Documentatie
- Alle functies hebben Nederlandse docstrings
- Alle functies hebben inline comments
- Type hints overal
- Uitzonderingsafhandeling

## Testing

```bash
# Test token telemetry
cd /tmp/oc-server-status-dev
python3 lib/token_telemetry.py

# Test metrics collection
python3 lib/metrics_collector.py

# Test full report
python3 scripts/server_status.py --now
```

## Integratie met Telegram

Status-reports worden automatisch naar Telegram gestuurd:
- Elke 6 uur via LaunchAgent
- Onmiddellijk bij kritieke RAM thresholds
- Via message queue system voor betrouwbare delivery

## Budget Control

Monthly budget tracking:
```json
{
  "budget": {
    "monthly_limit_eur": 100,
    "alert_threshold_percent": 75
  }
}
```

Alert stuurt een Telegram bericht als 75% van budget gebruikt is.

## Performance

- Metrics collection: <2 seconds
- Token query: <1 second (SQLite indexed)
- Report generation: <1 second
- Total: ~5 seconds per report

## Privacy & Security

- Database bevat geen API keys (alleen costs)
- Reports kunnen veilig gedeeld worden
- No external API calls voor telemetry (local SQLite)
- .env bevat geen secrets
