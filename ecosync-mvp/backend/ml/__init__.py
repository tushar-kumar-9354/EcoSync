"""
EcoSync ML Module

AI/ML modules for urban sustainability:
- Energy Optimization Engine (LSTM + Transformer)
- Waste Management AI (YOLOv8 + Route Optimization)
- Green Space & Climate (Satellite Imagery + U-Net)
- NLP Module (BERT Intent Classification)
- ML Training Pipeline (MLOps infrastructure)
"""

from .energy import EnergyForecastingModel, EnergyInference, EnergyTrainer, FeatureEngineering
from .waste import WasteClassifier, RouteOptimizer, OverflowPredictor
from .greenspace import SatelliteProcessor, LandCoverModel, HeatIslandAnalyzer, RecommendationEngine
from .nlp import IntentClassifier, SentimentAnalyzer, CitizenReportNLP
from .training import DriftDetector, ModelMonitor, ExperimentTracker

__all__ = [
    # Energy
    'EnergyForecastingModel',
    'EnergyInference',
    'EnergyTrainer',
    'FeatureEngineering',
    # Waste
    'WasteClassifier',
    'RouteOptimizer',
    'OverflowPredictor',
    # Green Space
    'SatelliteProcessor',
    'LandCoverModel',
    'HeatIslandAnalyzer',
    'RecommendationEngine',
    # NLP
    'IntentClassifier',
    'SentimentAnalyzer',
    'CitizenReportNLP',
    # Training
    'DriftDetector',
    'ModelMonitor',
    'ExperimentTracker',
]
