"""
Start the Legal Research API server
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from api.legal_research import app
    
    PORT = int(os.getenv("PORT", 8000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    print("=" * 80)
    print("LEGAL RESEARCH API - PRODUCTION SERVER")
    print("=" * 80)
    print(f"Server: {HOST}:{PORT}")
    print(f"API Docs: http://localhost:{PORT}/api/docs")
    print(f"Health Check: http://localhost:{PORT}/api/health")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print("=" * 80)
    print()
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
