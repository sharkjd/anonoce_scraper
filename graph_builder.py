from langgraph.graph import END, StateGraph

from nodes import (
    agency_classification_node,
    dedupe_listings_node,
    deep_crawl_details_node,
    discover_anonce_node,
    export_csv_node,
    input_node,
    validate_and_normalize_node,
)
from state import ScraperState


def build_graph():
    graph = StateGraph(ScraperState)
    graph.add_node("input_node", input_node)
    graph.add_node("discover_anonce_node", discover_anonce_node)
    graph.add_node("dedupe_listings_node", dedupe_listings_node)
    graph.add_node("agency_classification_node", agency_classification_node)
    graph.add_node("deep_crawl_details_node", deep_crawl_details_node)
    graph.add_node("validate_and_normalize_node", validate_and_normalize_node)
    graph.add_node("export_csv_node", export_csv_node)

    graph.set_entry_point("input_node")
    graph.add_edge("input_node", "discover_anonce_node")
    graph.add_edge("discover_anonce_node", "dedupe_listings_node")
    graph.add_edge("dedupe_listings_node", "agency_classification_node")
    graph.add_edge("agency_classification_node", "deep_crawl_details_node")
    graph.add_edge("deep_crawl_details_node", "validate_and_normalize_node")
    graph.add_edge("validate_and_normalize_node", "export_csv_node")
    graph.add_edge("export_csv_node", END)
    return graph.compile()
