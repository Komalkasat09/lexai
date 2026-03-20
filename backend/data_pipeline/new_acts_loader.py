"""
New Acts Loader (BNS/BNSS/BSA) - PDF-based approach
=====================================================
The 2023 criminal law transition acts are too new to be fully indexed
on Indian Kanoon. This loader downloads official PDFs from government
sources and extracts sections directly.

Prerequisites:
pip install pymupdf requests

Run: python new_acts_loader.py
"""

import fitz  # PyMuPDF
import requests
import re
import chromadb
import json
import os
import textwrap
from typing import List, Dict

# Official government sources for 2023 acts
# Multiple URLs tried - government sites frequently change URLs
NEW_ACTS_PDFS = [
    {
        "act_name": "Bharatiya Nyaya Sanhita 2023",
        "short_name": "BNS",
        "pdf_urls": [
            "https://www.mha.gov.in/sites/default/files/2023-12/BNS_06122023.pdf",
            "https://prsindia.org/files/bills_acts/bills_parliament/2023/Bharatiya_Nyaya_Sanhita_2023.pdf",
            "https://legislative.gov.in/sites/default/files/BNS2023.pdf",
            "https://mha.gov.in/sites/default/files/BNS_0.pdf",
            "https://egazette.gov.in/WriteReadData/2023/249128.pdf",
        ],
        "total_sections": 358,
        "replaces": "Indian Penal Code 1860",
        "effective_date": "2024-07-01",
        "priority": "CRITICAL"
    },
    {
        "act_name": "Bharatiya Nagarik Suraksha Sanhita 2023",
        "short_name": "BNSS",
        "pdf_urls": [
            "https://www.mha.gov.in/sites/default/files/2023-12/BNSS_06122023.pdf",
            "https://prsindia.org/files/bills_acts/bills_parliament/2023/Bharatiya_Nagarik_Suraksha_Sanhita_2023.pdf",
            "https://legislative.gov.in/sites/default/files/BNSS2023.pdf",
            "https://mha.gov.in/sites/default/files/BNSS_0.pdf",
            "https://egazette.gov.in/WriteReadData/2023/249129.pdf",
        ],
        "total_sections": 531,
        "replaces": "Code of Criminal Procedure 1973",
        "effective_date": "2024-07-01",
        "priority": "CRITICAL"
    },
    {
        "act_name": "Bharatiya Sakshya Adhiniyam 2023",
        "short_name": "BSA",
        "pdf_urls": [
            "https://www.mha.gov.in/sites/default/files/2023-12/BSA_06122023.pdf",
            "https://prsindia.org/files/bills_acts/bills_parliament/2023/Bharatiya_Sakshya_Adhiniyam_2023.pdf",
            "https://legislative.gov.in/sites/default/files/BSA2023.pdf",
            "https://mha.gov.in/sites/default/files/BSA_0.pdf",
            "https://egazette.gov.in/WriteReadData/2023/249130.pdf",
        ],
        "total_sections": 170,
        "replaces": "Indian Evidence Act 1872",
        "effective_date": "2024-07-01",
        "priority": "CRITICAL"
    },
]


