"""
LangGraph Agent for SEC Crypto Knowledge Research

This module implements a LangGraph agent with a RAG (Retrieval-Augmented Generation) tool
to assist users with SEC Crypto knowledge research. The agent can search through the
knowledge base, provide evidence-backed answers, and ask follow-up questions for deeper research.
"""

from typing import Annotated, List, Dict, Any, Optional, TypedDict
import operator
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from search_handler import search_pinecone
from utils import get_llm


# Define the agent state
class AgentState(TypedDict):
    """State of the agent conversation."""
    messages: Annotated[List[BaseMessage], operator.add]
    research_depth: int  # Track how deep the user wants to go
    conversation_context: List[Dict[str, str]]  # Store conversation history


@tool
def rag_search(
    query: str,
    top_k: int = 5,
    alpha: float = 0.5,
    score_threshold: float = 0.5
) -> str:
    """
    RAG (Retrieval-Augmented Generation) Search Tool for SEC Crypto Knowledge Base.
    
    This tool performs a hybrid semantic search across the SEC Crypto knowledge base to find
    relevant information that can help answer user queries. It combines two search strategies:
    
    1. **Dense Semantic Search**: Uses neural embeddings to find documents that are semantically
       similar to the query, even if they don't contain exact keywords. This helps find contextual
       matches where the meaning aligns with the query.
    
    2. **Sparse Keyword Search**: Uses keyword matching (via SPLADE) to find documents containing
       specific terms from the query. This ensures exact term matches are captured.
    
    **How to use this tool effectively:**
    
    - **For specific terms/concepts**: Use the exact terminology from SEC regulations, crypto terms,
      or legal language. The sparse search will match these keywords precisely.
    
    - **For contextual questions**: Frame your query as a natural question or sentence. The dense
      search will find semantically related content even without exact keyword matches.
    
    - **For comprehensive research**: The tool returns multiple relevant passages with relevance scores.
      Higher scores indicate stronger matches. Use multiple search queries with different phrasings
      to gather comprehensive evidence.
    
    **What the tool returns:**
    - Each result includes: title, snippet (text content), relevance score (0-1), and metadata
    - Results are ranked by relevance, with the most relevant passages first
    - Scores above the threshold (default 0.5) indicate meaningful relevance
    - The snippets contain the actual text from SEC documents that can be used as evidence
    
    **Best practices for query formulation:**
    - Use specific SEC regulation numbers, crypto terminology, or legal concepts
    - Ask questions naturally: "What are the requirements for..." or "How does SEC regulate..."
    - Include context: "cryptocurrency exchanges" is better than just "exchanges"
    - For deep research, break complex questions into multiple focused queries
    
    Args:
        query: The search query. Can be:
            - Specific terms: "Bitcoin ETF", "SEC Form 10-K", "cryptocurrency regulation"
            - Contextual sentences: "What are the disclosure requirements for crypto assets?"
            - Research questions: "How does the SEC define digital assets?"
        top_k: Number of results to return (default: 10, max recommended: 20)
        alpha: Blend factor between dense (1.0) and sparse (0.0) search.
               - 0.0 = pure keyword search (good for exact terms)
               - 0.5 = balanced (default, good for most queries)
               - 1.0 = pure semantic search (good for conceptual questions)
        score_threshold: Minimum relevance score (0-1). Results below this are filtered out.
                        Lower threshold (0.3) returns more results but may include less relevant ones.
                        Higher threshold (0.7) returns fewer but highly relevant results.
    
    Returns:
        A formatted string containing search results with:
        - Result number and title
        - Relevance score
        - Text snippet (evidence from SEC documents)
        - Metadata (source information if available)
        
        Results are formatted for easy reading and citation in responses.
    
    Example queries:
        - "Bitcoin ETF approval process"
        - "What are the reporting requirements for cryptocurrency exchanges?"
        - "SEC guidance on stablecoins"
        - "How are digital assets classified under securities law?"
    """
    try:
        results = search_pinecone(
            query=query,
            alpha=alpha,
            top_k=top_k,
            score_threshold=score_threshold,
            include_scores=True
        )
        
        if not results or (len(results) == 1 and results[0].get("error")):
            return f"No relevant results found for query: '{query}'. Try rephrasing with different terms or lowering the score_threshold."
        
        # Format results for the agent
        formatted_results = []
        formatted_results.append(f"Found {len(results)} relevant results for query: '{query}'\n")
        formatted_results.append("=" * 80)
        
        for idx, result in enumerate(results, 1):
            title = result.get("title", f"Result {idx}")
            snippet = result.get("snippet", "No content available")
            score = result.get("score", "0.00")
            metadata = result.get("metadata", {})
            
            formatted_results.append(f"\n[{idx}] {title}")
            formatted_results.append(f"Relevance Score: {score}")
            formatted_results.append(f"Evidence:\n{snippet}")
            
            # Include metadata if available
            if metadata:
                metadata_str = ", ".join([f"{k}: {v}" for k, v in metadata.items() if k not in ["text", "content", "snippet"]])
                if metadata_str:
                    formatted_results.append(f"Source: {metadata_str}")
            
            formatted_results.append("-" * 80)
        
        return "\n".join(formatted_results)
    
    except Exception as e:
        return f"Error performing RAG search: {str(e)}. Please try again with a different query."


