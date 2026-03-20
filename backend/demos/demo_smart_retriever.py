"""
Demo script showing Smart Retriever with sample legal data
Demonstrates the full 7-step pipeline with BNS/BNSS middleware
"""

from database.chroma_setup import initialize_legal_db
from retrieval.smart_retriever import initialize_smart_retriever
import json

print("\n" + "="*80)
print("SMART RETRIEVER DEMO - WITH SAMPLE DATA")
print("="*80 + "\n")

# Initialize database
db = initialize_legal_db()

# Add sample IPC sections to demonstrate BNS middleware
print("📝 Adding sample bare act sections...\n")

# IPC Section 420 - Famous cheating section
db.add_bare_act_section(
    section_id="IPC_420",
    act_name="Indian Penal Code 1860",
    section_number="420",
    section_title="Cheating and dishonestly inducing delivery of property",
    full_text="""Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, or to make, alter or destroy the whole or any part of a valuable security, or anything which is signed or sealed, and which is capable of being converted into a valuable security, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.""",
    simplified_text="Punishment for cheating someone into giving property - up to 7 years imprisonment and fine",
    punishment="Imprisonment up to 7 years and fine",
    is_replaced=True,
    replaced_by_act="Bharatiya Nyaya Sanhita 2023",
    replaced_by_section="318",
    replacement_changes="substantially same with minor wording changes"
)
print("  ✓ Added IPC Section 420 (Cheating)")

# IPC Section 302 - Murder
db.add_bare_act_section(
    section_id="IPC_302",
    act_name="Indian Penal Code 1860",
    section_number="302",
    section_title="Punishment for murder",
    full_text="""Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.""",
    simplified_text="Punishment for murder - death or life imprisonment and fine",
    punishment="Death or life imprisonment and fine",
    is_replaced=True,
    replaced_by_act="Bharatiya Nyaya Sanhita 2023",
    replaced_by_section="103",
    replacement_changes="substantially same"
)
print("  ✓ Added IPC Section 302 (Murder)")

# IPC Section 376 - Rape
db.add_bare_act_section(
    section_id="IPC_376",
    act_name="Indian Penal Code 1860",
    section_number="376",
    section_title="Punishment for rape",
    full_text="""Whoever commits rape shall be punished with rigorous imprisonment of either description for a term which shall not be less than ten years, but which may extend to imprisonment for life, and shall also be liable to fine.""",
    simplified_text="Punishment for rape - minimum 10 years rigorous imprisonment up to life, and fine",
    punishment="Minimum 10 years RI up to life imprisonment and fine",
    is_replaced=True,
    replaced_by_act="Bharatiya Nyaya Sanhita 2023",
    replaced_by_section="64",
    replacement_changes="expanded definition of consent and enhanced punishment"
)
print("  ✓ Added IPC Section 376 (Rape)")

# CrPC Section 154 - FIR
db.add_bare_act_section(
    section_id="CRPC_154",
    act_name="Code of Criminal Procedure 1973",
    section_number="154",
    section_title="Information in cognizable cases",
    full_text="""Every information relating to the commission of a cognizable offence, if given orally to an officer in charge of a police station, shall be reduced to writing by him or under his direction, and be read over to the informant; and every such information, whether given in writing or reduced to writing as aforesaid, shall be signed by the person giving it, and the substance thereof shall be entered in a book to be kept by such officer in such form as the State Government may prescribe in this behalf.""",
    simplified_text="FIR must be registered for cognizable offences, written down, read to informant, and signed",
    is_replaced=True,
    replaced_by_act="Bharatiya Nagarik Suraksha Sanhita 2023",
    replaced_by_section="173",
    replacement_changes="added e-FIR and zero FIR provisions"
)
print("  ✓ Added CrPC Section 154 (FIR)")

# Add sample case law
print("\n📚 Adding sample case law...\n")

db.add_case_law(
    case_id="SC_2019_CHEATING_001",
    case_name="State of Maharashtra v. Rajesh Kumar",
    citation="AIR 2019 SC 1234",
    court="Supreme Court",
    year="2019",
    chunk_text="""The Supreme Court held that for an offence under Section 420 IPC to be made out, the prosecution must prove dishonest intention from the very beginning. Mere breach of contract does not amount to cheating. The court observed that the distinction between civil wrong and criminal offence must be maintained. The essential ingredients of cheating are: (1) deception of a person, (2) fraudulent or dishonest inducement to deliver property, (3) mens rea to cheat from the inception.""",
    legal_principle="Dishonest intention from the beginning must be proved for Section 420 IPC. Mere breach of contract is not cheating.",
    acts_referred=["Indian Penal Code"],
    sections_referred=["420"],
    held="Conviction under Section 420 IPC quashed as dishonest intention not proved from inception",
    source="demo",
    is_overruled=False
)
print("  ✓ Added Supreme Court case on Section 420 IPC")

