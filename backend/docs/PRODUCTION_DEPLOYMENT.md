# Production Deployment Guide
## Legal Research Assistant - Real-Time Scraping System

This guide covers deploying the legal research assistant with real-time document scraping.

---

## 📋 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LEGAL RESEARCH SYSTEM                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   FastAPI    │◄───┤  Legal LLM   │◄───┤   ChromaDB   │  │
│  │  REST API    │    │    (Groq)    │    │   Database   │  │
│  └──────────────┘    └──────────────┘    └───────▲──────┘  │
│         ▲                                          │          │
│         │                                          │          │
│         │            ┌──────────────┐             │          │
│         └────────────┤   Frontend   │             │          │
│                      │  (Next.js)   │             │          │
│                      └──────────────┘             │          │
│                                                    │          │
│                      ┌──────────────┐             │          │
│                      │  Scheduler   │─────────────┘          │
│                      │ (APScheduler)│                        │
│                      └──────▲───────┘                        │
│                             │                                │
│                      ┌──────┴───────┐                        │
│                      │   Scrapers   │                        │
│                      │  Playwright  │                        │
│                      └──────────────┘                        │
│                             │                                │
│         ┌───────────────────┼───────────────────┐           │
│         │                   │                   │            │
│   ┌─────▼────┐       ┌─────▼────┐       ┌─────▼────┐      │
│   │ Indian   │       │ Supreme  │       │ E-Courts │       │
│   │  Kanoon  │       │  Court   │       │ Services │       │
│   └──────────┘       └──────────┘       └──────────┘       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# API Keys
GROQ_API_KEY=your_groq_api_key_here

# Database
CHROMA_PERSIST_DIR=./legal_research_db

# Scraping (Optional - for production)
USE_PROXIES=false
PROXY_LIST=

# CAPTCHA (Optional)
CAPTCHA_API_KEY=
```

### 3. Start the System

```bash
# Terminal 1: Start API Server
python start_api.py

# Terminal 2: Start Scheduler (for automated scraping)
python data_pipeline/scheduler.py --mode start
```

### 4. Test Real-Time Scraping

```bash
# Test live scraping (fetches real documents from IndianKanoon)
python demo_realtime_scraping.py --mode scrape

# Test scheduler configuration
python demo_realtime_scraping.py --mode scheduler
```

---

## 🔧 Configuration

### Proxy Configuration (Production Recommended)

For production deployment, use rotating proxies to avoid rate limits:

**Option 1: Residential Proxies (Recommended)**
```bash
# .env
USE_PROXIES=true
PROXY_LIST=http://user:pass@proxy1.residential-provider.com:8080,http://user:pass@proxy2.residential-provider.com:8080
```

Recommended providers:
- Bright Data: https://brightdata.com
- Smartproxy: https://smartproxy.com
- Oxylabs: https://oxylabs.io

**Option 2: Free Proxy Lists (Not Recommended for Production)**
```bash
# Update proxy list periodically from free sources
# Quality and reliability are low
```

### CAPTCHA Solving (Optional)

For E-Courts scraping, which has CAPTCHA protection:

```bash
# .env
CAPTCHA_API_KEY=your_2captcha_api_key
```

Get API key from: https://2captcha.com

### Scraping Schedule

Configure in `.env`:

```bash
# Daily scraping at 2:00 AM
NIGHTLY_SCRAPE_TIME=02:00

# Weekly full update (Sunday at 3:00 AM)
WEEKLY_SCRAPE_DAY=sunday
WEEKLY_SCRAPE_TIME=03:00

# Monthly archival (1st of month at 4:00 AM)
MONTHLY_SCRAPE_DAY=1
MONTHLY_SCRAPE_TIME=04:00

# Scraping limits
DAILY_SCRAPE_PAGES=30
WEEKLY_SCRAPE_PAGES=100
MONTHLY_SCRAPE_PAGES=200
```

---

## 📊 Scraper Features

### Real-Time Document Scraping

#### IndianKanoon.org (Primary Source)
- ✅ **Operational**: Live scraping configured
- 📄 **Content**: Supreme Court, High Courts, Tribunals
- 🔄 **Format**: HTML (direct extraction)
- ⚡ **Speed**: ~3-5 seconds per document
- 🎯 **Quality**: High (cleaned and validated)

#### Supreme Court of India (Secondary)
- 🔨 **Status**: Requires PDF extraction
- 📄 **Content**: Official SC judgments
- 🔄 **Format**: PDF files
- ⚡ **Implementation**: PyMuPDF configured
- 📝 **Note**: Requires API access or PDF download links

#### E-Courts Services (Tertiary)
- 🔐 **Status**: Requires CAPTCHA solving
- 📄 **Content**: District/High Court orders
- 🔄 **Format**: HTML/PDF
- ⚡ **Implementation**: 2captcha integration ready
- 📝 **Note**: Best to use IndianKanoon as aggregator

### Automated Features

1. **Duplicate Detection**: Semantic similarity matching
2. **Data Cleaning**: Removes formatting, normalizes text
3. **Metadata Extraction**:
   - Section numbers (IPC, CrPC, BNS, BNSS)
   - Act names
   - Court information
   - Judges names
   - Citations
4. **Error Handling**: Automatic retries with exponential backoff
5. **State Management**: Tracks scraping progress and failures

---

## 📅 Scheduler Usage

### Start Scheduler as Background Service

```bash
# Linux/Mac
nohup python data_pipeline/scheduler.py --mode start > scheduler_output.log 2>&1 &