def download_and_extract_act(act_info: Dict) -> List[Dict]:
    """
    Download official government PDF and extract sections.
    Far more reliable than scraping for new acts.
    """
    # Setup paths
    pdf_path = f"data/backup/pdfs/{act_info['short_name']}.pdf"
    os.makedirs('data/backup/pdfs', exist_ok=True)
    
    # Check if PDF already exists (manually placed)
    if os.path.exists(pdf_path):
        pdf_size = os.path.getsize(pdf_path)
        print(f"  ✓ Found existing PDF: {pdf_size:,} bytes")
        print(f"  Skipping download - using manually placed file")
        pdf_downloaded = True
    else:
        # Try to download PDF
        pdf_downloaded = False
        
        for idx, url in enumerate(act_info['pdf_urls'], 1):
            try:
                print(f"  [{idx}/{len(act_info['pdf_urls'])}] Trying: {url}")
                response = requests.get(url, timeout=60, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }, allow_redirects=True)
                
                if response.status_code == 200 and len(response.content) > 10000:  # At least 10KB
                    with open(pdf_path, 'wb') as f:
                        f.write(response.content)
                    print(f"  ✓ Downloaded: {len(response.content):,} bytes from source {idx}")
                    pdf_downloaded = True
                    break
                else:
                    print(f"  ✗ HTTP {response.status_code} or file too small ({len(response.content)} bytes)")
                    
            except Exception as e:
                print(f"  ✗ Failed: {str(e)[:100]}")
                continue
    
    # Check if PDF exists (either downloaded or manually placed)
    if not os.path.exists(pdf_path):
        if not pdf_downloaded:
            print(f"\n  ⚠ MANUAL STEP REQUIRED:")
            print(f"  Could not auto-download {act_info['act_name']}")
            print(f"  Please download PDF manually and save to:")
            print(f"  {os.path.abspath(pdf_path)}")
            print(f"\n  Sources tried ({len(act_info['pdf_urls'])}):")
            for idx, url in enumerate(act_info['pdf_urls'], 1):
                print(f"    {idx}. {url}")
            print(f"\n  Alternative: Search 'site:egazette.gov.in {act_info['act_name']}'")
            return []
    
    # Extract text from PDF
    print(f"  Extracting text from PDF...")
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            full_text += page_text
            
            if (page_num + 1) % 10 == 0:
                print(f"    Processed {page_num + 1}/{len(doc)} pages...")
        
        total_pages = len(doc)
        doc.close()
        
        print(f"  ✓ Extracted {len(full_text):,} characters from {total_pages} pages")
        
    except Exception as e:
        print(f"  ✗ PDF extraction failed: {e}")
        return []
    
    # Parse sections
    print(f"  Parsing sections...")
    sections = parse_sections_from_text(full_text, act_info)
    
    return sections


