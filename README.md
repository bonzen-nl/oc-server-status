# oc-server-status

**Unified Server & Token Monitoring for OpenClaw**

Realtime monitoring van server gezondheid, token verbruik (alle providers), en kostenanalyse. Alle informatie in ÉÉN geïntegreerd rapport.

## Features

### 📊 Server Metrics
- **RAM/Swap:** Realtime gebruik in GB en percentages
- **CPU:** Load average (1/5/15 min), core count
- **Disk:** Free space, total, percentage used
- **Temperature:** CPU temp (macOS via system_profiler)
- **Services:** Ollama models count/memory, ChromaDB doc count

### 💰 Token Telemetry (Unified)
- **Alle providers:** Anthropic, OpenAI, Google Gemini, Ollama
- **Per provider:** Totaal tokens, kosten (EUR), aantal calls
- **Top models:** Top 10 modellen per kosten (alle providers)
- **Budget tracking:** Monthly limits, spent/remaining

### 📈 Token Timeline Analysis
- **Dagelijks:** Per-model breakdown (vandaag, gisteren, eergisteren)
- **Wekelijks:** Trends per week per model
- **Maandelijks:** Vergelijking vorige maanden per model
- **Efficiency:** Kosten/token, tokens/call gemiddeld

### ⚙️ Intelligent Recommendations
- RAM pressure detection & actions
- Swap usage warnings
- Budget burn rate alerts
- Service availability checks

## Installation

```bash
# Clone the repo
git clone https://github.com/bonzen-nl/oc-server-status.git
cd oc-server-status

# Setup Python venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

```bash
# Copy example config
cp config/server_status.json.example config/server_status.json

# Edit with your settings
nano config/server_status.json
```

**Configuration keys:**
- `monitoring.report_interval_hours` — Interval tussen rapporten
- `monitoring.critical_ram_threshold_percent` — Critical RAM threshold
- `telegram.enabled` — Telegram notifications aan/uit
- `telegram.chat_id` — Telegram chat ID voor alerts
- `chromadb_path` — Path naar ChromaDB index
- `budget.monthly_limit_eur` — Monthly token budget (EUR)
- `ollama_base_url` — Ollama API endpoint
- `openai_api_key` — OpenAI API key (optioneel)
- `anthropic_api_key` — Anthropic API key (optioneel)
- `google_api_key` — Google Gemini API key (optioneel)

## Usage

### Generate Report (Text)
```bash
python3 scripts/server_status.py --now
```

Output:
```
📊 OPENСLAW SERVER STATUS — 2026-02-27 23:05 CET
================================================================================

🟢 HEALTHY
────────────────────────────────────────────────
RAM:  25.6% (  5.5GB /  24.0GB)
CPU:    1.87 load (4 cores)
Swap:   68.0% (  2.7GB /   4.0GB)
Disk:    6.9% (155.4GB free)

SERVICES:
  Ollama:    2 models (4.0GB)
  ChromaDB:  99 docs (2.0MB)

================================================================================
💰 TOKEN TELEMETRIE — 2026-02
================================================================================

📊 TOTAAL:
  Tokens:                130
  Kosten:    €          0.00

🔌 PER AANBIEDER (Anthropic, OpenAI, Google, Ollama):
  ollama          | €    0.00 |        130 tokens

🏆 TOP MODELLEN (alle providers):
   1. ollama      /mistral                        €    0.00

💳 BUDGET:
  Monthly:   €    100.00
  Spent:     €      0.00  (  0.0%)
  Remaining: €    100.00
  ✅ Gezond

======================================================================
📈 TOKEN VERBRUIK PER MODEL — Dag / Week / Maand
======================================================================

📅 DAGELIJKS (meest recent):

  2026-02-27:
    ollama/mistral                      |      130 tokens | €0.00

📊 WEKELIJKS:

  Week 2026-W08:
    ollama/mistral                      |      130 tokens | €0.00 (1d)

📈 MAANDELIJKS (trend):

  ollama/mistral:
    2026-02:      130 tokens | €0.00

======================================================================

================================================================================
⚙️  AANBEVELINGEN:
  ✅ RAM gezond

================================================================================
```

### Generate Report (JSON)
```bash
python3 scripts/server_status.py --now --format json
```

Output: Complete JSON with metrics, tokens, timeline for automation.

### Scheduled Reports (LaunchAgent / Cron)
```bash
# Every 6 hours (or custom interval)
# Writes to /tmp/openclaw_messages/ for heartbeat delivery
python3 /path/to/oc-server-status/scripts/server_status.py --now
```

## Project Structure

```
oc-server-status/
├── README.md                           # Dit bestand
├── LICENSE                             # MIT
├── requirements.txt                    # Python dependencies
│
├── config/
│   └── server_status.json.example      # Configuration template
│
├── scripts/
│   └── server_status.py                # Main unified report generator
│
└── lib/
    ├── metrics_collector.py            # System metrics (RAM, CPU, Disk, etc)
    ├── token_telemetry.py              # Token tracking + timeline analysis
    └── __init__.py