db.add_case_law(
    case_id="SC_2020_RAPE_001",
    case_name="Vijay Singh v. State of NCT Delhi",
    citation="AIR 2020 SC 5678",
    court="Supreme Court",
    year="2020",
    chunk_text="""In this landmark judgment on Section 376 IPC, the Supreme Court emphasized that consent obtained under false promise of marriage does not vitiate consent unless the promise was false from the inception. The court held that every breach of promise to marry cannot be treated as rape. The false promise must be of immediate relevance or bear a direct nexus to the sexual act and must have been given with the intention to seduce the woman.""",
    legal_principle="False promise of marriage vitiates consent only if false from inception and given with intention to seduce",
    acts_referred=["Indian Penal Code"],
    sections_referred=["376", "375"],
    held="Conviction under Section 376 upheld where promise to marry was false from beginning",
    source="demo",
    is_overruled=False
)
print("  ✓ Added Supreme Court case on Section 376 IPC")

# Add sample amendment
print("\n📋 Adding sample amendment...\n")

db.add_amendment(
    amendment_id="AMEND_420_2013",
    act_name="Indian Penal Code 1860",
    section_number="420",
    amendment_year="2013",
    amendment_act="Criminal Law (Amendment) Act 2013",
    old_text="Whoever cheats and thereby dishonestly induces...",
    new_text="Whoever cheats and thereby dishonestly induces... [enhanced punishment provisions added]",
    effective_date="2013-04-03",
    impact_summary="Enhanced punishment provisions for cheating",
    gazette_reference="No. 13 of 2013"
)
print("  ✓ Added 2013 amendment to Section 420 IPC")

# Show collection stats
stats = db.get_collection_stats()
print(f"\n📊 Database Statistics:")
print(f"  • Bare Acts: {stats['bare_acts']}")
print(f"  • Case Law: {stats['case_law']}")
print(f"  • Amendments: {stats['amendments']}")
print(f"  • Total: {stats['total']}")

# Initialize smart retriever
print("\n" + "="*80)
print("TESTING SMART RETRIEVER WITH SAMPLE DATA")
print("="*80 + "\n")

retriever = initialize_smart_retriever(db)

# Test queries
test_queries = [
    "What is Section 420 IPC",
    "Can mere breach of promise to marry be rape",
    "What is the punishment for cheating",
    "Tell me about FIR registration"
]

for i, query in enumerate(test_queries, 1):
    print(f"\n{'─'*80}")
    print(f"Query {i}: {query}")
    print('─'*80)
    
    try:
        result = retriever.retrieve(query)
    except Exception as e:
        print(f"\n❌ Error during retrieval: {e}")
        import traceback
        traceback.print_exc()
        continue
    
    print(f"\n📋 Query Type: {result['query_type']}")
    print(f"🎯 Confidence: {result['confidence_level']}")
    print(f"⚠️  BNS/BNSS Notes: {'Yes' if result['has_bns_bnss_notes'] else 'No'}")
    
    # Show bare acts
    if result['bare_acts']:
        print(f"\n📚 Bare Acts Retrieved ({len(result['bare_acts'])}):")
        for act in result['bare_acts']:
            print(f"\n  • {act['metadata']['act_name']}")
            print(f"    Section {act['metadata']['section_number']}: {act['metadata']['section_title']}")
            print(f"    Confidence: {act['confidence_level']} ({act['confidence_score']})")
            
            # Show BNS transition if exists
            if 'bns_transition' in act:
                print(f"    {act['bns_transition']['note']}")
            
            # Show BNSS transition if exists
            if 'bnss_transition' in act:
                print(f"    {act['bnss_transition']['note']}")
            
            # Show amendments if exists
            if act.get('has_amendments'):
                print(f"    ⚠️  Has {act['amendments_count']} amendment(s)")
    
    # Show case laws
    if result['case_laws']:
        print(f"\n⚖️  Case Laws Retrieved ({len(result['case_laws'])}):")
        for case in result['case_laws']:
            print(f"\n  • {case['metadata']['case_name']}")
            print(f"    {case['metadata']['citation']}")
            print(f"    Court: {case['metadata']['court']}, Year: {case['metadata']['year']}")
            print(f"    Confidence: {case['confidence_level']} ({case['confidence_score']})")
            
            # Show IPC sections mentioned
            if 'ipc_sections_mentioned' in case:
                print(f"    IPC Sections: {', '.join(case['ipc_sections_mentioned'])}")
            
            # Show if overruled
            if case.get('is_overruled'):
                print(f"    {case['warning']}")
    
    # Show stats
    print(f"\n📊 Retrieval Stats:")
    print(f"  • Bare Acts: {result['stats']['bare_acts_retrieved']}")
    print(f"  • Case Laws: {result['stats']['case_laws_retrieved']}")
    print(f"  • Amendments: {result['stats']['amendments_found']}")
    print(f"  • Overruled Cases: {result['stats']['overruled_cases']}")

print("\n" + "="*80)
print("✅ DEMO COMPLETE - Smart Retriever working with full 7-step pipeline!")
print("="*80 + "\n")
