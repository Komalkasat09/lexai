"""
DEMO: Legal LLM with Groq Integration
======================================
Demonstrates Step 4 - LLM layer for legal research assistant.

This demo shows:
- Integration between SmartRetriever (Step 3) and LegalLLM (Step 4)
- Deterministic LLM responses with Groq (temp=0.0, seed=42)
- Confidence-based response filtering
- BNS/BNSS transition handling
- Citation-aware answers

Prerequisites:
- GROQ_API_KEY environment variable must be set
- Sample legal data in database (run demo_smart_retriever.py first)
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.chroma_setup import LegalResearchDB
from llm.legal_llm import LegalLLM


def populate_sample_data():
    """Add sample legal data to database (same as demo_smart_retriever.py)"""
    print("📝 Adding sample legal data to database...\n")
    
    db = LegalResearchDB(persist_directory="./legal_research_db")
    
    # Sample bare acts
    db.add_bare_act_section(
        section_id="IPC_420",
        act_name="Indian Penal Code 1860",
        section_number="420",
        section_title="Cheating and dishonestly inducing delivery of property",
        full_text="Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, or to make, alter or destroy the whole or any part of a valuable security, or anything which is signed or sealed, and which is capable of being converted into a valuable security, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.",
        simplified_text="Punishment for cheating someone into giving property - up to 7 years imprisonment and fine",
        punishment="Imprisonment up to 7 years and fine",
        is_replaced=True,
        replaced_by_act="Bharatiya Nyaya Sanhita 2023",
        replaced_by_section="318",
        replacement_changes="substantially same with minor wording changes"
    )
    print(f"  ✓ Added IPC Section 420 (Cheating)")
    
    db.add_bare_act_section(
        section_id="IPC_302",
        act_name="Indian Penal Code 1860",
        section_number="302",
        section_title="Punishment for murder",
        full_text="Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
        simplified_text="Punishment for murder - death or life imprisonment and fine",
        punishment="Death or life imprisonment and fine",
        is_replaced=True,
        replaced_by_act="Bharatiya Nyaya Sanhita 2023",
        replaced_by_section="103",
        replacement_changes="substantially same"
    )
    print(f"  ✓ Added IPC Section 302 (Murder)")
    
    db.add_bare_act_section(
        section_id="IPC_376",
        act_name="Indian Penal Code 1860",
        section_number="376",
        section_title="Punishment for rape",
        full_text="Whoever, except in the cases provided for in sub-section (2), commits rape, shall be punished with rigorous imprisonment of either description for a term which shall not be less than ten years, but which may extend to imprisonment for life, and shall also be liable to fine.",
        simplified_text="Punishment for rape - rigorous imprisonment 10 years to life and fine",
        punishment="Rigorous imprisonment 10 years to life and fine",
        is_replaced=True,
        replaced_by_act="Bharatiya Nyaya Sanhita 2023",
        replaced_by_section="64",
        replacement_changes="punishment for rape - enhanced"
    )
    print(f"  ✓ Added IPC Section 376 (Rape)")
    
    db.add_bare_act_section(
        section_id="CRPC_154",
        act_name="Code of Criminal Procedure 1973",
        section_number="154",
        section_title="Information in cognizable cases",
        full_text="Every information relating to the commission of a cognizable offence, if given orally to an officer in charge of a police station, shall be reduced to writing by him or under his direction, and be read over to the informant; and every such information, whether given in writing or reduced to writing as aforesaid, shall be signed by the person giving it.",
        simplified_text="FIR lodging procedure - oral information must be written down and signed",
        is_replaced=True,
        replaced_by_act="Bharatiya Nagarik Suraksha Sanhita 2023",
        replaced_by_section="173",
        replacement_changes="FIR - now includes provision for e-FIR"
    )
    print(f"  ✓ Added CrPC Section 154 (FIR)")
    
    # Sample case law
    print("\n📚 Adding sample case law...\n")
    
    db.add_case_law(
        case_id="SC_2019_CHEATING_001",
        case_name="State of Maharashtra v. Rajesh Kumar",
        citation="AIR 2019 SC 1234",
        court="Supreme Court",
        year="2019",
        chunk_text="The Supreme Court held that for establishing the offense of cheating under Section 420 IPC, there must be fraudulent or dishonest inducement from the very beginning. Mere breach of contract does not amount to cheating. The prosecution must prove: (1) deception of the complainant, (2) fraudulent or dishonest inducement, (3) delivery of property pursuant to such inducement.",
        legal_principle="Dishonest intention from the beginning must be proved for Section 420 IPC. Mere breach of contract is not cheating.",
        acts_referred=["Indian Penal Code"],
        sections_referred=["420"],
        held="Conviction under Section 420 IPC quashed as dishonest intention not proved from inception",
        source="demo",
        is_overruled=False
    )
    print(f"  ✓ Added case: State of Maharashtra v. Rajesh Kumar")
    
    db.add_case_law(
        case_id="SC_2020_RAPE_001",
        case_name="Vijay Singh v. State of NCT Delhi",
        citation="AIR 2020 SC 5678",
        court="Supreme Court",
        year="2020",
        chunk_text="The Supreme Court clarified that a mere breach of promise to marry does not automatically constitute rape under Section 376 IPC. There must be evidence that the consent was obtained on a false promise made with mala fide intention from the inception. The promise must be shown to be false at the time it was made.",
        legal_principle="False promise of marriage vitiates consent only if false from inception and given with intention to seduce",
        acts_referred=["Indian Penal Code"],
        sections_referred=["376"],
        held="Conviction under Section 376 upheld where promise to marry was false from beginning",
        source="demo",
        is_overruled=False
    )
    print(f"  ✓ Added case: Vijay Singh v. State of NCT Delhi")
    
    # Sample amendment
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
        impact_summary="Enhanced punishment provisions for cheating - imprisonment extended from 3 years to 7 years for offenses involving financial fraud exceeding Rs. 1 lakh.",
        gazette_reference="No. 13 of 2013"
    )
    print(f"  ✓ Added amendment: Criminal Law (Amendment) Act 2013")
    
    stats = db.get_collection_stats()
    print(f"\n📊 Database now contains:")
    print(f"  • Bare Acts: {stats['bare_acts']}")
    print(f"  • Case Law: {stats['case_law']}")
    print(f"  • Amendments: {stats['amendments']}")
    print(f"  • Total: {stats['total']}\n")


def print_result(result, query_number):
    """Pretty print LegalLLM result"""
    print(f"\n{'─' * 80}")
    print(f"QUERY {query_number} RESULT")
    print('─' * 80)
    
    print(f"\n📋 Query Type: {result['query_type']}")
    print(f"🎯 Confidence: {result['confidence']}")
    print(f"⚠️  Trigger Uncertainty: {result['trigger_uncertainty']}")
    
    if result['warnings']:
        print(f"\n⚠️  Warnings ({len(result['warnings'])}):")
        for warning in result['warnings']:
            print(f"  • {warning}")
    
    print(f"\n📊 Retrieval Stats:")
    stats = result['stats']
    print(f"  • Bare Acts: {stats.get('bare_acts_retrieved', 0)}")
    print(f"  • Case Laws: {stats.get('case_laws_retrieved', 0)}")
    print(f"  • Amendments: {stats.get('amendments_found', 0)}")
    print(f"  • Overruled Cases: {stats.get('overruled_cases', 0)}")
    
    print(f"\n💬 LLM Answer:")
    print('-' * 80)
    print(result['answer'])
    print('-' * 80)


def main():
    """Main demo function"""
    print("=" * 80)
    print("LEGAL LLM DEMO - WITH GROQ INTEGRATION")
    print("=" * 80)
    print()
    
    # Check for GROQ_API_KEY
    if not os.getenv("GROQ_API_KEY"):
        print("❌ ERROR: GROQ_API_KEY environment variable not set!")
        print()
        print("To run this demo, set your Groq API key:")
        print("  export GROQ_API_KEY='your-api-key-here'")
        print()
        print("Get your API key from: https://console.groq.com/keys")
        print()
        return
    
    print("✅ GROQ_API_KEY found in environment")
    print()
    
    # Populate sample data
    populate_sample_data()
    
    # Initialize LegalLLM
    print("🔧 Initializing LegalLLM...")
    legal_llm = LegalLLM(persist_directory="./legal_research_db")
    print()
    
    print("=" * 80)
    print("TESTING LEGAL LLM WITH SAMPLE QUERIES")
    print("=" * 80)
    
    # Test 1: Section lookup query
    print(f"\n{'▓' * 80}")
    print("TEST 1: Section Lookup Query")
    print('▓' * 80)
    query1 = "What is Section 420 IPC?"
    print(f"Query: {query1}")
    
    result1 = legal_llm.answer_legal_question(query1)
    print_result(result1, 1)
    
    # Test 2: Legal question with case law
    print(f"\n\n{'▓' * 80}")
    print("TEST 2: Legal Question (Case Law)")
    print('▓' * 80)
    query2 = "Can mere breach of promise to marry be rape?"
    print(f"Query: {query2}")
    
    result2 = legal_llm.answer_legal_question(query2)
    print_result(result2, 2)
    
    # Test 3: Punishment query
    print(f"\n\n{'▓' * 80}")
    print("TEST 3: Punishment Query")
    print('▓' * 80)
    query3 = "What is the punishment for cheating under IPC?"
    print(f"Query: {query3}")
    
    result3 = legal_llm.answer_legal_question(query3)
    print_result(result3, 3)
    
    # Test 4: Explain section (dedicated function)
    print(f"\n\n{'▓' * 80}")
    print("TEST 4: Explain Section (Dedicated Function)")
    print('▓' * 80)
    print(f"Function: explain_section('Indian Penal Code 1860', '302')")
    
    result4 = legal_llm.explain_section("Indian Penal Code 1860", "302")
    print_result(result4, 4)
    
    # Final summary
    print(f"\n\n{'=' * 80}")
    print("✅ LEGAL LLM DEMO COMPLETE!")
    print('=' * 80)
    print()
    print("Demonstrated Features:")
    print("  ✓ SmartRetriever + LLM integration")
    print("  ✓ Deterministic responses (temp=0.0, seed=42)")
    print("  ✓ Confidence-based filtering")
    print("  ✓ BNS/BNSS transition warnings")
    print("  ✓ Citation-aware answers")
    print("  ✓ Dedicated functions (explain_section, etc.)")
    print()


if __name__ == "__main__":
    main()