```

## Integrations

### Telegram Notifications
Automatic alerts when:
- RAM > 90% (critical)
- Swap > 85% (soft cleanup trigger)
- Monthly budget > 75% spent
- Server errors detected

### Ollama Integration
- Auto-detect running models
- Memory tracking per model
- Model unload on RAM pressure

### ChromaDB Integration
- Document count monitoring
- Database size tracking
- Integrity checks

### Multi-Provider Token Tracking
Automatically aggregates token usage from:
- **Anthropic:** Claude models (Haiku, Sonnet, etc)
- **OpenAI:** GPT models
- **Google:** Gemini models
- **Ollama:** Local models (Mistral, Llama, etc)

## Architecture

### metrics_collector.py
Collects system metrics via psutil & macOS system_profiler.

**Functions:**
- `collect()` — Gather all metrics snapshot
- Returns: Dict with ram, swap, cpu, disk, temperature, ollama, chromadb

### token_telemetry.py

#### TokenTelemetry class
Primary token tracking & cost analysis.

**Methods:**
- `get_monthly_stats()` — Maandelijkse token stats (totaal, per provider, per model, budget)
- `get_provider_models()` — Lijst modellen per provider
- `calculate_cost()` — Cost calculation per model

#### TokenTimelineAnalyzer class
Per-model timeline breakdown.

**Methods:**
- `get_daily_model_tokens(year, month)` — Dagelijks per model
- `get_weekly_model_tokens(year, month)` — Wekelijks per model
- `get_monthly_model_tokens(months_back)` — Maandelijks trend

**Helper:**
- `format_token_timeline_section()` — Geformateerde output voor rapport

### server_status.py
Main orchestrator. Combineert alle data in unified rapport.

**Functions:**
- `generate_unified_report()` — Samenstelt server + tokens + timeline
- `main()` — CLI entry point

## Monitoring Strategy

### Token Budget
- Default: €100/month per provider
- Configurable per provider/model
- Forecasting: extrapolatie naar maand-einde

### RAM Management
- Warning: 70% RAM used
- Critical: 90% RAM used
- Swap: 80% warns, 90% critical alert

### System Health
- Status indicator: HEALTHY / CAUTION / CRITICAL
- Color-coded output (emojis)
- Actionable recommendations

## Data Sources

### Metrics
- `psutil.virtual_memory()` — RAM/Swap
- `psutil.cpu_times()` — CPU load
- `psutil.disk_usage()` — Disk space
- `system_profiler` — Temperature (macOS)
- Ollama JSON-RPC API — Model info
- ChromaDB direct query — Doc counts

### Tokens
- Local database: `token_usage.db` (software-architect skill)
- SQL queries for aggregation:
  - `model_calls` table (timestamp, model, provider, tokens, cost)
  - Group by date/week/month for timeline

## Security

- ✅ API keys in `.env` (not in git)
- ✅ Sensitive data masked in Telegram messages
- ✅ Local computation only (no external APIs for metrics)
- ✅ Database encryption ready (future)

## Troubleshooting

### "Database not found"
```bash
# Check token_usage.db location
ls -la /Users/bonzen/.openclaw/skills/software-architect/token_usage.db

# Update db_path in scripts/server_status.py if needed
```

### "Ollama connection error"
```bash
# Check Ollama is running
ollama serve

# Check endpoint in config
curl http://127.0.0.1:11434/api/tags
```

### "Telegram not sending"
```bash
# Verify chat ID in config
# Check message queue: ls -la /tmp/openclaw_messages/

# Send manual test
python3 scripts/server_status.py --now
```

### "Memory calculation off"
```bash
# Verify metrics collection
python3 -c "from lib.metrics_collector import MetricsCollector; m = MetricsCollector(); print(m.collect()['ram'])"
```

## Contributing

Issues & PRs welcome! Please:
1. Keep code in Dutch (docstrings, comments)
2. Type hints on all functions
3. Error handling comprehensive
4. Test before push

## License

MIT — See LICENSE file

## Support

- **Docs:** https://docs.openclaw.ai/
- **Issues:** https://github.com/bonzen-nl/oc-server-status/issues
- **Discord:** https://discord.com/invite/clawd

---

**Version:** 1.3.0 (Unified Report)  
**Last Updated:** 2026-02-27  
**Author:** Mavy (OpenClaw Agent)
