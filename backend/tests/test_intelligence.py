"""
Test script for Intelligence Layer
====================================
This script tests the query logging, analytics, and feedback collection.

Run this after the API has processed some queries.
"""

import sys
from datetime import datetime

from intelligence.query_logger import QueryLogger, QueryLog, ResponseLog
from intelligence.analytics import AnalyticsEngine
from intelligence.feedback import FeedbackCollector

def test_query_logging():
    """Test query logging functionality"""
    print("\n" + "="*80)
    print("TEST 1: Query Logging")
    print("="*80)
    
    # Initialize logger
    logger = QueryLogger(db_path="./intelligence.db")
    
    # Log a test query
    query_log = QueryLog(
        query_text="What is the punishment for cheating under IPC 420?",
        query_type="general_question",
        user_id=None,
        session_id="test-session-001",
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0 (Test Browser)"
    )
    
    query_id = logger.log_query(query_log)
    print(f"✅ Query logged with ID: {query_id}")
    
    # Log response
    response_log = ResponseLog(
        query_id=query_id,
        answer="Section 420 of IPC deals with cheating...",
        confidence="HIGH",
        sources_count=5,
        response_time_ms=1234,
        warnings=[],
        trigger_uncertainty=False
    )
    
    response_id = logger.log_response(response_log)
    print(f"✅ Response logged with ID: {response_id}")
    
    # Get query history
    history = logger.get_query_history(limit=5)
    print(f"\n📊 Recent Query History ({len(history)} queries):")
    for i, query in enumerate(history[:3], 1):
        print(f"{i}. [{query['timestamp']}] {query['query_text'][:60]}...")
        print(f"   Type: {query['query_type']}, Session: {query['session_id']}")
    
    # Get performance stats
    stats = logger.get_performance_stats(days=30)
    print(f"\n📈 Performance Stats (last 30 days):")
    print(f"   Total Queries: {stats['total_queries']}")
    print(f"   Avg Response Time: {stats['avg_response_time_ms']:.2f}ms")
    print(f"   Confidence Distribution: {stats['confidence_distribution']}")
    
    return query_id, response_id

def test_analytics(logger):
    """Test analytics functionality"""
    print("\n" + "="*80)
    print("TEST 2: Analytics Engine")
    print("="*80)
    
    # Initialize analytics
    analytics = AnalyticsEngine(logger)
    
    # Get dashboard stats
    dashboard = analytics.get_dashboard_stats()
    print("\n📊 Dashboard Statistics:")
    
    if 'today' in dashboard:
        print(f"\n   Today:")
        print(f"      Queries: {dashboard['today'].get('total_queries', 0)}")
        print(f"      Sessions: {dashboard['today'].get('unique_sessions', 0)}")
        print(f"      Avg Response Time: {dashboard['today'].get('avg_response_time_ms', 0):.2f}ms")
    
    if 'this_week' in dashboard:
        print(f"\n   This Week:")
        print(f"      Queries: {dashboard['this_week'].get('total_queries', 0)}")
        print(f"      Sessions: {dashboard['this_week'].get('unique_sessions', 0)}")
    
    if 'all_time' in dashboard:
        print(f"\n   All Time:")
        print(f"      Queries: {dashboard['all_time'].get('total_queries', 0)}")
        print(f"      Sessions: {dashboard['all_time'].get('unique_sessions', 0)}")
    
    if 'confidence_distribution' in dashboard:
        print(f"\n   Confidence Distribution:")
        for level, count in dashboard['confidence_distribution'].items():
            print(f"      {level}: {count}")
    
    # Analyze query patterns
    patterns = analytics.analyze_query_patterns()
    print("\n🔍 Query Pattern Analysis:")
    
    if 'common_sections' in patterns and patterns['common_sections']:
        print(f"\n   Most Queried Sections:")
        for section, count in patterns['common_sections'][:5]:
            print(f"      {section}: {count} queries")
    
    if 'common_acts' in patterns and patterns['common_acts']:
        print(f"\n   Most Queried Acts:")
        for act, count in patterns['common_acts'][:5]:
            print(f"      {act}: {count} queries")
    
    if 'peak_hours' in patterns and patterns['peak_hours']:
        print(f"\n   Peak Query Hours:")
        peak_hours = patterns['peak_hours']
        if isinstance(peak_hours, dict):
            for hour, count in sorted(peak_hours.items(), 
                                      key=lambda x: x[1], reverse=True)[:5]:
                print(f"      {hour:02d}:00 - {count} queries")
        elif isinstance(peak_hours, list):
            for item in peak_hours[:5]:
                print(f"      {item}")
    
    # Get improvement suggestions
    suggestions = analytics.get_improvement_suggestions()
    if suggestions:
        print(f"\n💡 Improvement Suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")

def test_feedback(logger, query_id, response_id):
    """Test feedback collection"""
    print("\n" + "="*80)
    print("TEST 3: Feedback Collection")
    print("="*80)
    
    # Initialize feedback collector
    feedback = FeedbackCollector(logger)
    
    # Submit test feedback
    feedback_id = feedback.submit_feedback(
        query_id=query_id,
        response_id=response_id,
        rating=5,
        helpful=True,
        accurate=True,
        comment="Excellent explanation with proper citations!"
    )
    
    print(f"✅ Feedback submitted with ID: {feedback_id}")
    
    # Get feedback summary
    summary = feedback.get_feedback_summary(days=30)
    print(f"\n📊 Feedback Summary (last 30 days):")
    print(f"   Total Feedback: {summary['total_feedback']}")
    print(f"   Average Rating: {summary.get('avg_rating', 0):.2f}/5.0")
    print(f"   Helpful Rate: {summary.get('helpful_percentage', 0):.1f}%")
    print(f"   Accurate Rate: {summary.get('accurate_percentage', 0):.1f}%")
    
    if summary['rating_distribution']:
        print(f"\n   Rating Distribution:")
        for rating, count in sorted(summary['rating_distribution'].items(), reverse=True):
            stars = '⭐' * rating
            print(f"      {stars} ({rating}): {count}")
    
    # Check for problematic responses
    problematic = feedback.get_problematic_responses(threshold=2)
    if problematic:
        print(f"\n⚠️  Problematic Responses (rating ≤ 2): {len(problematic)}")
        for resp in problematic[:3]:
            print(f"   - Query: {resp['query_text'][:60]}...")
            print(f"     Rating: {resp['rating']}/5, Comment: {resp['comment']}")
    else:
        print(f"\n✅ No problematic responses found (all ratings > 2)")

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 INTELLIGENCE LAYER TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Test query logging
        query_id, response_id = test_query_logging()
        
        # Test analytics
        logger = QueryLogger(db_path="./intelligence.db")
        test_analytics(logger)
        
        # Test feedback
        test_feedback(logger, query_id, response_id)
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nThe intelligence layer is working correctly.")
        print("\nNext steps:")
        print("1. Start the API: python start_api.py")
        print("2. Make some queries via the API endpoints")
        print("3. Check analytics at: GET http://localhost:8000/api/analytics/dashboard")
        print("4. Submit feedback via: POST http://localhost:8000/api/feedback")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
