import logging
import networkx as nx
from app.models.schemas import EngineScoreResponse
from app.database import find_many

logger = logging.getLogger(__name__)


class GraphEngine:
    """Engine for graph-based fraud analysis using NetworkX."""

    def __init__(self):
        self.graph = nx.Graph()

    async def build_graph(self):
        """Load edges from DB and construct in-memory graph."""
        edges = await find_many("graph_edges", {}, limit=10000)
        self.graph.clear()
        for edge in edges:
            self.graph.add_edge(
                edge.get("from_node"), edge.get("to_node"),
                weight=edge.get("weight", 1.0),
                edge_type=edge.get("edge_type")
            )

    async def score(self, user_id: str, device_id: str) -> EngineScoreResponse:
        """Score user/device based on graph connections."""
        if self.graph.number_of_nodes() == 0:
            await self.build_graph()

        if self.graph.number_of_nodes() == 0:
            return EngineScoreResponse(
                score=0.0, confidence=0.3,
                signals=["Clean graph profile"],
                details={"message": "Graph is empty"}
            )

        score = 0.0
        signals = []

        if self.graph.has_node(user_id):
            neighbors = list(self.graph.neighbors(user_id))
            suspicious = sum(1 for n in neighbors if str(n).startswith("flagged_"))
            if suspicious > 0:
                score += 0.3 * min(suspicious, 3)
                signals.append("Shared device with flagged user" if suspicious == 1 else "Connected to known mule account")

            try:
                component = nx.node_connected_component(self.graph, user_id)
                flagged_in = sum(1 for n in component if str(n).startswith("flagged_"))
                if len(component) > 3 and flagged_in >= 2:
                    score += 0.4
                    signals.append("Part of potential fraud ring")
            except Exception:
                pass

        if self.graph.has_node(device_id):
            device_neighbors = list(self.graph.neighbors(device_id))
            user_count = sum(1 for n in device_neighbors if n != user_id)
            if user_count > 2:
                score += 0.2
                signals.append("Shared device across multiple users")

        if not signals:
            signals.append("Clean graph profile")

        score = min(score, 1.0)
        confidence = 0.8 if self.graph.number_of_nodes() > 100 else 0.5

        return EngineScoreResponse(
            score=score, confidence=confidence, signals=signals,
            details={"node_count": self.graph.number_of_nodes()}
        )
