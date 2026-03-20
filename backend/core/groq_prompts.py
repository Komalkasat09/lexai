"""
Groq LLM Integration
Contains all 5 prompt functions for contract analysis pipeline.
Each function makes a single Groq API call with temperature 0.0 and seed 42 for deterministic, reproducible results.
"""

import os
import json
from typing import Dict, List, Optional
from groq import Groq


# Initialize Groq client
def get_groq_client() -> Groq:
    """
    Get Groq client instance.
    
    Returns:
        Groq client
        
    Raises:
        ValueError: If GROQ_API_KEY is not set
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable not set. "
            "Please set it in your .env file."
        )
    return Groq(api_key=api_key)


# Configuration constants
# Updated to current Groq model (llama3-70b-8192 was decommissioned in Feb 2026)
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.0  # Set to 0 for deterministic outputs
GROQ_SEED = 42  # Fixed seed for reproducible results


# ============================================================================
# FUNCTION 1: IDENTIFY CONTRACT
# ============================================================================

def identify_contract(full_text: str, valid_citations_prompt: str = "") -> Dict:
    """
    Identify contract metadata and overview information.
    
    Args:
        full_text: Complete contract text
        valid_citations_prompt: Optional prompt snippet with valid citations
        
    Returns:
        Dictionary with overview information
    """
    client = get_groq_client()
    
    prompt = f"""You are a legal contract analyst specializing in Indian commercial law.

TASK: Analyze the following contract and extract key metadata.

{valid_citations_prompt}

CONTRACT TEXT:
{full_text}

INSTRUCTIONS:
Extract and structure the following information:
1. Contract Type (e.g., Service Agreement, NDA, Employment Agreement, Vendor Agreement)
2. Party A Name and Description
3. Party B Name and Description
4. Governing Law (jurisdiction/legal framework)
5. Jurisdiction (which court/city)
6. Effective Date
7. Duration/Term

Return ONLY a valid JSON object in this exact format:
{{
  "contract_type": "string",
  "party_a": "string",
  "party_b": "string",
  "governing_law": "string",
  "jurisdiction": "string",
  "effective_date": "string",
  "duration": "string"
}}

If any information is not found, use "Not specified" as the value.
Do not include any text before or after the JSON object."""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=GROQ_TEMPERATURE,
        seed=GROQ_SEED
    )
    
    # Parse JSON response
    try:
        result = json.loads(response.choices[0].message.content)
        return {"overview": result}
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "overview": {
                "contract_type": "Unable to determine",
                "party_a": "Not specified",
                "party_b": "Not specified",
                "governing_law": "Not specified",
                "jurisdiction": "Not specified",
                "effective_date": "Not specified",
                "duration": "Not specified"
            }
        }


# ============================================================================
# FUNCTION 2: CLASSIFY CLAUSES
# ============================================================================

def classify_clauses(clauses: List[Dict]) -> List[Dict]:
    """
    Classify each clause by type.
    
    Args:
        clauses: List of clause dictionaries with 'heading' and 'content'
        
    Returns:
        Same list with 'type' field added to each clause
    """
    client = get_groq_client()
    
    # Prepare clause text for LLM
    clauses_text = ""
    for i, clause in enumerate(clauses):
        clauses_text += f"\n--- CLAUSE {i+1} ---\n"
        clauses_text += f"Heading: {clause.get('heading', 'No heading')}\n"
        clauses_text += f"Content: {clause.get('content', '')[:500]}...\n"
    
    prompt = f"""You are a legal contract analyst specializing in clause classification.

TASK: Classify each of the following contract clauses into one of these types:
- Confidentiality
- Indemnity
- Limitation of Liability
- Termination
- Dispute Resolution
- Force Majeure
- Payment Terms
- IP Ownership (Intellectual Property)
- Non-compete
- Assignment
- Governing Law
- Data Protection
- Definitions
- Scope of Work
- Warranties
- Other

CLAUSES:
{clauses_text}

INSTRUCTIONS:
Return ONLY a valid JSON array with one object per clause in this exact format:
[
  {{"clause_number": 1, "type": "Confidentiality"}},
  {{"clause_number": 2, "type": "Indemnity"}},
  ...
]

