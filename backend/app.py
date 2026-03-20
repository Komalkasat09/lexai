"""
Legal Research API - Single Entry Point
=========================================

Production-ready FastAPI server with all features:
- Legal document research and analysis
- Contract review
- Smart retrieval with LLM
- Real-time analytics and feedback
- Auto-updating legal database

Usage:
    python app.py                    # Start API server
    python app.py --port 8080        # Custom port
    python app.py --load-data        # Load production data first
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure backend is in path
sys.path.insert(0, str(Path(__file__).parent))

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI server"""
    import uvicorn
    from api.legal_research import app
    
    print("=" * 80)
    print("🏛️  LEGAL RESEARCH API - PRODUCTION SERVER")
    print("=" * 80)
    print(f"🌐 Server: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print(f"📚 API Docs: http://localhost:{port}/api/docs")
    print(f"❤️  Health Check: http://localhost:{port}/api/health")
    print(f"🔧 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"🗄️  Database: ./legal_research_db")
    print("=" * 80)
    print()
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=os.getenv('ENVIRONMENT') == 'development'
    )

def load_production_data():
    """Load production data before starting server"""
    print("\n📦 Loading production data...")
    sys.path.insert(0, str(Path(__file__).parent / "scripts"))
    from production_data_loader import load_huggingface_data
    from database.chroma_setup import LegalResearchDB
    
    db = LegalResearchDB(persist_directory="./legal_research_db")
    load_huggingface_data(db, quick_test=False)
    print("✅ Production data loaded!")

def main():
    parser = argparse.ArgumentParser(description="Legal Research API Server")
    parser.add_argument('--host', default=os.getenv('HOST', '0.0.0.0'), help='Host address')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', 8000)), help='Port number')
    parser.add_argument('--load-data', action='store_true', help='Load production data before starting')
    
    args = parser.parse_args()
    
    if args.load_data:
        load_production_data()
    
    start_server(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
