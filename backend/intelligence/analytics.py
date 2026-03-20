"""
Analytics Engine - Intelligence Layer
=====================================

Analyzes query patterns, performance metrics, and system health.

Features:
- Real-time analytics dashboard data
- Query pattern analysis
- Source quality metrics
- User engagement tracking
- System optimization insights

Author: Legal Research System
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import Counter
import re


class AnalyticsEngine:
    """
    Analyzes system usage and performance for optimization
    
    Provides insights on:
    - Query patterns and trends
    - Source effectiveness
    - Response quality metrics
    - User engagement
    - System performance
    """
    
    def __init__(self, query_logger):
        """
        Initialize analytics engine
        
        Args:
            query_logger: QueryLogger instance or str path to database
        """
        if isinstance(query_logger, str):
            self.db_path = Path(query_logger)
        else:
            # query_logger is a QueryLogger instance
            self.db_path = Path(query_logger.db_path)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Query logs database not found: {self.db_path}")
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard statistics
        
        Returns complete system metrics for dashboard display
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Today's stats
        cursor.execute("""
            SELECT 
                COUNT(*) as queries_today,
                COUNT(DISTINCT session_id) as sessions_today
            FROM queries
            WHERE DATE(timestamp) = DATE('now')
        """)
        today = cursor.fetchone()
        
        # This week's stats
        cursor.execute("""
            SELECT 
                COUNT(*) as queries_week,
                AVG(r.response_time_ms) as avg_response_time
            FROM queries q
            LEFT JOIN responses r ON q.query_id = r.query_id
            WHERE q.timestamp >= datetime('now', '-7 days')
        """)
        week = cursor.fetchone()
        
        # Total stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_queries,
                COUNT(DISTINCT session_id) as total_sessions
            FROM queries
        """)
        total = cursor.fetchone()
        
        # Average feedback rating
        cursor.execute("""
            SELECT 
                AVG(rating) as avg_rating,
                COUNT(*) as feedback_count
            FROM feedback
        """)
        feedback = cursor.fetchone ()
        
        # Confidence breakdown
        cursor.execute("""
            SELECT 
                confidence,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM responses), 2) as percentage
            FROM responses
            GROUP BY confidence
        """)
        confidence_breakdown = {row[0]: {'count': row[1], 'percentage': row[2]} 
                               for row in cursor.fetchall()}
        
        # Query type breakdown
        cursor.execute("""
            SELECT 
                query_type,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM queries), 2) as percentage
            FROM queries
            GROUP BY query_type
        """)
        query_type_breakdown = {row[0]: {'count': row[1], 'percentage': row[2]} 
                                for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'today': {
                'queries': today[0] or 0,
                'sessions': today[1] or 0
            },
            'this_week': {
                'queries': week[0] or 0,
                'avg_response_time_ms': round(week[1] or 0, 2)
            },
            'all_time': {
                'total_queries': total[0] or 0,
                'total_sessions': total[1] or 0
            },
            'user_satisfaction': {
                'avg_rating': round(feedback[0] or 0, 2),
                'total_feedback': feedback[1] or 0
            },
            'confidence_distribution': confidence_breakdown,
            'query_type_distribution': query_type_breakdown
        }
    
    def analyze_query_patterns(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze query patterns over time
        
        Identifies:
        - Common query themes
        - Peak usage times
        - Query complexity trends
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all queries in period
        cursor.execute("""
            SELECT query_text, query_type, timestamp
            FROM queries
            WHERE timestamp >= datetime('now', '-{} days')
        """.format(days))
        
        queries = cursor.fetchall()
        
        # Extract section numbers mentioned
        section_pattern = r'[Ss]ection\s+(\d+[A-Z]*)'
        sections_mentioned = []
        for query_text, _, _ in queries:
            sections = re.findall(section_pattern, query_text)
            sections_mentioned.extend(sections)
        
        # Most mentioned sections
        section_counter = Counter(sections_mentioned)
        
        # Extract act names
        act_pattern = r'(IPC|CrPC|BNS|BNSS|Evidence Act|Constitution)'
        acts_mentioned = []
        for query_text, _, _ in queries:
            acts = re.findall(act_pattern, query_text, re.IGNORECASE)
            acts_mentioned.extend([act.upper() for act in acts])
        
        # Most mentioned acts
        act_counter = Counter(acts_mentioned)
        
        # Query complexity (word count distribution)
        query_lengths = [len(query_text.split()) for query_text, _, _ in queries]
        avg_query_length = sum(query_lengths) / len(query_lengths) if query_lengths else 0
        
        # Peak hours analysis
        hours = [datetime.fromisoformat(ts).hour for _, _, ts in queries]
        hour_counter = Counter(hours)
        peak_hours = sorted(hour_counter.items(), key=lambda x: x[1], reverse=True)[:5]
        
        conn.close()
        
        return {
            'total_queries_analyzed': len(queries),
            'top_sections': dict(section_counter.most_common(10)),
            'top_acts': dict(act_counter.most_common(10)),
            'avg_query_length_words': round(avg_query_length, 2),
            'peak_hours': [{'hour': h, 'count': c} for h, c in peak_hours],
            'analysis_period_days': days
        }
    
    def analyze_source_effectiveness(self) -> Dict[str, Any]:
        """
        Analyze which sources provide best results
        
        Tracks:
        - Bare acts vs case law effectiveness
        - Source count correlation with confidence
        - Best performing source combinations
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Average confidence by source count
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN sources_count = 0 THEN '0'
                    WHEN sources_count <= 2 THEN '1-2'
                    WHEN sources_count <= 5 THEN '3-5'
                    ELSE '6+'
                END as source_range,
                AVG(CASE confidence
                    WHEN 'HIGH' THEN 3
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'LOW' THEN 1
                END) as avg_confidence_score,
                COUNT(*) as count
            FROM responses
            GROUP BY source_range
        """)
        
        source_confidence = [
            {
                'source_range': row[0],
                'avg_confidence_score': round(row[1] or 0, 2),
                'sample_size': row[2]
            }
            for row in cursor.fetchall()
        ]
        
        # Bare acts vs case law effectiveness
        cursor.execute("""
            SELECT 
                AVG(bare_acts_retrieved) as avg_bare_acts,
                AVG(case_laws_retrieved) as avg_case_laws,
                AVG(amendments_retrieved) as avg_amendments,
                confidence,
                COUNT(*) as count
            FROM responses
            GROUP BY confidence
        """)
        
        source_by_confidence = [
            {
                'confidence': row[3],
                'avg_bare_acts': round(row[0] or 0, 2),
                'avg_case_laws': round(row[1] or 0, 2),
                'avg_amendments': round(row[2] or 0, 2),
                'sample_size': row[4]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            'source_count_effectiveness': source_confidence,
            'source_type_by_confidence': source_by_confidence
        }
    
    def get_improvement_suggestions(self) -> List[Dict[str, str]]:
        """
        Generate actionable improvement suggestions
        
        Based on:
        - Low confidence queries
        - Common query patterns
        - Missing sources
        - User feedback
        """
        suggestions = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for high percentage of low confidence responses
        cursor.execute("""
            SELECT 
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM responses), 2) as low_conf_percentage
            FROM responses
            WHERE confidence = 'LOW'
        """)
        low_conf_pct = cursor.fetchone()[0] or 0
        
        if low_conf_pct > 20:
            suggestions.append({
                'type': 'data_quality',
                'priority': 'high',
                'issue': f'{low_conf_pct}% of queries return low confidence responses',
                'recommendation': 'Increase data scraping frequency or expand source coverage'
            })
        
        # Check for slow response times
        cursor.execute("""
            SELECT AVG(response_time_ms) as avg_time
            FROM responses
            WHERE timestamp >= datetime('now', '-7 days')
        """)
        avg_time = cursor.fetchone()[0] or 0
        
        if avg_time > 5000:  # More than 5 seconds
            suggestions.append({
                'type': 'performance',
                'priority': 'medium',
                'issue': f'Average response time is {round(avg_time/1000, 2)}s',
                'recommendation': 'Consider caching common queries or optimizing retrieval'
            })
        
        # Check for queries with zero sources
        cursor.execute("""
            SELECT COUNT(*) as zero_source_count
            FROM responses
            WHERE sources_count = 0
        """)
        zero_sources = cursor.fetchone()[0] or 0
        
        if zero_sources > 10:
            suggestions.append({
                'type': 'data_coverage',
                'priority': 'high',
                'issue': f'{zero_sources} queries returned zero sources',
                'recommendation': 'Review low-source queries to identify gaps in database coverage'
            })
        
        # Check feedback ratings
        cursor.execute("""
            SELECT AVG(rating) as avg_rating
            FROM feedback
            WHERE timestamp >= datetime('now', '-30 days')
        """)
        avg_rating = cursor.fetchone()[0]
        
        if avg_rating and avg_rating < 3.5:
            suggestions.append({
                'type': 'user_satisfaction',
                'priority': 'high',
                'issue': f'Average user rating is {round(avg_rating, 2)}/5',
                'recommendation': 'Review user feedback comments to identify specific issues'
            })
        
        conn.close()
        
        return suggestions
    
    def generate_report(self, format: str = 'json') -> str:
        """Generate comprehensive analytics report"""
        dashboard = self.get_dashboard_stats()
        patterns = self.analyze_query_patterns(days=30)
        sources = self.analyze_source_effectiveness()
        suggestions = self.get_improvement_suggestions()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'dashboard_overview': dashboard,
            'query_patterns': patterns,
            'source_effectiveness': sources,
            'improvement_suggestions': suggestions
        }
        
        if format == 'json':
            return json.dumps(report, indent=2)
        else:
            # Text format
            text = f"""
===============================================================
LEGAL RESEARCH SYSTEM - ANALYTICS REPORT
===============================================================
Generated: {report['generated_at']}

OVERVIEW
---------------------------------------------------------------
Total Queries (All Time): {dashboard['all_time']['total_queries']}
Unique Sessions: {dashboard['all_time']['total_sessions']}
Queries Today: {dashboard['today']['queries']}
Queries This Week: {dashboard['this_week']['queries']}
Avg Response Time: {dashboard['this_week']['avg_response_time_ms']}ms
User Rating: {dashboard['user_satisfaction']['avg_rating']}/5.0

QUERY PATTERNS (Last 30 Days)
---------------------------------------------------------------
Total Analyzed: {patterns['total_queries_analyzed']}
Avg Query Length: {patterns['avg_query_length_words']} words
Top Sections: {', '.join(f"Sec {k} ({v})" for k, v in list(patterns['top_sections'].items())[:5])}
Top Acts: {', '.join(f"{k} ({v})" for k, v in list(patterns['top_acts'].items())[:3])}

IMPROVEMENT SUGGESTIONS
---------------------------------------------------------------
"""
            for i, sug in enumerate(suggestions, 1):
                text += f"{i}. [{sug['priority'].upper()}] {sug['issue']}\n"
                text += f"   → {sug['recommendation']}\n\n"
            
            text += "===============================================================\n"
            return text


# CLI interface
if __name__ == "__main__":
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Legal Research Analytics")
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                        help='Report format')
    parser.add_argument('--output', help='Output file (default: stdout)')
    parser.add_argument('--db', default='./intelligence.db',
                        help='Path to intelligence database (default: ./intelligence.db)')
    
    args = parser.parse_args()
    
    try:
        # Check if database exists
        db_path = Path(args.db)
        if not db_path.exists():
            print(f"Error: Database not found: {args.db}")
            print("\nThe intelligence database will be created automatically when you:")
            print("1. Start the API server: python start_api.py")
            print("2. Make some queries to the API endpoints")
            print("3. Run this analytics tool again")
            exit(1)
        
        # Create analytics engine with database path
        analytics = AnalyticsEngine(args.db)
        report = analytics.generate_report(format=args.format)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"✅ Report written to {args.output}")
        else:
            print(report)
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nRun some queries first to generate analytics data.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
