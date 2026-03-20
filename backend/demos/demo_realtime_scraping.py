"""
Real-Time Legal Document Scraping System
=========================================

This script demonstrates the complete real-time scraping pipeline:
1. Scraping live legal documents from IndianKanoon
2. Extracting and cleaning document content
3. Storing in ChromaDB with proper indexing
4. Making documents immediately queryable via API

NO DUMMY DATA - All documents are scraped in real-time from actual sources.

Author: Legal Research System
"""

import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).parent))

from data_pipeline.playwright_scraper import LegalDocumentScraper, ScraperConfig
from data_pipeline.scheduler import LegalScraperScheduler


def demo_real_time_scraping():
    """Demonstrate real-time scraping with live data"""
    
    print("\n" + "="*70)
    print("🔴 REAL-TIME LEGAL DOCUMENT SCRAPING SYSTEM")
    print("="*70)
    print("\n⚠️  THIS USES REAL DATA - NO DUMMY/SAMPLE DOCUMENTS")
    print("   All documents are scraped live from IndianKanoon.org")
    print("   This may take several minutes due to respectful rate limiting\n")
    
    # Configuration
    print("📋 CONFIGURATION:")
    print("   • Source: IndianKanoon.org (Live)")
    print("   • Rate Limiting: 3-5 seconds between requests")
    print("   • Max Documents: 5 (for demo)")
    print("   • Headless Browser: Yes")
    print("   • Duplicate Detection: Enabled")
    print()
    
    input("Press ENTER to start real-time scraping... ")
    
    # Create scraper configuration
    config = ScraperConfig(
        min_delay=3.0,
        max_delay=5.0,
        max_pages_per_run=5,  # Limit for demo
        headless=True,
        timeout=60000,
        use_proxy_rotation=False,  # Disable for demo (enable for production)
        enable_pdf_extraction=True,
    )
    
    scraper = LegalDocumentScraper(
        db_path="./legal_research_db",
        config=config
    )
    
    print("\n" + "="*70)
    print("🌐 STARTING LIVE SCRAPING FROM INDIANKANOON.ORG")
    print("="*70)
    print("\n⏱️  This will take ~20-30 seconds (respectful rate limiting)...\n")
    
    # Scrape live documents
    stats = scraper.scrape_indiankanoon_only(days_back=30)
    
    print("\n" + "="*70)
    print("📊 REAL-TIME SCRAPING RESULTS")
    print("="*70)
    print(f"\n✅ Documents Scraped (Live): {stats['total_scraped']}")
    print(f"💾 Documents Stored: {stats['total_stored']}")
    print(f"⏭️  Duplicates Skipped: {stats['duplicates_skipped']}")
    print(f"❌ Errors: {stats['errors']}")
    
    if stats['total_scraped'] > 0:
        print("\n✅ SUCCESS: Real-time scraping operational!")
        print("   • Live documents fetched from IndianKanoon")
        print("   • Stored in ChromaDB with full metadata")
        print("   • Immediately available for API queries")
        print("   • Duplicate detection prevented redundancy")
    else:
        print("\n⚠️  NO NEW DOCUMENTS SCRAPED")
        print("   This could mean:")
        print("   • All recent documents already in database (high duplicate rate)")
        print("   • Network/website access issues")
        print("   • Rate limiting or anti-bot measures")
        print("\n💡 TIP: In production, enable rotating proxies to avoid blocks")
    
    print("\n" + "="*70)
    print("🔄 AUTOMATED SCHEDULING")
    print("="*70)
    print("\nTo enable fully automated daily scraping:")
    print("   python data_pipeline/scheduler.py --mode start")
    print("\nScheduled jobs:")
    print("   • Daily scrape: 2:00 AM (last 7 days)")
    print("   • Weekly update: Sunday 3:00 AM (last 30 days)")
    print("   • Monthly archival: 1st of month 4:00 AM (last 90 days)")
    
    print("\n" + "="*70)
    print("🚀 PRODUCTION DEPLOYMENT")
    print("="*70)
    print("\nFor production use:")
    print("   1. Set up rotating proxies in .env:")
    print("      USE_PROXIES=true")
    print("      PROXY_LIST=http://proxy1:port,http://proxy2:port")
    print()
    print("   2. (Optional) Configure CAPTCHA solving:")
    print("      CAPTCHA_API_KEY=your_2captcha_key")
    print()
    print("   3. Start the scheduler as a background service:")
    print("      nohup python data_pipeline/scheduler.py --mode start &")
    print()
    print("   4. Monitor logs:")
    print("      tail -f scheduler.log")
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE")
    print("="*70 + "\n")


def test_scheduler():
    """Test the scheduler configuration"""
    print("\n" + "="*70)
    print("📅 TESTING SCHEDULER CONFIGURATION")
    print("="*70)
    
    scheduler = LegalScraperScheduler(db_path="./legal_research_db")
    scheduler.start()
    
    print("\n✅ Scheduler initialized successfully")
    print("\n📋 To run a job immediately:")
    print("   python data_pipeline/scheduler.py --mode run-daily")
    print("   python data_pipeline/scheduler.py --mode run-weekly")
    print("   python data_pipeline/scheduler.py --mode run-monthly")
    
    time.sleep(2)
    scheduler.stop()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Real-Time Scraping Demo")
    parser.add_argument(
        '--mode',
        choices=['scrape', 'scheduler'],
        default='scrape',
        help='Demo mode'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'scrape':
        demo_real_time_scraping()
    else:
        test_scheduler()
