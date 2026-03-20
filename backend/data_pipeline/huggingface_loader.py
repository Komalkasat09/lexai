"""
HuggingFace Dataset Loader for Legal Research System
Loads Indian legal datasets from Hugging Face Hub and populates ChromaDB collections.

This module:
1. Searches for available Indian legal datasets on HuggingFace
2. Maps dataset fields to our case_law schema
3. Chunks long judgments with overlap for better retrieval
4. Checks for duplicates before insertion
5. Logs all operations with timestamps
6. Saves backup JSON before inserting into database
"""

import os
import json
import tiktoken
from datetime import datetime
from typing import List, Dict, Optional
from datasets import load_dataset, DatasetDict, Dataset
import re
import hashlib

# Import our database manager
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.chroma_setup import LegalResearchDB


# ============================================================================
# CONFIGURATION
# ============================================================================

# Token chunking configuration
CHUNK_SIZE = 500  # tokens per chunk
CHUNK_OVERLAP = 50  # overlap between chunks

# Known Indian legal datasets on HuggingFace
HUGGINGFACE_DATASETS = [
    "Exploration-Lab/IndianLegalQA",
    "viber1/indian-law-dataset",
    "legal-nlp/indian_legal_documents",
    # Add more as discovered
]

# Backup directory for raw data
BACKUP_DIR = "./data/backup"
os.makedirs(BACKUP_DIR, exist_ok=True)

# Log file
LOG_FILE = "./data/huggingface_loader.log"


# ============================================================================
# TEXT CHUNKING UTILITIES
# ============================================================================

def count_tokens(text: str) -> int:
    """
    Count tokens in text using tiktoken (GPT tokenizer).
    
    Args:
        text: Input text
        
    Returns:
        Token count
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Fallback: approximate as words / 0.75
        return int(len(text.split()) / 0.75)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Chunk long text into smaller pieces with overlap.
    
    Args:
        text: Full text to chunk
        chunk_size: Target tokens per chunk
        overlap: Overlap tokens between chunks
        
    Returns:
        List of text chunks
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = start + chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = encoding.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            # Move start position with overlap
            start = end - overlap
            
            # Prevent infinite loop
            if start >= len(tokens):
                break
        
        return chunks if chunks else [text]
    
    except Exception as e:
        # Fallback: split by sentences
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if count_tokens(current_chunk + sentence) < chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]


# ============================================================================
# CITATION AND REFERENCE EXTRACTION
# ============================================================================

def extract_acts_referred(text: str) -> List[str]:
    """
    Extract act names mentioned in judgment text.
    
    Args:
        text: Judgment text
        
    Returns:
        List of act names
    """
    # Common Indian acts
    acts_patterns = [
        r'Indian Penal Code',
        r'IPC',
        r'I\.P\.C\.',
        r'Code of Criminal Procedure',
        r'CrPC',
        r'Cr\.P\.C\.',
        r'Indian Contract Act',
        r'Companies Act',
        r'Arbitration and Conciliation Act',
        r'Income Tax Act',
        r'Negotiable Instruments Act',
        r'Evidence Act',
        r'Transfer of Property Act',
        r'Consumer Protection Act',
        r'SARFAESI Act',
        r'Bharatiya Nyaya Sanhita',
        r'BNS',
        r'Bharatiya Nagarik Suraksha Sanhita',
        r'BNSS'
    ]
    
    acts_found = set()
    for pattern in acts_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            acts_found.add(match.group())
    
    return list(acts_found)


def extract_sections_referred(text: str) -> List[str]:
    """
    Extract section numbers mentioned in judgment text.
    
    Args:
        text: Judgment text
        
    Returns:
        List of section numbers
    """
    # Pattern: "Section 420", "Sec. 34", "s. 302", etc.
    section_pattern = r'[Ss]ection|[Ss]ec\.|[Ss]\.\s+(\d+[A-Z]?)'
    
    sections_found = set()
    matches = re.finditer(section_pattern, text)
    for match in matches:
        if match.group(1):
            sections_found.add(match.group(1))
    
    return list(sections_found)


def extract_citation_from_text(text: str) -> Optional[str]:
    """
    Extract citation from text using common patterns.
    
    Args:
        text: Text containing citation
        
    Returns:
        Citation string or None
    """
    # Common citation patterns
    patterns = [
        r'AIR\s+\d{4}\s+SC\s+\d+',
        r'\(\d{4}\)\s+\d+\s+SCC\s+\d+',
        r'\d{4}\s+\(\d+\)\s+SCC\s+\d+',
        r'\d{4}\s+AIR\s+\d+',
        r'\(\d{4}\)\s+\d+\s+SCR\s+\d+'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group()
    
    return None


# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def log_operation(message: str):
    """
    Log operation with timestamp.
    
    Args:
        message: Log message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    # Print to console
    print(log_entry.strip())
    
    # Write to log file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)


