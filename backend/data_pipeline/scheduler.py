"""
Automated Scheduler for Legal Document Scraping
================================================

Schedules and manages automated scraping of legal documents:
- Nightly scraping of new judgments
- Weekly full updates
- Monthly archival scraping
- Real-time monitoring and health checks

Uses APScheduler for job management with persistence and error handling.

Author: Legal Research System
"""

import logging
import os
from datetime import datetime, time
from pathlib import Path
from typing import Optional
import json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

import sys
sys.path.append(str(Path(__file__).parent.parent))
from data_pipeline.playwright_scraper import LegalDocumentScraper, ScraperConfig
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# CONFIGURATION
# ============================================================================

class SchedulerConfig:
    """Configuration for scraping scheduler"""
    
    # Scraping schedules (cron format)
    NIGHTLY_SCRAPE_TIME = "02:00"  # 2:00 AM daily
    WEEKLY_FULL_UPDATE_DAY = "sun"  # Full update every Sunday (use3-letter abbreviation)
    WEEKLY_FULL_UPDATE_TIME = "03:00"  # 3:00 AM
    
    # Scraping parameters
    DAILY_DAYS_BACK = 7  # Look back 7 days in daily scrapes
    WEEKLY_DAYS_BACK = 30  # Look back 30 days in weekly scrapes
    MONTHLY_DAYS_BACK = 90  # Look back 90 days in monthly scrapes
    
    # Monitoring
    HEALTH_CHECK_INTERVAL_MINUTES = 30  # Health check every 30 minutes
    
    # Database
    JOB_STORE_DB = "sqlite:///legal_scheduler.db"  # Job persistence
    LOG_FILE = "scheduler.log"  # Scheduler logs
    
    # Proxy configuration (optional)
    USE_PROXIES = os.getenv("USE_PROXIES", "false").lower() == "true"
    PROXY_LIST = os.getenv("PROXY_LIST", "").split(",") if os.getenv("PROXY_LIST") else []
    
    # CAPTCHA (optional)
    CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY", None)


# ============================================================================
# SCRAPING JOBS
# ============================================================================

