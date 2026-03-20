"""
Complete Bare Acts Loader for LexAI
====================================
Scrapes complete text of all major Indian acts from official sources.
Primary: India Code (official government source)
Fallback: IndianKanoon (if India Code fails)

Prerequisites:
pip install playwright
playwright install chromium

Run: python bare_acts_loader.py
"""

import asyncio
from playwright.async_api import async_playwright
import chromadb
import json
import time
import random
import re
import os
import sys
import textwrap
import hashlib
from typing import List, Dict, Optional
try:
    from data_pipeline.hindi_heading_utils import (
        derive_hindi_heading,
        build_embedding_text_with_headings,
    )
except ModuleNotFoundError:
    from hindi_heading_utils import (
        derive_hindi_heading,
        build_embedding_text_with_headings,
    )

# ============================================================
# ACTS TO LOAD - All major Indian legislation
# ============================================================
ACTS_TO_LOAD = [
    # Criminal Law — HIGHEST PRIORITY
    {
        "act_name": "Bharatiya Nyaya Sanhita 2023",
        "short_name": "BNS",
        "search_term": "Bharatiya Nyaya Sanhita 2023",
        "total_sections": 358,
        "replaced_act": "Indian Penal Code 1860",
        "effective_date": "2024-07-01",
        "priority": "CRITICAL"
    },
    {
        "act_name": "Indian Penal Code 1860",
        "short_name": "IPC",
        "search_term": "Indian Penal Code",
        "total_sections": 511,
        "replaced_by": "Bharatiya Nyaya Sanhita 2023",
        "priority": "CRITICAL"
    },
    {
        "act_name": "Bharatiya Nagarik Suraksha Sanhita 2023",
        "short_name": "BNSS",
        "search_term": "Bharatiya Nagarik Suraksha Sanhita 2023",
        "total_sections": 531,
        "replaced_act": "Code of Criminal Procedure 1973",
        "effective_date": "2024-07-01",
        "priority": "CRITICAL"
    },
    {
        "act_name": "Code of Criminal Procedure 1973",
        "short_name": "CrPC",
        "search_term": "Code of Criminal Procedure 1973",
        "total_sections": 484,
        "replaced_by": "Bharatiya Nagarik Suraksha Sanhita 2023",
        "priority": "CRITICAL"
    },
    {
        "act_name": "Bharatiya Sakshya Adhiniyam 2023",
        "short_name": "BSA",
        "search_term": "Bharatiya Sakshya Adhiniyam 2023",
        "total_sections": 170,
        "replaced_act": "Indian Evidence Act 1872",
        "effective_date": "2024-07-01",
        "priority": "CRITICAL"
    },
    {
        "act_name": "Indian Evidence Act 1872",
        "short_name": "IEA",
        "search_term": "Indian Evidence Act",
        "total_sections": 167,
        "replaced_by": "Bharatiya Sakshya Adhiniyam 2023",
        "priority": "CRITICAL"
    },
    
    # Civil Law
    {
        "act_name": "Indian Contract Act 1872",
        "short_name": "ICA",
        "search_term": "Indian Contract Act 1872",
        "total_sections": 238,
        "priority": "HIGH"
    },
    {
        "act_name": "Code of Civil Procedure 1908",
        "short_name": "CPC",
        "search_term": "Code of Civil Procedure 1908",
        "total_sections": 158,
        "priority": "HIGH"
    },
    {
        "act_name": "Specific Relief Act 1963",
        "short_name": "SRA",
        "search_term": "Specific Relief Act 1963",
        "total_sections": 44,
        "priority": "HIGH"
    },
    {
        "act_name": "Transfer of Property Act 1882",
        "short_name": "TPA",
        "search_term": "Transfer of Property Act 1882",
        "total_sections": 137,
        "priority": "HIGH"
    },
    {
        "act_name": "Limitation Act 1963",
        "short_name": "LA",
        "search_term": "Limitation Act 1963",
        "total_sections": 32,
        "priority": "HIGH"
    },
    
    # Commercial Law
    {
        "act_name": "Negotiable Instruments Act 1881",
        "short_name": "NIA",
        "search_term": "Negotiable Instruments Act 1881",
        "total_sections": 147,
        "priority": "CRITICAL"
    },
    {
        "act_name": "Arbitration and Conciliation Act 1996",
        "short_name": "ACA",
        "search_term": "Arbitration and Conciliation Act 1996",
        "total_sections": 87,
        "priority": "HIGH"
    },
    {
        "act_name": "Companies Act 2013",
        "short_name": "CA",
        "search_term": "Companies Act 2013",
        "total_sections": 470,
        "priority": "MEDIUM"
    },
    {
        "act_name": "Information Technology Act 2000",
        "short_name": "ITA",
        "search_term": "Information Technology Act 2000",
        "total_sections": 94,
        "priority": "HIGH"
    },
    
    # Constitutional
    {
        "act_name": "Constitution of India 1950",
        "short_name": "COI",
        "search_term": "Constitution of India",
        "total_sections": 395,
        "priority": "CRITICAL"
    },
    
    # Family Law
    {
        "act_name": "Hindu Marriage Act 1955",
        "short_name": "HMA",
        "search_term": "Hindu Marriage Act 1955",
        "total_sections": 37,
        "priority": "HIGH"
    },
    {
        "act_name": "Protection of Women from Domestic Violence Act 2005",
        "short_name": "PWDVA",
        "search_term": "Protection of Women from Domestic Violence Act 2005",
        "total_sections": 37,
        "priority": "HIGH"
    },
    {
        "act_name": "Protection of Children from Sexual Offences Act 2012",
        "short_name": "POCSO",
        "search_term": "Protection of Children from Sexual Offences Act 2012",
        "total_sections": 46,
        "priority": "CRITICAL"
    },
    
    # Additional Important Acts
    {
        "act_name": "Consumer Protection Act 2019",
        "short_name": "CPA",
        "search_term": "Consumer Protection Act 2019",
        "total_sections": 108,
        "priority": "MEDIUM"
    },
    {
        "act_name": "Insolvency and Bankruptcy Code 2016",
        "short_name": "IBC",
        "search_term": "Insolvency and Bankruptcy Code 2016",
        "total_sections": 255,
        "priority": "HIGH"
    },
]


