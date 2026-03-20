"""
Test script for Legal Research API
Tests all endpoints with sample requests
"""

import requests
import json
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"

def print_response(title: str, response: requests.Response):
    """Pretty print API response"""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print('=' * 80)
    print(f"Status Code: {response.status_code}")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(response.text)

def test_health():
    """Test health check endpoint"""
    print("\n🔍 Testing Health Check...")
    response = requests.get(f"{BASE_URL}/api/health")
    print_response("HEALTH CHECK", response)
    return response.status_code == 200

def test_legal_question():
    """Test legal question endpoint"""
    print("\n🔍 Testing Legal Question...")
    
    payload = {
        "query": "What is the punishment for cheating under IPC?",
        "include_reasoning": True
    }
    
    response = requests.post(f"{BASE_URL}/api/legal/question", json=payload)
    print_response("LEGAL QUESTION", response)
    return response.status_code == 200

def test_explain_section():
    """Test section explanation endpoint"""
    print("\n🔍 Testing Section Explanation...")
    
    payload = {
        "act_name": "Indian Penal Code 1860",
        "section_number": "420"
    }
    
    response = requests.post(f"{BASE_URL}/api/legal/section/explain", json=payload)
    print_response("SECTION EXPLANATION", response)
    return response.status_code == 200

def test_summarize_judgment():
    """Test judgment summary endpoint"""
    print("\n🔍 Testing Judgment Summary...")
    
    payload = {
        "citation": "AIR 2019 SC 1234"
    }
    
    response = requests.post(f"{BASE_URL}/api/legal/judgment/summarize", json=payload)
    print_response("JUDGMENT SUMMARY", response)
    return response.status_code == 200

def test_compare_sections():
    """Test section comparison endpoint"""
    print("\n🔍 Testing Section Comparison...")
    
    payload = {
        "old_section": "IPC 420",
        "new_section": "BNS 318"
    }
    
    response = requests.post(f"{BASE_URL}/api/legal/section/compare", json=payload)
    print_response("SECTION COMPARISON", response)
    return response.status_code == 200

def test_legal_opinion():
    """Test legal opinion endpoint"""
    print("\n🔍 Testing Legal Opinion...")
    
    payload = {
        "facts": "Party A promised to marry Party B but later refused after the relationship was consummated. Party B claims this constitutes rape.",
        "legal_issue": "Can mere breach of promise to marry be prosecuted as rape under IPC 376?"
    }
    
    response = requests.post(f"{BASE_URL}/api/legal/opinion", json=payload)
    print_response("LEGAL OPINION", response)
    return response.status_code == 200

def main():
    """Run all tests"""
    print("=" * 80)
    print("LEGAL RESEARCH API - TEST SUITE")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print()
    
    results = {
        "Health Check": False,
        "Legal Question": False,
        "Section Explanation": False,
        "Judgment Summary": False,
        "Section Comparison": False,
        "Legal Opinion": False
    }
    
    try:
        # Run tests
        results["Health Check"] = test_health()
        results["Legal Question"] = test_legal_question()
        results["Section Explanation"] = test_explain_section()
        results["Judgment Summary"] = test_summarize_judgment()
        results["Section Comparison"] = test_compare_sections()
        results["Legal Opinion"] = test_legal_opinion()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API server")
        print(f"Make sure the server is running on {BASE_URL}")
        print("\nStart the server with:")
        print("  cd backend")
        print("  python api/legal_research.py")
        return
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<50} {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print("=" * 80)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 80)

if __name__ == "__main__":
    main()
