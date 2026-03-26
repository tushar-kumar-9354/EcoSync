"""
Sentiment Analyzer for Citizen Reports

Tracks neighborhood satisfaction trends and identifies emerging concerns.
"""

import torch
import torch.nn as nn
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta
import json


class SentimentAnalyzer:
    """
    Sentiment analysis for citizen engagement.

    Features:
    - Text-level sentiment scoring
    - Neighborhood-level aggregation
    - Trend detection
    - Alert generation for negative sentiment spikes
    """

    def __init__(self, device: str = 'cpu'):
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = torch.device(device)

        # Lexicon-based sentiment (VADER-like)
        self.positive_words = {
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'love', 'best', 'helpful', 'thank', 'thanks', 'appreciate',
            'beautiful', 'nice', 'pleasant', 'happy', 'satisfied', 'improved',
            'clean', 'friendly', 'professional', 'responsive', 'quick'
        }

        self.negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'angry',
            'frustrated', 'disappointed', 'annoyed', 'unhappy', 'upset',
            'dangerous', 'unsafe', 'problem', 'issue', 'broken', 'failed',
            'ignored', 'delayed', 'rude', 'slow', 'dirty', 'smells', 'stink',
            'health', 'sick', 'asthma', 'breathing', 'emergency', 'urgent'
        }

        self.intensifiers = {'very', 'really', 'extremely', 'absolutely', 'completely'}
        self.negators = {'not', 'no', 'never', 'dont', "don't", 'doesnt', "doesn't", 'wont', "won't"}

    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of a single text.

        Returns:
            Dict with score (-1 to 1), label, and confidence
        """
        words = text.lower().split()
        if not words:
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.5,
                'word_count': 0
            }

        pos_count = 0
        neg_count = 0
        word_count = len(words)

        negate = False
        intensifier = 1.0

        for i, word in enumerate(words):
            # Check for negators
            if word in self.negators:
                negate = True
                continue

            # Check for intensifiers
            if word in self.intensifiers:
                intensifier = 1.5
                continue

            # Check sentiment words
            if word in self.positive_words:
                if negate:
                    neg_count += 1 * intensifier
                else:
                    pos_count += 1 * intensifier
                negate = False
                intensifier = 1.0

            elif word in self.negative_words:
                if negate:
                    pos_count += 0.5 * intensifier
                else:
                    neg_count += 1 * intensifier
                negate = False
                intensifier = 1.0

        # Calculate sentiment score
        total = pos_count + neg_count
        if total == 0:
            score = 0.0
        else:
            score = (pos_count - neg_count) / (pos_count + neg_count)

        # Determine label
        if score > 0.3:
            label = 'positive'
        elif score < -0.3:
            label = 'negative'
        else:
            label = 'neutral'

        # Confidence based on word count and sentiment word matches
        sentiment_words = pos_count + neg_count
        if word_count < 5:
            confidence = 0.5
        elif sentiment_words == 0:
            confidence = 0.3
        else:
            confidence = min(0.95, 0.5 + (sentiment_words / word_count) * 0.5)

        return {
            'score': round(score, 3),
            'label': label,
            'confidence': round(confidence, 3),
            'word_count': word_count,
            'positive_signals': pos_count,
            'negative_signals': neg_count
        }

    def aggregate_by_neighborhood(self, reports: List[Dict]) -> Dict:
        """
        Aggregate sentiment by neighborhood.

        Args:
            reports: List of reports with 'text', 'location' (neighborhood name)

        Returns:
            Sentiment statistics per neighborhood
        """
        neighborhood_stats = {}

        for report in reports:
            neighborhood = report.get('neighborhood', 'unknown')
            text = report.get('text', '')

            if not text:
                continue

            sentiment = self.analyze_sentiment(text)

            if neighborhood not in neighborhood_stats:
                neighborhood_stats[neighborhood] = {
                    'scores': [],
                    'total_reports': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0
                }

            neighborhood_stats[neighborhood]['scores'].append(sentiment['score'])
            neighborhood_stats[neighborhood]['total_reports'] += 1

            if sentiment['label'] == 'positive':
                neighborhood_stats[neighborhood]['positive_count'] += 1
            elif sentiment['label'] == 'negative':
                neighborhood_stats[neighborhood]['negative_count'] += 1
            else:
                neighborhood_stats[neighborhood]['neutral_count'] += 1

        # Calculate aggregates
        result = {}
        for neighborhood, stats in neighborhood_stats.items():
            scores = stats['scores']
            result[neighborhood] = {
                'total_reports': stats['total_reports'],
                'avg_sentiment': round(np.mean(scores), 3) if scores else 0,
                'median_sentiment': round(np.median(scores), 3) if scores else 0,
                'sentiment_std': round(np.std(scores), 3) if scores else 0,
                'positive_percent': round(stats['positive_count'] / stats['total_reports'] * 100, 1),
                'negative_percent': round(stats['negative_count'] / stats['total_reports'] * 100, 1),
                'trend': self._calculate_trend(scores)
            }

        return result

    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate sentiment trend from recent scores."""
        if len(scores) < 5:
            return 'insufficient_data'

        # Compare recent 50% to older 50%
        mid = len(scores) // 2
        recent = scores[mid:]
        older = scores[:mid]

        recent_avg = np.mean(recent)
        older_avg = np.mean(older)

        diff = recent_avg - older_avg

        if diff > 0.1:
            return 'improving'
        elif diff < -0.1:
            return 'worsening'
        return 'stable'

    def detect_sentiment_spikes(self, reports: List[Dict], threshold: float = -0.3) -> List[Dict]:
        """
        Detect neighborhoods with sudden negative sentiment spikes.

        Args:
            reports: List of reports with timestamps
            threshold: Sentiment score below which to flag

        Returns:
            List of alert dicts
        """
        alerts = []

        # Group by neighborhood and time period
        neighborhood_recent = {}

        for report in reports:
            neighborhood = report.get('neighborhood', 'unknown')
            text = report.get('text', '')
            timestamp_str = report.get('created_at', '')

            if not text or not timestamp_str:
                continue

            sentiment = self.analyze_sentiment(text)

            if neighborhood not in neighborhood_recent:
                neighborhood_recent[neighborhood] = []

            neighborhood_recent[neighborhood].append({
                'sentiment': sentiment,
                'timestamp': timestamp_str
            })

        # Check each neighborhood for spikes
        for neighborhood, data in neighborhood_recent.items():
            if len(data) < 3:
                continue

            # Get recent reports (last 7 days or last 10 reports)
            recent = data[-10:]
            recent_avg = np.mean([d['sentiment']['score'] for d in recent])
            recent_negative_pct = sum(
                1 for d in recent if d['sentiment']['label'] == 'negative'
            ) / len(recent) * 100

            if recent_avg < threshold:
                alerts.append({
                    'type': 'sentiment_spike',
                    'severity': 'high' if recent_avg < -0.5 else 'medium',
                    'neighborhood': neighborhood,
                    'avg_sentiment': round(recent_avg, 3),
                    'negative_percent': round(recent_negative_pct, 1),
                    'report_count': len(recent),
                    'message': f"Negative sentiment spike detected in {neighborhood}: {recent_negative_pct:.0f}% negative reports",
                    'recommended_action': 'Review recent reports and assess if city response is needed'
                })

        return alerts

    def generate_sentiment_report(
        self,
        reports: List[Dict],
        time_period_days: int = 30
    ) -> Dict:
        """
        Generate comprehensive sentiment report.

        Args:
            reports: List of reports
            time_period_days: Time period to analyze

        Returns:
            Full sentiment report
        """
        # Filter by time period if timestamps available
        cutoff = datetime.now() - timedelta(days=time_period_days)
        filtered_reports = []

        for report in reports:
            created_at_str = report.get('created_at', '')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at < cutoff:
                        continue
                except:
                    pass
            filtered_reports.append(report)

        # Overall sentiment
        all_scores = []
        category_sentiment = {}

        for report in filtered_reports:
            text = report.get('text', '')
            category = report.get('category', 'unknown')

            if not text:
                continue

            sentiment = self.analyze_sentiment(text)
            all_scores.append(sentiment['score'])

            if category not in category_sentiment:
                category_sentiment[category] = []
            category_sentiment[category].append(sentiment['score'])

        # Neighborhood aggregation
        neighborhood_stats = self.aggregate_by_neighborhood(filtered_reports)

        # Detect spikes
        alerts = self.detect_sentiment_spikes(filtered_reports)

        return {
            'overall': {
                'total_reports': len(filtered_reports),
                'avg_sentiment': round(np.mean(all_scores), 3) if all_scores else 0,
                'median_sentiment': round(np.median(all_scores), 3) if all_scores else 0,
                'sentiment_distribution': {
                    'positive': sum(1 for s in all_scores if s > 0.3),
                    'neutral': sum(1 for s in all_scores if -0.3 <= s <= 0.3),
                    'negative': sum(1 for s in all_scores if s < -0.3)
                }
            },
            'by_category': {
                cat: {
                    'avg_sentiment': round(np.mean(scores), 3),
                    'report_count': len(scores)
                }
                for cat, scores in category_sentiment.items()
            },
            'by_neighborhood': neighborhood_stats,
            'alerts': alerts,
            'period_days': time_period_days,
            'generated_at': datetime.now().isoformat()
        }

    def format_trend_response(self, reports_by_zone: Dict[str, List[Dict]]) -> Dict:
        """Format neighborhood sentiment trends for dashboard."""
        trends = {}

        for zone, reports in reports_by_zone.items():
            if not reports:
                continue

            scores = [self.analyze_sentiment(r.get('text', ''))['score'] for r in reports]
            avg = np.mean(scores) if scores else 0

            # Get status
            if avg > 0.3:
                status = 'positive'
            elif avg > -0.3:
                status = 'neutral'
            else:
                status = 'concern'

            trends[zone] = {
                'avg_sentiment': round(avg, 2),
                'status': status,
                'report_count': len(reports),
                'trend_direction': self._calculate_trend(scores) if len(scores) >= 5 else 'stable'
            }

        return trends
