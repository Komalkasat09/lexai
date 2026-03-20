"""
Query Logger - Intelligence Layer
=================================

Logs all queries, responses, and metadata for analytics and optimization.

Database Schema:
- queries: All user queries with metadata
- responses: LLM responses with sources
- feedback: User feedback on responses
- performance: Response time and quality metrics

Author: Legal Research System
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
import hashlib


@dataclass
class QueryLog:
    """Represents a logged query"""
    query_text: str
    query_type: str  # section_lookup, legal_question, case_search
    query_id: str = field(default_factory=lambda: f"query_{datetime.now().timestamp()}")
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ResponseLog:
    """Represents a logged response"""
    query_id: str
    answer: str
    confidence: str  # LOW, MEDIUM, HIGH
    sources_count: int
    response_time_ms: float
    response_id: str = field(default_factory=lambda: f"resp_{datetime.now().timestamp()}")
    query_type: str = "general_question"
    bare_acts_retrieved: int = 0
    case_laws_retrieved: int = 0
    amendments_retrieved: int = 0
    warnings: Optional[List[str]] = None
    trigger_uncertainty: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FeedbackLog:
    """Represents user feedback"""
    query_id: str
    response_id: str
    rating: int  # 1-5 stars
    helpful: bool
    accurate: bool
    feedback_id: str = field(default_factory=lambda: f"feedback_{datetime.now().timestamp()}")
    comment: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class QueryLogger:
    """
    Logs and manages query/response data for analytics
    
    Features:
    - SQLite persistence
    - Query deduplication
    - Performance tracking
    - Source attribution
    - User feedback
    """
    
    def __init__(self, db_path: str = "./intelligence/query_logs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Queries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                query_id TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                query_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Responses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                response_id TEXT PRIMARY KEY,
                query_id TEXT NOT NULL,
                answer TEXT NOT NULL,
                confidence TEXT NOT NULL,
                query_type TEXT NOT NULL,
                sources_count INTEGER DEFAULT 0,
                bare_acts_retrieved INTEGER DEFAULT 0,
                case_laws_retrieved INTEGER DEFAULT 0,
                amendments_retrieved INTEGER DEFAULT 0,
                response_time_ms REAL DEFAULT 0,
                warnings TEXT,
                trigger_uncertainty BOOLEAN DEFAULT 0,
                timestamp TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (query_id) REFERENCES queries(query_id)
            )
        """)
        
        # Feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                query_id TEXT NOT NULL,
                response_id TEXT NOT NULL,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                helpful BOOLEAN,
                accurate BOOLEAN,
                comment TEXT,
                timestamp TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (query_id) REFERENCES queries(query_id),
                FOREIGN KEY (response_id) REFERENCES responses(response_id)
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_date DATE NOT NULL,
                total_queries INTEGER DEFAULT 0,
                avg_response_time_ms REAL DEFAULT 0,
                high_confidence_count INTEGER DEFAULT 0,
                medium_confidence_count INTEGER DEFAULT 0,
                low_confidence_count INTEGER DEFAULT 0,
                avg_rating REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_timestamp ON queries(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_response_query_id ON responses(query_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_response_id ON feedback(response_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_type ON queries(query_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_confidence ON responses(confidence)")
        
        conn.commit()
        conn.close()
    
    def _generate_id(self, text: str) -> str:
        """Generate unique ID from text"""
        return hashlib.sha256(f"{text}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    
    def log_query(self, query_log: QueryLog) -> str:
        """
        Log a user query
        
        Args:
            query_log: QueryLog object
            
        Returns:
            query_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO queries (
                query_id, query_text, query_type, timestamp,
                user_id, session_id, ip_address, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            query_log.query_id,
            query_log.query_text,
            query_log.query_type,
            query_log.timestamp,
            query_log.user_id,
            query_log.session_id,
            query_log.ip_address,
            query_log.user_agent
        ))
        
        conn.commit()
        conn.close()
        
        return query_log.query_id
    
    def log_response(self, response_log: ResponseLog) -> str:
        """
        Log an LLM response
        
        Args:
            response_log: ResponseLog object
            
        Returns:
            response_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        warnings_json = json.dumps(response_log.warnings) if response_log.warnings else None
        
        cursor.execute("""
            INSERT INTO responses (
                response_id, query_id, answer, confidence, query_type,
                sources_count, bare_acts_retrieved, case_laws_retrieved,
                amendments_retrieved, response_time_ms, warnings,
                trigger_uncertainty, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            response_log.response_id,
            response_log.query_id,
            response_log.answer,
            response_log.confidence,
            response_log.query_type,
            response_log.sources_count,
            response_log.bare_acts_retrieved,
            response_log.case_laws_retrieved,
            response_log.amendments_retrieved,
            response_log.response_time_ms,
            warnings_json,
            response_log.trigger_uncertainty,
            response_log.timestamp
        ))
        
        conn.commit()
        conn.close()
        
        return response_log.response_id
    
    def log_feedback(self, feedback_log: FeedbackLog) -> str:
        """
        Log user feedback
        
        Args:
            feedback_log: FeedbackLog object
            
        Returns:
            feedback_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO feedback (
                feedback_id, query_id, response_id, rating,
                helpful, accurate, comment, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback_log.feedback_id,
            feedback_log.query_id,
            feedback_log.response_id,
            feedback_log.rating,
            feedback_log.helpful,
            feedback_log.accurate,
            feedback_log.comment,
            feedback_log.timestamp
        ))
        
        conn.commit()
        conn.close()
        
        return feedback_log.feedback_id
    
    def get_query_history(
        self,
        limit: int = 100,
        query_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Get query history with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM queries WHERE 1=1"
        params = []
        
        if query_type:
            query += " AND query_type = ?"
            params.append(query_type)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_performance_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get performance statistics for last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_queries,
                AVG(r.response_time_ms) as avg_response_time,
                COUNT(DISTINCT q.session_id) as unique_sessions
            FROM queries q
            LEFT JOIN responses r ON q.query_id = r.query_id
            WHERE q.timestamp >= datetime('now', '-{} days')
        """.format(days))
        
        overall = cursor.fetchone()
        
        # Confidence distribution
        cursor.execute("""
            SELECT 
                confidence,
                COUNT(*) as count
            FROM responses
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY confidence
        """.format(days))
        
        confidence_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Query type distribution
        cursor.execute("""
            SELECT 
                query_type,
                COUNT(*) as count
            FROM queries
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY query_type
        """.format(days))
        
        query_type_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Average rating
        cursor.execute("""
            SELECT AVG(rating) as avg_rating
            FROM feedback
            WHERE timestamp >= datetime('now', '-{} days')
        """.format(days))
        
        avg_rating = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_queries': overall[0] or 0,
            'avg_response_time_ms': overall[1] or 0,
            'unique_sessions': overall[2] or 0,
            'confidence_distribution': confidence_dist,
            'query_type_distribution': query_type_dist,
            'avg_rating': avg_rating,
            'period_days': days
        }
    
    def get_common_queries(self, limit: int = 10) -> List[Dict]:
        """Get most common query patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                query_text,
                COUNT(*) as frequency,
                AVG(r.response_time_ms) as avg_response_time,
                MAX(q.timestamp) as last_asked
            FROM queries q
            LEFT JOIN responses r ON q.query_id = r.query_id
            GROUP BY LOWER(query_text)
            HAVING frequency > 1
            ORDER BY frequency DESC
            LIMIT ?
        """, (limit,))
        
        columns = ['query_text', 'frequency', 'avg_response_time', 'last_asked']
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_low_confidence_queries(self, limit: int = 20) -> List[Dict]:
        """Get queries that resulted in low confidence responses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                q.query_text,
                q.query_type,
                r.confidence,
                r.sources_count,
                q.timestamp
            FROM queries q
            JOIN responses r ON q.query_id = r.query_id
            WHERE r.confidence = 'LOW' OR r.trigger_uncertainty = 1
            ORDER BY q.created_at DESC
            LIMIT ?
        """, (limit,))
        
        columns = ['query_text', 'query_type', 'confidence', 'sources_count', 'timestamp']
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results


# Example usage and testing
if __name__ == "__main__":
    logger = QueryLogger()
    
    # Test query logging
    query_log = QueryLog(
        query_id=logger._generate_id("test_query"),
        query_text="What is Section 420 IPC?",
        query_type="section_lookup",
        timestamp=datetime.now().isoformat(),
        session_id="test_session_123"
    )
    
    logger.log_query(query_log)
    
    # Test response logging
    response_log = ResponseLog(
        response_id=logger._generate_id("test_response"),
        query_id=query_log.query_id,
        answer="Section 420 IPC deals with cheating...",
        confidence="MEDIUM",
        query_type="section_lookup",
        sources_count=3,
        bare_acts_retrieved=1,
        case_laws_retrieved=2,
        amendments_retrieved=0,
        response_time_ms=2500.0,
        timestamp=datetime.now().isoformat(),
        warnings=["BNS transition warning"]
    )
    
    logger.log_response(response_log)
    
    # Get stats
    stats = logger.get_performance_stats(days=7)
    print("\nPerformance Stats:")
    print(json.dumps(stats, indent=2))
    
    history = logger.get_query_history(limit=10)
    print(f"\nQuery History: {len(history)} queries")