Do not include any text before or after the JSON array."""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=GROQ_TEMPERATURE,
        seed=GROQ_SEED
    )
    
    # Parse JSON response
    try:
        classifications = json.loads(response.choices[0].message.content)
        
        # Merge classifications into original clauses
        classified_clauses = []
        for i, clause in enumerate(clauses):
            clause_copy = clause.copy()
            # Find matching classification
            classification = next(
                (c for c in classifications if c.get('clause_number') == i + 1),
                None
            )
            clause_copy['type'] = classification['type'] if classification else 'Other'
            classified_clauses.append(clause_copy)
        
        return classified_clauses
    
    except (json.JSONDecodeError, KeyError):
        # Fallback: mark all as 'Other'
        return [
            {**clause, 'type': 'Other'}
            for clause in clauses
        ]


# ============================================================================
# FUNCTION 3: ASSESS RISK
# ============================================================================

def assess_risk(
    classified_clauses: List[Dict],
    rag_context_map: Dict[int, List[Dict]],
    valid_citations_prompt: str
) -> Dict:
    """
    Assess risk level for each clause.
    
    Args:
        classified_clauses: List of clauses with 'type' field
        rag_context_map: Dictionary mapping clause index to relevant bare act sections
        valid_citations_prompt: Prompt snippet with valid citations list
        
    Returns:
        Dictionary with risk assessments
    """
    client = get_groq_client()
    
    # Prepare clause data with RAG context
    clauses_with_context = ""
    for i, clause in enumerate(classified_clauses):
        clauses_with_context += f"\n--- CLAUSE {i+1} ---\n"
        clauses_with_context += f"Heading: {clause.get('heading', 'No heading')}\n"
        clauses_with_context += f"Type: {clause.get('type', 'Other')}\n"
        clauses_with_context += f"Content: {clause.get('content', '')}\n"
        
        # Add relevant bare act sections
        if i in rag_context_map and rag_context_map[i]:
            clauses_with_context += "\nRelevant bare act sections:\n"
            for section in rag_context_map[i]:
                clauses_with_context += f"- {section['section']} of {section['act']}\n"
                clauses_with_context += f"  {section['text'][:200]}...\n"
        clauses_with_context += "\n"
    
    prompt = f"""You are a senior legal counsel specializing in Indian contract law.

TASK: Assess the risk level of each clause based on Indian legal standards.

{valid_citations_prompt}

CLAUSES TO ASSESS:
{clauses_with_context}

INSTRUCTIONS:
For each clause, assign a risk level:
- "standard": Clause follows standard legal practices, low risk
- "moderate": Clause may need review but not immediately problematic
- "high": Clause poses significant legal risk or disadvantage

Provide a one-sentence legal explanation for the risk level.

CITATION RULES:
- ONLY cite bare act sections listed in the "VALID BARE ACT CITATIONS" section above
- If citing a section, reference it as: "Section X of Act Name"
- If uncertain about a citation or section is not in the valid list, DO NOT cite it
- If uncertain about risk assessment, output exactly: "Unable to conclusively assess based on provided clause."

Return ONLY a valid JSON array:
[
  {{
    "clause_number": 1,
    "clause_heading": "string",
    "risk_level": "standard|moderate|high",
    "explanation": "Legal explanation in one sentence"
  }},
  ...
]

Do not include any text before or after the JSON array."""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=GROQ_TEMPERATURE,
        seed=GROQ_SEED
    )
    
    # Parse JSON response
    try:
        risks = json.loads(response.choices[0].message.content)
        return {"risks": risks}
    except json.JSONDecodeError:
        # Fallback
        return {
            "risks": [
                {
                    "clause_number": i + 1,
                    "clause_heading": clause.get('heading', 'No heading'),
                    "risk_level": "unknown",
                    "explanation": "Unable to conclusively assess based on provided clause."
                }
                for i, clause in enumerate(classified_clauses)
            ]
        }


# ============================================================================
# FUNCTION 4: DETECT MISSING CLAUSES
# ============================================================================

def detect_missing(classified_clauses: List[Dict]) -> Dict:
    """
    Detect which standard clauses are missing from the contract.
    
    Args:
        classified_clauses: List of clauses with 'type' field
        
    Returns:
        Dictionary with list of missing clauses
    """
    client = get_groq_client()
    
    # Extract present clause types
    present_types = [clause.get('type', 'Other') for clause in classified_clauses]
    present_types_str = ", ".join(set(present_types))
    
    prompt = f"""You are a legal contract consultant specializing in Indian commercial agreements.

TASK: Identify which standard clauses are missing from this contract.

CLAUSE TYPES PRESENT IN CONTRACT:
{present_types_str}

STANDARD CLAUSES CHECKLIST:
- Confidentiality
- Indemnity
- Limitation of Liability
- Termination
- Dispute Resolution
- Force Majeure
- Payment Terms
- IP Ownership
- Governing Law
- Data Protection
- Warranties
- Assignment
- Non-compete (if applicable)

INSTRUCTIONS:
Compare the present clause types against the standard checklist.
Identify which important clauses are missing.

Return ONLY a valid JSON array listing the missing clause types:
[
  {{
    "clause_type": "string",
    "importance": "critical|recommended|optional",
    "reason": "One sentence explaining why this clause is recommended"
  }},
  ...
]

Only include clauses that are actually missing. If all standard clauses are present, return an empty array: []

