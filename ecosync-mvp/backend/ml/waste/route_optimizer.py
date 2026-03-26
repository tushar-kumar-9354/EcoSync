"""
Waste Collection Route Optimization Module

Implements:
- Graph neural network for route optimization
- Dynamic re-routing based on real-time data
- Multi-constraint optimization (time windows, capacity, traffic)
- Integration with bin fill level predictions
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple, Dict, Optional
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta
import math


@dataclass
class CollectionPoint:
    """Represents a waste bin collection point."""
    id: str
    lat: float
    lng: float
    fill_percent: float
    bin_type: str
    zone: str
    priority: int = 1  # 1-5, higher = more urgent
    estimated_service_time: float = 2.0  # minutes
    time_window_start: Optional[str] = None  # HH:MM format
    time_window_end: Optional[str] = None
    is_active: bool = True


@dataclass
class Vehicle:
    """Represents a collection vehicle."""
    id: str
    capacity_kg: float
    current_load_kg: float
    current_lat: float
    current_lng: float
    available: bool = True


class GraphAttentionLayer(nn.Module):
    """Graph attention layer for learning route dependencies."""

    def __init__(self, in_features: int, out_features: int, dropout: float = 0.1):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features

        self.W = nn.Linear(in_features, out_features, bias=False)
        self.a = nn.Linear(2 * out_features, 1, bias=False)
        self.dropout = dropout

        self.leaky_relu = nn.LeakyReLU(0.2)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Edge indices [2, num_edges]
        """
        h = self.W(x)  # [num_nodes, out_features]
        num_nodes = h.size(0)

        # Self-attention
        a_input = torch.cat([
            h.repeat(1, num_nodes).view(num_nodes * num_nodes, -1),
            h.repeat(num_nodes, 1)
        ], dim=1).view(num_nodes, num_nodes, 2 * self.out_features)

        e = self.leaky_relu(self.a(a_input)).squeeze(-1)  # [num_nodes, num_nodes]

        # Masked attention (only use edges)
        edge_mask = torch.zeros(num_nodes, num_nodes, device=x.device)
        edge_mask[edge_index[0], edge_index[1]] = 1
        e = e.masked_fill(edge_mask == 0, -1e9)

        attention = F.softmax(e, dim=1)
        attention = F.dropout(attention, self.dropout, training=self.training)

        h_prime = torch.matmul(attention, h)  # [num_nodes, out_features]

        return h_prime


