"""
LexAI Data Pipeline
===================
Complete database building pipeline for research publication quality.

Modules:
- amendment_seeder: Load verified legislative amendments
- overruling_seeder: Load verified case overrulings
- bare_acts_loader: Scrape complete bare acts from India Code
- judgment_loader: Load real court judgments from HuggingFace + Kanoon
- run_database_build: Master script to run all in sequence
- validate_database: Comprehensive validation suite

Quick Start:
    from data_pipeline.run_database_build import run_complete_database_build
    run_complete_database_build()

Or run from command line:
    python run_database_build.py
"""

__version__ = "1.0.0"
__author__ = "LexAI Research Team"

# Import main functions for external use
try:
    from .amendment_seeder import seed_amendments
    from .overruling_seeder import seed_overruling_map
    from .run_database_build import run_complete_database_build
    from .validate_database import run_all_validation_tests
    
    __all__ = [
        'seed_amendments',
        'seed_overruling_map',
        'run_complete_database_build',
        'run_all_validation_tests'
    ]
except ImportError:
    # Allow scripts to run standalone
    pass
