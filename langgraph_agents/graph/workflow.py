from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph_agents.agents.submission_agent import submission_agent
from langgraph_agents.agents.evaluation_agent import evaluate_engagement

graph = StateGraph(dict)

graph.add_node("submission_agent", submission_agent)
graph.add_node("evaluate_engagement", evaluate_engagement)

graph.set_entry_point("evaluate_engagement")
graph.add_edge("evaluate_engagement", END)

# graph.add_edge("evaluate_engagement", END)

compiled_graph = graph.compile()