def make_section_id(act_info: Dict, section_num: str, section_text: str, index: int) -> str:
    """
    Build a stable, collision-resistant id for each section/chunk.
    Prevents duplicate-id errors when multiple fragments share a section number.
    """
    short_name = act_info.get('short_name', 'ACT')
    safe_num = re.sub(r'[^0-9A-Za-z_\-]+', '_', str(section_num or 'unknown'))
    text_hash = hashlib.md5(section_text[:500].encode('utf-8')).hexdigest()[:10]
    return f"{short_name}_{safe_num}_{index}_{text_hash}"


def normalize_section_number(raw: str) -> str:
    """Normalize extracted section/article labels into consistent short form."""
    if not raw:
        return "unknown"

    value = raw.strip()
    value = re.sub(r'\s+', ' ', value)
    value = re.sub(r'(?i)^(section|sec\.?|article|art\.?)\s+', '', value).strip()

    # Keep common legal numbering styles: 123, 123A, 123(1), 123-A, 123A(2)
    match = re.match(r'([0-9]+[A-Z]?(?:\([0-9A-Za-z]+\))?(?:-[0-9A-Za-z]+)?)', value, re.IGNORECASE)
    if match:
        return match.group(1)

    return re.sub(r'[^0-9A-Za-z()\-]+', '', value) or "unknown"