class ScrapingJobs:
    """Defines all scheduled scraping jobs"""
    
    def __init__(self, db_path: str = "./legal_research_db"):
        self.db_path = db_path
        self.logger = self._setup_logger()
        self.stats_file = Path("scraper_stats.json")
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for scraping jobs"""
        logger = logging.getLogger("ScrapingJobs")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # File handler
            file_handler = logging.FileHandler(SchedulerConfig.LOG_FILE)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(console_handler)
        
        return logger
    
    def _get_scraper_config(self, max_pages: int = 50) -> ScraperConfig:
        """Get scraper configuration"""
        config = ScraperConfig(
            min_delay=3.0,
            max_delay=5.0,
            max_pages_per_run=max_pages,
            headless=True,
            timeout=60000,
            use_proxy_rotation=SchedulerConfig.USE_PROXIES,
            proxies=SchedulerConfig.PROXY_LIST if SchedulerConfig.USE_PROXIES else None,
            enable_pdf_extraction=True,
            captcha_api_key=SchedulerConfig.CAPTCHA_API_KEY,
            enable_captcha_solving=bool(SchedulerConfig.CAPTCHA_API_KEY),
        )
        return config
    
    def _save_stats(self, job_name: str, stats: dict):
        """Save scraping statistics"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                all_stats = json.load(f)
        else:
            all_stats = {}
        
        if job_name not in all_stats:
            all_stats[job_name] = []
        
        stats['timestamp'] = datetime.now().isoformat()
        all_stats[job_name].append(stats)
        
        # Keep only last 30 runs per job
        all_stats[job_name] = all_stats[job_name][-30:]
        
        with open(self.stats_file, 'w') as f:
            json.dump(all_stats, f, indent=2)
    
    def daily_scrape(self):
        """
        Daily scraping job - runs every night at 2:00 AM
        Scrapes recent judgments from the past week
        """
        self.logger.info("="*70)
        self.logger.info("🌙 STARTING DAILY SCRAPE JOB")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*70)
        
        try:
            config = self._get_scraper_config(max_pages=30)  # Limit daily scraping
            scraper = LegalDocumentScraper(
                db_path=self.db_path,
                config=config
            )
            
            # Scrape recent documents
            stats = scraper.scrape_indiankanoon_only(
                days_back=SchedulerConfig.DAILY_DAYS_BACK
            )
            
            self._save_stats("daily_scrape", stats)
            
            self.logger.info(f"✅ Daily scrape completed: {stats['total_stored']} new documents")
            
        except Exception as e:
            self.logger.error(f"❌ Daily scrape failed: {e}", exc_info=True)
    
    def weekly_full_update(self):
        """
        Weekly full update - runs every Sunday at 3:00 AM
        Comprehensive scraping of the past month
        """
        self.logger.info("="*70)
        self.logger.info("📅 STARTING WEEKLY FULL UPDATE")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*70)
        
        try:
            config = self._get_scraper_config(max_pages=100)  # More pages for weekly
            scraper = LegalDocumentScraper(
                db_path=self.db_path,
                config=config
            )
            
            # Comprehensive scraping
            stats = scraper.scrape_indiankanoon_only(
                days_back=SchedulerConfig.WEEKLY_DAYS_BACK
            )
            
            self._save_stats("weekly_full_update", stats)
            
            self.logger.info(f"✅ Weekly update completed: {stats['total_stored']} new documents")
            
        except Exception as e:
            self.logger.error(f"❌ Weekly update failed: {e}", exc_info=True)
    
    def monthly_archival_scrape(self):
        """
        Monthly archival scraping - runs on 1st of every month at 4:00 AM
        Deep scraping for archival purposes
        """
        self.logger.info("="*70)
        self.logger.info("🗄️  STARTING MONTHLY ARCHIVAL SCRAPE")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*70)
        
        try:
            config = self._get_scraper_config(max_pages=200)  # Extensive for monthly
            scraper = LegalDocumentScraper(
                db_path=self.db_path,
                config=config
            )
            
            # Deep scraping
            stats = scraper.scrape_indiankanoon_only(
                days_back=SchedulerConfig.MONTHLY_DAYS_BACK
            )
            
            self._save_stats("monthly_archival_scrape", stats)
            
            self.logger.info(f"✅ Monthly archival completed: {stats['total_stored']} new documents")
            
        except Exception as e:
            self.logger.error(f"❌ Monthly archival failed: {e}", exc_info=True)
    
    def health_check(self):
        """
        Health check - runs every 30 minutes
        Monitors scraper health and database status
        """
        self.logger.debug("🏥 Running health check...")
        
        try:
            # Check database connection
            from database.chroma_setup import LegalResearchDB
            db = LegalResearchDB(persist_directory=self.db_path)
            
            # Get collection counts
            bare_acts_count = db.bare_acts_collection.count()
            case_law_count = db.case_law_collection.count()
            
            self.logger.debug(f"✓ Database healthy: {case_law_count} cases, {bare_acts_count} acts")
            
            # Check recent scraping stats
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    stats = json.load(f)
                    
                if 'daily_scrape' in stats and len(stats['daily_scrape']) > 0:
                    last_run = stats['daily_scrape'][-1]
                    self.logger.debug(f"✓ Last scrape: {last_run.get('timestamp', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"⚠️  Health check failed: {e}")


# ============================================================================
# MAIN SCHEDULER
# ============================================================================

class LegalScraperScheduler:
    """
    Main scheduler for automated legal document scraping
    
    Manages:
    - Daily scraping jobs
    - Weekly full updates
    - Monthly archival scraping
    - Health monitoring
    """
    
    def __init__(self, db_path: str = "./legal_research_db"):
        self.db_path = db_path
        self.logger = self._setup_logger()
        self.jobs = ScrapingJobs(db_path=db_path)
        self.scheduler = None
        
    def _setup_logger(self) -> logging.Logger:
        """Setup main logger"""
        logger = logging.getLogger("LegalScraperScheduler")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # File handler
            file_handler = logging.FileHandler(SchedulerConfig.LOG_FILE)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(console_handler)
        
        return logger
    
    def start(self):
        """Start the scheduler"""
        self.logger.info("="*70)
        self.logger.info("🚀 STARTING LEGAL DOCUMENT SCRAPER SCHEDULER")
        self.logger.info("="*70)
        
        # Configure job stores
        jobstores = {
            'default': SQLAlchemyJobStore(url=SchedulerConfig.JOB_STORE_DB)
        }
        
        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(max_workers=3)
        }
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults={
                'coalesce': True,  # Combine missed runs
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 3600  # 1 hour grace period
            }
        )
        
        # Add jobs
        self._add_jobs()
        
        # Start scheduler
        self.scheduler.start()
        
        self.logger.info("✅ Scheduler started successfully")
        self._print_schedule()
    
    def _add_jobs(self):
        """Add all scheduled jobs"""
        
        # Daily scrape at 2:00 AM
        hour, minute = map(int, SchedulerConfig.NIGHTLY_SCRAPE_TIME.split(':'))
        self.scheduler.add_job(
            self.jobs.daily_scrape,
            CronTrigger(hour=hour, minute=minute),
            id='daily_scrape',
            name='Daily Legal Document Scrape',
            replace_existing=True
        )
        self.logger.info(f"✓ Added daily scrape job (runs at {SchedulerConfig.NIGHTLY_SCRAPE_TIME})")
        
        # Weekly full update on Sunday at 3:00 AM
        hour, minute = map(int, SchedulerConfig.WEEKLY_FULL_UPDATE_TIME.split(':'))
        self.scheduler.add_job(
            self.jobs.weekly_full_update,
            CronTrigger(day_of_week=SchedulerConfig.WEEKLY_FULL_UPDATE_DAY, hour=hour, minute=minute),
            id='weekly_full_update',
            name='Weekly Full Update',
            replace_existing=True
        )
        self.logger.info(f"✓ Added weekly update job (runs {SchedulerConfig.WEEKLY_FULL_UPDATE_DAY} at {SchedulerConfig.WEEKLY_FULL_UPDATE_TIME})")
        
        # Monthly archival on 1st of month at 4:00 AM
        self.scheduler.add_job(
            self.jobs.monthly_archival_scrape,
            CronTrigger(day=1, hour=4, minute=0),
            id='monthly_archival',
            name='Monthly Archival Scrape',
            replace_existing=True
        )
        self.logger.info("✓ Added monthly archival job (runs 1st of month at 04:00)")
        
        # Health check every 30 minutes
        self.scheduler.add_job(
            self.jobs.health_check,
            IntervalTrigger(minutes=SchedulerConfig.HEALTH_CHECK_INTERVAL_MINUTES),
            id='health_check',
            name='Health Check',
            replace_existing=True
        )
        self.logger.info(f"✓ Added health check job (every {SchedulerConfig.HEALTH_CHECK_INTERVAL_MINUTES} minutes)")
    
    def _print_schedule(self):
        """Print current schedule"""
        self.logger.info("\n" + "="*70)
        self.logger.info("📋 SCHEDULED JOBS")
        self.logger.info("="*70)
        
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            self.logger.info(f"  • {job.name}")
            self.logger.info(f"    ID: {job.id}")
            self.logger.info(f"    Next run: {job.next_run_time}")
            self.logger.info("")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.logger.info("✅ Scheduler stopped")
    
    def run_job_now(self, job_id: str):
        """Manually trigger a job"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                self.logger.info(f"▶️  Manually running job: {job.name}")
                job.func()
            else:
                self.logger.error(f"Job not found: {job_id}")
        except Exception as e:
            self.logger.error(f"Error running job: {e}")


# ============================================================================
# CLI & DEMO
# ============================================================================

def main():
    """Main entry point for scheduler"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Legal Document Scraper Scheduler")
    parser.add_argument(
        '--mode',
        choices=['start', 'run-daily', 'run-weekly', 'run-monthly', 'status'],
        default='start',
        help='Scheduler mode'
    )
    parser.add_argument(
        '--db-path',
        default='./legal_research_db',
        help='Path to ChromaDB database'
    )
    
    args = parser.parse_args()
    
    scheduler = LegalScraperScheduler(db_path=args.db_path)
    
    if args.mode == 'start':
        # Start scheduler and keep running
        scheduler.start()
        
        print("\n" + "="*70)
        print("📡 SCHEDULER RUNNING")
        print("="*70)
        print("\nPress Ctrl+C to stop\n")
        
        try:
            # Keep running
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping scheduler...")
            scheduler.stop()
            print("✅ Scheduler stopped\n")
    
    elif args.mode == 'run-daily':
        # Run daily job immediately
        print("\n▶️  Running daily scrape job...\n")
        scheduler.jobs.daily_scrape()
    
    elif args.mode == 'run-weekly':
        # Run weekly job immediately
        print("\n▶️  Running weekly update job...\n")
        scheduler.jobs.weekly_full_update()
    
    elif args.mode == 'run-monthly':
        # Run monthly job immediately
        print("\n▶️  Running monthly archival job...\n")
        scheduler.jobs.monthly_archival_scrape()
    
    elif args.mode == 'status':
        # Show scheduler status
        scheduler.start()
        scheduler._print_schedule()
        scheduler.stop()


if __name__ == "__main__":
    main()
