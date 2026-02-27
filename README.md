# Server Status — OpenClaw Skill

**Gedetailleerde server health monitoring met autonoom rapportage.**

Verzamelt RAM, CPU, Ollama, ChromaDB, API-kosten metrics en genereert intelligent Nederlandse analyses. Real-time Telegram alerts bij issues.

---

## 🎯 Wat doet Server Status?

Server Status is een **comprehensive health monitoring systeem** dat:

- **Metric Collection** — RAM, CPU, Swap, Disk, Temperature, Ollama, ChromaDB, API costs
- **Analysis** — Mistral analyzeert metrics in context
- **Rapportage** — Genereer 100-word Dutch summaries + knelpunten
- **Automated Alerts** — Every 6 hours OR immediately on critical thresholds
- **Cost Tracking** — Integreert API-spend data
- **Message Queueing** — Reliable Telegram delivery via queue

### 🔄 Monitoring Cycle

```
Every 6 hours (+ critical triggers):
    ↓
Collect metrics (psutil, system_profiler, Ollama, ChromaDB)
    ↓
Aggregate JSON
    ↓
Mistral analysis (local, no cloud API)
    ↓
Generate Dutch report (max 100 words)
    ↓
Queue to Telegram message queue
    ↓
Heartbeat processor sends Telegram
    ↓
Bob receives report + metrics
```

---

## 📦 Afhankelijkheden

### Systeemvereisten
- **Python:** 3.8+
- **macOS:** system_profiler (for CPU/Temp)
- **Ollama:** Running (optional, for model metrics)
- **ChromaDB:** Path to database (optional)

### Python Dependencies

```
psutil>=5.9.0                 # System metrics
requests>=2.28.0              # Ollama API
python-dotenv>=0.20.0         # .env loading
pyyaml>=6.0                   # Config parsing
```

### External Services (optional)
- Telegram bot (for alerts)
- OpenAI/Gemini APIs (for cost tracking)

---

## ⚡ Quickstart

### 1. Installatie

```bash
# Clone repository
git clone https://github.com/bonzen-nl/oc-server-status
cd oc-server-status

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Dependencies
pip install -r requirements.txt
```

### 2. Configuratie

```bash
# Copy template
cp .env.example .env

# Instellingen:
# TELEGRAM_CHAT_ID=your_chat_id
# OLLAMA_BASE_URL=http://127.0.0.1:11434
# CHROMADB_PATH=/path/to/chromadb
# REPORT_INTERVAL_HOURS=6
```

### 3. Setup LaunchAgent (Auto-start macOS)

```bash
# One-time setup
python3 scripts/install_launchagent.py

# Verify
launchctl list | grep server-status

# View logs
tail -f /tmp/server_status.log
```

### 4. Test Report

```bash
# Generate report immediately (don't wait 6 hours)
python3 scripts/server_status.py --now

# Output: Full report with all metrics
```

---

## 🚀 Gebruik

### Manual Reports

```bash
# Immediate status report
python3 scripts/server_status.py --now

# Verbose output (with all details)
python3 scripts/server_status.py --now --verbose

# JSON format (for parsing)
python3 scripts/server_status.py --now --format json > /tmp/status.json
```

### Automatic Monitoring

Once LaunchAgent installed, runs automatically:

```bash
# Check if running
ps aux | grep server_status

# View latest report logs
tail -20 /tmp/server_status.log
```

### Report Content Example

```
📊 Server Status — 2026-02-27 22:00 CET

System Health: ⚠️ CAUTION
RAM: 72.5% (7.9GB / 10.9GB) — Approaching threshold
CPU: Load 2.3 (4 cores) — Normal
Swap: 58.2% (4.1GB / 7.0GB) — Healthy

Ollama Models: 2 active
  • mistral-small3.1:24b (5.2GB)
  • nomic-embed-text (1.3GB)

ChromaDB: 99 documents indexed
  • Size: 2.5MB
  • Last access: 2m ago

API Costs (Month):
  • Claude: €12.50 (3,200 tokens)
  • Gemini: €3.20 (estimated)
  • Total: €15.70 / €50 budget

⚠️ Knelpunten:
- RAM approaching 75% threshold
- Recommend: Close Safari/Chrome to free 2-3GB
- Consider: Unload Mistral if not in use

✅ System Status: OPERATIONAL
```