def normalize_for_match(value: str) -> str:
    """Normalize text for lightweight fuzzy matching."""
    value = (value or '').lower()
    value = re.sub(r'[^a-z0-9\s]+', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def get_act_hint_tokens(act_info: Dict) -> List[str]:
    """Build discriminative tokens used for search ranking and validation."""
    stopwords = {
        'the', 'of', 'and', 'act', 'code', 'india', 'indian', 'from',
        'law', 'rules', 'rule', 'section', 'sanhita', 'adhiniyam'
    }
    base = normalize_for_match(act_info.get('act_name', ''))
    tokens = [t for t in base.split() if len(t) >= 3 and t not in stopwords]

    # Keep year tokens because many search results are close variants.
    years = re.findall(r'\b(18\d{2}|19\d{2}|20\d{2})\b', base)
    tokens.extend(years)

    # Add short-name specific discriminators to separate similar acts.
    special = {
        'BNS': ['nyaya'],
        'BNSS': ['nagarik', 'suraksha'],
        'BSA': ['sakshya'],
        'POCSO': ['children', 'sexual', 'offences'],
        'ICA': ['contract'],
        'SRA': ['specific', 'relief'],
        'IBC': ['insolvency', 'bankruptcy'],
        'COI': ['constitution'],
    }
    tokens.extend(special.get(act_info.get('short_name', ''), []))

    # Preserve insertion order while deduping.
    seen = set()
    ordered = []
    for token in tokens:
        if token and token not in seen:
            ordered.append(token)
            seen.add(token)
    return ordered


def score_search_result(text: str, act_info: Dict) -> int:
    """Score a search result title to prefer likely target act links."""
    norm = normalize_for_match(text)
    if not norm:
        return -999

    tokens = get_act_hint_tokens(act_info)
    overlap = sum(1 for t in tokens if t in norm)
    score = overlap * 10

    # Prefer statute pages and avoid judgments.
    if ' vs ' in f' {norm} ' or ' high court ' in f' {norm} ' or ' supreme court ' in f' {norm} ':
        score -= 30
    if ' act ' in f' {norm} ' or ' code ' in f' {norm} ' or ' constitution ' in f' {norm} ':
        score += 8

    # Heavily prefer exact short-name signatures when available.
    short_name = act_info.get('short_name', '')
    if short_name == 'BNS' and 'nyaya' in norm and 'nagarik' not in norm:
        score += 25
    if short_name == 'BNSS' and 'nagarik' in norm and 'suraksha' in norm:
        score += 25
    if short_name == 'BSA' and 'sakshya' in norm:
        score += 25

    return score


def looks_like_target_act_page(full_text: str, act_info: Dict) -> bool:
    """Validate that extracted page text belongs to the intended act, not a judgment."""
    sample = normalize_for_match(full_text[:6000])
    if len(sample) < 200:
        return False

    tokens = get_act_hint_tokens(act_info)
    overlap = sum(1 for t in tokens if t in sample)

    has_judgment_markers = (
        (' vs ' in f' {sample} ' and 'high court' in sample)
        or 'petitioner' in sample
        or 'respondent' in sample
    )
    has_statute_markers = (
        'union of india act' in sample
        or 'published in gazette' in sample
        or 'act ' in sample
        or 'code of ' in sample
        or 'part i' in sample
    )

    # Strong token overlap is required for closely named modern acts.
    required_overlap = 3 if act_info.get('short_name') in {'BNS', 'BNSS', 'BSA'} else 2

    if overlap < required_overlap:
        return False
    if has_judgment_markers and not has_statute_markers:
        return False
    return True


async def get_search_candidate_urls(page, act_info: Dict, max_candidates: int = 8) -> List[str]:
    """Collect and rank likely act URLs from Indian Kanoon search results."""
    search_url = (
        f"https://indiankanoon.org/search/"
        f"?formInput={act_info['search_term'].replace(' ', '+')}"
        f"+doctypes:acts"
    )
    await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3)

    anchors = await page.query_selector_all('.result_title a, .result a')
    scored = []
    seen = set()

    for anchor in anchors:
        href = await anchor.get_attribute('href')
        label = (await anchor.inner_text() or '').strip()
        if not href:
            continue
        if not href.startswith('http'):
            href = f"https://indiankanoon.org{href}"
        if href in seen:
            continue
        seen.add(href)

        score = score_search_result(label, act_info)
        scored.append((score, href, label))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:max_candidates]
    if '--test' in sys.argv:
        print("  DEBUG: Top search candidates:")
        for score, href, label in top[:5]:
            print(f"    score={score:>3} url={href} label={label[:80]}")

    return [href for _, href, _ in top]


async def scrape_bare_text(page, url: str, selector: str) -> str:
    """
    Navigate to URL and extract text using selector.
    Handles JavaScript-rendered content.
    """
    try:
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await asyncio.sleep(random.uniform(2, 4))
        
        # Wait for content to render
        await page.wait_for_selector(selector, timeout=10000)
        
        element = await page.query_selector(selector)
        if element:
            text = await element.text_content()
            return text.strip()
        return ""
    except Exception as e:
        print(f"  Error extracting text from {url}: {str(e)[:100]}")
        return ""


