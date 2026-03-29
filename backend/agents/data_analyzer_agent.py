from typing import Any, Dict, List

from backend.tools.csv_search_tool import CSVSearchTool


class DataAnalyzerAgent:
    """Runs structured analysis on uploaded CSV rows using shared tools."""

    def __init__(self, csv_search_tool: CSVSearchTool | None = None):
        self.csv_search_tool = csv_search_tool or CSVSearchTool()

    def analyze_rows(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        top_spend_items = self.csv_search_tool.top_items_by_amount(rows, top_n=5)
        sla_breaches = self.csv_search_tool.extract_sla_signals(rows, top_n=5)
        return {
            'row_count': len(rows),
            'top_spend_items': top_spend_items,
            'sla_breaches': sla_breaches,
        }
