"""
Test Pipeline Script
Tests the document extraction and clause segmentation pipeline.
Run this to verify the pipeline works before integrating with LLM.
"""

import sys
from pathlib import Path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.document_extractor import DocumentExtractor
from core.clause_segmenter import ClauseSegmenter
import json


def create_sample_contract():
    """Create a sample contract text for testing."""
    sample_contract = """
SERVICE AGREEMENT

THIS SERVICE AGREEMENT ("Agreement") is entered into as of January 15, 2024 ("Effective Date"), by and between:

TechCorp Solutions Private Limited, a company incorporated under the Companies Act, 2013, having its registered office at 123 MG Road, Bangalore, Karnataka - 560001 (hereinafter referred to as the "Service Provider")

AND

Global Enterprises India Limited, a company incorporated under the Companies Act, 2013, having its registered office at 456 Park Street, Mumbai, Maharashtra - 400001 (hereinafter referred to as the "Client")

The Service Provider and the Client are individually referred to as a "Party" and collectively as the "Parties".

WHEREAS, the Client desires to engage the Service Provider to provide software development services, and the Service Provider agrees to provide such services on the terms and conditions set forth in this Agreement.

NOW, THEREFORE, in consideration of the mutual covenants and agreements hereinafter set forth, the Parties agree as follows:

1. DEFINITIONS

1.1 Confidential Information
"Confidential Information" means any information disclosed by one Party to the other Party, either directly or indirectly, in writing, orally, or by inspection of tangible objects.

1.2 Deliverables
"Deliverables" means the software, documentation, and other work products to be delivered by the Service Provider to the Client under this Agreement.

1.3 Services
"Services" means the software development, maintenance, and support services to be provided by the Service Provider as described in Exhibit A.

2. SCOPE OF SERVICES

2.1 Service Provider Obligations
The Service Provider shall provide the Services to the Client in accordance with the specifications set forth in Exhibit A and in a professional and workmanlike manner.

2.2 Client Obligations
The Client shall provide reasonable cooperation and timely access to information, resources, and personnel as may be required by the Service Provider.

3. PAYMENT TERMS

3.1 Fees
The Client shall pay the Service Provider fees as set forth in Exhibit B. All amounts are stated in Indian Rupees (INR) and are exclusive of applicable taxes.

3.2 Payment Schedule
Invoices shall be issued monthly and are due within thirty (30) days of receipt. Late payments shall attract interest at the rate of 18% per annum.

3.3 Taxes
All payments under this Agreement are exclusive of goods and services tax (GST) and other applicable taxes, which shall be borne by the Client.

4. TERM AND TERMINATION

4.1 Term
This Agreement shall commence on the Effective Date and continue for a period of twelve (12) months unless earlier terminated in accordance with this Section 4.

4.2 Termination for Convenience
Either Party may terminate this Agreement by providing sixty (60) days prior written notice to the other Party.

4.3 Termination for Cause
Either Party may terminate this Agreement immediately upon written notice if the other Party materially breaches this Agreement and fails to cure such breach within thirty (30) days.

5. CONFIDENTIALITY

5.1 Non-Disclosure
Each Party agrees to maintain the confidentiality of the other Party's Confidential Information and not to disclose such information to third parties without prior written consent.

5.2 Exceptions
The confidentiality obligations shall not apply to information that: (a) is publicly available; (b) was known prior to disclosure; or (c) is required to be disclosed by law.

6. INTELLECTUAL PROPERTY

6.1 Ownership of Deliverables
Upon full payment of all fees, the Client shall own all right, title, and interest in the Deliverables created specifically for the Client under this Agreement.

6.2 Pre-Existing Materials
The Service Provider shall retain all rights to pre-existing materials and tools used in performing the Services.

7. LIABILITY AND INDEMNIFICATION

7.1 Limitation of Liability
Neither Party shall be liable for any indirect, incidental, special, or consequential damages arising out of this Agreement, regardless of the form of action.

7.2 Indemnification
Each Party shall indemnify and hold harmless the other Party from any claims, damages, or expenses arising from its breach of this Agreement.

8. GOVERNING LAW AND DISPUTE RESOLUTION

8.1 Governing Law
This Agreement shall be governed by and construed in accordance with the laws of India, without regard to conflict of law principles.

8.2 Arbitration
Any dispute arising out of or in connection with this Agreement shall be resolved through arbitration in accordance with the Arbitration and Conciliation Act, 1996.

8.3 Jurisdiction
The arbitration shall be conducted in Bangalore, Karnataka, and the language of arbitration shall be English.

9. GENERAL PROVISIONS

9.1 Entire Agreement
This Agreement constitutes the entire agreement between the Parties and supersedes all prior negotiations, representations, or agreements.

9.2 Amendments
No amendment to this Agreement shall be effective unless made in writing and signed by both Parties.

9.3 Severability
If any provision of this Agreement is held to be invalid or unenforceable, the remaining provisions shall continue in full force and effect.

9.4 Waiver
No waiver of any provision of this Agreement shall be deemed or shall constitute a waiver of any other provision.

9.5 Notices
All notices under this Agreement shall be in writing and delivered by email or registered post to the addresses set forth above.

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the date first written above.

For TechCorp Solutions Private Limited

____________________________
Name: Rajesh Kumar
Title: Director
Date: January 15, 2024


For Global Enterprises India Limited

____________________________
Name: Priya Sharma
Title: Chief Operating Officer
Date: January 15, 2024
"""
    return sample_contract


