"""
Real Judgment Loader for LexAI
===============================
Loads real Supreme Court and High Court judgments.
Source 1: Hugging Face datasets (real judgment text)
Source 2: Indian Kanoon (landmark cases)

Current case_law has 12,808 Q&A pairs (synthetic).
This script adds REAL judgment text alongside them.

Prerequisites:
pip install datasets
pip install playwright
playwright install chromium

Run: python judgment_loader.py
"""

import asyncio
from playwright.async_api import async_playwright
import chromadb
import json
import os
import random
import re
from typing import List, Dict, Optional
from groq import Groq


# ============================================================
# LANDMARK CASES TO SCRAPE
# ============================================================
LANDMARK_CASES = [
    # Constitutional Law Landmarks
    "Kesavananda Bharati v State of Kerala AIR 1973 SC 1461",
    "Maneka Gandhi v Union of India AIR 1978 SC 597",
    "Minerva Mills v Union of India AIR 1980 SC 1789",
    "K.S. Puttaswamy v Union of India 2017 10 SCC 1",
    "SR Bommai v Union of India AIR 1994 SC 1918",
    
    # Criminal Law Landmarks
    "Bachan Singh v State of Punjab AIR 1980 SC 898",
    "Machhi Singh v State of Punjab AIR 1983 SC 957",
    "Navtej Singh Johar v Union of India 2018 10 SCC 1",
    "Joseph Shine v Union of India 2018 14 SCC 350",
    "Shreya Singhal v Union of India 2015 5 SCC 1",
    
    # Criminal Procedure Landmarks
    "Arnesh Kumar v State of Bihar 2014 8 SCC 273",
    "Lalita Kumari v Government of UP 2014 2 SCC 1",
    "D.K. Basu v State of West Bengal AIR 1997 SC 610",
    "Sanjay Chandra v CBI 2012 1 SCC 40",
    "Satender Kumar Antil v CBI 2022 10 SCC 51",
    
    # Cheque Bounce Landmarks
    "Dashrath Rupsingh Rathod v State of Maharashtra 2014 9 SCC 129",
    "Meters and Instruments v Kanchan Mehta 2018 1 SCC 492",
    "Kumar Exports v Sharma Carpets 2009 2 SCC 513",
    
    # Evidence Law
    "State of Punjab v Gurmit Singh AIR 1996 SC 1393",
    "Selvi v State of Karnataka 2010 7 SCC 263",
    "Arjun Panditrao Khotkar v Kailash Gorantyal 2020 7 SCC 1",
    
    # Contract and Property
    "Satyabrata Ghose v Mugneeram Bangur AIR 1954 SC 44",
    "Vidya Drolia v Durga Trading Corporation 2021 2 SCC 1",
    
    # Domestic Violence / Family
    "Hiral P. Harsora v Kusum Harsora 2016 10 SCC 165",
    "Indra Sarma v V.K.V. Sarma 2013 15 SCC 755",
    "Vishaka v State of Rajasthan AIR 1997 SC 3011",
    
    # Service Law
    "Secretary State of Karnataka v Umadevi 2006 4 SCC 1",
    
    # Tax Law
    "Vodafone International v Union of India 2012 6 SCC 613",
    
    # Company Law
    "Innovative Industries v ICICI Bank 2017 8 SCC 781",
]


