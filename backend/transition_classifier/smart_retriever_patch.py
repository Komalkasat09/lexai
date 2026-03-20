"""
Step 5 — Integration snippet for SmartRetriever.
Shows BEFORE (hardcoded dict lookup) vs AFTER (learned TransitionClassifier + replacement).
Use this as reference when patching backend/retrieval/smart_retriever.py.
"""

# =============================================================================
# BEFORE: Hardcoded dictionary lookup in apply_bns_bnss_middleware()
# (current logic in smart_retriever.py around lines 358–382)
# =============================================================================
"""
        # Check if this is IPC section
        if "IPC" in act_name or "Indian Penal Code" in act_name:
            if section_number in IPC_BNS_MAP:
                bns_info = IPC_BNS_MAP[section_number]
                result["bns_transition"] = {
                    "original": f"IPC Section {section_number}",
                    "replaced_by": f"BNS Section {bns_info['bns']}" if bns_info['bns'] != 'removed' else "Removed in BNS",
                    ...
                }
        elif "CrPC" in act_name or ...:
            if section_number in CRPC_BNSS_MAP:
                bnss_info = CRPC_BNSS_MAP[section_number]
                ...
"""

# =============================================================================
# AFTER: Learned classifier + replacement retrieval
# =============================================================================
"""
# At top of smart_retriever.py (lazy init to avoid loading model at import):
_transition_classifier = None

def _get_transition_classifier():
    global _transition_classifier
    if _transition_classifier is None:
        from transition_classifier import TransitionClassifier
        _transition_classifier = TransitionClassifier()
    return _transition_classifier

def _section_reference_from_metadata(act_name: str, section_number: str) -> str:
    '''Build full section reference string for classifier input.'''
    if not section_number:
        return ""
    act = (act_name or "").strip()
    if not act or act.upper() in ("IPC", "INDIAN PENAL CODE"):
        return f"Section {section_number} of the Indian Penal Code"
    if act.upper() in ("CRPC", "CR.P.C", "CODE OF CRIMINAL PROCEDURE"):
        return f"Section {section_number} of the Code of Criminal Procedure"
    return f"Section {section_number} of the {act}"

def retrieve_replacement(replacement_str: str, db) -> Optional[Dict]:
    '''
    Given classifier output e.g. "BNS Section 103", retrieve that section from DB
    for enriched context. Returns None if not found.
    '''
    import re
    m = re.match(r"^(BNS|BNSS)\s+Section\s+(\S+)$", replacement_str, re.I)
    if not m or not db:
        return None
    act_type, sec = m.group(1).upper(), m.group(2)
    act_name = "Bharatiya Nyaya Sanhita 2023" if act_type == "BNS" else "Bharatiya Nagarik Suraksha Sanhita 2023"
    # Use existing DB API to get section content (e.g. get_section or query by metadata)
    return db.get_section_content(act_name=act_name, section_number=sec)  # adapt to your DB API

# Inside apply_bns_bnss_middleware(), replace the IPC/CrPC block with:
        section_reference = _section_reference_from_metadata(act_name, section_number)
        if section_reference:
            classifier = _get_transition_classifier()
            prediction = classifier.predict(section_reference)
            if prediction["is_superseded"]:
                result["bns_transition"] = {
                    "original": f"IPC Section {section_number}" if "IPC" in act_name or "Indian Penal Code" in act_name else f"CrPC Section {section_number}",
                    "replaced_by": prediction["replacement"] or "Removed in BNS",
                    "changes": "(see replacement)",
                    "note": f"⚠️ Note: Superseded by {prediction['replacement']}."
                }
                # Optionally enrich with replacement section content from DB
                # repl_doc = retrieve_replacement(prediction["replacement"], self.db)
                # if repl_doc: result["replacement_content"] = repl_doc
"""

# Minimal copy-paste block for the core replacement (no DB retrieval):
INTEGRATION_SNIPPET = """
# Replace dict lookup with:
section_reference = _section_reference_from_metadata(act_name, section_number)
if section_reference:
    prediction = _get_transition_classifier().predict(section_reference)
    if prediction["is_superseded"]:
        result["bns_transition"] = {
            "original": f"IPC Section {section_number}" if "IPC" in act_name or "Indian Penal Code" in act_name else f"CrPC Section {section_number}",
            "replaced_by": prediction["replacement"] or "Removed in BNS",
            "note": f"⚠️ Note: Superseded by {prediction['replacement']}."
        }
"""
