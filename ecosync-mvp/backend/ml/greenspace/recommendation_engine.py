"""
Green Space Recommendation Engine

Multi-criteria optimization for identifying optimal intervention sites.

Criteria:
- Heat island reduction potential
- Cooling effect (evapotranspiration)
- Community input and equity
- Maintenance requirements
- Cost effectiveness
- Environmental justice prioritization
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class GreenSpaceRecommendation:
    """Represents a recommended green space intervention."""
    site_id: str
    lat: float
    lng: float
    intervention_type: str  # 'tree_planting', 'park_creation', 'green_roof', 'pocket_park'
    priority_score: float  # 0-100
    estimated_area_km2: float
    estimated_cost_usd: float
    expected_cooling_effect_celsius: float
    expected_canopy_coverage_percent: float
    maintenance_level: str  # 'low', 'medium', 'high'
    equity_score: float  # Environmental justice score
    community_benefit_score: float
    payback_years: float
    risk_factors: List[str]
    reasoning: List[str]


class RecommendationEngine:
    """
    Multi-criteria optimization for green space recommendations.

    Uses weighted scoring based on:
    - Heat reduction potential
    - Cost effectiveness
    - Community benefits
    - Equity considerations
    - Feasibility
    """

    def __init__(self):
        self.default_weights = {
            'heat_reduction': 0.30,
            'cost_effectiveness': 0.20,
            'community_benefit': 0.20,
            'equity': 0.15,
            'feasibility': 0.10,
            'maintenance': 0.05
        }

    def analyze_intervention_site(
        self,
        lat: float,
        lng: float,
        current_land_cover: int,
        canopy_percent: float,
        lst_celsius: float,
        impervious_percent: float,
        population_density: float,
        median_income: Optional[float] = None,
        tree_canopy_gap: bool = True
    ) -> Dict:
        """
        Analyze a potential intervention site.

        Args:
            lat, lng: Site coordinates
            current_land_cover: 0-5 (tree, grass, impervious, water, bare, building)
            canopy_percent: Current tree canopy coverage
            lst_celsius: Land surface temperature
            impervious_percent: Impervious surface coverage
            population_density: People per km2
            median_income: Optional median household income
            tree_canopy_gap: Whether site is suitable for tree planting

        Returns:
            Site analysis with scores
        """
        scores = {}

        # Heat reduction potential (higher is better)
        # More impervious + less canopy = higher potential
        heat_reduction = min(100, (impervious_percent / 100) * (1 - canopy_percent / 100) * lst_celsius)
        scores['heat_reduction'] = heat_reduction

        # Cost effectiveness (estimated)
        intervention_type = self._estimate_intervention_type(current_land_cover, tree_canopy_gap)
        if intervention_type:
            cost_per_km2, benefit_per_year = self._estimate_cost_benefit(
                intervention_type, lst_celsius, impervious_percent
            )
            scores['cost_effectiveness'] = min(100, (benefit_per_year / cost_per_km2) * 1000)
            estimated_cost = cost_per_km2
        else:
            scores['cost_effectiveness'] = 0
            estimated_cost = 0

        # Community benefit
        community_score = min(100, population_density / 100)  # Higher density = more benefit
        scores['community_benefit'] = community_score

        # Equity score (favor underserved areas)
        equity_score = 50  # Default
        if median_income is not None:
            # Lower income = higher equity priority
            equity_score = max(0, 100 - (median_income / 1000))
        scores['equity'] = equity_score

        # Feasibility
        if current_land_cover in [0, 1]:  # Already has vegetation
            feasibility = 40  # Would need removal
        elif current_land_cover == 4:  # Bare soil - easy
            feasibility = 90
        elif current_land_cover == 2:  # Impervious - requires conversion
            feasibility = 70
        else:
            feasibility = 50
        scores['feasibility'] = feasibility

        # Maintenance (inverse - lower maintenance = higher score)
        maintenance_map = {'low': 100, 'medium': 60, 'high': 30}
        maintenance_level, _ = self._estimate_maintenance(current_land_cover, intervention_type)
        scores['maintenance'] = maintenance_map.get(maintenance_level, 50)

        # Calculate weighted priority score
        weights = self.default_weights
        priority_score = sum(scores[k] * weights[k] for k in weights)

        return {
            'site_id': f'SITE-{lat:.4f}-{lng:.4f}',
            'lat': lat,
            'lng': lng,
            'intervention_type': intervention_type,
            'priority_score': round(priority_score, 1),
            'component_scores': {k: round(v, 1) for k, v in scores.items()},
            'estimated_cost_usd': estimated_cost,
            'maintenance_level': maintenance_level,
            'cooling_effect_celsius': self._estimate_cooling(lst_celsius, intervention_type),
            'equity_score': round(equity_score, 1)
        }

    def _estimate_intervention_type(self, land_cover: int, canopy_gap: bool) -> Optional[str]:
        """Determine best intervention type for land cover."""
        if land_cover == 0:  # Tree
            return None  # No intervention needed
        elif land_cover == 1:  # Grass
            if canopy_gap:
                return 'tree_planting'
            return 'pocket_park'
        elif land_cover == 2:  # Impervious
            if canopy_gap:
                return 'tree_planting'
            return 'green_roof'
        elif land_cover == 4:  # Bare soil
            return 'tree_planting'
        return None

    def _estimate_cost_benefit(
        self,
        intervention_type: str,
        lst_celsius: float,
        impervious_percent: float
    ) -> Tuple[float, float]:
        """
        Estimate cost per km2 and annual benefit.

        Returns:
            (cost_per_km2_usd, annual_benefit_usd)
        """
        costs = {
            'tree_planting': 500_000,
            'pocket_park': 1_500_000,
            'green_roof': 5_000_000,
            'park_creation': 3_000_000
        }

        base_benefit = lst_celsius * 10_000

        return costs.get(intervention_type, 1_000_000), base_benefit

    def _estimate_maintenance(self, land_cover: int, intervention_type: str) -> Tuple[str, float]:
        """Estimate maintenance requirements."""
        if intervention_type == 'tree_planting':
            return 'medium', 15_000
        elif intervention_type == 'pocket_park':
            return 'high', 50_000
        elif intervention_type == 'green_roof':
            return 'high', 80_000
        return 'medium', 30_000

    def _estimate_cooling(self, lst_celsius: float, intervention_type: str) -> float:
        """Estimate cooling effect in Celsius."""
        if intervention_type == 'tree_planting':
            return min(5.0, lst_celsius * 0.15)
        elif intervention_type == 'pocket_park':
            return min(4.0, lst_celsius * 0.12)
        elif intervention_type == 'green_roof':
            return min(3.0, lst_celsius * 0.08)
        return 0.0

    def generate_recommendations(
        self,
        candidate_sites: List[Dict],
        max_sites: int = 50,
        budget_constraint_usd: Optional[float] = None
    ) -> List[GreenSpaceRecommendation]:
        """
        Generate prioritized recommendations from candidate sites.
        """
        recommendations = []

        for site in candidate_sites:
            priority_score = site.get('priority_score', 0)

            if priority_score < 20:
                continue

            rec = GreenSpaceRecommendation(
                site_id=site['site_id'],
                lat=site['lat'],
                lng=site['lng'],
                intervention_type=site['intervention_type'],
                priority_score=priority_score,
                estimated_area_km2=site.get('estimated_area_km2', 0.01),
                estimated_cost_usd=site.get('estimated_cost_usd', 100_000),
                expected_cooling_effect_celsius=site.get('cooling_effect_celsius', 0),
                expected_canopy_coverage_percent=site.get('canopy_coverage_gain', 0),
                maintenance_level=site.get('maintenance_level', 'medium'),
                equity_score=site.get('equity_score', 50),
                community_benefit_score=site.get('community_benefit', 50),
                payback_years=self._calculate_payback(site),
                risk_factors=self._identify_risks(site),
                reasoning=self._generate_reasoning(site)
            )

            recommendations.append(rec)

        recommendations.sort(key=lambda x: x.priority_score, reverse=True)

        if budget_constraint_usd:
            recommendations = self._apply_budget_constraint(recommendations, budget_constraint_usd)

        return recommendations[:max_sites]

    def _calculate_payback(self, site: Dict) -> float:
        """Calculate payback period in years."""
        cost = site.get('estimated_cost_usd', 100_000)
        annual_benefit = site.get('community_benefit', 50) * 100
        if annual_benefit > 0:
            return round(cost / annual_benefit, 1)
        return 99.9

    def _identify_risks(self, site: Dict) -> List[str]:
        """Identify risk factors for the intervention."""
        risks = []

        if site.get('maintenance_level') == 'high':
            risks.append('High maintenance requirements may strain municipal budgets')

        equity = site.get('equity_score', 50)
        if equity > 80:
            risks.append('Site in underserved area - ensure community engagement')

        land_cover = site.get('current_land_cover', 2)
        if land_cover == 2:
            risks.append('Requires removal of existing surface - may face permitting challenges')

        intervention = site.get('intervention_type', '')
        if intervention == 'green_roof':
            risks.append('Building structural requirements may limit applicability')

        return risks

    def _generate_reasoning(self, site: Dict) -> List[str]:
        """Generate human-readable reasoning for recommendation."""
        reasoning = []

        scores = site.get('component_scores', {})
        if scores.get('heat_reduction', 0) > 60:
            reasoning.append(f"High heat reduction potential (score: {scores['heat_reduction']:.0f})")

        equity = site.get('equity_score', 50)
        if equity > 70:
            reasoning.append(f"Located in underserved community (equity score: {equity:.0f})")

        intervention = site.get('intervention_type', '')
        if intervention == 'tree_planting':
            reasoning.append("Tree planting offers best cost-to-cooling ratio")
        elif intervention == 'pocket_park':
            reasoning.append("Pocket park will provide community recreation space")

        cooling = site.get('cooling_effect_celsius', 0)
        if cooling > 2:
            reasoning.append(f"Expected to reduce local temperature by {cooling:.1f}°C")

        return reasoning

    def _apply_budget_constraint(
        self,
        recommendations: List[GreenSpaceRecommendation],
        budget_usd: float
    ) -> List[GreenSpaceRecommendation]:
        """Filter recommendations to fit within budget."""
        selected = []
        total_cost = 0

        for rec in recommendations:
            if total_cost + rec.estimated_cost_usd <= budget_usd:
                selected.append(rec)
                total_cost += rec.estimated_cost_usd

        return selected

    def generate_equity_report(self, recommendations: List[GreenSpaceRecommendation]) -> Dict:
        """Generate environmental justice report."""
        high_equity = sum(1 for r in recommendations if r.equity_score > 70)
        medium_equity = sum(1 for r in recommendations if 50 <= r.equity_score <= 70)
        low_equity = sum(1 for r in recommendations if r.equity_score < 50)

        total_investment = sum(r.estimated_cost_usd for r in recommendations)
        equity_investment = sum(
            r.estimated_cost_usd for r in recommendations if r.equity_score > 70
        )

        return {
            'total_recommendations': len(recommendations),
            'by_equity_category': {
                'high_priority_equity': high_equity,
                'medium_equity': medium_equity,
                'low_equity': low_equity
            },
            'investment_distribution': {
                'high_equity_percent': round(equity_investment / total_investment * 100, 1) if total_investment > 0 else 0,
                'total_investment_usd': total_investment
            },
            'meets_equity_target': high_equity >= len(recommendations) * 0.6
        }

    def format_recommendations_response(
        self,
        recommendations: List[GreenSpaceRecommendation]
    ) -> Dict:
        """Format recommendations for API response."""
        return {
            'recommendations': [
                {
                    'site_id': r.site_id,
                    'location': {'lat': r.lat, 'lng': r.lng},
                    'intervention_type': r.intervention_type,
                    'priority_score': r.priority_score,
                    'estimated_cost_usd': r.estimated_cost_usd,
                    'expected_cooling_celsius': r.expected_cooling_effect_celsius,
                    'payback_years': r.payback_years,
                    'maintenance_level': r.maintenance_level,
                    'equity_score': r.equity_score,
                    'risk_factors': r.risk_factors,
                    'reasoning': r.reasoning
                }
                for r in recommendations
            ],
            'summary': {
                'total_sites': len(recommendations),
                'total_investment_usd': sum(r.estimated_cost_usd for r in recommendations),
                'total_cooling_effect_celsius': sum(r.expected_cooling_effect_celsius for r in recommendations),
                'avg_priority_score': float(np.mean([r.priority_score for r in recommendations])) if recommendations else 0,
                'avg_payback_years': float(np.mean([r.payback_years for r in recommendations])) if recommendations else 99
            },
            'generated_at': datetime.now().isoformat()
        }