Do not include any text before or after the JSON array."""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=GROQ_TEMPERATURE,
        seed=GROQ_SEED
    )
    
    # Parse JSON response
    try:
        missing = json.loads(response.choices[0].message.content)
        return {"missing_clauses": missing}
    except json.JSONDecodeError:
        return {"missing_clauses": []}


# ============================================================================
# FUNCTION 5: SUGGEST REVISIONS
# ============================================================================

def suggest_revisions(
    high_risk_clauses: List[Dict],
    valid_citations_prompt: str
) -> Dict:
    """
    Generate revised versions of high-risk clauses.
    
    Args:
        high_risk_clauses: List of clauses marked as high risk
        valid_citations_prompt: Prompt snippet with valid citations
        
    Returns:
        Dictionary with suggested revisions
    """
    if not high_risk_clauses:
        return {"suggested_revisions": []}
    
    client = get_groq_client()
    
    # Prepare high-risk clauses
    clauses_text = ""
    for i, clause in enumerate(high_risk_clauses):
        clauses_text += f"\n--- HIGH RISK CLAUSE {i+1} ---\n"
        clauses_text += f"Heading: {clause.get('clause_heading', 'No heading')}\n"
        clauses_text += f"Original Text: {clause.get('original_text', '')}\n"
        clauses_text += f"Risk Explanation: {clause.get('explanation', '')}\n\n"
    
    prompt = f"""You are a senior legal drafter specializing in Indian commercial contracts.

TASK: Provide revised versions of the following high-risk clauses using proper Indian legal drafting language.

{valid_citations_prompt}

HIGH RISK CLAUSES:
{clauses_text}

INSTRUCTIONS:
For each high-risk clause, provide a revised version that:
1. Addresses the identified risk
2. Uses proper Indian legal drafting language
3. Is copy-paste ready for immediate use
4. Follows standard Indian contract law principles

CITATION RULES:
- ONLY cite bare act sections from the "VALID BARE ACT CITATIONS" list above
- Do NOT invent or reference any other sections
- If uncertain, omit the citation entirely

Return ONLY a valid JSON array:
[
  {{
    "clause_number": 1,
    "clause_heading": "string",
    "original_issue": "Brief description of the risk",
    "revised_clause": "Complete revised clause text in legal language",
    "key_changes": "Brief explanation of what was changed and why"
  }},
  ...
]

Do not include any text before or after the JSON array."""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=GROQ_TEMPERATURE,
        seed=GROQ_SEED
    )
    
    # Parse JSON response
    try:
        revisions = json.loads(response.choices[0].message.content)
        return {"suggested_revisions": revisions}
    except json.JSONDecodeError:
        return {"suggested_revisions": []}


# Test function
if __name__ == "__main__":
    print("\n" + "="*80)
    print("GROQ LLM INTEGRATION TEST")
    print("="*80 + "\n")
    
    # Check API key
    try:
        client = get_groq_client()
        print("✓ Groq API key found and client initialized\n")
    except ValueError as e:
        print(f"✗ Error: {e}")
        print("\nPlease set GROQ_API_KEY in your .env file:")
        print("  1. Create/edit .env file in backend directory")
        print("  2. Add line: GROQ_API_KEY=your_api_key_here")
        print("  3. Get API key from: https://console.groq.com/keys\n")
        exit(1)
    
    # Test data
    sample_contract = """
    SERVICE AGREEMENT
    
    This agreement is entered into on January 15, 2024 between TechCorp Solutions 
    Private Limited (Party A) and Global Enterprises India Limited (Party B).
    
    1. PAYMENT TERMS
    Party B shall pay Party A Rs. 10,00,000 per month.
    
    2. INDEMNITY
    Party A shall indemnify Party B for all damages, claims, and losses.
    
    This agreement is governed by the laws of India and jurisdiction lies with 
    Bangalore courts. The term is for 12 months.
    """
    
    sample_clauses = [
        {
            "clause_number": "1",
            "heading": "PAYMENT TERMS",
            "content": "Party B shall pay Party A Rs. 10,00,000 per month.",
            "level": 1,
            "start_line": 10
        },
        {
            "clause_number": "2",
            "heading": "INDEMNITY",
            "content": "Party A shall indemnify Party B for all damages, claims, and losses.",
            "level": 1,
            "start_line": 15
        }
    ]
    
    print("Testing Function 1: identify_contract()\n")
    print("This will make a real API call to Groq...")
    
    try:
        result = identify_contract(sample_contract, "")
        print("\n✓ Function 1 completed successfully")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("\n" + "="*80)
    print("\nNote: Other functions work similarly but are not tested here")
    print("to avoid excessive API calls. They will be tested in integration.\n")
    
    print("✓ Groq integration module ready!")