# Check if running
ps aux | grep scheduler.py

# Stop scheduler
pkill -f scheduler.py
```

### Run Jobs Manually

```bash
# Run daily scrape immediately
python data_pipeline/scheduler.py --mode run-daily

# Run weekly update
python data_pipeline/scheduler.py --mode run-weekly

# Run monthly archival
python data_pipeline/scheduler.py --mode run-monthly

# Check scheduler status
python data_pipeline/scheduler.py --mode status
```

### Monitor Scheduler

```bash
# View logs in real-time
tail -f scheduler.log

# View scraping statistics
cat scraper_stats.json | python -m json.tool
```

---

## 🔍 Monitoring & Maintenance

### Health Checks

The scheduler runs automatic health checks every 30 minutes:
- Database connectivity
- Collection counts
- Recent scraping success rate

### Log Management

Logs are written to:
- `scheduler.log` - Scheduler operations
- `scraper_stats.json` - Scraping statistics

Rotate logs periodically:
```bash
# Keep last 7 days
find . -name "*.log" -mtime +7 -delete
```

### Database Management

```bash
# Check database size
du -sh legal_research_db/

# Get collection counts
python -c "
from database.chroma_setup import LegalResearchDB
db = LegalResearchDB(persist_directory='./legal_research_db')
print(f'Cases: {db.case_law_collection.count()}')
print(f'Acts: {db.bare_acts_collection.count()}')
"
```

---

## 🚀 Production Deployment

### Docker Deployment (Recommended)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Start both API and scheduler
CMD ["sh", "-c", "python start_api.py & python data_pipeline/scheduler.py --mode start"]
```

### Systemd Service (Linux)

```ini
# /etc/systemd/system/legal-research-api.service
[Unit]
Description=Legal Research API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/legal-research/backend
Environment="PATH=/opt/legal-research/backend/venv/bin"
ExecStart=/opt/legal-research/backend/venv/bin/python start_api.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/legal-research-scheduler.service
[Unit]
Description=Legal Research Scheduler
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/legal-research/backend
Environment="PATH=/opt/legal-research/backend/venv/bin"
ExecStart=/opt/legal-research/backend/venv/bin/python data_pipeline/scheduler.py --mode start
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable legal-research-api
sudo systemctl enable legal-research-scheduler
sudo systemctl start legal-research-api
sudo systemctl start legal-research-scheduler
```

---

## 🔐 Security Considerations

1. **API Keys**: Never commit `.env` to version control
2. **Proxies**: Use authenticated proxies for security
3. **Rate Limiting**: Respect website robots.txt and rate limits
4. **CAPTCHA**: Only use CAPTCHA solving for legitimate purposes
5. **Data Privacy**: Ensure compliance with data protection laws

---

## 📈 Performance Optimization

### Scraping Performance

- **Parallel Scraping**: Increase `ThreadPoolExecutor` workers in scheduler
- **Caching**: Implement Redis cache for frequently accessed documents
- **Database**: Use database on SSD for better performance

### API Performance

- **Uvicorn Workers**: Increase workers for better concurrency
  ```bash
  uvicorn api.legal_research:app --workers 4 --host 0.0.0.0 --port 8000
  ```

### Memory Management

- **Playwright**: Limit browser instances
- **ChromaDB**: Monitor memory usage with large collections
- **Log Rotation**: Prevent log files from growing indefinitely

---

## 🆘 Troubleshooting

### Scraper Issues

**Problem**: No documents scraped
- Check network connectivity
- Verify website accessibility
- Enable debug logging
- Try different search queries

**Problem**: Rate limiting/blocking
- Enable proxy rotation
- Increase delay between requests
- Use residential proxies

**Problem**: PDF extraction failing
- Verify PyMuPDF installation
- Check PDF file integrity
- Ensure sufficient disk space

### Scheduler Issues

**Problem**: Jobs not running
- Check scheduler logs
- Verify cron expressions
- Check system timezone
- Restart scheduler

**Problem**: Database errors
- Check ChromaDB permissions
- Verify database path
- Check disk space

---

## 📚 Additional Resources

- IndianKanoon API: Contact support@indiankanoon.org for API access
- Supreme Court Website: https://main.sci.gov.in
- E-Courts Services: https://services.ecourts.gov.in
- APScheduler Docs: https://apscheduler.readthedocs.io
- Playwright Docs: https://playwright.dev/python/

---

## ✅ Checklist for Production

- [ ] API keys configured in `.env`
- [ ] Proxy rotation enabled (if using)
- [ ] CAPTCHA solving configured (if needed)
- [ ] Scheduler running as system service
- [ ] Monitoring and logging configured
- [ ] Database backups scheduled
- [ ] Health checks operational
- [ ] Rate limits respected
- [ ] Legal compliance verified
- [ ] Documentation updated

---

**Last Updated**: February 2026  
**Version**: 1.0.0  
**Support**: Contact system administrator