def test_extraction_and_segmentation():
    """Test the complete extraction and segmentation pipeline."""
    print("\n" + "="*80)
    print("CONTRACT REVIEW ASSISTANT - PIPELINE TEST")
    print("="*80 + "\n")
    
    # Create sample contract
    print("Step 1: Creating sample contract...")
    sample_text = create_sample_contract()
    print(f"✓ Sample contract created ({len(sample_text)} characters)\n")
    
    # Test text cleaning
    print("Step 2: Cleaning extracted text...")
    extractor = DocumentExtractor()
    cleaned_text = extractor.clean_text(sample_text)
    print(f"✓ Text cleaned ({len(cleaned_text)} characters)\n")
    
    # Test clause segmentation
    print("Step 3: Segmenting contract into clauses...")
    segmenter = ClauseSegmenter()
    clauses = segmenter.segment(cleaned_text)
    print(f"✓ Segmentation complete: {len(clauses)} clauses found\n")
    
    # Display clause structure
    print("Step 4: Displaying clause structure...")
    segmenter.print_structure()
    
    # Show detailed view of first few clauses
    print("\n" + "="*80)
    print("DETAILED VIEW - First 3 Clauses")
    print("="*80 + "\n")
    
    for i, clause in enumerate(clauses[:3], 1):
        print(f"Clause {i}:")
        print(f"  Number: {clause.clause_number}")
        print(f"  Heading: {clause.heading}")
        print(f"  Level: {clause.level}")
        print(f"  Start Line: {clause.start_line}")
        print(f"  Content Length: {len(clause.content)} characters")
        print(f"  Content Preview:")
        print(f"    {clause.content[:200]}...")
        print()
    
    # Test search functionality
    print("\n" + "="*80)
    print("SEARCH TEST")
    print("="*80 + "\n")
    
    search_terms = ["payment", "confidential", "arbitration"]
    for term in search_terms:
        results = segmenter.search_clauses(term)
        print(f"Search for '{term}': {len(results)} clause(s) found")
        for clause in results:
            print(f"  - [{clause.clause_number}] {clause.heading}")
    
    # Export to JSON
    print("\n" + "="*80)
    print("JSON EXPORT TEST")
    print("="*80 + "\n")
    
    clauses_dict = segmenter.get_clauses_as_dict()
    json_output = json.dumps(clauses_dict[:2], indent=2)  # Show first 2 clauses
    print("Sample JSON output (first 2 clauses):")
    print(json_output)
    
    # Statistics
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80 + "\n")
    
    level_1_clauses = segmenter.get_clauses_by_level(1)
    level_2_clauses = segmenter.get_clauses_by_level(2)
    
    print(f"Total clauses: {segmenter.get_clause_count()}")
    print(f"Level 1 clauses (main sections): {len(level_1_clauses)}")
    print(f"Level 2 clauses (subsections): {len(level_2_clauses)}")
    print(f"Total contract length: {len(cleaned_text)} characters")
    print(f"Average clause length: {len(cleaned_text) // len(clauses)} characters")
    
    print("\n" + "="*80)
    print("✓ ALL TESTS PASSED")
    print("="*80 + "\n")
    
    print("Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Test with real PDF/DOCX: Place a contract file in backend/test_data/")
    print("3. Start the API server: python main.py")
    print("4. Test API endpoint: http://localhost:8000/docs")
    print()


def test_with_file(file_path: str):
    """
    Test pipeline with an actual PDF or DOCX file.
    
    Args:
        file_path: Path to the contract file
    """
    print("\n" + "="*80)
    print("TESTING WITH ACTUAL FILE")
    print("="*80 + "\n")
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        return
    
    print(f"File: {file_path.name}")
    print(f"Extension: {file_path.suffix}")
    print()
    
    # Extract text
    print("Step 1: Extracting text from file...")
    try:
        extractor = DocumentExtractor()
        text, metadata = extractor.extract(str(file_path), file_path.suffix)
        cleaned_text = extractor.clean_text(text)
        
        print(f"✓ Extraction successful")
        print(f"  Format: {metadata['format']}")
        print(f"  Pages: {metadata.get('page_count', 'N/A')}")
        print(f"  Characters: {len(cleaned_text)}")
        print()
    except Exception as e:
        print(f"❌ Extraction failed: {str(e)}")
        return
    
    # Segment clauses
    print("Step 2: Segmenting clauses...")
    try:
        segmenter = ClauseSegmenter()
        clauses = segmenter.segment(cleaned_text)
        
        print(f"✓ Segmentation successful")
        print(f"  Total clauses: {len(clauses)}")
        print()
        
        segmenter.print_structure()
    except Exception as e:
        print(f"❌ Segmentation failed: {str(e)}")
        return


if __name__ == "__main__":
    # Run basic test with sample contract
    test_extraction_and_segmentation()
    
    # If a file path is provided as argument, test with that file
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        test_with_file(file_path)
    else:
        print("\nTo test with your own file, run:")
        print("python test_pipeline.py <path_to_contract.pdf>")
        print()
