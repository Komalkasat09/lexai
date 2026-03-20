"""
LexAI Evaluation Dataset Builder
=================================
Generates ground truth dataset template for legal research evaluation.

This file creates a 300-query evaluation dataset across 7 categories.
The template must be verified by a qualified lawyer before use.

Usage:
    python evaluation/dataset_builder.py
    
Output:
    evaluation/ground_truth_template.xlsx (for lawyer verification)
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import random

# Set seed for reproducibility
random.seed(42)


class EvaluationDatasetBuilder:
    """
    Builds ground truth evaluation dataset for LexAI research paper.
    Generates 300 queries across 7 legal research categories.
    """
    
    def __init__(self):
        self.queries = []
        self.query_id_counter = 1
        
    def _add_query(self, category: str, query_text: str, difficulty: str = "medium"):
        """Add a query to the dataset with placeholder ground truth fields."""
        self.queries.append({
            "query_id": f"Q{self.query_id_counter:03d}",
            "category": category,
            "query_text": query_text,
            "correct_answer_summary": "",  # Lawyer fills this
            "correct_act": "",  # e.g., "IPC", "NI Act", "Companies Act"
            "correct_section": "",  # e.g., "138", "420", "9"
            "correct_citation": "",  # e.g., "AIR 1978 SC 597"
            "amendment_applies": "",  # Lawyer marks "yes" or "no"
            "amendment_detail": "",  # Lawyer describes amendment
            "overruling_applies": "",  # "yes" or "no"
            "overruled_by": "",  # Case citation if applicable
            "bns_bnss_transition_applies": "",  # "yes" or "no"
            "bns_bnss_detail": "",  # Describe IPC→BNS transition
            "difficulty_level": difficulty,
            "verified_by_lawyer": "",  # Lawyer signs name here
            "lawyer_notes": ""  # Any additional notes
        })
        self.query_id_counter += 1
    
    def generate_category1_section_lookup(self):
        """CATEGORY 1: Section Lookup Queries (50 queries)"""
        print("Generating Category 1: Section Lookup (50 queries)")
        
        # IPC sections (most common)
        ipc_queries = [
            ("What does Section 420 IPC say?", "easy"),
            ("Explain Section 302 IPC", "easy"),
            ("What is Section 498A IPC?", "easy"),
            ("Show me Section 376 IPC", "medium"),
            ("What does Section 354 IPC cover?", "medium"),
            ("Explain Section 506 IPC", "easy"),
            ("What is Section 323 IPC about?", "easy"),
            ("What does Section 406 IPC say?", "medium"),
            ("Explain Section 279 IPC", "easy"),
            ("What is Section 304B IPC?", "medium"),
            ("What does Section 120B IPC say?", "hard"),
            ("Explain Section 166 IPC", "medium"),
            ("What is Section 34 IPC?", "medium"),
            ("Show me Section 307 IPC", "medium"),
            ("What does Section 411 IPC cover?", "medium"),
        ]
        
        # BNS sections (new law - 2023)
        bns_queries = [
            ("What does Section 318 BNS say?", "medium"),
            ("Explain Section 103 BNS", "medium"),
            ("What is Section 69 BNS?", "medium"),
            ("Show me Section 351 BNS", "hard"),
            ("What does Section 214 BNS cover?", "medium"),
        ]
        
        # Negotiable Instruments Act
        ni_act_queries = [
            ("What does Section 138 of the Negotiable Instruments Act say?", "easy"),
            ("Explain Section 141 NI Act", "medium"),
            ("What is Section 143 of NI Act?", "hard"),
            ("What does Section 139 NI Act say about presumption?", "medium"),
        ]
        
        # CrPC sections
        crpc_queries = [
            ("What does Section 41 CrPC say?", "medium"),
            ("Explain Section 154 CrPC", "easy"),
            ("What is Section 482 CrPC?", "hard"),
            ("Show me Section 125 CrPC", "medium"),
            ("What does Section 438 CrPC cover?", "medium"),
            ("Explain Section 156(3) CrPC", "medium"),
            ("What is Section 167 CrPC about?", "medium"),
        ]
        
        # BNSS sections (CrPC replacement)
        bnss_queries = [
            ("What does Section 35 BNSS say?", "medium"),
            ("Explain Section 173 BNSS", "medium"),
            ("What is Section 528 BNSS?", "hard"),
        ]
        
        # Other important acts
        other_queries = [
            ("What does Section 9 of the Arbitration Act say?", "medium"),
            ("Explain Section 66A of the IT Act", "hard"),
            ("What is Section 141 of the Companies Act 2013?", "medium"),
            ("Show me Section 27 of the Indian Evidence Act", "medium"),
            ("What does Section 8 of the Hindu Marriage Act say?", "easy"),
            ("Explain Section 65B of the Evidence Act", "hard"),
            ("What is Section 17 of the Registration Act?", "medium"),
            ("What does Section 53A of the Transfer of Property Act say?", "medium"),
            ("Explain Section 2(h) of the Consumer Protection Act", "medium"),
        ]
        
        all_queries = ipc_queries + bns_queries + ni_act_queries + crpc_queries + bnss_queries + other_queries
        
        for query_text, difficulty in all_queries:
            self._add_query("Section Lookup", query_text, difficulty)
    
    def generate_category2_punishment_queries(self):
        """CATEGORY 2: Punishment Queries (40 queries)"""
        print("Generating Category 2: Punishment Queries (40 queries)")
        
        queries = [
            ("What is the punishment for rape under BNS?", "medium"),
            ("What is the sentence for cheque bounce?", "easy"),
            ("How many years imprisonment for murder under IPC?", "easy"),
            ("What is the punishment for dowry harassment under Section 498A?", "medium"),
            ("What is the sentence for criminal breach of trust under IPC 406?", "medium"),
            ("How long can you be jailed for causing death by negligence?", "medium"),
            ("What is the punishment for dishonest misappropriation?", "medium"),
            ("What is the sentence for gang rape under IPC?", "medium"),
            ("How many years for kidnapping under IPC 363?", "medium"),
            ("What is the punishment for attempt to murder under Section 307 IPC?", "medium"),
            ("What is the sentence for culpable homicide not amounting to murder?", "hard"),
            ("How long imprisonment for robbery under IPC 392?", "medium"),
            ("What is the punishment for dacoity with murder?", "medium"),
            ("What is the sentence for causing grievous hurt under IPC 325?", "easy"),
            ("How many years for criminal intimidation under IPC 506?", "easy"),
            ("What is the punishment for assault on woman with intent to outrage modesty?", "medium"),
            ("What is the sentence for wrongful confinement under IPC?", "medium"),
            ("How long imprisonment for rioting under IPC 147?", "medium"),
            ("What is the punishment for sedition under IPC 124A?", "hard"),
            ("What is the sentence for defamation under IPC 500?", "medium"),
            ("How many years for falsifying accounts under Companies Act?", "hard"),
            ("What is the punishment for insider trading under SEBI Act?", "hard"),
            ("What is the sentence for contempt of court?", "medium"),
            ("How long imprisonment for POCSO Act violations?", "medium"),
            ("What is the punishment for money laundering under PMLA?", "hard"),
            ("What is the sentence for terrorism under UAPA?", "hard"),
            ("How many years for cheating under BNS 318?", "medium"),
            ("What is the punishment for theft under BNS?", "easy"),
            ("What is the sentence for destruction of evidence under IPC?", "medium"),
            ("How long imprisonment for forgery of valuable security?", "medium"),
            ("What is the punishment for abetment to suicide under IPC 306?", "medium"),
            ("What is the sentence for drunk driving causing death?", "medium"),
            ("How many years for running a prostitution racket?", "hard"),
            ("What is the punishment for bribery under Prevention of Corruption Act?", "medium"),
            ("What is the sentence for narcotics possession under NDPS Act?", "medium"),
            ("How long imprisonment for criminal conspiracy to commit murder?", "hard"),
            ("What is the punishment for rioting with deadly weapon?", "medium"),
            ("What is the sentence for voluntarily causing hurt to extort confession?", "hard"),
            ("How many years for dishonest inducement to deliver property?", "medium"),
            ("What is the punishment for criminal trespass with intent to commit offense?", "medium"),
        ]
        
        for query_text, difficulty in queries:
            self._add_query("Punishment Queries", query_text, difficulty)
    
    def generate_category3_amendment_specific(self):
        """CATEGORY 3: Amendment Specific Queries (40 queries)"""
        print("Generating Category 3: Amendment Specific (40 queries)")
        
        queries = [
            ("Has Section 66A IT Act been struck down?", "medium"),
            ("What changed in CrPC after BNSS came into force?", "hard"),
            ("What are the new bail provisions under BNSS 2023?", "hard"),
            ("Was adultery decriminalized in India?", "medium"),
            ("What happened to Section 377 IPC?", "medium"),
            ("Has the definition of rape been amended?", "medium"),
            ("What changes did the 2013 Criminal Law Amendment make to IPC?", "hard"),
            ("Is triple talaq still valid in India?", "easy"),
            ("What changed in the Arbitration Act after 2019 amendment?", "hard"),
            ("Has the Companies Act 2013 been amended?", "medium"),
            ("What are the new provisions for anticipatory bail?", "hard"),
            ("Did the definition of sedition change?", "medium"),
            ("What amendments were made to POCSO Act?", "medium"),
            ("Has the divorce law under Hindu Marriage Act been amended?", "medium"),
            ("What changed in cheque bounce law after Supreme Court judgments?", "hard"),
            ("Are there new provisions for victim compensation in BNSS?", "hard"),
            ("What happened to death penalty for gang rape?", "medium"),
            ("Has the age of consent been changed?", "medium"),
            ("What are the new stalking provisions in IPC?", "medium"),
            ("Did the definition of abetment to suicide change after Sushant Singh case?", "hard"),
            ("What amendments were made to dowry laws?", "medium"),
            ("Has the juvenile justice age been amended?", "medium"),
            ("What changed in arrest procedures under BNSS?", "hard"),
            ("Are there new electronic evidence provisions?", "hard"),
            ("What happened to handcuffs provision in CrPC?", "medium"),
            ("Has the witness protection law been formalized?", "hard"),
            ("What changed in inquiry and trial timelines under BNSS?", "hard"),
            ("Are there new provisions for audio-video recording of statements?", "hard"),
            ("What amendments were made to FIR registration procedures?", "medium"),
            ("Has the plea bargaining provision been amended?", "hard"),
            ("What changed in summons and warrant procedures?", "medium"),
            ("Are there new provisions for forensic investigation?", "hard"),
            ("What happened to Section 377 after Navtej Johar judgment?", "medium"),
            ("Has the definition of criminal breach of trust been amended?", "medium"),
            ("What changed in anticipatory bail for scheduled offenses?", "hard"),
            ("Are there new provisions for crime against children?", "medium"),
            ("What amendments were made to sexual assault laws post-Nirbhaya?", "hard"),
            ("Has the definition of document been expanded for cybercrimes?", "hard"),
            ("What changed in defamation law after recent judgments?", "medium"),
            ("Are there new provisions for victim participation in trials?", "hard"),
        ]
        
        for query_text, difficulty in queries:
            self._add_query("Amendment Specific", query_text, difficulty)
    
    def generate_category4_ipc_to_bns(self):
        """CATEGORY 4: IPC to BNS Transition Queries (50 queries)"""
        print("Generating Category 4: IPC to BNS Transition (50 queries)")
        
        queries = [
            ("What is the BNS equivalent of IPC 420?", "easy"),
            ("Has IPC 302 been replaced?", "easy"),
            ("What changed in the definition of rape from IPC to BNS?", "medium"),
            ("Is IPC still valid or has BNS replaced it completely?", "medium"),
            ("What is IPC 376 called in BNS?", "easy"),
            ("Has the punishment for murder changed in BNS?", "medium"),
            ("What is the BNS equivalent of IPC 498A?", "easy"),
            ("Is theft defined differently in BNS compared to IPC?", "medium"),
            ("What is IPC 307 called in BNS?", "easy"),
            ("Has the definition of cheating changed from IPC to BNS?", "medium"),
            ("What is the BNS section for criminal breach of trust?", "medium"),
            ("Is IPC 354 the same as any BNS section?", "easy"),
            ("What happened to IPC 377 in BNS?", "hard"),
            ("What is the BNS equivalent of IPC 506 (criminal intimidation)?", "easy"),
            ("Has the definition of kidnapping changed in BNS?", "medium"),
            ("What is IPC 120B called in BNS?", "medium"),
            ("Is wrongful confinement defined differently in BNS?", "medium"),
            ("What is the BNS section for defamation?", "medium"),
            ("Has assault definition changed from IPC to BNS?", "medium"),
            ("What is IPC 304B (dowry death) called in BNS?", "medium"),
            ("Is gang rape punishment different in BNS?", "medium"),
            ("What is the BNS equivalent of IPC 147 (rioting)?", "medium"),
            ("Has the definition of hurt changed in BNS?", "medium"),
            ("What is IPC 279 (rash driving) called in BNS?", "easy"),
            ("Is adultery still a crime under BNS?", "medium"),
            ("What is the BNS section for sedition?", "hard"),
            ("Has abetment to suicide changed from IPC to BNS?", "medium"),
            ("What is IPC 411 (dishonestly receiving stolen property) in BNS?", "medium"),
            ("Is forgery defined the same way in BNS?", "medium"),
            ("What is the BNS equivalent of IPC 366 (kidnapping for marriage)?", "medium"),
            ("Has the concept of common intention (IPC 34) changed in BNS?", "hard"),
            ("What is IPC 109 (abetment) called in BNS?", "medium"),
            ("Is voluntarily causing grievous hurt different in BNS?", "medium"),
            ("What is the BNS section for robbery with murder?", "medium"),
            ("Has the definition of a woman been updated in BNS?", "medium"),
            ("What is IPC 201 (destruction of evidence) in BNS?", "hard"),
            ("Is criminal trespass defined differently in BNS?", "medium"),
            ("What is the BNS equivalent of IPC 325?", "easy"),
            ("Has the age of criminal responsibility changed in BNS?", "hard"),
            ("What is IPC 511 (attempt) called in BNS?", "medium"),
            ("Is the definition of public servant different in BNS?", "hard"),
            ("What is the BNS section for eve-teasing (IPC 509)?", "medium"),
            ("Has the concept of mens rea changed in BNS?", "hard"),
            ("What is IPC 141 (unlawful assembly) in BNS?", "medium"),
            ("Is extortion defined the same in BNS?", "medium"),
            ("What is the BNS equivalent of IPC 323 (voluntarily causing hurt)?", "easy"),
            ("Has the punishment for culpable homicide changed in BNS?", "medium"),
            ("What is IPC 406 (criminal breach of trust) called in BNS?", "easy"),
            ("Is the insanity defense different under BNS?", "hard"),
            ("When did BNS come into force replacing IPC?", "easy"),
        ]
        
        for query_text, difficulty in queries:
            self._add_query("IPC to BNS Transition", query_text, difficulty)
    
    def generate_category5_case_law(self):
        """CATEGORY 5: Case Law Search Queries (50 queries)"""
        print("Generating Category 5: Case Law Search (50 queries)")
        
        queries = [
            ("Landmark cases on cheque bounce Section 138", "medium"),
            ("Supreme Court judgment on anticipatory bail principles", "medium"),
            ("Cases on dowry harassment Section 498A IPC", "medium"),
            ("Landmark judgment on right to silence", "hard"),
            ("Supreme Court cases on sedition Section 124A", "hard"),
            ("Important judgments on Section 377 IPC", "medium"),
            ("Cases on adultery Section 497 IPC", "medium"),
            ("Landmark judgment on rape and consent", "hard"),
            ("Supreme Court on interpretation of murder vs culpable homicide", "hard"),
            ("Cases on criminal breach of trust by public servant", "hard"),
            ("Landmark judgment on defamation and free speech", "hard"),
            ("Supreme Court on Section 498A misuse", "medium"),
            ("Cases on triple talaq constitutional validity", "medium"),
            ("Important judgment on right to privacy", "hard"),
            ("Supreme Court on death penalty guidelines", "hard"),
            ("Cases on juvenile age determination", "medium"),
            ("Landmark judgment on custodial torture", "medium"),
            ("Supreme Court on bail is the rule, jail is exception", "medium"),
            ("Cases on Section 66A IT Act constitutionality", "medium"),
            ("Important judgment on live-in relationships", "medium"),
            ("Supreme Court on extraordinary powers under Article 142", "hard"),
            ("Cases on marital rape not being a crime", "hard"),
            ("Landmark judgment on Aadhaar constitutional validity", "medium"),
            ("Supreme Court on abortion rights", "medium"),
            ("Cases on UAPA and terrorism", "hard"),
            ("Important judgment on res judicata in criminal law", "hard"),
            ("Supreme Court on plea bargaining", "medium"),
            ("Cases on compounding of offenses", "medium"),
            ("Landmark judgment on FIR quashing under Section 482", "hard"),
            ("Supreme Court on anticipatory bail for economic offenses", "hard"),
            ("Cases on Section 156(3) CrPC investigation direction", "medium"),
            ("Important judgment on dying declaration evidentiary value", "hard"),
            ("Supreme Court on POCSO Act strict liability", "medium"),
            ("Cases on narco analysis admissibility", "hard"),
            ("Landmark judgment on witness protection", "medium"),
            ("Supreme Court on victim compensation", "medium"),
            ("Cases on Section 313 CrPC statement of accused", "hard"),
            ("Important judgment on adverse inference from silence", "hard"),
            ("Supreme Court on electronic evidence Section 65B", "hard"),
            ("Cases on police custody vs judicial custody", "medium"),
            ("Landmark judgment on right to speedy trial", "medium"),
            ("Supreme Court on principles of natural justice in criminal law", "hard"),
            ("Cases on territorial jurisdiction in cybercrime", "hard"),
            ("Important judgment on entrapment and sting operations", "hard"),
            ("Supreme Court on burden of proof in criminal cases", "medium"),
            ("Cases on circumstantial evidence being sole basis", "hard"),
            ("Landmark judgment on hostile witness", "medium"),
            ("Supreme Court on double jeopardy Article 20", "hard"),
            ("Cases on compulsory self-incrimination", "hard"),
            ("Important judgment on standard of proof beyond reasonable doubt", "hard"),
        ]
        
        for query_text, difficulty in queries:
            self._add_query("Case Law Search", query_text, difficulty)
    
    def generate_category6_overruled_cases(self):
        """CATEGORY 6: Overruled Case Detection Queries (30 queries)"""
        print("Generating Category 6: Overruled Case Detection (30 queries)")
        
        queries = [
            ("Is A.K. Gopalan v State of Madras still good law?", "hard"),
            ("What happened to the judgment in Suresh Kumar Koushal case?", "medium"),
            ("Has ADM Jabalpur v Shukla been overruled?", "hard"),
            ("Is the Joseph Shine judgment on adultery still valid?", "easy"),
            ("What happened to Maneka Gandhi v Union of India?", "medium"),
            ("Has Kesavananda Bharati been overruled?", "hard"),
            ("Is Shreya Singhal v Union of India still good law?", "easy"),
            ("What happened to the Navtej Johar judgment?", "easy"),
            ("Has Vishaka v State of Rajasthan been superseded?", "medium"),
            ("Is the Aruna Shanbaug passive euthanasia judgment still valid?", "medium"),
            ("What happened to the Common Cause judgment on living will?", "medium"),
            ("Has the Lily Thomas judgment on convicted MPs been overruled?", "medium"),
            ("Is Golaknath v State of Punjab still good law?", "hard"),
            ("What happened to the Second Judges Case?", "hard"),
            ("Has the NJAC judgment been challenged?", "medium"),
            ("Is the Puttaswamy right to privacy judgment still valid?", "easy"),
            ("What happened to the Sabarimala temple entry judgment?", "medium"),
            ("Has Shah Bano been effectively overruled by legislation?", "hard"),
            ("Is the Indra Sawhney reservation judgment still good law?", "medium"),
            ("What happened to the Shayara Bano triple talaq judgment?", "easy"),
            ("Has the Mathura rape case judgment been overruled?", "hard"),
            ("Is Bachan Singh on death penalty still valid?", "medium"),
            ("What happened to the Hadiya marriage case?", "medium"),
            ("Has the Section 377 judgment been challenged after decriminalization?", "medium"),
            ("Is the Nirbhaya juvenile convict judgment still good law?", "medium"),
            ("What happened to the Lalita Kumari FIR registration judgment?", "medium"),
            ("Has the Arnesh Kumar arrest guidelines judgment been modified?", "medium"),
            ("Is the Rajesh Sharma 498A guidelines judgment still valid?", "medium"),
            ("What happened to the DK Basu custodial violence guidelines?", "medium"),
            ("Has the Jolly George Varghese civil prison judgment been overruled?", "hard"),
        ]
        
        for query_text, difficulty in queries:
            self._add_query("Overruled Case Detection", query_text, difficulty)
    
    def generate_category7_complex_interpretation(self):
        """CATEGORY 7: Complex Legal Interpretation Queries (40 queries)"""
        print("Generating Category 7: Complex Legal Interpretation (40 queries)")
        
        queries = [
            ("What are the ingredients to prove cheating under IPC 420?", "hard"),
            ("What must prosecution prove in a murder trial?", "hard"),
            ("What is the legal position on anticipatory bail for economic offences?", "hard"),
            ("What are the essential elements of defamation?", "hard"),
            ("What constitutes consent in rape cases under IPC/BNS?", "hard"),
            ("What are the differences between murder and culpable homicide?", "hard"),
            ("What is the test for determining abetment to suicide?", "hard"),
            ("What are the ingredients of criminal breach of trust?", "hard"),
            ("What constitutes a valid FIR under CrPC?", "medium"),
            ("What are the grounds for quashing FIR under Section 482?", "hard"),
            ("What is the difference between bail and anticipatory bail?", "medium"),
            ("What are the legal requirements for dying declaration?", "hard"),
            ("What constitutes cruelty under Section 498A IPC?", "hard"),
            ("What is the test for mens rea in criminal cases?", "hard"),
            ("What are the ingredients of criminal conspiracy?", "hard"),
            ("What constitutes a cognizable vs non-cognizable offense?", "medium"),
            ("What is the difference between bailable and non-bailable offenses?", "medium"),
            ("What are the legal requirements for electronic evidence admissibility?", "hard"),
            ("What constitutes a hostile witness?", "hard"),
            ("What is the difference between examination-in-chief and cross-examination?", "medium"),
            ("What are the legal grounds for seeking divorce under Hindu Marriage Act?", "medium"),
            ("What constitutes dishonest intention under IPC?", "hard"),
            ("What is the difference between theft, robbery, and dacoity?", "medium"),
            ("What are the ingredients of extortion?", "hard"),
            ("What constitutes wrongful confinement vs wrongful restraint?", "medium"),
            ("What is the legal test for obscenity?", "hard"),
            ("What are the elements of criminal intimidation?", "medium"),
            ("What constitutes voluntarily causing hurt vs grievous hurt?", "medium"),
            ("What is the difference between rioting and unlawful assembly?", "medium"),
            ("What are the legal requirements for arrest without warrant?", "hard"),
            ("What constitutes a continuing offense?", "hard"),
            ("What is the doctrine of common intention under Section 34 IPC?", "hard"),
            ("What are the ingredients of forgery?", "hard"),
            ("What constitutes criminal trespass?", "medium"),
            ("What is the difference between robbery with murder and dacoity with murder?", "hard"),
            ("What are the legal grounds for seeking anticipatory bail?", "medium"),
            ("What constitutes valid service of summons?", "hard"),
            ("What is the test for determining juvenile status?", "medium"),
            ("What are the legal requirements for compounding of offenses?", "hard"),
            ("What constitutes a charge sheet under CrPC?", "medium"),
        ]
        
        for query_text, difficulty in queries:
            self._add_query("Complex Legal Interpretation", query_text, difficulty)
    
    def generate_all_categories(self):
        """Generate all 300 queries across 7 categories."""
        self.generate_category1_section_lookup()  # 50
        self.generate_category2_punishment_queries()  # 40
        self.generate_category3_amendment_specific()  # 40
        self.generate_category4_ipc_to_bns()  # 50
        self.generate_category5_case_law()  # 50
        self.generate_category6_overruled_cases()  # 30
        self.generate_category7_complex_interpretation()  # 40
        # Total: 300 queries
    
    def save_to_excel(self, filepath: str):
        """
        Save dataset to Excel with instructions header.
        """
        df = pd.DataFrame(self.queries)
        
        # Create Excel writer
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write instructions on separate sheet
            instructions = pd.DataFrame({
                "INSTRUCTIONS FOR LAWYER VERIFICATION": [
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    "This file must be verified by a qualified lawyer before use in research evaluation.",
                    "",
                    "For EACH ROW, please verify and fill in:",
                    "  1. correct_answer_summary - Brief correct answer (1-2 sentences)",
                    "  2. correct_act - The relevant act (e.g., 'IPC', 'BNS', 'NI Act', 'CrPC')",
                    "  3. correct_section - The section number (e.g., '138', '420', '302')",
                    "  4. correct_citation - Relevant case citation if any (e.g., 'AIR 1978 SC 597')",
                    "  5. amendment_applies - Mark 'yes' or 'no'",
                    "  6. amendment_detail - If yes, describe the amendment",
                    "  7. overruling_applies - Mark 'yes' or 'no'",
                    "  8. overruled_by - If yes, provide overruling case citation",
                    "  9. bns_bnss_transition_applies - Mark 'yes' or 'no'",
                    "  10. bns_bnss_detail - If yes, describe IPC→BNS or CrPC→BNSS transition",
                    "  11. verified_by_lawyer - Sign your name after verification",
                    "  12. lawyer_notes - Any additional notes or concerns",
                    "",
                    "IMPORTANT:",
                    "  - Do NOT modify query_id or query_text columns",
                    "  - Mark difficulty_level as 'easy', 'medium', or 'hard'",
                    "  - Be precise with act names and section numbers",
                    "  - If a query has multiple correct answers, note in lawyer_notes",
                    "  - If a query is ambiguous or unanswerable, note in lawyer_notes",
                    "",
                    f"Dataset generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Total queries: {len(self.queries)}",
                    "Categories: Section Lookup (50), Punishment (40), Amendment (40),",
                    "            IPC→BNS Transition (50), Case Law (50), Overruled Cases (30),",
                    "            Complex Interpretation (40)",
                    "",
                    "After verification, save as: ground_truth_verified.xlsx",
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                ]
            })
            instructions.to_excel(writer, sheet_name='INSTRUCTIONS', index=False)
            
            # Write dataset
            df.to_excel(writer, sheet_name='Ground Truth Dataset', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Ground Truth Dataset']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
        
        print(f"\n✓ Dataset template saved to: {output_path}")
        print(f"  Total queries: {len(self.queries)}")
        print(f"  Categories: 7")
        print(f"  Status: Ready for lawyer verification")
        print(f"\n  Next step: Send this file to a qualified lawyer for verification")
        print(f"  They should fill in all blank columns and save as 'ground_truth_verified.xlsx'")


def main():
    """Generate ground truth dataset template."""
    print("=" * 60)
    print("LexAI Evaluation Dataset Builder")
    print("=" * 60)
    print("\nGenerating 300 evaluation queries across 7 categories...\n")
    
    builder = EvaluationDatasetBuilder()
    builder.generate_all_categories()
    
    output_file = "evaluation/ground_truth_template.xlsx"
    builder.save_to_excel(output_file)
    
    print("\n" + "=" * 60)
    print("Dataset generation complete!")
    print("=" * 60)
    
    # Print category breakdown
    df = pd.DataFrame(builder.queries)
    print("\nCategory Breakdown:")
    print(df['category'].value_counts().sort_index())
    
    print("\nDifficulty Breakdown:")
    print(df['difficulty_level'].value_counts())


if __name__ == "__main__":
    main()
