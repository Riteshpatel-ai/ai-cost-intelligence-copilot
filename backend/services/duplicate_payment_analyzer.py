import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

_AMOUNT_CANDIDATES = [
    'amount',
    'cost',
    'cost_inr',
    'salary',
    'monthly_salary',
    'payment_amount',
    'invoice_amount',
    'value',
]

_VENDOR_CANDIDATES = [
    'payee',
    'vendor',
    'department',
    'employee_id',
    'supplier',
    'tool',
    'merchant',
    'name',
    'beneficiary',
]

_AMOUNT_KEYWORDS = ('amount', 'cost', 'spend', 'expense', 'salary', 'payment', 'value', 'price')
_VENDOR_KEYWORDS = (
    'vendor',
    'supplier',
    'tool',
    'department',
    'employee',
    'team',
    'service',
    'project',
    'name',
    'business',
    'unit',
)
_DATE_KEYWORDS = ('date', 'month', 'period', 'week')

_DATE_CANDIDATES = [
    'date',
    'payment_date',
    'invoice_date',
    'txn_date',
]

_INVOICE_CANDIDATES = [
    'invoice_no',
    'invoice_number',
    'invoice',
    'reference_no',
    'ref_no',
]

_STOPWORDS = {
    'india',
    'business',
    'enterprise',
    'premium',
    'standard',
    'pro',
    'duplicate',
    'hidden',
    'overlap',
    'addon',
    'add-on',
    'cost',
    'workspace',
    'software',
    'api',
}


def _normalize_key(value: str) -> str:
    if not value:
        return ''
    cleaned = re.sub(r'[^a-z0-9\s]+', ' ', value.lower()).strip()
    tokens = [token for token in cleaned.split() if token and token not in _STOPWORDS]
    if not tokens:
        return cleaned
    return ' '.join(tokens[:2])


def _pick_field(row: Dict[str, Any], candidates: List[str]) -> Optional[str]:
    if not row:
        return None
    normalized = {str(key).strip().lower(): key for key in row.keys()}
    for candidate in candidates:
        if candidate in normalized:
            original_key = normalized[candidate]
            value = row.get(original_key)
            if value is not None and str(value).strip() != '':
                return str(value).strip()

    # Fallback: keyword-based key inference for dynamic schemas.
    keywords = ()
    if candidates is _AMOUNT_CANDIDATES:
        keywords = _AMOUNT_KEYWORDS
    elif candidates is _VENDOR_CANDIDATES:
        keywords = _VENDOR_KEYWORDS
    elif candidates is _DATE_CANDIDATES:
        keywords = _DATE_KEYWORDS

    if keywords:
        best_key = None
        best_score = 0
        for norm_key, raw_key in normalized.items():
            score = sum(1 for kw in keywords if kw in norm_key)
            if score > best_score:
                best_key = raw_key
                best_score = score

        if best_key is not None and best_score > 0:
            value = row.get(best_key)
            if value is not None and str(value).strip() != '':
                return str(value).strip()
    return None


def _parse_amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    cleaned = re.sub(r'[^0-9.\-]', '', text)
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_amount(row: Dict[str, Any]) -> Optional[float]:
    normalized = {str(key).strip().lower(): key for key in row.keys()}
    for candidate in _AMOUNT_CANDIDATES:
        if candidate in normalized:
            amount = _parse_amount(row.get(normalized[candidate]))
            if amount is not None:
                return amount

    # Dynamic fallback: infer amount column by keyword matches.
    best_key = None
    best_score = 0
    for norm_key, raw_key in normalized.items():
        score = sum(1 for kw in _AMOUNT_KEYWORDS if kw in norm_key)
        if score > best_score:
            best_key = raw_key
            best_score = score

    if best_key is not None and best_score > 0:
        amount = _parse_amount(row.get(best_key))
        if amount is not None:
            return amount
    return None


def analyze_uploaded_duplicates(rows: List[Dict[str, Any]], top_n: int = 5) -> Dict[str, Any]:
    if not rows:
        return {
            'duplicate_sets': [],
            'total_overpayment': 0.0,
            'total_calculated_impact': 0.0,
            'coverage': {'rows_analyzed': 0, 'rows_with_amount': 0},
        }

    groups: Dict[str, List[Tuple[Dict[str, Any], float, str, str]]] = defaultdict(list)
    rows_with_amount = 0

    for index, row in enumerate(rows):
        amount = _extract_amount(row)
        if amount is None:
            continue
        rows_with_amount += 1

        vendor = _pick_field(row, _VENDOR_CANDIDATES) or f'row_{index + 1}'
        date_value = _pick_field(row, _DATE_CANDIDATES) or ''
        invoice_no = _pick_field(row, _INVOICE_CANDIDATES) or ''

        normalized_vendor = _normalize_key(vendor)
        group_key = normalized_vendor or _normalize_key(vendor.lower())
        if not group_key:
            group_key = vendor.lower()

        groups[group_key].append((row, amount, date_value, invoice_no))

    duplicate_sets: List[Dict[str, Any]] = []
    for group_key, items in groups.items():
        if len(items) <= 1:
            continue

        amounts = [entry[1] for entry in items]
        avg_amount = sum(amounts) / len(amounts)
        min_amount = min(amounts)
        max_amount = max(amounts)
        spread_ratio = 0.0 if avg_amount == 0 else (max_amount - min_amount) / avg_amount

        is_exact = spread_ratio <= 0.05
        confidence = 0.9 if is_exact else 0.72
        recovery_probability = 0.8 if is_exact else 0.58

        overpayment = max(0.0, (len(items) - 1) * avg_amount)
        calculated_impact = overpayment * confidence * recovery_probability

        representative = items[0][0]
        vendor_name = _pick_field(representative, _VENDOR_CANDIDATES) or group_key

        evidence_rows = []
        for idx, (raw_row, amount, date_value, invoice_no) in enumerate(items[:5]):
            evidence_rows.append(
                {
                    'id': str(raw_row.get('id', f'{group_key}_{idx + 1}')),
                    'vendor': vendor_name,
                    'amount': amount,
                    'date': date_value,
                    'invoice_no': invoice_no,
                }
            )

        duplicate_sets.append(
            {
                'group': group_key,
                'vendor': vendor_name,
                'dup_count': len(items),
                'average_amount': round(avg_amount, 2),
                'overpayment': round(overpayment, 2),
                'confidence': confidence,
                'recovery_probability': recovery_probability,
                'calculated_impact': round(calculated_impact, 2),
                'is_exact_duplicate': is_exact,
                'evidence': evidence_rows,
            }
        )

    ranked = sorted(duplicate_sets, key=lambda item: item['calculated_impact'], reverse=True)[:top_n]

    total_overpayment = round(sum(item['overpayment'] for item in ranked), 2)
    total_calculated_impact = round(sum(item['calculated_impact'] for item in ranked), 2)

    return {
        'duplicate_sets': ranked,
        'total_overpayment': total_overpayment,
        'total_calculated_impact': total_calculated_impact,
        'coverage': {'rows_analyzed': len(rows), 'rows_with_amount': rows_with_amount},
    }