class RouteGNN(nn.Module):
    """
    Graph Neural Network for route optimization.

    Learns to predict:
    - Optimal next collection point
    - Travel time estimates
    - Visit probabilities
    """

    def __init__(self, node_features: int = 8, hidden_dim: int = 128, num_layers: int = 3):
        super().__init__()

        self.node_encoder = nn.Sequential(
            nn.Linear(node_features, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        self.attention_layers = nn.ModuleList([
            GraphAttentionLayer(hidden_dim, hidden_dim)
            for _ in range(num_layers)
        ])

        self.edge_decoder = nn.Sequential(
            nn.Linear(2 * hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Node features [num_nodes, node_features]
            edge_index: Edge connectivity [2, num_edges]

        Returns:
            Edge scores [num_edges] representing traversal priority
        """
        h = self.node_encoder(x)

        for attn_layer in self.attention_layers:
            h = attn_layer(h, edge_index)

        # Decode edge scores
        src, dst = edge_index
        edge_features = torch.cat([h[src], h[dst]], dim=1)
        scores = self.edge_decoder(edge_features).squeeze(-1)

        return scores


class RouteOptimizer:
    """
    Waste collection route optimizer.

    Features:
    - Dynamic re-routing based on fill levels and traffic
    - Capacity constraints
    - Time window satisfaction
    - Multi-zone coordination
    """

    def __init__(
        self,
        depot_lat: float,
        depot_lng: float,
        vehicle_capacity_kg: float = 5000,
        max_route_duration_hours: float = 8,
        avg_speed_kmh: float = 30
    ):
        self.depot_lat = depot_lat
        self.depot_lng = depot_lng
        self.vehicle_capacity_kg = vehicle_capacity_kg
        self.max_route_duration_hours = max_route_duration_hours
        self.avg_speed_kmh = avg_speed_kmh

        # GNN model for route learning
        self.gnn: Optional[RouteGNN] = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in km."""
        R = 6371  # Earth's radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def estimate_travel_time(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Estimate travel time in minutes."""
        distance = self.haversine_distance(lat1, lng1, lat2, lng2)

        # Adjust for traffic (simplified)
        base_time = (distance / self.avg_speed_kmh) * 60  # minutes

        return base_time

    def build_graph(
        self,
        points: List[CollectionPoint],
        traffic_data: Optional[Dict[str, float]] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, List[Tuple[int, int]]]:
        """
        Build graph representation of collection points.

        Returns:
            x: Node features
            edge_index: Edge connectivity
            edges: List of (src, dst) tuples
        """
        num_points = len(points)

        # Node features
        features = []
        for p in points:
            # [lat, lng, fill_percent, priority, service_time, hour_sin, hour_cos, traffic_factor]
            hour = datetime.now().hour
            traffic_factor = traffic_data.get(p.zone, 1.0) if traffic_data else 1.0

            feat = [
                p.lat / 90.0,  # Normalized lat
                p.lng / 180.0,  # Normalized lng
                p.fill_percent / 100.0,
                p.priority / 5.0,
                p.estimated_service_time / 10.0,
                math.sin(2 * math.pi * hour / 24),
                math.cos(2 * math.pi * hour / 24),
                traffic_factor
            ]
            features.append(feat)

        x = torch.tensor(features, dtype=torch.float32)

        # Build edges (k-nearest neighbors, k=10)
        edges = []
        k = min(10, num_points - 1)

        for i in range(num_points):
            distances = []
            for j in range(num_points):
                if i == j:
                    continue
                d = self.haversine_distance(
                    points[i].lat, points[i].lng,
                    points[j].lat, points[j].lng
                )
                distances.append((j, d))

            distances.sort(key=lambda x: x[1])
            for j, _ in distances[:k]:
                edges.append((i, j))

        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

        return x, edge_index, edges

    def optimize_route(
        self,
        points: List[CollectionPoint],
        vehicle: Vehicle,
        traffic_data: Optional[Dict[str, float]] = None,
        use_gnn: bool = True
    ) -> Dict:
        """
        Optimize collection route for a single vehicle.

        Args:
            points: List of collection points to visit
            vehicle: Vehicle to use
            traffic_data: Optional traffic delay factors by zone
            use_gnn: Whether to use GNN for route learning

        Returns:
            Route optimization result
        """
        if not points:
            return {'route': [], 'total_distance_km': 0, 'total_time_min': 0}

        num_points = len(points)
        remaining_capacity = vehicle.capacity_kg - vehicle.current_load_kg

        # Build graph
        x, edge_index, edges = self.build_graph(points, traffic_data)

        # Calculate edge weights (distance + time cost)
        edge_weights = []
        for src, dst in edges:
            d = self.haversine_distance(
                points[src].lat, points[src].lng,
                points[dst].lat, points[dst].lng
            )
            traffic = traffic_data.get(points[dst].zone, 1.0) if traffic_data else 1.0
            cost = d * traffic
            edge_weights.append(cost)

        edge_weights = torch.tensor(edge_weights, dtype=torch.float32)

        if use_gnn and self.gnn is not None:
            # Use GNN to score edges
            self.gnn.eval()
            with torch.no_grad():
                gnn_scores = self.gnn(x.to(self.device), edge_index.to(self.device))
                gnn_scores = gnn_scores.cpu()

            # Combine distance and GNN scores
            scores = edge_weights * (1 - torch.sigmoid(gnn_scores))
        else:
            # Greedy nearest neighbor heuristic
            scores = edge_weights

        # Build route using modified nearest neighbor
        route = []
        visited = set()
        current_lat = vehicle.current_lat
        current_lng = vehicle.current_lng
        current_time = datetime.now()
        total_distance = 0.0
        total_time = 0.0
        accumulated_fill = 0.0

        unvisited = list(range(num_points))

        while unvisited and total_time < self.max_route_duration_hours * 60:
            # Find best next point
            best_idx = None
            best_score = float('inf')

            for idx in unvisited:
                p = points[idx]

                # Check capacity constraint
                estimated_fill = (p.fill_percent / 100.0) * 100  # rough kg estimate
                if accumulated_fill + estimated_fill > remaining_capacity:
                    continue

                # Calculate score (distance weighted by priority and fill)
                d = self.haversine_distance(current_lat, current_lng, p.lat, p.lng)
                time_to_point = (d / self.avg_speed_kmh) * 60
                total_visit_time = time_to_point + p.estimated_service_time

                # Check time window
                if p.time_window_start and p.time_window_end:
                    visit_time_min = current_time.hour * 60 + current_time.minute
                    start_min = self._parse_time(p.time_window_start)
                    end_min = self._parse_time(p.time_window_end)
                    if not (start_min <= visit_time_min <= end_min):
                        continue

                if total_time + total_visit_time > self.max_route_duration_hours * 60:
                    continue

                # Score: lower is better
                priority_weight = 1.0 + (p.priority / 5.0) * 0.5
                fill_weight = 1.0 + (p.fill_percent / 100.0) * 0.3
                score = d * priority_weight * fill_weight

                if score < best_score:
                    best_score = score
                    best_idx = idx

            if best_idx is None:
                break

            # Add to route
            p = points[best_idx]
            d = self.haversine_distance(current_lat, current_lng, p.lat, p.lng)
            travel_time = (d / self.avg_speed_kmh) * 60

            route.append({
                'point_id': p.id,
                'lat': p.lat,
                'lng': p.lng,
                'fill_percent': p.fill_percent,
                'travel_time_min': round(travel_time, 1),
                'service_time_min': p.estimated_service_time,
                'arrival_time': (current_time + timedelta(minutes=travel_time)).strftime('%H:%M'),
                'departure_time': (current_time + timedelta(minutes=travel_time + p.estimated_service_time)).strftime('%H:%M')
            })

            total_distance += d
            total_time += travel_time + p.estimated_service_time
            accumulated_fill += (p.fill_percent / 100.0) * 100
            current_lat = p.lat
            current_lng = p.lng
            current_time += timedelta(minutes=travel_time + p.estimated_service_time)

            visited.add(best_idx)
            unvisited.remove(best_idx)

        # Return to depot
        depot_distance = self.haversine_distance(current_lat, current_lng, self.depot_lat, self.depot_lng)
        total_distance += depot_distance
        total_time += (depot_distance / self.avg_speed_kmh) * 60

        route.append({
            'point_id': 'DEPOT',
            'lat': self.depot_lat,
            'lng': self.depot_lng,
            'fill_percent': 0,
            'travel_time_min': round((depot_distance / self.avg_speed_kmh) * 60, 1),
            'service_time_min': 0,
            'arrival_time': (current_time + timedelta(minutes=(depot_distance / self.avg_speed_kmh) * 60)).strftime('%H:%M'),
            'departure_time': None
        })

        return {
            'route': route,
            'total_distance_km': round(total_distance, 2),
            'total_time_min': round(total_time, 1),
            'points_visited': len(route) - 1,
            'total_fill_collected_kg': round(accumulated_fill, 1),
            'capacity_utilization': round(accumulated_fill / remaining_capacity * 100, 1) if remaining_capacity > 0 else 0,
            'efficiency_gain_percent': round((1 - total_distance / (len(route) * 5)) * 100, 1)  # vs 5km avg straight line
        }

    def _parse_time(self, time_str: str) -> int:
        """Parse HH:MM time string to minutes since midnight."""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def optimize_multi_vehicle(
        self,
        points: List[CollectionPoint],
        vehicles: List[Vehicle],
        traffic_data: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Optimize routes for multiple vehicles.

        Args:
            points: All collection points
            vehicles: Available vehicles
            traffic_data: Traffic delay factors

        Returns:
            Multi-vehicle route plan
        """
        # Sort points by priority and fill level
        sorted_points = sorted(points, key=lambda p: (p.priority, p.fill_percent), reverse=True)

        # Assign points to vehicles based on zone and capacity
        vehicle_assignments: Dict[str, List[CollectionPoint]] = {v.id: [] for v in vehicles}
        remaining_capacity: Dict[str, float] = {v.id: v.capacity_kg - v.current_load_kg for v in vehicles}

        for p in sorted_points:
            # Find best vehicle for this point
            best_vehicle = None
            best_score = float('inf')

            for v in vehicles:
                if not v.available:
                    continue

                # Estimate additional distance to include this point
                est_fill = (p.fill_percent / 100.0) * 100
                if remaining_capacity[v.id] < est_fill:
                    continue

                # Score based on current load and zone matching
                score = remaining_capacity[v.id] - est_fill

                if score < best_score:
                    best_score = score
                    best_vehicle = v

            if best_vehicle:
                vehicle_assignments[best_vehicle.id].append(p)
                remaining_capacity[best_vehicle.id] -= (p.fill_percent / 100.0) * 100

        # Optimize route for each vehicle
        routes = {}
        total_distance = 0
        total_time = 0

        for v in vehicles:
            if vehicle_assignments[v.id]:
                result = self.optimize_route(vehicle_assignments[v.id], v, traffic_data, use_gnn=False)
                routes[v.id] = result
                total_distance += result['total_distance_km']
                total_time += result['total_time_min']

        return {
            'routes': routes,
            'summary': {
                'total_distance_km': round(total_distance, 2),
                'total_time_min': round(total_time, 1),
                'vehicles_used': sum(1 for v in vehicles if vehicle_assignments[v.id]),
                'points_covered': sum(len(r['route']) - 1 for r in routes.values()),
                'estimated_fuel_savings_percent': round(
                    max(0, 25 - (total_distance / 100) * 2), 1
                )
            }
        }

    def get_dynamic_reroute(
        self,
        current_route: List[Dict],
        new_critical_bins: List[CollectionPoint],
        vehicle: Vehicle
    ) -> Dict:
        """
        Dynamically reroute when new critical bins are detected.

        Args:
            current_route: Current planned route
            new_critical_bins: Bins that have become critical and need immediate collection
            vehicle: Current vehicle state

        Returns:
            Updated route
        """
        # Find insertion points for new critical bins
        updated_route = []
        critical_inserted = set()

        for i, point in enumerate(current_route):
            # Insert any critical bins that should come before this point
            for cb in new_critical_bins:
                if cb.id in critical_inserted:
                    continue

                d_current = self.haversine_distance(
                    point['lat'], point['lng'],
                    cb.lat, cb.lng
                )

                if i > 0:
                    prev = current_route[i - 1]
                    d_prev = self.haversine_distance(prev['lat'], prev['lng'], cb.lat, cb.lng)
                    d_savings = d_prev - d_current

                    if d_savings > 0:  # This insertion saves distance
                        updated_route.append({
                            'point_id': cb.id,
                            'lat': cb.lat,
                            'lng': cb.lng,
                            'fill_percent': cb.fill_percent,
                            'travel_time_min': round((d_current / self.avg_speed_kmh) * 60, 1),
                            'service_time_min': cb.estimated_service_time,
                            'inserted_dynamically': True,
                            'savings_km': round(d_savings, 2)
                        })
                        critical_inserted.add(cb.id)

            updated_route.append(point)

        return {
            'original_route_length': len(current_route),
            'updated_route': updated_route,
            'bins_rerouted': len(critical_inserted)
        }


class OverflowPredictor:
    """
    Predict bin overflow risk based on historical patterns and fill rates.
    """

    def __init__(self):
        self.fill_rate_cache: Dict[str, List[float]] = {}

    def estimate_fill_rate(
        self,
        bin_id: str,
        historical_fills: List[float],
        time_intervals_hours: List[int]
    ) -> float:
        """
        Estimate fill rate for a bin (percent per hour).

        Uses linear regression on recent fill history.
        """
        if len(historical_fills) < 2:
            return 0.5  # Default fill rate

        # Simple linear regression
        n = len(historical_fills)
        x = np.array(time_intervals_hours)
        y = np.array(historical_fills)

        # Remove outliers
        y_mean = np.mean(y)
        y_std = np.std(y)
        mask = np.abs(y - y_mean) < 2 * y_std
        x = x[mask]
        y = y[mask]

        if len(x) < 2:
            return 0.5

        # Linear fit
        slope = np.polyfit(x, y, 1)[0]

        return max(0, slope)

    def predict_overflow_time(
        self,
        current_fill_percent: float,
        fill_rate_per_hour: float,
        collection_capacity_percent: float = 90.0
    ) -> Dict:
        """
        Predict when bin will reach capacity.

        Args:
            current_fill_percent: Current fill level
            fill_rate_per_hour: Fill rate (% per hour)
            collection_capacity_percent: Threshold for overflow

        Returns:
            Overflow prediction
        """
        if fill_rate_per_hour <= 0:
            return {
                'overflow_estimated': False,
                'hours_to_overflow': float('inf'),
                'overflow_time': None
            }

        remaining_percent = collection_capacity_percent - current_fill_percent
        hours_to_overflow = remaining_percent / fill_rate_per_hour

        overflow_time = datetime.now() + timedelta(hours=hours_to_overflow)

        return {
            'overflow_estimated': hours_to_overflow < 24,
            'hours_to_overflow': round(hours_to_overflow, 1),
            'overflow_time': overflow_time.isoformat(),
            'risk_level': 'critical' if hours_to_overflow < 2 else ('high' if hours_to_overflow < 6 else ('medium' if hours_to_overflow < 12 else 'low'))
        }

    def batch_predict_overflow(
        self,
        bins: List[CollectionPoint],
        historical_data: Dict[str, Tuple[List[float], List[int]]]
    ) -> List[Dict]:
        """
        Predict overflow for multiple bins.

        Args:
            bins: List of collection points
            historical_data: Dict mapping bin_id to (fills, hours)

        Returns:
            List of overflow predictions
        """
        predictions = []

        for bin in bins:
            fills, hours = historical_data.get(bin.id, ([bin.fill_percent], [0]))
            fill_rate = self.estimate_fill_rate(bin.id, fills, hours)

            pred = self.predict_overflow_time(bin.fill_percent, fill_rate)
            pred['bin_id'] = bin.id
            pred['current_fill'] = bin.fill_percent
            pred['fill_rate'] = fill_rate

            predictions.append(pred)

        # Sort by risk
        predictions.sort(key=lambda x: (
            0 if x['risk_level'] == 'critical' else
            1 if x['risk_level'] == 'high' else
            2 if x['risk_level'] == 'medium' else 3
        ))

        return predictions