def load_real_judgments_huggingface():
    """
    Load real judgment datasets from Hugging Face.
    Multiple datasets containing actual Indian court judgments.
    """
    client = chromadb.PersistentClient(path='./legal_research_db')
    
    try:
        collection = client.get_collection('case_law')
        print(f"Found existing case_law collection with {collection.count()} documents")
    except:
        collection = client.create_collection('case_law')
        print("Created new case_law collection")
    
    loaded = 0
    
    # Dataset 1: Try multi_legal_pile India subset
    try:
        print("\n" + "="*60)
        print("Loading Dataset 1: multi_legal_pile (Indian Legal Documents)")
        print("="*60)
        
        from datasets import load_dataset
        
        dataset = load_dataset(
            "joelito/multi_legal_pile",
            "in",  # India subset
            split="train",
            streaming=True
        )
        
        for idx, item in enumerate(dataset):
            if loaded >= 3000:  # Limit to 3000 from this dataset
                break
            
            text = item.get('text', '')
            
            if len(text) < 500:
                continue
            
            # Chunk long judgments into manageable pieces
            chunks = chunk_judgment(text, chunk_size=600, overlap=100)
            
            for i, chunk in enumerate(chunks):
                doc_id = f"MLEG_{loaded}_{i}"
                
                # Extract metadata from text
                court = extract_court(chunk)
                year = extract_year(chunk)
                citation = extract_citation(chunk)
                acts = extract_acts(chunk)
                
                try:
                    collection.add(
                        ids=[doc_id],
                        documents=[chunk],
                        metadatas=[{
                            "type": "case_law",
                            "source": "multi_legal_pile_india",
                            "chunk_number": i,
                            "total_chunks": len(chunks),
                            "is_real_judgment": True,
                            "court": court,
                            "year": year,
                            "citation": citation,
                            "acts_referred": str(acts),
                            "is_overruled": False
                        }]
                    )
                except:
                    # Upsert if exists
                    collection.upsert(
                        ids=[doc_id],
                        documents=[chunk],
                        metadatas=[{
                            "type": "case_law",
                            "source": "multi_legal_pile_india",
                            "is_real_judgment": True,
                            "is_overruled": False
                        }]
                    )
            
            loaded += 1
            
            if loaded % 100 == 0:
                print(f"  Loaded {loaded} judgments, {collection.count()} total docs in DB")
        
        print(f"  ✓ Loaded {loaded} judgments from multi_legal_pile")
        
    except Exception as e:
        print(f"  ⚠ multi_legal_pile failed: {str(e)[:200]}")
        print("  Trying alternative datasets...")
        
        # Fallback Dataset: Indian Legal Bert Dataset
        try:
            print("\nTrying fallback: InLegalBERT dataset...")
            dataset = load_dataset(
                "law-ai/indian_legal_nlp",
                split="train",
                streaming=True
            )
            
            for idx, item in enumerate(dataset):
                if loaded >= 2000:
                    break
                
                text = item.get('text', item.get('content', ''))
                
                if len(text) < 300:
                    continue
                
                chunks = chunk_judgment(text, chunk_size=600, overlap=100)
                
                for i, chunk in enumerate(chunks):
                    doc_id = f"ILBERT_{loaded}_{i}"
                    
                    try:
                        collection.add(
                            ids=[doc_id],
                            documents=[chunk],
                            metadatas=[{
                                "type": "case_law",
                                "source": "indian_legal_nlp",
                                "is_real_judgment": True,
                                "is_overruled": False,
                                "chunk_number": i
                            }]
                        )
                    except:
                        pass
                
                loaded += 1
                
                if loaded % 100 == 0:
                    print(f"  Loaded {loaded} judgments")
            
            print(f"  ✓ Loaded {loaded} judgments from fallback dataset")
            
        except Exception as e2:
            print(f"  ⚠ Fallback also failed: {str(e2)[:200]}")
    
    print(f"\n{'='*60}")
    print(f"Total judgments loaded from HuggingFace: {loaded}")
    print(f"Collection count: {collection.count()}")
    print(f"{'='*60}")
    
    return collection


def load_landmark_cases_kanoon():
    """
    Scrape specific landmark cases from Indian Kanoon.
    These are the most important cases for legal research.
    """
    print("\n" + "="*60)
    print("Loading Landmark Cases from Indian Kanoon")
    print(f"Total cases to scrape: {len(LANDMARK_CASES)}")
    print("="*60)
    
    asyncio.run(_scrape_landmark_cases(LANDMARK_CASES))