async def scrape_act_from_indiacode(playwright, act_info: Dict) -> List[Dict]:
    """
    Scrape complete act text from India Code (official government source).
    Returns list of section documents.
    """
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    )
    page = await context.new_page()
    
    sections = []
    
    try:
        print(f"  Accessing India Code website...")
        await page.goto('https://www.indiacode.nic.in', 
                        wait_until='networkidle',
                        timeout=60000)
        await asyncio.sleep(random.uniform(3, 5))
        
        # Search for act
        search_selectors = ['input[type="search"]', '#search', '.search-box', 'input[name="q"]']
        search_input = None
        for selector in search_selectors:
            try:
                search_input = await page.query_selector(selector)
                if search_input:
                    break
            except:
                continue
        
        if search_input:
            await search_input.fill(act_info['search_term'])
            await search_input.press('Enter')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(random.uniform(3, 6))
        else:
            raise Exception("Could not find search box on India Code")
        
        # Click on first matching result
        result_selectors = [
            'a.act-title', '.search-result a', '.result-item a',
            'a[href*="act"]', 'a[href*="Act"]'
        ]
        
        clicked = False
        for selector in result_selectors:
            try:
                links = await page.query_selector_all(selector)
                for link in links:
                    text = await link.text_content()
                    if text and act_info['search_term'][:20].lower() in text.lower():
                        print(f"  Found act link: {text[:60]}...")
                        await link.click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(random.uniform(3, 5))
                        clicked = True
                        break
                if clicked:
                    break
            except:
                continue
        
        if not clicked:
            raise Exception(f"Could not find act link for {act_info['act_name']}")
        
        # Extract sections
        # India Code typically has sections in elements like .section, .act-section, etc.
        section_selectors = [
            '.section', '.act-section', '[class*="section"]',
            '.provision', 'section', 'article'
        ]
        
        section_elements = []
        for selector in section_selectors:
            try:
                elems = await page.query_selector_all(selector)
                if elems and len(elems) > 5:  # Must have multiple sections
                    section_elements = elems
                    print(f"  Found {len(section_elements)} sections using selector: {selector}")
                    break
            except:
                continue
        
        if not section_elements:
            # Fallback: get all text and parse manually
            print(f"  No section elements found, trying full page extraction...")
            full_text = await page.text_content('body')
            sections = parse_sections_from_text(full_text, act_info)
            if sections:
                print(f"  Extracted {len(sections)} sections from full text")
            else:
                raise Exception("Could not extract any sections")
        else:
            # Process each section element
            for elem in section_elements:
                section_text = await elem.text_content()
                
                if not section_text or len(section_text.strip()) < 20:
                    continue
                
                # Parse section document
                section_doc = parse_section_text(section_text, act_info)
                if section_doc:
                    sections.append(section_doc)
        
    except Exception as e:
        print(f"  India Code scraping failed: {str(e)[:150]}")
        
    finally:
        await context.close()
        await browser.close()
    
    return sections


def parse_section_text(text: str, act_info: Dict) -> Optional[Dict]:
    """
    Parse a single section text into structured document.
    Extracts section number, title, full text, punishment.
    """
    # Extract section number
    # Patterns: "Section 138.", "138.", "Article 21.", "Sec. 420"
    section_patterns = [
        r'(?:Section|Sec\.?|Article|Art\.?)\s+(\d+[A-Z]?)',
        r'^(\d+[A-Z]?)\.',
        r'(\d+[A-Z]?)\s*[-–—]\s*',
    ]
    
    section_num = None
    for pattern in section_patterns:
        match = re.search(pattern, text[:200], re.IGNORECASE)
        if match:
            section_num = match.group(1)
            break
    
    if not section_num:
        section_num = f"unknown_{hash(text[:100]) % 10000}"

    section_num = normalize_section_number(section_num)
    
    # Extract section title (usually first line or first sentence after section number)
    title_match = re.search(
        r'(?:Section|Sec\.?|Article)\s+\d+[A-Z]?[\.:\s–—]+([^.]+)',
        text[:300], re.IGNORECASE
    )
    section_title = title_match.group(1).strip() if title_match else text[:100].strip()
    
    # Clean title (remove newlines, extra spaces)
    section_title = re.sub(r'\s+', ' ', section_title)
    
    # Extract punishment if present
    punishment = None
    punishment_patterns = [
        r'(?:punishable|punishment|imprison|sentence|fine)[^.]{0,200}\.',
        r'shall be punished[^.]{0,200}\.',
        r'imprisonment[^.]{0,200}\.',
    ]
    
    for pattern in punishment_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            punishment = match.group(0).strip()
            break
    
    # Create document
    heading_hi = derive_hindi_heading(section_title)

    section_doc = {
        "id": make_section_id(act_info, section_num, text.strip(), 0),
        "act_name": act_info['act_name'],
        "short_name": act_info['short_name'],
        "section_number": section_num,
        "section_title": section_title,
        "heading_en": section_title,
        "heading_hi": heading_hi,
        "full_text": text.strip(),
        "punishment": punishment,
        "is_replaced": 'replaced_by' in act_info,
        "replaced_by_act": act_info.get('replaced_by'),
        "replaced_act": act_info.get('replaced_act'),
        "effective_date": act_info.get('effective_date'),
        "source": "indiacode.nic.in",
        "priority": act_info.get('priority', 'MEDIUM'),
        "embedding_text": build_embedding_text_with_headings(
            act_name=act_info['act_name'],
            section_number=section_num,
            heading_en=section_title,
            heading_hi=heading_hi,
            body_preview=text[:500],
        ),
    }
    
    return section_doc


