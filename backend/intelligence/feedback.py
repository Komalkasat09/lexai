"""
Feedback Collector - Intelligence Layer
=======================================

Collects and processes user feedback for continuous improvement.

Features:
- User ratings (1-5 stars)
- Helpfulness tracking
- Accuracy verification
- Comment collection
- Feedback aggregation

Author: Legal Research System
"""

from datetime import datetime
from typing import Dict, List, Optional
import json


class FeedbackCollector:
    """
    Collects and analyzes user feedback
    
    Used to:
    - Track response quality
    - Identify problematic answers
    - Improve system over time
    - Validate LLM outputs
    """
    
    def __init__(self, query_logger):
        """
        Initialize feedback collector
        
        Args:
            query_logger: QueryLogger instance for persistence
        """
        self.logger = query_logger
    
    def submit_feedback(
        self,
        query_id: str,
        response_id: str,
        rating: int,
        helpful: bool,
        accurate: bool,
        comment: Optional[str] = None
    ) -> bool:
        """
        Submit user feedback for a response
        
        Args:
            query_id: ID of the query
            response_id: ID of the response
            rating: 1-5 star rating
            helpful: Was the response helpful?
            accurate: Was the response accurate?
            comment: Optional user comment
            
        Returns:
            Success status
        """
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")
        
        from .query_logger import FeedbackLog
        
        feedback = FeedbackLog(
            feedback_id=self.logger._generate_id(f"{response_id}_feedback"),
            query_id=query_id,
            response_id=response_id,
            rating=rating,
            helpful=helpful,
            accurate=accurate,
            comment=comment,
            timestamp=datetime.now().isoformat()
        )
        
        try:
            self.logger.log_feedback(feedback)
            return True
        except Exception as e:
            print(f"Error logging feedback: {e}")
            return False
    
    def get_response_feedback(self, response_id: str) -> List[Dict]:
        """Get all feedback for a specific response"""
        import sqlite3
        
        conn = sqlite3.connect(self.logger.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                feedback_id, rating, helpful, accurate, comment, timestamp
            FROM feedback
            WHERE response_id = ?
            ORDER BY created_at DESC
        """, (response_id,))
        
        columns = ['feedback_id', 'rating', 'helpful', 'accurate', 'comment', 'timestamp']
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_problematic_responses(self, threshold: int = 2) -> List[Dict]:
        """
        Get responses with low ratings
        
        Args:
            threshold: Rating threshold (responses <= threshold are problematic)
            
        Returns:
            List of problematic responses with context
        """
        import sqlite3
        
        conn = sqlite3.connect(self.logger.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                f.response_id,
                f.query_id,
                q.query_text,
                r.answer,
                r.confidence,
                f.rating,
                f.comment,
                f.timestamp
            FROM feedback f
            JOIN responses r ON f.response_id = r.response_id
            JOIN queries q ON f.query_id = q.query_id
            WHERE f.rating <= ?
            ORDER BY f.created_at DESC
        """, (threshold,))
        
        columns = ['response_id', 'query_id', 'query_text', 'answer', 
                   'confidence', 'rating', 'comment', 'timestamp']
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_feedback_summary(self, days: int = 30) -> Dict:
        """Get aggregated feedback summary"""
        import sqlite3
        
        conn = sqlite3.connect(self.logger.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_feedback,
                AVG(rating) as avg_rating,
                SUM(CASE WHEN helpful = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as helpful_percentage,
                SUM(CASE WHEN accurate = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as accurate_percentage
            FROM feedback
            WHERE timestamp >= datetime('now', '-{} days')
        """.format(days))
        
        result = cursor.fetchone()
        
        # Rating distribution
        cursor.execute("""
            SELECT 
                rating,
                COUNT(*) as count
            FROM feedback
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY rating
            ORDER BY rating
        """.format(days))
        
        rating_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'period_days': days,
            'total_feedback': result[0] or 0,
            'avg_rating': round(result[1] or 0, 2),
            'helpful_percentage': round(result[2] or 0, 2),
            'accurate_percentage': round(result[3] or 0, 2),
            'rating_distribution': rating_dist
        }


# Example standalone usage
if __name__ == "__main__":
    from .query_logger import QueryLogger
    
    logger = QueryLogger()
    collector = FeedbackCollector(logger)
    
    # Get feedback summary
    summary = collector.get_feedback_summary(days=30)
    print("\nFeedback Summary (Last 30 Days):")
    print(json.dumps(summary, indent=2))
    
    # Get problematic responses
    problematic = collector.get_problematic_responses(threshold=2)
    if problematic:
        print(f"\n{len(problematic)} Problematic Responses Found:")
        for resp in problematic[:5]:
            print(f"\nQuery: {resp['query_text']}")
            print(f"Rating: {resp['rating']}/5")
            if resp['comment']:
                print(f"Comment: {resp['comment']}")
    else:
        print("\nNo problematic responses found.")
