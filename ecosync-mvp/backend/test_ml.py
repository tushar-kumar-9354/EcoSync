"""
EcoSync ML Module Tests

Run this script to verify all ML modules are working correctly.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("EcoSync ML Module Test Suite")
print("=" * 60)

# Test 1: Energy Module
print("\n[1] Testing Energy Module...")
try:
    from ml.energy import EnergyForecastingModel, EnergyInference, FeatureEngineering

    # Test FeatureEngineering
    fe = FeatureEngineering()
    print("  - FeatureEngineering: OK")

    # Test model creation
    model = EnergyForecastingModel(
        input_dim=50,
        lstm_hidden=64,
        d_model=128,
        num_heads=4,
        num_transformer_layers=2,
        forecast_horizons=[1, 6, 12, 24]
    )
    print("  - EnergyForecastingModel: OK")

    # Test forward pass
    import torch
    x = torch.randn(2, 168, 50)  # [batch, seq, features]
    hour = torch.randint(0, 24, (2,))
    day = torch.randint(0, 7, (2,))
    month = torch.randint(1, 13, (2,))

    with torch.no_grad():
        output = model(x, hour, day, month)

    print(f"  - Forward pass: OK (forecasts shape: {output['forecasts'].shape})")
    print(f"    Peak prob: {output['peak_probability'].shape}")

except Exception as e:
    print(f"  - ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Waste Module
print("\n[2] Testing Waste Module...")
try:
    from ml.waste import WasteClassifier, RouteOptimizer, OverflowPredictor, CollectionPoint, Vehicle

    # Test RouteOptimizer
    optimizer = RouteOptimizer(
        depot_lat=37.7749,
        depot_lng=-122.4194,
        vehicle_capacity_kg=5000,
        max_route_duration_hours=8
    )
    print("  - RouteOptimizer: OK")

    # Test with sample data
    points = [
        CollectionPoint(
            id=f"bin-{i}",
            lat=37.77 + i*0.001,
            lng=-122.41 + i*0.001,
            fill_percent=50 + i*5,
            bin_type="residential",
            zone="downtown",
            priority=3
        )
        for i in range(5)
    ]

    vehicle = Vehicle(
        id="truck-1",
        capacity_kg=5000,
        current_load_kg=500,
        current_lat=37.7749,
        current_lng=-122.4194
    )

    route = optimizer.optimize_route(points, vehicle, use_gnn=False)
    print(f"  - Route optimization: OK ({route['points_visited']} points visited)")

    # Test OverflowPredictor
    predictor = OverflowPredictor()
    print("  - OverflowPredictor: OK")

except Exception as e:
    print(f"  - ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Green Space Module
print("\n[3] Testing Green Space Module...")
try:
    from ml.greenspace import SatelliteProcessor, LandCoverModel, HeatIslandAnalyzer, RecommendationEngine

    # Test LandCoverModel
    lcm = LandCoverModel()
    print("  - LandCoverModel: OK")

    # Test with random data
    import torch
    x = torch.randn(1, 4, 64, 64)  # [batch, channels, H, W]
    logits, preds = lcm(x)
    print(f"  - LandCover forward pass: OK (predictions shape: {preds.shape})")

    # Test HeatIslandAnalyzer
    analyzer = HeatIslandAnalyzer()
    print("  - HeatIslandAnalyzer: OK")

    # Test RecommendationEngine
    rec_engine = RecommendationEngine()
    site = rec_engine.analyze_intervention_site(
        lat=37.7749,
        lng=-122.4194,
        current_land_cover=2,  # Impervious
        canopy_percent=15.0,
        lst_celsius=38.0,
        impervious_percent=85.0,
        population_density=5000,
        median_income=45000
    )
    print(f"  - RecommendationEngine: OK (priority score: {site['priority_score']})")

except Exception as e:
    print(f"  - ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 4: NLP Module
print("\n[4] Testing NLP Module...")
try:
    from ml.nlp import IntentClassifier, SentimentAnalyzer, CitizenReportNLP

    # Test IntentClassifier (rule-based fallback since no BERT model)
    classifier = IntentClassifier(use_bert=False)
    print("  - IntentClassifier: OK")

    # Test classification
    result = classifier.classify_intent("There is illegal dumping behind the grocery store on Market Street")
    print(f"  - Intent classification: {result['intent']} (confidence: {result['confidence']})")

    # Test SentimentAnalyzer
    sentiment = SentimentAnalyzer()
    result = sentiment.analyze_sentiment("The air quality is terrible and smells like chemicals")
    print(f"  - Sentiment analysis: {result['label']} (score: {result['score']})")

    # Test CitizenReportNLP
    nlp = CitizenReportNLP()
    report = nlp.process_report(
        text="Someone is dumping trash near the park entrance. It's creating a bad smell.",
        location={"lat": 37.77, "lng": -122.41}
    )
    print(f"  - CitizenReportNLP: OK (category: {report['category']}, priority: {report['priority']})")

except Exception as e:
    print(f"  - ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Training Module
print("\n[5] Testing Training Module...")
try:
    from ml.training import DriftDetector, ModelMonitor, ExperimentTracker

    # Test ExperimentTracker
    tracker = ExperimentTracker(storage_path="./test_experiments")
    exp_id = tracker.create_experiment("test-energy-forecast", "Test experiment")
    run_id = tracker.log_run(exp_id, {"lr": 0.001, "epochs": 10}, {"train_loss": 0.5, "val_loss": 0.3})
    tracker.complete_run(run_id, exp_id, {"final_val_loss": 0.25})
    print("  - ExperimentTracker: OK")

    # Test DriftDetector
    import numpy as np
    detector = DriftDetector(threshold=0.2)
    baseline = np.random.normal(50, 10, 1000)
    detector.set_baseline(baseline, "test_feature")

    current = np.random.normal(52, 12, 500)
    drift_result = detector.detect_drift(current, "test_feature")
    print(f"  - DriftDetector: OK (PSI: {drift_result.get('psi', 'N/A')})")

    # Test ModelMonitor
    monitor = ModelMonitor()
    monitor.log_prediction("energy-model-v1", prediction=4500, features={"temp": 25, "hour": 14}, actual=4450)
    print("  - ModelMonitor: OK")

except Exception as e:
    print(f"  - ERROR: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 60)
print("Test Suite Complete!")
print("=" * 60)

# Cleanup
import shutil
if os.path.exists("./test_experiments"):
    shutil.rmtree("./test_experiments")