def parse_sections_from_text(full_text: str, act_info: Dict) -> List[Dict]:
    """
    Parse complete act text into individual sections.
    Handles multiple formatting patterns from Indian Kanoon and India Code.
    """
    sections = []
    
    # Clean up text first - remove excessive whitespace and normalize
    full_text = re.sub(r'\n\s*\n', '\n\n', full_text)  # Normalize paragraph breaks
    full_text = re.sub(r' +', ' ', full_text)  # Normalize spaces
    
    # Debug output in test mode
    if '--test' in sys.argv:
        print(f"\n  DEBUG: Trying to parse {len(full_text)} chars")
        print(f"  DEBUG: First 800 chars:")
        print(textwrap.indent(full_text[:800], '    '))
    
    # Match section/article headings line-by-line, then slice text between headings.
    heading_patterns = [
        # Section 138. / Section 138 Short title / Article 21.
        re.compile(
            r'(?im)^\s*(?:section|sec\.?|article|art\.?)\s+([0-9]+[A-Z]?(?:\([0-9A-Za-z]+\))?)\s*[\.\-:–—\)]?\s*(.*)$'
        ),
        # Bare numeric headings: 138. / 138) / 138 -
        re.compile(
            r'(?im)^\s*([0-9]+[A-Z]?(?:\([0-9A-Za-z]+\))?)\s*[\.\-:–—\)]\s+(.*)$'
        ),
    ]

    best_matches = []
    for idx, pattern in enumerate(heading_patterns, start=1):
        matches = list(pattern.finditer(full_text))
        if len(matches) > len(best_matches):
            best_matches = matches
        if '--test' in sys.argv:
            print(f"  DEBUG: Heading pattern {idx} matched {len(matches)} candidates")

    if len(best_matches) < 3:
        if '--test' in sys.argv:
            print("  DEBUG: No heading pattern matched sufficiently")
        print("  Warning: Could not parse sections, returning empty")
        return []

    print(f"  Found ~{len(best_matches)} sections in text")

    sections_added = 0
    seen_section_signatures = set()
    section_occurrences = {}
    for idx, match in enumerate(best_matches):
        section_num = normalize_section_number(match.group(1))
        heading_rest = (match.group(2) or '').strip()

        start = match.end()
        end = best_matches[idx + 1].start() if idx + 1 < len(best_matches) else len(full_text)
        body_text = full_text[start:end].strip()

        section_text = body_text
        if heading_rest:
            section_text = f"{heading_rest}\n{body_text}".strip()
        
        # Skip if section number looks invalid or text too short
        if not section_num or len(section_text) < 30:
            continue

        section_occurrences[section_num] = section_occurrences.get(section_num, 0) + 1
        # Keep at most 2 chunks per numeric section to reduce duplicate noise.
        if section_occurrences[section_num] > 2:
            continue
        
        # Take only first 3000 chars of section (some sections are very long)
        # We need enough for good context but not the entire section
        if len(section_text) > 3000:
            section_text = section_text[:3000] + "..."
        
        # Extract section title (usually first line or first sentence)
        lines = section_text.split('\n')
        first_line = lines[0].strip() if lines else section_text[:100]
        section_title = first_line[:200] if len(first_line) > 0 else f"Section {section_num}"
        
        # Remove numbers/bullets from title
        section_title = re.sub(r'^\d+[\.:\-–—\s]+', '', section_title)
        section_title = re.sub(r'\s+', ' ', section_title)
        
        # Extract punishment if present (for criminal law)
        punishment = None
        punishment_patterns = [
            r'(?:shall be punished|punishable|imprisonment|rigorous imprisonment|fine)[^.]{0,300}\.',
            r'penalty[^.]{0,200}\.',
        ]
        
        for pattern in punishment_patterns:
            match = re.search(pattern, section_text[:1000], re.IGNORECASE)
            if match:
                punishment = match.group(0).strip()
                break
        
        # Drop noisy navigation-like snippets that are not substantive sections.
        if len(section_text) < 120 and re.search(r'(?i)^(part|chapter|schedule)\b', section_title.strip()):
            continue

        signature_text = re.sub(r'\s+', ' ', section_text[:220]).strip().lower()
        signature = (section_num, signature_text)
        if signature in seen_section_signatures:
            continue
        seen_section_signatures.add(signature)

        # Create document
        heading_hi = derive_hindi_heading(section_title)

        section_doc = {
            "id": make_section_id(act_info, section_num, section_text, idx),
            "act_name": act_info['act_name'],
            "short_name": act_info['short_name'],
            "section_number": section_num,
            "section_title": section_title,
            "heading_en": section_title,
            "heading_hi": heading_hi,
            "full_text": section_text,
            "punishment": punishment,
            "is_replaced": 'replaced_by' in act_info,
            "replaced_by_act": act_info.get('replaced_by'),
            "replaced_act": act_info.get('replaced_act'),
            "effective_date": act_info.get('effective_date'),
            "source": "parsed_from_text",
            "priority": act_info.get('priority', 'MEDIUM'),
            "embedding_text": build_embedding_text_with_headings(
                act_name=act_info['act_name'],
                section_number=section_num,
                heading_en=section_title,
                heading_hi=heading_hi,
                body_preview=section_text[:600],
            ),
        }
        
        sections.append(section_doc)
        sections_added += 1
        
        # Limit sections to expected count with stricter margin to avoid over-splitting.
        expected = act_info.get('total_sections', 500)
        if sections_added >= expected * 1.2:
            print(f"  Reached expected section count ({sections_added}), stopping parse")
            break
    
    return sections


