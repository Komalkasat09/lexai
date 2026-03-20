"""
Intelligence Layer for Legal Research System
============================================

Provides:
- Query logging and analytics
- User feedback collection
- Performance metrics
- Usage patterns analysis
- System optimization insights

Author: Legal Research System
"""

from .query_logger import QueryLogger
from .analytics import AnalyticsEngine
from .feedback import FeedbackCollector

__all__ = ['QueryLogger', 'AnalyticsEngine', 'FeedbackCollector']
