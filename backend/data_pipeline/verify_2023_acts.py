"""
Quick verification that 2023 acts are in database and searchable
"""
import chromadb

def verify_2023_acts():
    client = chromadb.PersistentClient(path="./legal_research_db")
    bare_acts = client.get_collection("bare_acts")
    
    print("\n" + "="*80)
    print("2023 ACTS VERIFICATION")
    print("="*80)
    
    # Count sections per act
    for act_name in ["Bharatiya Nyaya Sanhita 2023", 
                     "Bharatiya Nagarik Suraksha Sanhita 2023",
                     "Bharatiya Sakshya Adhiniyam 2023"]:
        results = bare_acts.get(
            where={"act_name": act_name},
            limit=1000
        )
        count = len(results['ids'])
        print(f"\n{act_name}: {count} sections")
        
        # Show sample sections
        if count > 0:
            print(f"  Sample sections:")
            for i in range(min(5, count)):
                section_num = results['metadatas'][i].get('section_number', 'Unknown')
                title = results['metadatas'][i].get('section_title', 'No title')
                print(f"    • Section {section_num}: {title[:80]}")
    
    # Test specific query for BNS rape section
    print("\n" + "-"*80)
    print("TEST: Query for 'rape punishment BNS Section 63'")
    print("-"*80)
    
    results = bare_acts.query(
        query_texts=["rape punishment BNS Section 63"],
        n_results=5
    )
    
    for i, (doc_id, metadata, distance) in enumerate(zip(
        results['ids'][0],
        results['metadatas'][0],
        results['distances'][0]
    )):
        act = metadata.get('act_name', 'Unknown')
        section = metadata.get('section_number', 'Unknown')
        title = metadata.get('section_title', 'No title')
        print(f"{i+1}. [{act}] Section {section}: {title[:60]} (dist: {distance:.3f})")

if __name__ == "__main__":
    verify_2023_acts()