async def scrape_act_from_kanoon(playwright, act_info: Dict) -> List[Dict]:
    """
    Fallback scraper from Indian Kanoon.
    Uses direct URLs instead of searching for better reliability.
    """
    # Direct URL mappings for major acts (more reliable than searching)
    DIRECT_URLS = {
        "IPC": "https://indiankanoon.org/doc/1569253/",
        # NOTE: BNS direct URL has been unstable and may resolve to a judgment page.
        # Use search fallback for this act.
        "CrPC": "https://indiankanoon.org/doc/445276/",
        # NOTE: BNSS direct URL has been unstable and may resolve to non-act content.
        # Use search fallback for this act.
        "IEA": "https://indiankanoon.org/doc/1953529/",
        # NOTE: BSA direct URL has been unstable and may resolve to non-act content.
        # Use search fallback for this act.
        "ICA": "https://indiankanoon.org/doc/1676478/",
        "CPC": "https://indiankanoon.org/doc/1596610/",
        "SRA": "https://indiankanoon.org/doc/1649237/",
        "TPA": "https://indiankanoon.org/doc/140691/",
        "NI Act": "https://indiankanoon.org/doc/1132672/",  # Full act, not single section
        "NIA": "https://indiankanoon.org/doc/1132672/",
        "Companies Act": "https://indiankanoon.org/doc/94474621/",
        "Constitution": "https://indiankanoon.org/doc/663573/",
        "COI": "https://indiankanoon.org/doc/663573/",
        "Consumer Protection": "https://indiankanoon.org/doc/48103131/",  # Full act
        "Arbitration Act": "https://indiankanoon.org/doc/1306824/",
        "Hindu Marriage Act": "https://indiankanoon.org/doc/590166/",
        "PWDV Act": "https://indiankanoon.org/doc/542601/",  # Full act
        "POCSO": "https://indiankanoon.org/doc/145379145/",
        "IT Act": "https://indiankanoon.org/doc/1127741/",  # Updated to working URL
        "IBC": "https://indiankanoon.org/doc/34744797/",
        "GST Act": "https://indiankanoon.org/doc/143971657/",
    }
    
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    )
    page = await context.new_page()
    sections = []
    
    try:
        print(f"  Using Indian Kanoon direct URL...")
        
        direct_url = DIRECT_URLS.get(act_info['short_name'])
        candidate_urls: List[str] = []

        if direct_url:
            candidate_urls.append(direct_url)

        print(f"  Searching for best act URL...")
        candidate_urls.extend(await get_search_candidate_urls(page, act_info))

        # Keep first occurrence order while deduping.
        unique_candidates = []
        seen_candidates = set()
        for candidate in candidate_urls:
            if candidate and candidate not in seen_candidates:
                unique_candidates.append(candidate)
                seen_candidates.add(candidate)

        if not unique_candidates:
            raise Exception("No URL found for act")

        # Try candidates until one passes validation and parsing.
        for attempt, url in enumerate(unique_candidates[:8], start=1):
            print(f"  Candidate {attempt}: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)

            # Check if we're on a single section page - look for "Entire Act" link
            entire_act_link = await page.query_selector('a:has-text("Entire Act")')
            if entire_act_link:
                entire_act_url = await entire_act_link.get_attribute('href')
                if entire_act_url:
                    if not entire_act_url.startswith('http'):
                        entire_act_url = f"https://indiankanoon.org{entire_act_url}"
                    print(f"  ℹ Following 'Entire Act' link: {entire_act_url}")
                    await page.goto(entire_act_url, wait_until='domcontentloaded', timeout=60000)
                    await asyncio.sleep(3)

            # Extract full text from multiple possible containers
            content_selectors = [
                'article',
                'div.doc_content',
                '#doc_content',
                'div.judgments',
                'pre',
                'div.doc',
            ]

            full_text = ""
            for selector in content_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        full_text = await elem.inner_text()
                        if len(full_text) > 500:
                            print(f"  Got text using selector: {selector}")
                            break
                except:
                    continue

            if not full_text or len(full_text) < 500:
                full_text = await page.inner_text('body')

            if len(full_text) < 500:
                print("  Skipping candidate (insufficient text)")
                continue

            if '--test' in sys.argv:
                print(f"\n  DEBUG: Text length = {len(full_text)} chars")
                print(f"  DEBUG: First 1500 chars of extracted text:")
                print(f"  {'='*60}")
                print(textwrap.indent(full_text[:1500], '  '))
                print(f"  {'='*60}\n")

            if not looks_like_target_act_page(full_text, act_info):
                print("  Rejected candidate (title/content mismatch)")
                continue

            # Parse sections from full text
            sections = parse_sections_from_text(full_text, act_info)
            if not sections or len(sections) < 3:
                print("  Rejected candidate (parser returned too few sections)")
                continue

            for section in sections:
                section['source'] = f"indiankanoon.org ({url})"

            print(f"  ✓ Extracted {len(sections)} sections")
            break
        
    except Exception as e:
        print(f"  ✗ Kanoon scraping failed: {str(e)[:100]}")
    finally:
        await context.close()
        await browser.close()
    
    return sections


async def load_all_acts(only_short_names: Optional[set] = None, force_reload: bool = False):
    """
    Main loader function.
    Scrapes all acts and loads into ChromaDB.
    Saves backup JSON for each act.
    """
    client = chromadb.PersistentClient(path='./legal_research_db')
    
    try:
        collection = client.get_collection('bare_acts')
        print(f"Found existing bare_acts collection with {collection.count()} documents")
    except:
        collection = client.create_collection('bare_acts')
        print("Created new bare_acts collection")
    
    total_loaded = 0
    stats = {
        "success": [],
        "failed": [],
        "skipped": []
    }
    
    # Sort by priority
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_acts = sorted(
        ACTS_TO_LOAD,
        key=lambda x: priority_order.get(x.get('priority', 'MEDIUM'), 2)
    )

    if only_short_names:
        sorted_acts = [a for a in sorted_acts if a['short_name'] in only_short_names]
    
    async with async_playwright() as playwright:
        for idx, act_info in enumerate(sorted_acts, 1):
            print(f"\n{'='*60}")
            print(f"[{idx}/{len(sorted_acts)}] Scraping: {act_info['act_name']}")
            print(f"Priority: {act_info.get('priority', 'MEDIUM')}")
            print(f"{'='*60}")
            
            # Check if already loaded
            try:
                existing = collection.get(
                    where={"act_name": {"$eq": act_info['act_name']}}
                )
                if force_reload and existing and existing.get('ids'):
                    # Prevent duplicate-noise growth across reruns.
                    collection.delete(ids=existing['ids'])
                    print(f"  ♻ Force-reload: removed {len(existing['ids'])} existing chunks")
                    existing = {'ids': []}
                if not force_reload and existing and len(existing['ids']) > 20:
                    print(f"  ✓ Already loaded ({len(existing['ids'])} sections). Skipping.")
                    stats["skipped"].append(act_info['act_name'])
                    continue
            except Exception as e:
                print(f"  Warning: Could not check existing: {e}")
            
            # Use Indian Kanoon directly (more reliable than India Code)
            # India Code website structure changes frequently, causing scraping to fail
            sections = await scrape_act_from_kanoon(playwright, act_info)
            
            if not sections or len(sections) < 3:
                print(f"  ✗ FAILED: Could not scrape {act_info['act_name']}")
                stats["failed"].append(act_info['act_name'])
                continue
            
            # Save backup JSON
            os.makedirs('data/backup/bare_acts', exist_ok=True)
            backup_path = f"data/backup/bare_acts/{act_info['short_name']}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "act_info": act_info,
                    "total_sections": len(sections),
                    "sections": sections
                }, f, ensure_ascii=False, indent=2)
            print(f"  Backup saved: {backup_path}")
            
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
                    collection.add(
                        ids=ids,
                        documents=documents,
                        metadatas=metadatas
                    )
                    loaded_count += len(batch)
                except Exception as e:
                    # Try upsert for duplicates
                    try:
                        collection.upsert(
                            ids=ids,
                            documents=documents,
                            metadatas=metadatas
                        )
                        loaded_count += len(batch)
                    except Exception as e2:
                        print(f"  Error loading batch: {str(e2)[:100]}")
            
            total_loaded += loaded_count
            stats["success"].append(act_info['act_name'])
            print(f"  ✓ Loaded {loaded_count} sections to database")
            
            # Respectful delay between acts
            await asyncio.sleep(random.uniform(8, 15))
    
    # Final report
    print(f"\n{'='*60}")
    print("BARE ACTS LOADING COMPLETE")
    print(f"{'='*60}")
    print(f"Total sections loaded: {total_loaded}")
    print(f"Collection count: {collection.count()}")
    print(f"\nSuccessfully loaded: {len(stats['success'])} acts")
    print(f"Skipped (already loaded): {len(stats['skipped'])} acts")
    print(f"Failed: {len(stats['failed'])} acts")
    
    if stats["failed"]:
        print(f"\n⚠ Failed to load:")
        for act in stats["failed"]:
            print(f"  - {act}")
    
    # Save final stats
    os.makedirs('data/backup', exist_ok=True)
    with open('data/backup/bare_acts_loading_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    return collection


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="LexAI bare acts loader")
    parser.add_argument('--test', action='store_true', help='Run quick scraper test')
    parser.add_argument(
        '--only',
        type=str,
        default='',
        help='Comma-separated short names to load (example: BNS,BNSS,BSA)'
    )
    parser.add_argument(
        '--force-reload',
        action='store_true',
        help='Reload acts even if already present in the collection'
    )
    args = parser.parse_args()
    
    # Test mode: quickly test scraping a single act
    if args.test and not args.only.strip():
        print("""
╔══════════════════════════════════════════════════════════════╗
║         Testing Bare Acts Scraper                            ║
║         Testing with Negotiable Instruments Act (NI Act)     ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        async def test_scraper():
            # Test with NI Act (smaller, faster)
            test_act = {
                "act_name": "Negotiable Instruments Act 1881",
                "short_name": "NI Act",
                "search_term": "Negotiable Instruments Act",
                "total_sections": 147,
                "priority": "HIGH"
            }
            
            async with async_playwright() as playwright:
                print("\nTesting Indian Kanoon scraper...")
                sections = await scrape_act_from_kanoon(playwright, test_act)
                
                if sections and len(sections) >= 3:
                    print(f"\n✓ SUCCESS! Scraped {len(sections)} sections")
                    print(f"\nFirst 3 sections:")
                    for i, sec in enumerate(sections[:3]):
                        print(f"\n{i+1}. Section {sec['section_number']}: {sec['section_title']}")
                        print(f"   Text preview: {sec['full_text'][:150]}...")
                    
                    print(f"\n✓ Scraper is working! You can now run:")
                    print(f"   python bare_acts_loader.py")
                    print(f"\nThis will scrape all 20+ acts (2-3 hours).")
                else:
                    print(f"\n✗ FAILED: Could not scrape sections")
                    print(f"Debug: Got {len(sections) if sections else 0} sections")
        
        asyncio.run(test_scraper())
        sys.exit(0)
    
    # Normal mode: load all acts
    print("""
╔══════════════════════════════════════════════════════════════╗
║         LexAI Complete Bare Acts Loader                      ║
║         Loading 20+ major Indian acts from official sources  ║
║         Estimated time: 2-3 hours                            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    only_set = None
    if args.only.strip():
        only_set = {item.strip() for item in args.only.split(',') if item.strip()}
        print(f"\nLoading only selected acts: {', '.join(sorted(only_set))}")

    asyncio.run(load_all_acts(only_short_names=only_set, force_reload=args.force_reload))
    print("\n✓ Bare acts loading complete. Run judgment_loader.py next.")
