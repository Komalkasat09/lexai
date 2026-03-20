"""
Debug script to inspect PDF text format for 2023 acts
"""
import fitz  # PyMuPDF

def show_text_sample(pdf_path: str, pages_to_show: int = 3):
    """Show text sample from PDF to understand formatting"""
    print(f"\n{'='*80}")
    print(f"PDF: {pdf_path}")
    print(f"{'='*80}\n")
    
    doc = fitz.open(pdf_path)
    
    for page_num in range(min(pages_to_show, len(doc))):
        page = doc[page_num]
        text = page.get_text()
        
        print(f"\n{'-'*80}")
        print(f"PAGE {page_num + 1}")
        print(f"{'-'*80}")
        print(text[:2000])  # First 2000 chars
        print(f"\n[... rest of page {page_num + 1} omitted ...]\n")
    
    doc.close()

if __name__ == "__main__":
    # Show samples from all 3 acts
    show_text_sample("data/backup/pdfs/BNS.pdf", pages_to_show=2)
    show_text_sample("data/backup/pdfs/BNSS.pdf", pages_to_show=2)
    show_text_sample("data/backup/pdfs/BSA.pdf", pages_to_show=2)
