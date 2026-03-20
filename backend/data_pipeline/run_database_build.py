"""
Master Database Builder for LexAI
==================================
Runs all data pipeline scripts in correct order.
Validates each step before proceeding to next.

Run: python run_database_build.py

Order of execution:
1. Seed amendments (fastest - ~30 seconds)
2. Seed overrulings (fast - ~30 seconds)
3. Load bare acts (slow - 2-3 hours)
4. Load real judgments (medium - 30-60 minutes)
5. Validate complete database

Total estimated time: 3-4 hours
"""

import chromadb
import os
import time
from datetime import datetime


def validate_collection(collection_name: str, min_docs: int) -> bool:
    """
    Validate that a collection exists and has minimum documents.
    """
    try:
        client = chromadb.PersistentClient(path='./legal_research_db')
        collection = client.get_collection(collection_name)
        count = collection.count()
        
        if count >= min_docs:
            print(f"  ✓ {collection_name}: {count} documents (minimum: {min_docs})")
            return True
        else:
            print(f"  ✗ {collection_name}: {count} documents (minimum required: {min_docs})")
            return False
    except Exception as e:
        print(f"  ✗ {collection_name}: Collection not found or error: {e}")
        return False


def print_header(title: str):
    """
    Print a formatted section header.
    """
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}")


def print_step(step_num: int, total_steps: int, description: str):
    """
    Print a step header.
    """
    print(f"\n{'*'*70}")
    print(f"STEP {step_num}/{total_steps}: {description}")
    print(f"{'*'*70}")


