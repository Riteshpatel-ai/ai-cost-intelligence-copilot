from typing import Any, Dict, Iterable, List, Tuple
import re


class CSVSearchTool:
    """Search and analyze CSV-like row data."""

    amount_candidates: Tuple[str, ...] = (
        'Cost_INR',
        'cost_inr',
        'Salary',
        'salary',
        'Monthly_Salary',
        'monthly_salary',
        'amount',
        'Amount',
        'cost',
        'Cost',
    )

    name_candidates: Tuple[str, ...] = (
        'Tool',
        'tool',
        'Department',
        'department',
        'Employee_ID',
        'employee_id',
        'Vendor',
        'vendor',
        'name',
        'Name',
    )

    amount_keywords: Tuple[str, ...] = (
        'amount',
        'cost',
        'spend',
        'expense',
        'salary',
        'price',
        'value',
        'payable',
        'payment',
    )

    name_keywords: Tuple[str, ...] = (
        'tool',
        'vendor',
        'name',
        'business',
        'unit',
        'department',
        'team',
        'service',
        'product',
        'resource',
        'employee',
        'project',
        'account',
    )

    breach_risk_candidates: Tuple[str, ...] = (
        'SLA_Breach_Risk',
        'sla_breach_risk',
        'breach_risk',
        'sla_risk',
        'risk_score',
    )

    penalty_candidates: Tuple[str, ...] = (
        'Penalty_Risk_INR',
        'penalty_risk_inr',
        'penalty_risk',
        'penalty_inr',
        'sla_penalty',
    )

    days_to_breach_candidates: Tuple[str, ...] = (
        'Days_To_Breach',
        'days_to_breach',
        'time_remaining_days',
        'days_remaining',
    )

    def filter_rows(
        self,
        rows: List[Dict[str, Any]],
        query_text: str,
        columns: Iterable[str] | None = None,
    ) -> List[Dict[str, Any]]:
        q = (query_text or '').strip().lower()
        if not q:
            return rows

        if columns:
            scoped_columns = tuple(columns)
            return [
                row
                for row in rows
                if any(q in str(row.get(col, '')).lower() for col in scoped_columns)
            ]

        return [
            row
            for row in rows
            if any(q in str(value).lower() for value in row.values())
        ]

    def top_items_by_amount(self, rows: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows):
            amount = self._row_metric(row, self.amount_candidates, dynamic_keywords=self.amount_keywords)
            if amount <= 0:
                continue
            items.append(
                {
                    'tool': self._row_name(row, idx),
                    'amount': amount,
                }
            )

        return sorted(items, key=lambda item: float(item['amount']), reverse=True)[:top_n]

    def extract_sla_signals(self, rows: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows):
            breach_risk = self._row_metric(
                row,
                self.breach_risk_candidates,
                dynamic_keywords=('sla', 'breach', 'risk'),
            )
            penalty_risk = self._row_metric(
                row,
                self.penalty_candidates,
                dynamic_keywords=('penalty', 'risk'),
            )
            time_remaining_days = self._row_metric(
                row,
                self.days_to_breach_candidates,
                dynamic_keywords=('days', 'breach'),
            )

            if (breach_risk >= 0.6) or (0 < time_remaining_days <= 7) or (penalty_risk > 0):
                signals.append(
                    {
                        'id': f'sla_{idx + 1}',
                        'task': self._row_name(row, idx),
                        'time_remaining': time_remaining_days,
                        'error_rate': breach_risk,
                        'penalty_risk': penalty_risk,
                    }
                )

        return sorted(
            signals,
            key=lambda item: (float(item.get('penalty_risk', 0.0)), float(item.get('error_rate', 0.0))),
            reverse=True,
        )[:top_n]

    def _row_name(self, row: Dict[str, Any], idx: int) -> str:
        key = self._resolve_key(row, self.name_candidates)
        if key is not None and row.get(key):
            return str(row.get(key))

        dyn_key = self._resolve_key_by_keywords(row, self.name_keywords)
        if dyn_key is not None and row.get(dyn_key):
            return str(row.get(dyn_key))
        return f'row_{idx + 1}'

    def _resolve_key(self, row: Dict[str, Any], keys: Tuple[str, ...]) -> str | None:
        if not row:
            return None

        normalized_map = {self._normalize_key(str(k)): str(k) for k in row.keys()}
        for key in keys:
            key_norm = self._normalize_key(key)
            if key_norm in normalized_map:
                return normalized_map[key_norm]
        return None

    def _resolve_key_by_keywords(self, row: Dict[str, Any], keywords: Tuple[str, ...]) -> str | None:
        if not row:
            return None

        best_key: str | None = None
        best_score = 0
        for raw_key in row.keys():
            norm = self._normalize_key(str(raw_key))
            score = 0
            for kw in keywords:
                if kw in norm:
                    score += 1
            if score > best_score:
                best_key = str(raw_key)
                best_score = score
        return best_key if best_score > 0 else None

    def _normalize_key(self, value: str) -> str:
        return re.sub(r'[^a-z0-9]+', '_', value.strip().lower()).strip('_')

    def _to_float(self, value: Any) -> float:
        try:
            text = str(value).replace(',', '').strip()
            text = re.sub(r'[^0-9.\-]', '', text)
            if not text:
                return 0.0
            return float(text)
        except ValueError:
            return 0.0

    def _row_metric(self, row: Dict[str, Any], keys: Tuple[str, ...], dynamic_keywords: Tuple[str, ...] = ()) -> float:
        key = self._resolve_key(row, keys)
        if key is not None:
            return self._to_float(row.get(key, 0))

        if dynamic_keywords:
            dyn_key = self._resolve_key_by_keywords(row, dynamic_keywords)
            if dyn_key is not None:
                return self._to_float(row.get(dyn_key, 0))
        return 0.0