def create_agent_graph():
    """
    Create and configure the LangGraph agent with RAG tool.
    
    Returns:
        Compiled LangGraph graph ready for execution.
    """
    # Initialize LLM with gpt-4o-mini
    llm = get_llm(streaming=False)
    
    # Bind the RAG tool to the LLM
    tools = [rag_search]
    llm_with_tools = llm.bind_tools(tools)
    
    # Create tool node for executing tools
    tool_node = ToolNode(tools)
    
    # Define the agent node
    def agent_node(state: AgentState):
        """Agent node that processes messages and decides on actions."""
        messages = state["messages"]
        
        # Add system message with instructions if this is the first message
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            system_prompt = """You are an expert SEC Crypto knowledge research assistant. Your role is to help users dive deep into SEC cryptocurrency regulations, policies, and guidance.

            **Your Capabilities:**
            - You have access to a RAG (Retrieval-Augmented Generation) tool that searches through SEC Crypto knowledge base
            - The RAG tool can find relevant documents, regulations, and guidance based on user queries
            - You can search for specific terms, contextual sentences, or answer research questions

            **How to Use the RAG Tool:**
            - When a user asks a question, use the rag_search tool to find relevant evidence
            - The tool searches for both exact keywords and semantically similar content
            - Always cite the evidence you find - include relevance scores and snippets
            - For complex questions, you may need multiple searches with different query phrasings

            **Research Depth Strategy:**
            - If a user wants to "dive deep" or asks for comprehensive research, ask follow-up questions to:
            1. Clarify specific aspects they're interested in
            2. Understand their use case or context
            3. Identify which regulations, time periods, or document types are most relevant
            4. Determine if they need regulatory history, current guidance, or both

            **Response Guidelines:**
            - Always provide evidence-backed answers using information from the RAG tool
            - Cite sources with relevance scores and document snippets
            - If initial search doesn't fully answer the question, perform additional searches
            - When asking follow-up questions, be specific and helpful
            - Structure your responses clearly with sections, bullet points, and citations
            - If you find conflicting information, present both perspectives with evidence

            **Example Workflow:**
            1. User asks: "What are the requirements for crypto exchanges?"
            2. You search: rag_search("cryptocurrency exchange requirements SEC")
            3. You analyze results and provide answer with citations
            4. If user wants more depth, ask: "Are you interested in registration requirements, reporting obligations, or both?"

            Remember: Your goal is to help users understand SEC Crypto regulations through evidence-based research."""
            
            messages = [SystemMessage(content=system_prompt)] + messages
        
        # Get response from LLM
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Define routing logic
    def should_continue(state: AgentState):
        """Determine if we should continue or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If the last message has tool calls, continue to tool execution
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        # Otherwise, end
        return END
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    
    # After tools, go back to agent
    workflow.add_edge("tools", "agent")
    
    # Compile the graph
    app = workflow.compile()
    
    return app


def run_agent(query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Run the agent with a user query.
    
    Args:
        query: User's question or research query
        conversation_history: Previous conversation messages (optional)
    
    Returns:
        Agent's response as a string
    """
    # Create the agent graph
    app = create_agent_graph()
    
    # Initialize state
    messages = []
    
    # Add conversation history if provided
    if conversation_history:
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
    
    # Add current query
    messages.append(HumanMessage(content=query))
    
    initial_state = {
        "messages": messages,
        "research_depth": 0,
        "conversation_context": conversation_history or []
    }
    
    # Run the agent
    final_state = app.invoke(initial_state)
    
    # Extract the final response
    final_messages = final_state["messages"]
    
    # Find the last AI message
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage):
            # If it's a tool call response, get the next message
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                continue
            return msg.content
    
    return "I apologize, but I couldn't generate a response. Please try again."


def chat_with_agent(query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Chat interface for the agent that returns structured response.
    
    Args:
        query: User's question or research query
        conversation_history: Previous conversation messages (optional)
    
    Returns:
        Dictionary with:
        - response: Agent's text response
        - tool_calls: List of tool calls made (if any)
        - evidence: List of evidence snippets used (if any)
    """
    app = create_agent_graph()
    
    messages = []
    if conversation_history:
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
    
    messages.append(HumanMessage(content=query))
    
    initial_state = {
        "messages": messages,
        "research_depth": 0,
        "conversation_context": conversation_history or []
    }
    
    final_state = app.invoke(initial_state)
    final_messages = final_state["messages"]
    
    # Extract response and tool calls
    response_text = ""
    tool_calls_made = []
    evidence_snippets = []
    
    for msg in final_messages:
        if isinstance(msg, AIMessage):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_calls_made.extend(msg.tool_calls)
            elif not msg.tool_calls:
                response_text = msg.content
        
        # Extract evidence from tool results
        if hasattr(msg, "content") and "Evidence:" in str(msg.content):
            # Try to extract evidence snippets
            content_str = str(msg.content)
            if "Evidence:" in content_str:
                evidence_snippets.append(content_str)
    
    return {
        "response": response_text,
        "tool_calls": tool_calls_made,
        "evidence": evidence_snippets
    }


if __name__ == "__main__":
    # Example usage
    print("SEC Crypto Knowledge Research Agent")
    print("=" * 80)
    
    # Test query
    test_query = "What are the SEC requirements for cryptocurrency exchanges?"
    
    print(f"\nUser Query: {test_query}\n")
    print("Agent Response:")
    print("-" * 80)
    
    response = run_agent(test_query)
    print(response)
    
    print("\n" + "=" * 80)
    print("\nExample: Deep Research Query")
    print("-" * 80)
    
    deep_query = "I want to dive deep into how the SEC regulates Bitcoin ETFs. Can you help me research this comprehensively?"
    
    print(f"\nUser Query: {deep_query}\n")
    print("Agent Response:")
    print("-" * 80)
    
    response = run_agent(deep_query)
    print(response)