def run_complete_database_build():
    """
    Execute all database building scripts in sequence.
    """
    start_time = time.time()
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              LexAI COMPLETE DATABASE BUILD                       ║
║              Research Publication Quality                        ║
║                                                                  ║
║  This will build a complete, production-ready legal database     ║
║  with real data from official sources.                           ║
║                                                                  ║
║  Estimated time: 3-4 hours                                       ║
║  Do NOT interrupt the process.                                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    input("Press ENTER to start database build...")
    
    # ============================================================
    # STEP 1: Seed Amendments
    # ============================================================
    print_step(1, 4, "Seeding Amendments Database")
    print("Loading 50+ verified legislative amendments...")
    
    try:
        from amendment_seeder import seed_amendments
        seed_amendments()
        
        if not validate_collection('amendments', min_docs=15):
            print("\n⚠ WARNING: Amendments collection has fewer documents than expected.")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Aborting.")
                return
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        print("Fix the error and run again.")
        return
    
    # ============================================================
    # STEP 2: Seed Overrulings
    # ============================================================
    print_step(2, 4, "Seeding Overruling Map Database")
    print("Loading 30+ verified case overrulings...")
    
    try:
        from overruling_seeder import seed_overruling_map
        seed_overruling_map()
        
        if not validate_collection('overruling_map', min_docs=10):
            print("\n⚠ WARNING: Overruling map has fewer documents than expected.")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Aborting.")
                return
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        print("Fix the error and run again.")
        return
    
    # ============================================================
    # STEP 3: Load Bare Acts
    # ============================================================
    print_step(3, 4, "Loading Complete Bare Acts")
    print("Scraping 20+ major Indian acts from India Code...")
    print("⏰ This will take 2-3 hours. Do NOT interrupt.")
    print("\nActs to be loaded:")
    print("- Criminal: IPC, BNS, CrPC, BNSS, Evidence Act, BSA")
    print("- Civil: Contract Act, CPC, TPA, Specific Relief Act")
    print("- Commercial: NI Act, Arbitration Act, Companies Act, IT Act")
    print("- Constitutional: Constitution of India")
    print("- Family: Hindu Marriage Act, PWDV Act, POCSO")
    print("- Others: Consumer Protection, Insolvency & Bankruptcy Code")
    
    response = input("\nStart bare acts loading? (y/n): ")
    if response.lower() != 'y':
        print("Skipping bare acts. You can run bare_acts_loader.py separately later.")
    else:
        try:
            import asyncio
            from bare_acts_loader import load_all_acts
            asyncio.run(load_all_acts())
            
            if not validate_collection('bare_acts', min_docs=100):
                print("\n⚠ WARNING: Bare acts collection has fewer documents than expected.")
                print("Some acts may have failed to load.")
                print("Check data/backup/bare_acts_loading_stats.json for details.")
        except Exception as e:
            print(f"\n✗ FAILED: {e}")
            print("You can retry by running: python bare_acts_loader.py")
    
    # ============================================================
    # STEP 4: Load Real Judgments
    # ============================================================
    print_step(4, 4, "Loading Real Court Judgments")
    print("Loading judgments from:")
    print("1. HuggingFace datasets (real judgment text)")
    print("2. Landmark cases from Indian Kanoon")
    print("\n⏰ This will take 30-60 minutes.")
    
    response = input("\nStart judgment loading? (y/n): ")
    if response.lower() != 'y':
        print("Skipping judgments. You can run judgment_loader.py separately later.")
    else:
        try:
            from judgment_loader import run_complete_judgment_loading
            run_complete_judgment_loading()
        except Exception as e:
            print(f"\n✗ FAILED: {e}")
            print("You can retry by running: python judgment_loader.py")
    
    # ============================================================
    # FINAL VALIDATION
    # ============================================================
    print_header("FINAL DATABASE VALIDATION")
    
    client = chromadb.PersistentClient(path='./legal_research_db')
    
    collections_requirements = {
        'bare_acts': {
            'min': 100,
            'target': 500,
            'description': 'Complete sections of major Indian acts'
        },
        'case_law': {
            'min': 100,
            'target': 15000,
            'description': 'Real court judgments + Q&A pairs'
        },
        'amendments': {
            'min': 15,
            'target': 50,
            'description': 'Verified legislative amendments'
        },
        'overruling_map': {
            'min': 10,
            'target': 30,
            'description': 'Verified case overrulings'
        }
    }
    
    print("\nValidating all collections:")
    all_valid = True
    
    for col_name, req in collections_requirements.items():
        try:
            collection = client.get_collection(col_name)
            count = collection.count()
            
            status = "✓" if count >= req['min'] else "✗"
            quality = "EXCELLENT" if count >= req['target'] else "ADEQUATE" if count >= req['min'] else "INSUFFICIENT"
            
            print(f"\n{status} {col_name.upper()}")
            print(f"  Count: {count:,} documents")
            print(f"  Minimum: {req['min']} | Target: {req['target']}")
            print(f"  Quality: {quality}")
            print(f"  Description: {req['description']}")
            
            if count < req['min']:
                all_valid = False
        except Exception as e:
            print(f"\n✗ {col_name.upper()}")
            print(f"  Error: {e}")
            all_valid = False
    
    # ============================================================
    # SAMPLE VALIDATION QUERIES
    # ============================================================
    print_header("SAMPLE VALIDATION QUERIES")
    
    validation_queries = [
        {
            "collection": "bare_acts",
            "query": "Section 138 Negotiable Instruments Act cheque bounce",
            "expected": "NI Act Section 138"
        },
        {
            "collection": "bare_acts",
            "query": "punishment for rape Indian Penal Code",
            "expected": "IPC Section 376 or BNS Section 63"
        },
        {
            "collection": "amendments",
            "query": "Section 66A IT Act struck down unconstitutional",
            "expected": "IT Act 66A struck down"
        },
        {
            "collection": "overruling_map",
            "query": "ADM Jabalpur emergency overruled Puttaswamy",
            "expected": "ADM Jabalpur overruled"
        },
        {
            "collection": "case_law",
            "query": "Navtej Singh Johar Section 377 decriminalized same sex",
            "expected": "Navtej Johar or Section 377"
        }
    ]
    
    print("\nRunning validation queries...")
    query_results = []
    
    for vq in validation_queries:
        try:
            collection = client.get_collection(vq['collection'])
            result = collection.query(
                query_texts=[vq['query']],
                n_results=1
            )
            
            if result['ids'][0]:
                matched = True
                result_text = str(result['metadatas'][0][0])[:150]
            else:
                matched = False
                result_text = "No results"
            
            status = "✓" if matched else "✗"
            print(f"\n{status} Query: {vq['query'][:60]}...")
            print(f"  Collection: {vq['collection']}")
            print(f"  Expected: {vq['expected']}")
            print(f"  Result: {result_text}")
            
            query_results.append(matched)
        except Exception as e:
            print(f"\n✗ Query failed: {e}")
            query_results.append(False)
    
    queries_passed = sum(query_results)
    queries_total = len(query_results)
    
    # ============================================================
    # FINAL REPORT
    # ============================================================
    elapsed = time.time() - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    
    print(f"\n{'='*70}")
    print(f"{'DATABASE BUILD COMPLETE':^70}")
    print(f"{'='*70}")
    
    print(f"\n⏱  Time taken: {hours}h {minutes}m")
    
    print(f"\n📊 VALIDATION SUMMARY:")
    print(f"  Collections validated: {4 if all_valid else '<4'}/4")
    print(f"  Sample queries passed: {queries_passed}/{queries_total}")
    
    if all_valid and queries_passed >= 4:
        print(f"\n{'✓ DATABASE IS PUBLICATION READY':^70}")
        print("\nNext steps:")
        print("1. Have lawyer verify amendments (data/backup/amendments/)")
        print("2. Have lawyer verify overrulings (data/backup/overrulings/)")
        print("3. Run evaluation: cd evaluation && python run_evaluation.py")
        print("4. Analyze results and prepare paper")
    elif all_valid:
        print(f"\n{'⚠ DATABASE ADEQUATE BUT NEEDS IMPROVEMENT':^70}")
        print("\nSome validation queries failed.")
        print("Database is usable but may need more data for specific topics.")
    else:
        print(f"\n{'✗ DATABASE INCOMPLETE':^70}")
        print("\nSome collections did not meet minimum requirements.")
        print("Run individual scripts to fix:")
        print("  python amendment_seeder.py")
        print("  python overruling_seeder.py")
        print("  python bare_acts_loader.py")
        print("  python judgment_loader.py")
    
    # Save build report
    build_report = {
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": int(elapsed),
        "collections": {},
        "validation_queries_passed": queries_passed,
        "validation_queries_total": queries_total,
        "all_valid": all_valid
    }
    
    for col_name in collections_requirements.keys():
        try:
            collection = client.get_collection(col_name)
            build_report["collections"][col_name] = collection.count()
        except:
            build_report["collections"][col_name] = 0
    
    os.makedirs('data/backup', exist_ok=True)
    import json
    with open('data/backup/database_build_report.json', 'w') as f:
        json.dump(build_report, f, indent=2)
    
    print(f"\n📄 Build report saved: data/backup/database_build_report.json")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    run_complete_database_build()