async def _scrape_landmark_cases(cases: List[str]):
    """
    Asynchronously scrape all landmark cases.
    """
    client = chromadb.PersistentClient(path='./legal_research_db')
    
    try:
        collection = client.get_collection('case_law')
    except:
        collection = client.create_collection('case_law')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        for idx, case_query in enumerate(cases, 1):
            print(f"\n[{idx}/{len(cases)}] Scraping: {case_query[:60]}...")
            
            page = await context.new_page()
            
            try:
                # Check if already loaded
                safe_name = case_query[:40].replace(' ', '_').replace('/', '_')
                existing = collection.get(
                    where={"case_name": {"$contains": case_query[:20]}}
                )
                
                if existing and len(existing['ids']) > 0:
                    print(f"  ✓ Already in database. Skipping.")
                    await page.close()
                    continue
                
                # Search Indian Kanoon
                search_url = (
                    f"https://indiankanoon.org/search/"
                    f"?formInput={case_query.replace(' ', '+')}"
                )
                await page.goto(search_url, wait_until='networkidle', timeout=60000)
                await asyncio.sleep(random.uniform(5, 8))
                
                # Click first result
                first = await page.query_selector('.result a, .result_title a')
                if not first:
                    print(f"  ✗ Not found on Indian Kanoon")
                    await page.close()
                    continue
                
                case_name = await first.text_content()
                case_url = await first.get_attribute('href')
                print(f"  Opening: {case_name[:50]}...")
                
                await first.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(random.uniform(5, 8))
                
                # Extract full judgment text
                content = None
                for selector in ['.doc_content', '#doc_content', 'pre', '.judgment', 'article']:
                    try:
                        content = await page.query_selector(selector)
                        if content:
                            break
                    except:
                        continue
                
                if not content:
                    print(f"  ✗ Could not extract content")
                    await page.close()
                    continue
                
                full_text = await content.text_content()
                
                if len(full_text) < 500:
                    print(f"  ✗ Text too short ({len(full_text)} chars)")
                    await page.close()
                    continue
                
                # Extract metadata
                citation = extract_citation(full_text)
                year = extract_year(full_text)
                court = extract_court(full_text)
                acts = extract_acts(full_text)
                
                # Generate structured summary using Groq (for landmark cases only)
                summary = await generate_case_summary(full_text[:5000])
                
                # Chunk and store
                chunks = chunk_judgment(full_text, chunk_size=700, overlap=100)
                
                print(f"  Loaded {len(chunks)} chunks")
                
                for i, chunk in enumerate(chunks):
                    doc_id = f"LANDMARK_{citation or case_name[:20]}_{i}".replace(' ', '_').replace('/', '_')
                    
                    try:
                        collection.add(
                            ids=[doc_id],
                            documents=[chunk],
                            metadatas=[{
                                "case_name": case_name.strip()[:500],
                                "citation": citation or "",
                                "court": court or "Supreme Court of India",
                                "year": year or "",
                                "acts_referred": str(acts)[:500],
                                "chunk_number": i,
                                "total_chunks": len(chunks),
                                "is_landmark": True,
                                "is_real_judgment": True,
                                "is_overruled": False,
                                "type": "case_law",
                                "source": "indiankanoon.org",
                                "source_url": f"https://indiankanoon.org{case_url}" if case_url else "",
                                "facts_summary": summary.get('facts', '')[:500],
                                "held_summary": summary.get('held', '')[:500],
                                "legal_principle": summary.get('principle', '')[:500]
                            }]
                        )
                    except Exception as e:
                        # Try upsert
                        try:
                            collection.upsert(
                                ids=[doc_id],
                                documents=[chunk],
                                metadatas=[{
                                    "case_name": case_name.strip()[:500],
                                    "is_landmark": True,
                                    "is_real_judgment": True,
                                    "source": "indiankanoon.org"
                                }]
                            )
                        except:
                            pass
                
                # Save backup
                os.makedirs('data/backup/landmarks', exist_ok=True)
                safe_name = case_query[:30].replace(' ', '_').replace('/', '_')
                with open(f'data/backup/landmarks/{safe_name}.json', 'w', encoding='utf-8') as f:
                    json.dump({
                        "case_name": case_name,
                        "citation": citation,
                        "court": court,
                        "year": year,
                        "full_text": full_text[:10000],  # Save first 10k chars
                        "summary": summary,
                        "chunks_count": len(chunks)
                    }, f, ensure_ascii=False, indent=2)
                
                print(f"  ✓ Saved to database and backup")
                
            except Exception as e:
                print(f"  ✗ Error: {str(e)[:100]}")
            finally:
                await page.close()
            
            # Respectful delay between cases
            await asyncio.sleep(random.uniform(10, 20))
        
        await context.close()
        await browser.close()
    
    print(f"\n{'='*60}")
    print(f"Landmark cases loading complete")
    print(f"Collection count: {collection.count()}")
    print(f"{'='*60}")