def parse_sections_from_text(text: str, act_info: Dict) -> List[Dict]:
    """
    Parse individual sections from act text.
    Handles the formatting of Indian legislation PDFs.
    """
    sections = []
    
    # Clean text first
    text = text.replace('\n\n\n', '\n\n')
    text = re.sub(r' +', ' ', text)
    
    # For 2023 acts: Split by lines that start with just a number and period
    # e.g., "1.", "2.", "63.", etc.
    # This handles BNS/BNSS/BSA format better
    section_splits = re.split(r'\n\s*(\d+)\.\s+', text)
    
    # section_splits will be: ['preamble', '1', 'section 1 content', '2', 'section 2 content', ...]
    if len(section_splits) > 20:  # Good split - found many sections
        print(f"    Using 2023 acts format (found {(len(section_splits)-1)//2} sections)")
        
        for i in range(1, len(section_splits), 2):
            if i+1 >= len(section_splits):
                break
                
            section_num = section_splits[i].strip()
            section_content = section_splits[i+1].strip()
            
            # Skip very short sections (likely formatting artifacts)
            if len(section_content) < 50:
                continue
            
            # Extract title from first line/sentence
            first_line = section_content.split('\n')[0].strip()
            # Try to get a meaningful title from content
            if len(first_line) > 150:
                section_title = first_line[:147] + "..."
            else:
                section_title = first_line
            
            # Limit body length
            if len(section_content) > 3000:
                section_body = section_content[:3000] + "..."
            else:
                section_body = section_content
            
            # Extract punishment if present
            punishment = None
            punishment_patterns = [
                r'(?:shall be punished?|punishable|imprisonment|rigorous imprisonment|fine)[^.]{0,300}\.',
                r'penalty[^.]{0,200}\.',
            ]
            
            for pattern in punishment_patterns:
                punishment_match = re.search(pattern, section_body[:1000], re.IGNORECASE)
                if punishment_match:
                    punishment = punishment_match.group(0).strip()
                    break
            
            section_doc = {
                "id": f"{act_info['short_name']}_{section_num}",
                "act_name": act_info['act_name'],
                "short_name": act_info['short_name'],
                "section_number": section_num,
                "section_title": section_title,
                "full_text": f"{section_num}. {section_title}\n{section_body}",
                "punishment": punishment,
                "is_replaced": False,
                "replaces_act": act_info.get('replaces'),
                "effective_date": act_info.get('effective_date'),
                "source": "official_government_pdf",
                "priority": act_info.get('priority', 'CRITICAL'),
                "embedding_text": (
                    f"{act_info['act_name']} Section {section_num}. "
                    f"{section_title[:100]}. {section_body[:300]}"
                )
            }
            
            if punishment:
                section_doc['punishment'] = punishment
            
            sections.append(section_doc)
        
        return sections
    
    # Fall back to old pattern matching for other acts
    # Multiple patterns to try for section detection
    # Pattern 1: "1." at start of line with title
    pattern1 = re.compile(
        r'(?:^|\n)\s*(\d+[A-Z]?)\.\s+([A-Z][^\n]{10,150}?)[.\-—]\s*\n(.*?)(?=\n\s*\d+[A-Z]?\.\s+[A-Z]|\Z)',
        re.DOTALL | re.MULTILINE
    )
    
    # Pattern 2: More relaxed - just "Section XXX"
    pattern2 = re.compile(
        r'(?:^|\n)\s*(?:Section|Sec\.?|SECTION)\s+(\d+[A-Z]?)[\.:\-–—]\s+([^\n]{10,150}?)\n(.*?)(?=\n\s*(?:Section|SECTION)\s+\d+|\Z)',
        re.DOTALL | re.MULTILINE | re.IGNORECASE
    )
    
    # Try pattern 1 first
    matches = list(pattern1.finditer(text))
    
    if len(matches) < 10:
        # Try pattern 2
        matches = list(pattern2.finditer(text))
        print(f"    Using pattern 2 (found {len(matches)} sections)")
    else:
        print(f"    Using pattern 1 (found {len(matches)} sections)")
    
    for match in matches:
        try:
            section_num = match.group(1).strip()
            section_title = match.group(2).strip()
            section_body = match.group(3).strip()
            
            # Clean title
            section_title = re.sub(r'\s+', ' ', section_title)
            section_title = section_title.rstrip('.-–—')
            
            # Skip very short matches (formatting artifacts)
            if len(section_body) < 30:
                continue
            
            # Limit body length for embedding
            if len(section_body) > 3000:
                section_body = section_body[:3000] + "..."
            
            # Extract punishment if present (for criminal law)
            punishment = None
            punishment_patterns = [
                r'(?:shall be punished?|punishable|imprisonment|rigorous imprisonment|fine)[^.]{0,300}\.',
                r'penalty[^.]{0,200}\.',
            ]
            
            for pattern in punishment_patterns:
                punishment_match = re.search(pattern, section_body[:1000], re.IGNORECASE)
                if punishment_match:
                    punishment = punishment_match.group(0).strip()
                    break
            
            section_doc = {
                "id": f"{act_info['short_name']}_{section_num}",
                "act_name": act_info['act_name'],
                "short_name": act_info['short_name'],
                "section_number": section_num,
                "section_title": section_title,
                "full_text": f"{section_num}. {section_title}\n{section_body}",
                "punishment": punishment,
                "is_replaced": False,
                "replaces_act": act_info.get('replaces'),
                "effective_date": act_info.get('effective_date'),
                "source": "official_government_pdf",
                "priority": act_info.get('priority', 'CRITICAL'),
                "embedding_text": (
                    f"{act_info['act_name']} Section {section_num}. "
                    f"{section_title}. {section_body[:400]}"
                )
            }
            
            sections.append(section_doc)
            
        except Exception as e:
            print(f"    Warning: Failed to parse section: {e}")
            continue
    
    print(f"  ✓ Parsed {len(sections)} sections")
    
    return sections


