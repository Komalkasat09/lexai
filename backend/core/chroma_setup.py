"""
ChromaDB Setup Module
Initializes vector database and loads bare act sections for RAG retrieval.
"""

import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict


# Bare Acts Data - Placeholder realistic legal text
# In production, replace with actual bare act text
BARE_ACTS_DATA = [
    # Indian Contract Act 1872
    {
        "section": "Section 10",
        "act": "Indian Contract Act 1872",
        "text": """What agreements are contracts - All agreements are contracts if they are made by the free consent of parties competent to contract, for a lawful consideration and with a lawful object, and are not hereby expressly declared to be void. Nothing herein contained shall affect any law in force in India and not hereby expressly repealed by which any contract is required to be made in writing or in the presence of witnesses, or any law relating to the registration of documents."""
    },
    {
        "section": "Section 23",
        "act": "Indian Contract Act 1872",
        "text": """What considerations and objects are lawful and what not - The consideration or object of an agreement is lawful, unless it is forbidden by law; or is of such a nature that, if permitted, it would defeat the provisions of any law; or is fraudulent; or involves or implies injury to the person or property of another; or the Court regards it as immoral, or opposed to public policy. In each of these cases, the consideration or object of an agreement is said to be unlawful. Every agreement of which the object or consideration is unlawful is void."""
    },
    {
        "section": "Section 27",
        "act": "Indian Contract Act 1872",
        "text": """Agreement in restraint of trade void - Every agreement by which anyone is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void. Exception 1 - Saving of agreement not to carry on business of which goodwill is sold. Exception 2 - Agreement between partners during the continuance of partnership. Exception 3 - Agreement between partners after dissolution."""
    },
    {
        "section": "Section 28",
        "act": "Indian Contract Act 1872",
        "text": """Agreements in restraint of legal proceedings void - Every agreement, by which any party thereto is restricted absolutely from enforcing his rights under or in respect of any contract, by the usual legal proceedings in the ordinary tribunals, or which limits the time within which he may thus enforce his rights, is void to that extent. Exception 1 - Saving of contract to refer to arbitration dispute that may arise. Exception 2 - Saving of contract to refer questions that have already arisen."""
    },
    {
        "section": "Section 73",
        "act": "Indian Contract Act 1872",
        "text": """Compensation for loss or damage caused by breach of contract - When a contract has been broken, the party who suffers by such breach is entitled to receive, from the party who has broken the contract, compensation for any loss or damage caused to him thereby, which naturally arose in the usual course of things from such breach, or which the parties knew, when they made the contract, to be likely to result from the breach of it. Such compensation is not to be given for any remote and indirect loss or damage sustained by reason of the breach."""
    },
    {
        "section": "Section 74",
        "act": "Indian Contract Act 1872",
        "text": """Compensation for breach of contract where penalty stipulated for - When a contract has been broken, if a sum is named in the contract as the amount to be paid in case of such breach, or if the contract contains any other stipulation by way of penalty, the party complaining of the breach is entitled, whether or not actual damage or loss is proved to have been caused thereby, to receive from the party who has broken the contract reasonable compensation not exceeding the amount so named or, as the case may be, the penalty stipulated for."""
    },
    
    # Arbitration and Conciliation Act 1996
    {
        "section": "Section 7",
        "act": "Arbitration and Conciliation Act 1996",
        "text": """Arbitration agreement - (1) In this Part, 'arbitration agreement' means an agreement by the parties to submit to arbitration all or certain disputes which have arisen or which may arise between them in respect of a defined legal relationship, whether contractual or not. (2) An arbitration agreement may be in the form of an arbitration clause in a contract or in the form of a separate agreement. (3) An arbitration agreement shall be in writing. (4) An arbitration agreement is in writing if it is contained in - (a) a document signed by the parties; (b) an exchange of letters, telex, telegrams or other means of telecommunication which provide a record of the agreement; or (c) an exchange of statements of claim and defence in which the existence of the agreement is alleged by one party and not denied by the other."""
    },
    {
        "section": "Section 8",
        "act": "Arbitration and Conciliation Act 1996",
        "text": """Power to refer parties to arbitration where there is an arbitration agreement - (1) A judicial authority, before which an action is brought in a matter which is the subject of an arbitration agreement shall, if a party to the arbitration agreement or any person claiming through or under him, so applies not later than the date of submitting his first statement on the substance of the dispute, then, notwithstanding any judgment, decree or order of the Supreme Court or any Court, refer the parties to arbitration unless it finds that prima facie no valid arbitration agreement exists. (2) The application referred to in sub-section (1) shall not be entertained unless it is accompanied by the original arbitration agreement or a duly certified copy thereof."""
    },
    {
        "section": "Section 11",
        "act": "Arbitration and Conciliation Act 1996",
        "text": """Appointment of arbitrators - (1) A person of any nationality may be an arbitrator, unless otherwise agreed by the parties. (2) Subject to sub-section (6), the parties are free to agree on a procedure for appointing the arbitrator or arbitrators. (3) Failing any agreement referred to in sub-section (2), in an arbitration with three arbitrators, each party shall appoint one arbitrator, and the two appointed arbitrators shall appoint the third arbitrator who shall act as the presiding arbitrator. (4) If the appointment procedure in sub-section (3) applies and - (a) a party fails to appoint an arbitrator within thirty days from the receipt of a request to do so from the other party; or (b) the two appointed arbitrators fail to agree on the third arbitrator within thirty days from the date of their appointment, the appointment shall be made, upon request of a party, by the arbitral institution designated by the parties."""
    },
    
    # Companies Act 2013
    {
        "section": "Section 2",
        "act": "Companies Act 2013",
        "text": """Definitions - In this Act, unless the context otherwise requires - (20) 'company' means a company incorporated under this Act or under any previous company law; (85) 'private company' means a company having a minimum paid-up share capital as may be prescribed, and which by its articles - (i) restricts the right to transfer its shares; (ii) except in case of One Person Company, limits the number of its members to two hundred; (iii) prohibits any invitation to the public to subscribe for any securities of the company; (87) 'public company' means a company which - (a) is not a private company; (b) has a minimum paid-up share capital, as may be prescribed."""
    },
    {
        "section": "Section 179",
        "act": "Companies Act 2013",
        "text": """Powers of Board - (1) The Board of Directors of a company shall be entitled to exercise all such powers, and to do all such acts and things, as the company is authorised to exercise and do: Provided that in exercising such power or doing such act or thing, the Board shall be subject to the provisions contained in that behalf in this Act, or in the memorandum or articles, or in any regulations not inconsistent therewith and duly made thereunder, including regulations made by the company in general meeting. (2) The Board of Directors of a company shall exercise the following powers on behalf of the company by means of resolutions passed at meetings of the Board, namely: (a) to make calls on shareholders in respect of money unpaid on their shares; (b) to authorise buy-back of securities under section 68; (c) to issue securities, including debentures, whether in or outside India."""
    },
    {
        "section": "Section 184",
        "act": "Companies Act 2013",
        "text": """Disclosure of interest by director - (1) Every director of a company who is in any way, whether directly or indirectly, concerned or interested in a contract or arrangement or proposed contract or arrangement entered into or to be entered into - (a) with a body corporate in which such director or such director in association with any other director, holds more than two per cent shareholding of that body corporate, or is a promoter, manager, Chief Executive Officer of that body corporate; or (b) with a firm or other entity in which, such director is a partner, owner or member, as the case may be, shall disclose the nature of his concern or interest at the meeting of the Board in which the contract or arrangement is discussed and shall not participate in such meeting."""
    }
]