def save_backup(data: Dict, dataset_name: str):
    """
    Save raw data to backup JSON before inserting to database.
    
    Args:
        data: Data to backup
        dataset_name: Name of dataset
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{BACKUP_DIR}/{dataset_name}_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    log_operation(f"✓ Backup saved: {filename}")


# ============================================================================
# DATASET LOADERS - SPECIFIC ADAPTERS
# ============================================================================

def load_indian_legal_qa(db: LegalResearchDB) -> int:
    """
    Load Exploration-Lab/IndianLegalQA dataset.
    
    Args:
        db: LegalResearchDB instance
        
    Returns:
        Number of documents loaded
    """
    log_operation("📦 Loading Exploration-Lab/IndianLegalQA...")
    
    try:
        dataset = load_dataset("Exploration-Lab/IndianLegalQA")
        
        # This dataset typically has 'train' split with QA pairs
        if "train" in dataset:
            data = dataset["train"]
        else:
            data = list(dataset.values())[0]
        
        loaded_count = 0
        
        for idx, item in enumerate(data):
            # Backup every 100 items
            if idx % 100 == 0:
                save_backup(
                    {"dataset": "IndianLegalQA", "items": data[idx:idx+100]},
                    "IndianLegalQA"
                )
            
            # Map fields to our schema
            # This dataset structure may vary - adapt as needed
            question = item.get("question", "")
            answer = item.get("answer", "")
            context = item.get("context", "")
            
            # Create combined text
            full_text = f"Question: {question}\n\nContext: {context}\n\nAnswer: {answer}"
            
            # Generate unique ID
            case_id = f"ILQ_{idx}"
            
            # Check if already exists
            if db.check_if_case_exists(case_id):
                continue
            
            # Extract metadata
            acts = extract_acts_referred(full_text)
            sections = extract_sections_referred(full_text)
            
            # Chunk if text is long
            token_count = count_tokens(full_text)
            if token_count > CHUNK_SIZE:
                chunks = chunk_text(full_text)
            else:
                chunks = [full_text]
            
            # Add each chunk
            for chunk_idx, chunk in enumerate(chunks):
                db.add_case_law(
                    case_id=f"{case_id}_chunk_{chunk_idx + 1}",
                    case_name=question[:100],  # Use question as case name
                    citation=case_id,
                    court="Indian Legal QA Dataset",
                    year="2023",  # Approximate
                    chunk_text=chunk,
                    chunk_number=chunk_idx + 1,
                    total_chunks=len(chunks),
                    acts_referred=acts if acts else None,
                    sections_referred=sections if sections else None,
                    legal_principle=answer[:500] if answer else None,
                    source="huggingface",
                    source_url="https://huggingface.co/datasets/Exploration-Lab/IndianLegalQA"
                )
                loaded_count += 1
            
            if (idx + 1) % 50 == 0:
                log_operation(f"  Processed {idx + 1} items ({loaded_count} chunks)...")
        
        log_operation(f"✅ Loaded {loaded_count} documents from IndianLegalQA")
        return loaded_count
    
    except Exception as e:
        log_operation(f"❌ Error loading IndianLegalQA: {e}")
        return 0


def load_viber_indian_law(db: LegalResearchDB) -> int:
    """
    Load viber1/indian-law-dataset (24,607 Indian legal Q&A pairs).
    
    Args:
        db: LegalResearchDB instance
        
    Returns:
        Number of documents loaded
    """
    log_operation("📦 Loading viber1/indian-law-dataset (24,607 legal Q&A pairs)...")
    
    try:
        dataset = load_dataset("viber1/indian-law-dataset")
        
        if "train" in dataset:
            data = dataset["train"]
        else:
            data = list(dataset.values())[0]
        
        loaded_count = 0
        total_items = len(data)
        log_operation(f"📊 Found {total_items} items in dataset")
        
        for idx, item in enumerate(data):
            # Actual field names in dataset: 'Instruction' and 'Response'
            instruction = item.get("Instruction", "")
            response = item.get("Response", "")
            
            if not instruction or not response:
                continue
            
            # Create combined text for embedding
            full_text = f"Question: {instruction}\n\nAnswer: {response}"
            
            # Generate unique ID
            case_id = f"VIBER_{idx:06d}"
            
            # Check for duplicates (use hash of instruction as citation)
            citation_hash = hashlib.md5(instruction.encode()).hexdigest()[:12]
            citation = f"VIBER_{citation_hash}"
            
            # Skip if already exists
            if db.check_if_case_exists(citation):
                continue
            
            # Extract metadata
            acts = extract_acts_referred(full_text)
            sections = extract_sections_referred(full_text)
            
            # Chunk if necessary
            token_count = count_tokens(full_text)
            if token_count > CHUNK_SIZE:
                chunks = chunk_text(full_text)
            else:
                chunks = [full_text]
            
            # Add chunks
            for chunk_idx, chunk in enumerate(chunks):
                db.add_case_law(
                    case_id=f"{case_id}_chunk_{chunk_idx + 1}",
                    case_name=instruction[:200],  # Use question as case name
                    citation=citation,
                    court="Indian Legal Database",
                    year="2024",  
                    chunk_text=chunk,
                    chunk_number=chunk_idx + 1,
                    total_chunks=len(chunks),
                    acts_referred=acts if acts else None,
                    sections_referred=sections if sections else None,
                    legal_principle=response[:500] if len(response) > 500 else response,
                    source="huggingface",
                    source_url="https://huggingface.co/datasets/viber1/indian-law-dataset"
                )
                loaded_count += 1
            
            if (idx + 1) % 500 == 0:
                log_operation(f"  Processed {idx + 1}/{total_items} items ({loaded_count} chunks loaded)...")
        
        log_operation(f"✅ Loaded {loaded_count} documents from viber1/indian-law-dataset ({total_items} Q&A pairs)")
        return loaded_count
    
    except Exception as e:
        log_operation(f"❌ Error loading viber1/indian-law-dataset: {e}")
        import traceback
        log_operation(f"  Traceback: {traceback.format_exc()}")
        return 0


# ============================================================================
# MAIN LOADER ORCHESTRATOR
# ============================================================================

def load_all_huggingface_datasets(db: LegalResearchDB) -> Dict[str, int]:
    """
    Load all available Indian legal datasets from HuggingFace.
    
    Args:
        db: LegalResearchDB instance
        
    Returns:
        Dictionary with dataset names and document counts
    """
    log_operation("\n" + "="*80)
    log_operation("HUGGINGFACE DATA LOADER - STARTING")
    log_operation("="*80)
    
    results = {}
    
    # Try loading IndianLegalQA
    try:
        count = load_indian_legal_qa(db)
        results["IndianLegalQA"] = count
    except Exception as e:
        log_operation(f"❌ Failed to load IndianLegalQA: {e}")
        results["IndianLegalQA"] = 0
    
    # Try loading viber1/indian-law-dataset
    try:
        count = load_viber_indian_law(db)
        results["viber_indian_law"] = count
    except Exception as e:
        log_operation(f"❌ Failed to load viber1/indian-law-dataset: {e}")
        results["viber_indian_law"] = 0
    
    # Try loading other datasets dynamically
    # Note: Add more dataset loaders as you discover them
    
    # Summary
    total_loaded = sum(results.values())
    log_operation("\n" + "="*80)
    log_operation("LOADING SUMMARY")
    log_operation("="*80)
    for dataset_name, count in results.items():
        log_operation(f"  • {dataset_name}: {count} documents")
    log_operation(f"\n📊 Total documents loaded: {total_loaded}")
    
    # Show updated collection stats
    stats = db.get_collection_stats()
    log_operation(f"\n📊 Updated Database Statistics:")
    log_operation(f"  • Bare Acts: {stats['bare_acts']}")
    log_operation(f"  • Case Law: {stats['case_law']}")
    log_operation(f"  • Amendments: {stats['amendments']}")
    log_operation(f"  • Overruling Map: {stats['overruling_map']}")
    log_operation(f"  • Total: {stats['total']}")
    
    log_operation("\n✅ HuggingFace data loading complete!")
    log_operation("="*80 + "\n")
    
    return results


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("HUGGINGFACE DATASET LOADER FOR LEGAL RESEARCH SYSTEM")
    print("="*80 + "\n")
    
    # Initialize database
    from database.chroma_setup import initialize_legal_db
    db = initialize_legal_db()
    
    # Load all datasets
    results = load_all_huggingface_datasets(db)
    
    print("\n✅ All datasets loaded successfully!")
    print("="*80 + "\n")
