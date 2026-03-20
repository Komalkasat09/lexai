# LexAI Database Build - Quick Start Guide

## ⚡ FASTEST PATH TO PUBLICATION-READY DATABASE

### Step 1: Install Dependencies (5 minutes)

```bash
cd /Users/komalkasat09/Desktop/legal-website/backend/data_pipeline

# Install Python packages
pip install -r data_pipeline_requirements.txt

# Install Playwright browser (CRITICAL - don't skip!)
playwright install chromium
```

### Step 2: Verify Environment (1 minute)

```bash
# Check that GROQ_API_KEY is set in ../.env
cat ../.env | grep GROQ_API_KEY

# Should show:
# GROQ_API_KEY=gsk_...

# If not set, add it:
echo "GROQ_API_KEY=your_key_here" >> ../.env
```

### Step 3: Run Complete Database Build (3-4 hours)

```bash
python run_database_build.py
```

**What this does:**
1. Seeds 50+ amendments (30 seconds)
2. Seeds 30+ overrulings (30 seconds)  
3. Scrapes 20+ complete acts from India Code (2-3 hours)
4. Loads real judgments from HuggingFace + Kanoon (30-60 minutes)
5. Validates entire database

**⚠️ IMPORTANT:**
- Do NOT interrupt the process
- Keep terminal open
- Ensure stable internet connection
- The script will ask for confirmation before long steps
- You can skip bare acts if you want to test first

### Step 4: Validate Database (2 minutes)

```bash
python validate_database.py
```

**Expected output:**
```
✓ Database Structure: PASS
✓ Critical Queries: 6/6 passed
✓ No Dummy Data: PASS
✓ SmartRetriever Integration: PASS
✓ Metadata Quality: PASS

✓✓✓ DATABASE VALIDATION PASSED ✓✓✓
```

### Step 5: Run Evaluation (30 minutes)

```bash
cd ../evaluation
python run_evaluation.py
```

**Expected improvements:**
- CAR: 68-75% (up from ~58%)
- P@1: 65-75% (up from ~45%)
- Confidence: +20-25% on semantic queries

---

## 🏃‍♂️ QUICKEST TEST (Skip Bare Acts)

If you want to test the pipeline quickly without waiting 3 hours:

```bash
# Just seed amendments and overrulings (1 minute total)
python amendment_seeder.py
python overruling_seeder.py

# Then validate
python validate_database.py
```

This will pass structure validation but fail critical queries (no bare acts loaded).

Later, run bare acts separately:
```bash
python bare_acts_loader.py
```

---

## 📊 CHECK DATABASE STATUS ANYTIME

```python
import chromadb
client = chromadb.PersistentClient(path='../chroma_db')

# Check all collections
for col_name in ['bare_acts', 'case_law', 'amendments', 'overruling_map']:
    try:
        collection = client.get_collection(col_name)
        print(f"{col_name}: {collection.count():,} documents")
    except:
        print(f"{col_name}: NOT FOUND")
```

---

## 🔧 TROUBLESHOOTING

### "playwright not found"
```bash
playwright install chromium
# Or on macOS:
brew install playwright
```

### "Collection already exists"
This is normal. Scripts automatically skip already-loaded data.

### "Rate limited by Indian Kanoon"
Wait 30 minutes and retry. Scripts have 10-20s delays but sometimes need more.

### "GROQ_API_KEY not found"
```bash
export GROQ_API_KEY=your_key_here
# Or add to ../.env file
```

### Clear and rebuild everything
```bash
rm -rf ../chroma_db/
python run_database_build.py
```

---

## ✅ VALIDATION CHECKLIST

Before running paper evaluation:

- [ ] `bare_acts` collection has **500+** sections
- [ ] `bare_acts` includes IPC, BNS, CrPC, BNSS, NI Act (critical for queries)
- [ ] `amendments` collection has **50+** amendments
- [ ] `overruling_map` collection has **30+** overrulings
- [ ] `case_law` collection has **15,000+** documents (including real judgments)
- [ ] All 6 validation queries pass with >70% confidence
- [ ] No dummy/placeholder data found
- [ ] SmartRetriever integration works
- [ ] Backups saved in `data/backup/`

If all ✅, you're ready for publication-quality evaluation!

---

## 📁 OUTPUT FILES

After complete build, you'll have:

```
data/backup/
├── amendments/
│   └── all_amendments.json              ✅ 50+ amendments
├── overrulings/
│   └── all_overrulings.json             ✅ 30+ overrulings
├── bare_acts/
│   ├── IPC.json                         ✅ Indian Penal Code
│   ├── BNS.json                         ✅ Bharatiya Nyaya Sanhita
│   ├── NIA.json                         ✅ Negotiable Instruments
│   └── ... (20+ more)
├── landmarks/
│   ├── Kesavananda_Bharati.json         ✅ Basic structure
│   ├── Maneka_Gandhi.json               ✅ Article 21
│   └── ... (30+ landmark cases)
├── database_build_report.json           ✅ Build summary
└── validation_report.json               ✅ Validation results
```

All JSON files can be reviewed/verified by your lawyer cousin!

---

## 🎯 NEXT STEPS AFTER DATABASE BUILD

1. **Lawyer Verification**
   ```bash
   # Share with lawyer:
   # - data/backup/amendments/all_amendments.json
   # - data/backup/overrulings/all_overrulings.json
   ```

2. **Run Full Evaluation**
   ```bash
   cd ../evaluation
   python run_evaluation.py
   ```

3. **Analyze Results**
   ```bash
   # Check outputs in evaluation/outputs/
   # - Metrics tables (LaTeX + Markdown)
   # - Visualizations (PNG)
   # - Sample responses
   ```

4. **Prepare Paper**
   - Update methodology section with database details
   - Add ablation study (with vs without hybrid retrieval)
   - Include database statistics table
   - Show improvement metrics

---

## ⏱️ TIME ESTIMATES

| Task | Time | Can Skip? |
|------|------|-----------|
| Install dependencies | 5 min | ❌ No |
| Seed amendments | 30 sec | ❌ No |
| Seed overrulings | 30 sec | ❌ No |
| Load bare acts | 2-3 hours | ✅ Yes (test first) |
| Load judgments | 30-60 min | ✅ Yes (test first) |
| Validate database | 2 min | ❌ No |
| **TOTAL** | **3-4 hours** | |

---

## 💡 PRO TIPS

1. **Run overnight**: Start `run_database_build.py` before bed, complete build ready in morning

2. **Test first**: Run just amendments + overrulings first (1 min), validate they work, then do full build

3. **Monitor progress**: Scripts print detailed progress. If stuck for >10 minutes, check internet connection

4. **Save backups**: All backups auto-saved to `data/backup/`. Commit to Git!

5. **Parallel loading**: Can run `judgment_loader.py` in separate terminal while `bare_acts_loader.py` runs

6. **Resume failed builds**: Scripts skip already-loaded collections automatically

---

## 🚀 READY TO START?

```bash
# The only command you need:
python run_database_build.py
```

Then grab coffee ☕ and let it run!

---

**Questions?** Check the README.md for detailed documentation.