def load_new_acts_to_chromadb():
    """
    Main function: download, parse, and load all 2023 acts.
    """
    print("\n" + "="*60)
    print("NEW ACTS LOADER (BNS/BNSS/BSA)")
    print("Loading 2023 Criminal Law Transition Acts from PDFs")
    print("="*60 + "\n")
    
    client = chromadb.PersistentClient(path='./legal_research_db')
    
    try:
        collection = client.get_collection('bare_acts')
        print(f"Found existing bare_acts collection with {collection.count()} documents\n")
    except:
        collection = client.create_collection('bare_acts')
        print("Created new bare_acts collection\n")
    
    total_loaded = 0
    successful = []
    failed = []
    
    for idx, act_info in enumerate(NEW_ACTS_PDFS, 1):
        print(f"\n[{idx}/{len(NEW_ACTS_PDFS)}] Processing: {act_info['act_name']}")
        print(f"Expected sections: ~{act_info['total_sections']}")
        print("-" * 60)
        
        # Check if already loaded
        try:
            existing = collection.get(
                where={"act_name": {"$eq": act_info['act_name']}}
            )
            if existing and len(existing['ids']) > 50:
                print(f"  ✓ Already loaded ({len(existing['ids'])} sections). Skipping.")
                successful.append(act_info['act_name'])
                total_loaded += len(existing['ids'])
                continue
        except Exception as e:
            print(f"  Warning: Could not check existing: {e}")
        
        # Download and extract
        sections = download_and_extract_act(act_info)
        
        if not sections:
            print(f"  ✗ No sections extracted")
            failed.append(act_info['act_name'])
            continue
        
        # Save backup JSON
        backup_path = f"data/backup/bare_acts/{act_info['short_name']}.json"
        os.makedirs('data/backup/bare_acts', exist_ok=True)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump({
                "act_info": act_info,
                "total_sections": len(sections),
                "sections": sections
            }, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ Backup saved: {backup_path}")
        
        # Load to ChromaDB in batches
        batch_size = 50
        loaded_count = 0
        
        for i in range(0, len(sections), batch_size):
            batch = sections[i:i+batch_size]
            
            ids = [s['id'] for s in batch]
            documents = [s['embedding_text'] for s in batch]
            metadatas = [
                {k: v for k, v in s.items()
                 if k != 'embedding_text' and v is not None
                 and isinstance(v, (str, int, float, bool))}
                for s in batch
            ]
            
            try:
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
                loaded_count += len(batch)
            except Exception as e:
                print(f"  ✗ Batch error: {e}")
        
        print(f"  ✓ Loaded {loaded_count} sections to database")
        total_loaded += loaded_count
        successful.append(act_info['act_name'])
    
    # Final summary
    print("\n" + "="*60)
    print("LOADING COMPLETE")
    print("="*60)
    print(f"Total sections loaded: {total_loaded}")
    print(f"Collection count: {collection.count()}")
    print()
    print(f"Successfully loaded: {len(successful)} acts")
    for act in successful:
        print(f"  ✓ {act}")
    
    if failed:
        print(f"\nFailed: {len(failed)} acts")
        for act in failed:
            print(f"  ✗ {act}")
    
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    
    # Test BNS section query
    try:
        results = collection.query(
            query_texts=["Section 63 rape punishment BNS"],
            n_results=3
        )
        
        print("\nTest query: 'Section 63 rape punishment BNS'")
        print("Top results:")
        for i, meta in enumerate(results['metadatas'][0], 1):
            print(f"  {i}. {meta.get('act_name')} Section {meta.get('section_number')}: {meta.get('section_title', 'N/A')[:60]}")
    except Exception as e:
        print(f"\n⚠ Verification query failed: {e}")


if __name__ == "__main__":
    load_new_acts_to_chromadb()
