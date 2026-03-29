from typing import Any, Dict, List


class PatternDetectionAgent:
    """Detect inefficiency patterns from analyzed CSV insights."""

    def detect_cost_leakage(self, top_spend_items: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        leakage: List[Dict[str, Any]] = []
        for idx, item in enumerate(top_spend_items[:top_n]):
            leakage.append(
                {
                    'id': f'cost_{idx + 1}',
                    'vendor': item.get('tool', f'row_{idx + 1}'),
                    'amount': float(item.get('amount', 0.0) or 0.0),
                    'note': 'High absolute spend concentration from uploaded dataset.',
                }
            )
        return leakage

    def estimate_optimization_impact(
        self,
        top_spend_items: List[Dict[str, Any]],
        optimization_rate: float = 0.7,
        recovery_probability: float = 0.65,
        top_n: int = 3,
    ) -> float:
        return sum(
            float(item.get('amount', 0.0) or 0.0) * optimization_rate * recovery_probability
            for item in top_spend_items[:top_n]
        )