def chunk_judgment(text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
    """
    Split judgment into overlapping chunks.
    Respects paragraph boundaries where possible.
    """
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk_text = ' '.join(chunk_words)
        chunks.append(chunk_text)
        i += chunk_size - overlap
    
    return chunks


def extract_citation(text: str) -> str:
    """
    Extract citation from judgment text.
    """
    patterns = [
        r'AIR\s+\d{4}\s+SC\s+\d+',
        r'\(\d{4}\)\s+\d+\s+SCC\s+\d+',
        r'\d{4}\s+\(\d+\)\s+SCC\s+\d+',
        r'AIR\s+\d{4}\s+(?:Bom|Del|Mad|Cal|All|Kar|Ker|Guj|Raj|P&H)\s+\d+',
        r'JT\s+\d{4}\s+\(\d+\)\s+SC\s+\d+',
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            return match.group(0)
    return ""


def extract_year(text: str) -> str:
    """
    Extract year from judgment text.
    """
    match = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', text)
    return match.group(0) if match else ""


def extract_court(text: str) -> str:
    """
    Extract court name from judgment text.
    """
    text_lower = text.lower()
    
    if 'supreme court' in text_lower:
        return 'Supreme Court of India'
    
    courts = [
        ('bombay', 'Bombay High Court'),
        ('delhi', 'Delhi High Court'),
        ('madras', 'Madras High Court'),
        ('calcutta', 'Calcutta High Court'),
        ('allahabad', 'Allahabad High Court'),
        ('karnataka', 'Karnataka High Court'),
        ('kerala', 'Kerala High Court'),
        ('gujarat', 'Gujarat High Court'),
        ('rajasthan', 'Rajasthan High Court'),
        ('punjab', 'Punjab and Haryana High Court'),
    ]
    
    for keyword, court_name in courts:
        if keyword in text_lower:
            return court_name
    
    return 'Unknown Court'


def extract_acts(text: str) -> List[str]:
    """
    Extract acts referred in judgment.
    """
    act_patterns = [
        r'Indian Penal Code',
        r'Bharatiya Nyaya Sanhita',
        r'Code of Criminal Procedure',
        r'Bharatiya Nagarik Suraksha Sanhita',
        r'Indian Evidence Act',
        r'Bharatiya Sakshya Adhiniyam',
        r'Indian Contract Act',
        r'Negotiable Instruments Act',
        r'Companies Act',
        r'Information Technology Act',
        r'Arbitration and Conciliation Act',
        r'Constitution of India',
        r'Hindu Marriage Act',
        r'Protection of Women from Domestic Violence Act',
        r'Protection of Children from Sexual Offences Act',
        r'POCSO',
    ]
    
    found = []
    for pattern in act_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(pattern)
    
    return list(set(found))  # Remove duplicates


async def generate_case_summary(text: str) -> Dict:
    """
    Use Groq to generate structured case summary.
    Only called for landmark cases — not every chunk.
    """
    try:
        client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
        
        prompt = f"""
Analyze this Indian court judgment excerpt and extract structured information.

Respond in JSON format only (no markdown, no code blocks):
{{
  "facts": "2-3 sentence summary of material facts",
  "issues": "key legal issues decided by court",
  "held": "what the court decided/held",
  "principle": "legal principle established or applied"
}}

Judgment excerpt:
{text[:3000]}
"""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=600
        )
        
        content = response.choices[0].message.content
        content = content.replace('```json', '').replace('```', '').strip()
        
        return json.loads(content)
        
    except Exception as e:
        print(f"  Warning: Summary generation failed: {str(e)[:100]}")
        return {
            "facts": "",
            "issues": "",
            "held": "",
            "principle": ""
        }


def run_complete_judgment_loading():
    """
    Master function to run both HuggingFace and Kanoon loading.
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║         LexAI Real Judgment Loader                           ║
║         Loading real court judgments from multiple sources   ║
║         1. HuggingFace datasets                              ║
║         2. Landmark cases from Indian Kanoon                 ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Load from HuggingFace
    load_real_judgments_huggingface()
    
    # Small delay
    print("\nWaiting 10 seconds before scraping landmark cases...")
    import time
    time.sleep(10)
    
    # Load landmark cases
    load_landmark_cases_kanoon()
    
    # Final report
    client = chromadb.PersistentClient(path='./legal_research_db')
    collection = client.get_collection('case_law')
    
    print(f"\n{'='*60}")
    print("JUDGMENT LOADING COMPLETE")
    print(f"{'='*60}")
    print(f"Total documents in case_law collection: {collection.count()}")
    
    # Count real judgments vs Q&A pairs
    try:
        real_judgments = collection.get(
            where={"is_real_judgment": {"$eq": True}}
        )
        landmark_cases = collection.get(
            where={"is_landmark": {"$eq": True}}
        )
        
        print(f"Real judgment chunks: {len(real_judgments['ids']) if real_judgments else 0}")
        print(f"Landmark case chunks: {len(landmark_cases['ids']) if landmark_cases else 0}")
    except:
        pass
    
    print(f"{'='*60}")


if __name__ == "__main__":
    run_complete_judgment_loading()
    print("\n✓ Judgment loading complete. Run run_database_build.py to execute all scripts.")
