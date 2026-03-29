from typing import Any, Dict, List, Set


class GraphBuilder:
	def __init__(self):
		self.nodes: List[Dict[str, Any]] = []
		self.edges: List[Dict[str, Any]] = []
		self._node_ids: Set[str] = set()
		self._edge_ids: Set[str] = set()

	def add_node(self, node_id: str, node_type: str, label: str = "", risk: str = "medium"):
		if node_id in self._node_ids:
			return
		index = len(self.nodes)
		x = 120 + (index % 4) * 220
		y = 90 + (index // 4) * 150
		self.nodes.append(
			{
				"id": node_id,
				"position": {"x": x, "y": y},
				"data": {"label": label or node_id, "type": node_type, "risk": risk},
			}
		)
		self._node_ids.add(node_id)

	def add_edge(self, source: str, target: str, label: str):
		edge_id = f"{source}->{target}:{label}"
		if edge_id in self._edge_ids:
			return
		self.edges.append(
			{
				"id": edge_id,
				"source": source,
				"target": target,
				"label": label,
				"animated": label in {"CAUSES_RISK", "DUPLICATE_OF"},
			}
		)
		self._edge_ids.add(edge_id)

	def build(self) -> Dict[str, List[Dict[str, Any]]]:
		return {"nodes": self.nodes, "edges": self.edges}
