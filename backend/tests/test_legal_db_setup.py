"""
Quick test script to verify legal database setup
"""

from database.chroma_setup import initialize_legal_db

print("\n" + "="*80)
print("TESTING LEGAL RESEARCH DATABASE SETUP")
print("="*80 + "\n")

# Initialize database
db = initialize_legal_db()

# Get statistics
stats = db.get_collection_stats()

print("\n📊 Collection Statistics:")
print(f"  • Bare Acts: {stats['bare_acts']}")
print(f"  • Case Law: {stats['case_law']}")
print(f"  • Amendments: {stats['amendments']}")
print(f"  • Overruling Map: {stats['overruling_map']}")
print(f"  • Total Documents: {stats['total']}")

print("\n✅ Database setup successful!")
print("="*80 + "\n")
