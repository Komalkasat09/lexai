"""Utilities for building Hindi heading aliases for bare-act sections."""

import re


_TERM_PATTERNS = [
    (r"\bpunishment\b", "दंड"),
    (r"\bpenalty\b", "दंड"),
    (r"\bfor\b", "के लिए"),
    (r"\bof\b", "का"),
    (r"\band\b", "और"),
    (r"\bwith\b", "सहित"),
    (r"\bwithout\b", "बिना"),
    (r"\bto\b", "को"),
    (r"\bin\b", "में"),
    (r"\bon\b", "पर"),
    (r"\bby\b", "द्वारा"),
    (r"\bfrom\b", "से"),
    (r"\bunder\b", "के तहत"),
    (r"\bagainst\b", "के विरुद्ध"),
    (r"\bdefinition\b", "परिभाषा"),
    (r"\binterpretation\b", "व्याख्या"),
    (r"\bgeneral explanation\b", "सामान्य स्पष्टीकरण"),
    (r"\belectronic\b", "इलेक्ट्रॉनिक"),
    (r"\bproperty\b", "संपत्ति"),
    (r"\bperson\b", "व्यक्ति"),
    (r"\bwoman\b", "महिला"),
    (r"\bchild\b", "बालक"),
    (r"\bdeath\b", "मृत्यु"),
    (r"\bdishonestly\b", "बेईमानी से"),
    (r"\bfraudulently\b", "कपटपूर्वक"),
    (r"\bdelivery\b", "सुपुर्दगी"),
    (r"\binducing\b", "प्रेरित करना"),
    (r"\bintent\b", "आशय"),
    (r"\bintention\b", "आशय"),
    (r"\bcriminal\b", "आपराधिक"),
    (r"\boffence\b", "अपराध"),
    (r"\boffences\b", "अपराध"),
    (r"\bact\b", "अधिनियम"),
    (r"\bsection\b", "धारा"),
    (r"\bmurder\b", "हत्या"),
    (r"\bculpable homicide\b", "गैर इरादतन हत्या"),
    (r"\btheft\b", "चोरी"),
    (r"\brobbery\b", "लूट"),
    (r"\bdacoity\b", "डकैती"),
    (r"\bcheating\b", "धोखाधड़ी"),
    (r"\bcriminal breach of trust\b", "आपराधिक न्यासभंग"),
    (r"\bforgery\b", "जालसाजी"),
    (r"\bextortion\b", "उगाही"),
    (r"\bkidnapping\b", "अपहरण"),
    (r"\babduction\b", "अपहरण"),
    (r"\brape\b", "बलात्कार"),
    (r"\bsexual harassment\b", "यौन उत्पीड़न"),
    (r"\bassault\b", "आक्रमण"),
    (r"\bhurt\b", "चोट"),
    (r"\bgrievous hurt\b", "गंभीर चोट"),
    (r"\bwrongful restraint\b", "अवैध निरोध"),
    (r"\bwrongful confinement\b", "अवैध निरुद्धि"),
    (r"\bdefamation\b", "मानहानि"),
    (r"\bsedition\b", "देशद्रोह"),
    (r"\badultery\b", "व्यभिचार"),
    (r"\bdowry death\b", "दहेज मृत्यु"),
    (r"\bdowry\b", "दहेज"),
    (r"\bpublic servant\b", "लोक सेवक"),
    (r"\babetment\b", "उकसावा"),
    (r"\battempt\b", "प्रयास"),
    (r"\bconspiracy\b", "षड्यंत्र"),
    (r"\bcommon intention\b", "समान आशय"),
    (r"\bcommon object\b", "सामान्य उद्देश्य"),
    (r"\bevidence\b", "साक्ष्य"),
    (r"\belectronic evidence\b", "इलेक्ट्रॉनिक साक्ष्य"),
    (r"\bconfession\b", "स्वीकारोक्ति"),
    (r"\bstatement\b", "बयान"),
    (r"\bbail\b", "जमानत"),
    (r"\banticipatory bail\b", "अग्रिम जमानत"),
    (r"\barrest\b", "गिरफ्तारी"),
    (r"\binvestigation\b", "जांच"),
    (r"\btrial\b", "विचारण"),
    (r"\bprocedure\b", "प्रक्रिया"),
    (r"\bcognizable\b", "संज्ञेय"),
    (r"\bnon-cognizable\b", "असंज्ञेय"),
    (r"\bcompoundable\b", "समझौतायोग्य"),
    (r"\bnon-compoundable\b", "असमझौतायोग्य"),
    (r"\bcontract\b", "अनुबंध"),
    (r"\bagreement\b", "समझौता"),
    (r"\bconsideration\b", "प्रतिफल"),
    (r"\bvoid\b", "शून्य"),
    (r"\bspecific relief\b", "विशिष्ट अनुतोष"),
    (r"\barbitration\b", "मध्यस्थता"),
    (r"\bconciliation\b", "सुलह"),
    (r"\bcompany\b", "कंपनी"),
    (r"\bdirector\b", "निदेशक"),
    (r"\binsolvency\b", "दिवालियापन"),
    (r"\bbankruptcy\b", "दिवालियापन"),
    (r"\bconsumer\b", "उपभोक्ता"),
    (r"\bmarriage\b", "विवाह"),
    (r"\bdomestic violence\b", "घरेलू हिंसा"),
    (r"\bchild\b", "बालक"),
    (r"\bchildren\b", "बालक"),
]


def derive_hindi_heading(heading_en: str) -> str:
    """Derive a lightweight Hindi alias from an English legal heading."""
    if not heading_en:
        return ""

    heading = heading_en.strip()
    lowered = heading.lower()
    translated = lowered

    for pattern, replacement in _TERM_PATTERNS:
        translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)

    translated = re.sub(r"\s+", " ", translated).strip(" .;-:")
    translated = re.sub(r"\bके लिए\s+के लिए\b", "के लिए", translated)
    translated = re.sub(r"\bका\s+का\b", "का", translated)
    translated = re.sub(r"\bऔर\s+और\b", "और", translated)
    if not translated:
        return ""

    # If nothing changed, avoid storing a duplicate alias.
    if translated.lower() == lowered:
        return ""

    return translated


def build_embedding_text_with_headings(
    act_name: str,
    section_number: str,
    heading_en: str,
    heading_hi: str,
    body_preview: str,
) -> str:
    """Create embedding text that contains bilingual heading anchors."""
    parts = [
        f"{act_name} Section {section_number}",
        f"Heading EN: {heading_en}" if heading_en else "",
        f"Heading HI: {heading_hi}" if heading_hi else "",
        body_preview.strip(),
    ]
    return " ".join(p for p in parts if p).strip()
