"""
Debug Single Act Scraper
=========================
Test scraping a specific act with full debug output.
"""

import asyncio
from playwright.async_api import async_playwright
import sys

async def debug_scrape():
    """Scrape and debug a single act."""
    
    # Test Indian Contract Act (should exist - old act from 1872)
    url = "https://indiankanoon.org/doc/1676478/"
    
    print(f"\nFetching: {url}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Load page
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3)
        
        # Try different selectors
        selectors = ['div.judgments', 'div.doc_content', '#doc_content', 'pre', 'article', 'div.doc']
        
        for selector in selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if len(text) > 500:
                        print(f"✓ Selector '{selector}' got {len(text)} chars")
                        print(f"\nFirst 2000 chars:\n{'-'*60}")
                        print(text[:2000])
                        print(f"{'-'*60}")
                        print(f"\nLast 1000 chars:\n{'-'*60}")
                        print(text[-1000:])
                        print(f"{'-'*60}\n")
                        break
                    else:
                        print(f"  Selector '{selector}': Too short ({len(text)} chars)")
                else:
                    print(f"  Selector '{selector}': Not found")
            except Exception as e:
                print(f"  Selector '{selector}': Error - {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_scrape())