class ChromaDBManager:
    """Manages ChromaDB operations for bare acts retrieval."""
    
    def __init__(self, persist_directory: str = "./legal_research_db"):
        """
        Initialize ChromaDB client and collection.
        
        Args:
            persist_directory: Directory where ChromaDB will persist data
        """
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection for bare acts
        self.collection = None
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize or get existing bare_acts collection."""
        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(name="bare_acts")
            print(f"✓ Loaded existing collection 'bare_acts' with {self.collection.count()} documents")
        except Exception:
            # Create new collection if doesn't exist
            self.collection = self.client.create_collection(
                name="bare_acts",
                metadata={"description": "Indian legal bare acts for contract analysis"}
            )
            print("✓ Created new collection 'bare_acts'")
            # Load initial data
            self.load_bare_acts()
    
    def reset_collection(self):
        """Reset the collection (useful for testing/reloading)."""
        try:
            self.client.delete_collection(name="bare_acts")
            print("✓ Deleted existing collection")
        except Exception:
            pass
        
        self.collection = self.client.create_collection(
            name="bare_acts",
            metadata={"description": "Indian legal bare acts for contract analysis"}
        )
        print("✓ Created new collection")
        self.load_bare_acts()
    
    def load_bare_acts(self):
        """Load bare act sections into ChromaDB."""
        if self.collection.count() > 0:
            print(f"Collection already has {self.collection.count()} documents, skipping load")
            return
        
        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for idx, act_data in enumerate(BARE_ACTS_DATA):
            # Document text for embedding
            documents.append(act_data["text"])
            
            # Metadata for filtering and retrieval
            metadatas.append({
                "section": act_data["section"],
                "act": act_data["act"],
                "section_number": act_data["section"].replace("Section ", "")
            })
            
            # Unique ID
            ids.append(f"{act_data['act']}_{act_data['section'].replace(' ', '_')}")
        
        # Add to ChromaDB
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✓ Loaded {len(BARE_ACTS_DATA)} bare act sections into ChromaDB")
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection."""
        count = self.collection.count()
        
        # Get sample to show acts distribution
        if count > 0:
            results = self.collection.get(limit=count)
            acts = {}
            for metadata in results['metadatas']:
                act = metadata['act']
                acts[act] = acts.get(act, 0) + 1
            
            return {
                "total_sections": count,
                "acts_distribution": acts
            }
        
        return {"total_sections": 0, "acts_distribution": {}}
    
    def query_similar_sections(
        self, 
        query_text: str, 
        n_results: int = 2
    ) -> List[Dict]:
        """
        Query ChromaDB for similar bare act sections.
        
        Args:
            query_text: The clause text to find similar sections for
            n_results: Number of results to return (default: 2)
            
        Returns:
            List of dictionaries with section, act, text, and similarity score
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "section": results['metadatas'][0][i]['section'],
                    "act": results['metadatas'][0][i]['act'],
                    "text": results['documents'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted_results
    
    def get_section_by_reference(self, section: str, act: str) -> Dict | None:
        """
        Get a specific section by its reference.
        Used for citation validation.
        
        Args:
            section: Section reference (e.g., "Section 73")
            act: Act name
            
        Returns:
            Dictionary with section data or None if not found
        """
        results = self.collection.get(
            where={
                "$and": [
                    {"section": section},
                    {"act": act}
                ]
            }
        )
        
        if results['documents']:
            return {
                "section": results['metadatas'][0]['section'],
                "act": results['metadatas'][0]['act'],
                "text": results['documents'][0]
            }
        
        return None
    
    def list_all_sections(self) -> List[Dict]:
        """
        List all sections in the database.
        Useful for debugging and validation.
        
        Returns:
            List of all section references
        """
        count = self.collection.count()
        if count == 0:
            return []
        
        results = self.collection.get(limit=count)
        
        sections = []
        for metadata in results['metadatas']:
            sections.append({
                "section": metadata['section'],
                "act": metadata['act']
            })
        
        return sections


def initialize_chroma_db(reset: bool = False) -> ChromaDBManager:
    """
    Initialize ChromaDB manager.
    
    Args:
        reset: If True, reset the collection and reload data
        
    Returns:
        ChromaDBManager instance
    """
    manager = ChromaDBManager()
    
    if reset:
        manager.reset_collection()
    
    return manager


# Test function
if __name__ == "__main__":
    print("\n" + "="*80)
    print("CHROMADB SETUP TEST")
    print("="*80 + "\n")
    
    # Initialize ChromaDB
    manager = initialize_chroma_db(reset=False)
    
    # Show statistics
    stats = manager.get_collection_stats()
    print(f"\nCollection Statistics:")
    print(f"  Total sections: {stats['total_sections']}")
    print(f"  Acts distribution:")
    for act, count in stats['acts_distribution'].items():
        print(f"    - {act}: {count} sections")
    
    # Test retrieval
    print("\n" + "="*80)
    print("TEST RETRIEVAL")
    print("="*80 + "\n")
    
    test_clause = "The party shall indemnify and hold harmless the other party from all claims and damages."
    print(f"Query: {test_clause}\n")
    
    results = manager.query_similar_sections(test_clause, n_results=2)
    print(f"Top {len(results)} relevant sections:\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['section']} - {result['act']}")
        print(f"   Distance: {result['distance']:.4f}")
        print(f"   Text: {result['text'][:200]}...")
        print()
    
    # Test citation validation
    print("="*80)
    print("TEST CITATION VALIDATION")
    print("="*80 + "\n")
    
    valid_section = manager.get_section_by_reference("Section 73", "Indian Contract Act 1872")
    print(f"Valid citation test: {valid_section is not None}")
    
    invalid_section = manager.get_section_by_reference("Section 999", "Indian Contract Act 1872")
    print(f"Invalid citation test: {invalid_section is None}")
    
    print("\n✓ ChromaDB setup complete!")