---

## 🏗️ Projectstructuur

```
oc-server-status/
├── SKILL.md                          # Skill documentatie
├── README.md                         # Dit bestand
├── requirements.txt                  # Python dependencies
├── .env.example                      # Configuration template
├── .gitignore                        # Git security
├── LICENSE                           # MIT
├── config/
│   └── server_status.json            # Report settings
├── scripts/
│   ├── server_status.py              # Main monitor
│   ├── metrics_collector.py          # System metrics
│   ├── install_launchagent.py        # macOS setup
│   └── cost_tracker.py               # API costs
├── lib/
│   ├── analyzer.py                   # Mistral analysis
│   ├── reporter.py                   # Report generation
│   ├── notifier.py                   # Telegram queue
│   └── metrics.py                    # Collection logic
└── .venv/                            # Virtual environment
```

---

## 📊 Collected Metrics

### System Metrics
- **RAM:** Total, used, available (GB + %)
- **Swap:** Total, used (GB + %)
- **CPU:** Load averages (1min, 5min, 15min)
- **Disk:** Free space per volume
- **Temperature:** M-chip temperature (if available)

### Service Metrics
- **Ollama:** Running models, tokens/sec, memory usage
- **ChromaDB:** Document count, database size
- **System Load:** CPU percentage, process count

### Cost Metrics
- **Claude (Anthropic):** Monthly spend + tokens
- **Gemini (Google):** Estimated spend
- **OpenAI:** If configured
- **Total:** Budget vs. spent

---

## 🔐 Veiligheid

### Environment Variables
- TELEGRAM_CHAT_ID — Safely stored in .env
- API keys (optional) — Never logged
- Metrics — Contain no sensitive data

### Data Retention
- Reports queued in `/tmp/openclaw_messages/`
- Processed & deleted after send
- Logs in `/tmp/server_status.log` (safe to share)

---

## 🧪 Testing

### Unit Tests

```bash
# Test metrics collection
python3 -m pytest tests/test_metrics.py -v

# Test report generation
python3 -m pytest tests/test_reporter.py

# Test message queue
python3 -m pytest tests/test_notifier.py
```

### Manual Tests

```bash
# Dry-run (show report, don't send)
python3 scripts/server_status.py --now --dry-run

# Test Telegram connectivity
python3 scripts/test_telegram.py
```

---

## 🐛 Troubleshooting

### LaunchAgent Not Running
```bash
# Check status
launchctl list | grep server-status

# Restart service
launchctl stop nl.openclaw.server-status
launchctl start nl.openclaw.server-status

# Debug
log stream --predicate 'process == "server_status"'
```

### Missing Metrics
- Ollama not running? → Install via `brew install ollama`
- ChromaDB path wrong? → Check in .env
- Telegram failing? → Verify bot token

### Reports Not Sending
- Check message queue: `ls -la /tmp/openclaw_messages/`
- Verify Telegram chat ID in .env
- Test: `python3 scripts/test_telegram.py`

---

## 🔗 Sub-Projecten & Integraties

Server Status is onderdeel van het **OpenClaw Skills Ecosystem**:

### Master Hub
- **[oc-overzicht](https://github.com/bonzen-nl/oc-overzicht)** — Central index

### Gerelateerde Skills
- **[oc-software-architect](https://github.com/bonzen-nl/oc-software-architect)** — Receives cost metrics
- **[oc-ram-guardian](https://github.com/bonzen-nl/oc-ram-guardian)** — Complementary monitoring
- **[oc-openclaw-expert](https://github.com/bonzen-nl/oc-openclaw-expert)** — Monitored service
- **[oc-github-manager](https://github.com/bonzen-nl/oc-github-manager)** — Can log issues

### Integration Points

**Software-Architect consults status:**
```python
status = architect.get_system_status()
if status['ram_percent'] > 80:
    task.defer()  # Wait for system to stabilize
```

**GitHub Manager logs critical events:**
```python
if status['critical_alert']:
    github_mgr.create_issue(
        title="🚨 Critical system event",
        description=status['report']
    )
```

---

## 📈 Performance Metrics

- **Collection overhead:** ~2-3% CPU
- **Analysis (Mistral):** ~7-8 sec, local only
- **Report generation:** ~1 sec
- **Total cycle:** <15 seconds
- **Memory footprint:** ~50MB

---

## 📝 Licentie

MIT © 2026 Bonzen

---

## 📬 Ondersteuning

- **Issues:** [oc-server-status/issues](https://github.com/bonzen-nl/oc-server-status/issues)
- **Integration:** Zie [oc-software-architect](https://github.com/bonzen-nl/oc-software-architect)

---

**Onderdeel van:** [OpenClaw Skills Suite](https://github.com/bonzen-nl/oc-overzicht)

---

## 💰 Token Telemetry Integration (v1.1.0)

**NEW:** Volledige token-tracking en cost-analyse in status-reports!

OpenClaw Server Status bevat nu gedetailleerde token-verbruik analytics. Elke status-rapport toont:

### Token Overview
- Totaal tokens (input + output)
- Totaal kosten (EUR)
- Breakdown per aanbieder (Anthropic, OpenAI, Gemini, Ollama)
- Per-model kostening
- Per-project tracking
- Monthly budget remaining

### Module Details

**`lib/token_telemetry.py`** — Token tracking engine
- Reads from software-architect's token_usage.db
- Calculates costs per provider/model
- Supports monthly, daily, project-level reporting
- Budget alerts & tracking
- Full Dutch documentation + inline comments

**`lib/metrics_collector.py`** — System metrics collector
- RAM, CPU, Disk, Temperature monitoring
- Ollama service metrics
- ChromaDB statistics
- Complete with docstrings & type hints

**`scripts/server_status.py`** — Main orchestrator
- Combines metrics + token telemetry
- Generates unified Dutch report
- Supports text/JSON output
- CLI interface (--now, --verbose, --format)

### Example Output

```
💰 TOKEN TELEMETRIE (2026-02):
  Totaal Tokens:        125,450
  Totaal Kosten:        €15.70

  Per aanbieder:
    anthropic   : €12.50 (  95,000 tokens)
      • claude-3-5-sonnet: €12.50
    openai      :  €2.80 (  23,450 tokens)
      • gpt-4o-mini: €2.80
    gemini      :  €0.40 (   7,000 tokens)
    ollama      :  €0.00 (   0 tokens)

  Budget Remaining: €84.30
```

### Usage

```bash
# Generate full report with token telemetry
python3 scripts/server_status.py --now

# JSON output
python3 scripts/server_status.py --now --format json

# Verbose details
python3 scripts/server_status.py --now --verbose
```

### Files Added
- `lib/token_telemetry.py` — Token analytics (350+ lines, fully documented)
- `lib/metrics_collector.py` — System metrics (280+ lines, fully documented)
- `scripts/server_status.py` — Main script (220+ lines, fully documented)
- `config/server_status.json` — Configuration
- `requirements.txt` — Dependencies
- `README_TOKEN_TELEMETRY.md` — Integration details

### Testing
All modules have been tested and verified:
✅ Metrics collection
✅ Token database queries
✅ Report generation
✅ Full server status with token telemetry

### Documentatie
- Alle Python modules: Nederlandse docstrings + inline comments
- Type hints op alle functies
- Exception handling voor robustness
- Complete integration documentation

See `README_TOKEN_TELEMETRY.md` for detailed technical documentation.

