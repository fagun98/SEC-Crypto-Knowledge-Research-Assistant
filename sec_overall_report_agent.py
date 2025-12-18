"""
SEC Round Table Overall Report Agent

This module implements a LangGraph agent to generate a comprehensive overall report
that combines insights from all SEC Round Table Meeting reports. The agent:
- Combines views of the same speaker across all meetings
- Tags speakers with topics they're interested in or spoke about
- Identifies the most influential person across all meetings
- Predicts future SEC actions and decisions based on influencer views
"""

from typing import Annotated, List, Dict, Any, Optional, TypedDict
import operator
import os
import glob
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv

from search_handler import search_pinecone
from utils import get_llm

load_dotenv()


# Define the agent state
class OverallReportAgentState(TypedDict):
    """State of the overall report agent."""
    messages: Annotated[List[BaseMessage], operator.add]
    report_files: List[str]
    report_contents: Dict[str, str]
    overall_report: str
    sources: List[str]


@tool
def read_meeting_report(file_path: str) -> str:
    """
    Read and return the content of a SEC meeting report file.
    
    Args:
        file_path: Path to the meeting report file (e.g., "SEC_Meeting_Report_defi-american-spirit.txt")
    
    Returns:
        Full content of the meeting report file.
    """
    try:
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' not found."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"Report from file: {file_path}\n\n{content}"
    
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


@tool
def find_all_meeting_reports(directory: str = ".") -> str:
    """
    Find all SEC meeting report files in the specified directory.
    
    Args:
        directory: Directory to search for report files (default: current directory)
    
    Returns:
        List of all found meeting report file paths.
    """
    try:
        # Search for SEC meeting report files
        pattern = os.path.join(directory, "SEC_Meeting_Report_*.txt")
        report_files = glob.glob(pattern)
        
        if not report_files:
            return f"No meeting report files found in {directory}. Pattern used: SEC_Meeting_Report_*.txt"
        
        # Sort by modification time (newest first)
        report_files.sort(key=os.path.getmtime, reverse=True)
        
        result = f"Found {len(report_files)} meeting report file(s):\n\n"
        for idx, file_path in enumerate(report_files, 1):
            file_name = os.path.basename(file_path)
            result += f"{idx}. {file_name}\n"
        
        result += "\nFile paths:\n"
        for file_path in report_files:
            result += f"- {os.path.abspath(file_path)}\n"
        
        return result
    
    except Exception as e:
        return f"Error finding meeting reports: {str(e)}"


@tool
def rag_search(
    query: str,
    top_k: int = 5,
    alpha: float = 0.5,
    score_threshold: float = 0.5
) -> str:
    """
    RAG (Retrieval-Augmented Generation) Search Tool for SEC Crypto Knowledge Base.
    
    Use this tool to search for relevant SEC regulations, guidance, or historical context
    that might be relevant for understanding trends and future predictions.
    
    Args:
        query: The search query about SEC regulations, crypto policies, etc.
        top_k: Number of results to return (default: 5)
        alpha: Blend factor between dense (1.0) and sparse (0.0) search (default: 0.5)
        score_threshold: Minimum relevance score (0-1, default: 0.5)
    
    Returns:
        Formatted search results with evidence snippets and citations.
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
            return f"No relevant results found for query: '{query}'. Try rephrasing with different terms."
        
        formatted_results = []
        formatted_results.append(f"Found {len(results)} relevant results for query: '{query}'\n")
        formatted_results.append("=" * 80)
        
        for idx, result in enumerate(results, 1):
            title = result.get("title", f"Result {idx}")
            snippet = result.get("snippet", "No content available")
            score = result.get("score", "0.00")
            url = result.get("url", "")
            
            formatted_results.append(f"\n[{idx}] {title}")
            formatted_results.append(f"Relevance Score: {score}")
            formatted_results.append(f"Evidence:\n{snippet}")
            if url:
                formatted_results.append(f"Source URL: {url}")
            formatted_results.append("-" * 80)
        
        return "\n".join(formatted_results)
    
    except Exception as e:
        return f"Error performing RAG search: {str(e)}. Please try again with a different query."


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for additional information about SEC trends, future plans, or speaker backgrounds.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
    
    Returns:
        Formatted search results with titles, snippets, and URLs.
    """
    try:
        # Use DuckDuckGo search (no API key required)
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        if not results:
            return f"No web search results found for query: '{query}'"
        
        formatted_results = []
        formatted_results.append(f"Web search results for: '{query}'\n")
        formatted_results.append("=" * 80)
        
        for idx, result in enumerate(results, 1):
            title = result.get('title', f'Result {idx}')
            snippet = result.get('body', 'No description available')
            url = result.get('href', '')
            
            formatted_results.append(f"\n[{idx}] {title}")
            formatted_results.append(f"URL: {url}")
            formatted_results.append(f"Description: {snippet}")
            formatted_results.append("-" * 80)
        
        return "\n".join(formatted_results)
    
    except ImportError:
        return f"Web search tool requires 'duckduckgo-search' package. Install with: pip install duckduckgo-search\nQuery: {query}"
    except Exception as e:
        return f"Error performing web search: {str(e)}"


def create_overall_report_agent():
    """
    Create and configure the LangGraph agent for overall SEC meeting report generation.
    
    Returns:
        Compiled LangGraph graph ready for execution.
    """
    # Initialize LLM
    llm = get_llm(streaming=False)
    
    # Bind tools to the LLM
    tools = [read_meeting_report, find_all_meeting_reports, rag_search, web_search]
    llm_with_tools = llm.bind_tools(tools)
    
    # Create tool node for executing tools
    tool_node = ToolNode(tools)
    
    # Define planner node
    def planner_node(state: OverallReportAgentState):
        """Planner node that creates a plan for analyzing all meeting reports."""
        messages = state["messages"]
        report_files = state.get("report_files", [])
        
        planner_prompt = f"""You are a planning assistant for generating an overall SEC Round Table Meeting report.

                Your task is to create a detailed plan for analyzing multiple SEC meeting reports and generating a comprehensive overall report.

                Number of meeting reports to analyze: {len(report_files)}

                The overall report must include:
                1. Combined views of the same speaker across all meetings
                2. Topic tags for each speaker (topics they're interested in or spoke about)
                3. Overall view of each person on different topics
                4. Identification of the most strongly influenced person across all round table meetings
                5. Future predictions:
                - Decisions on hold or planned for future action
                - Predictions on SEC-Crypto future
                - Future steps/decisions based on strong influencers and their views

                Create a step-by-step plan that:
                - Identifies all meeting reports to read and analyze
                - Determines how to aggregate speaker views across meetings
                - Outlines how to identify topics and tag speakers
                - Plans how to identify the most influential person
                - Determines what additional context might be needed (RAG search, web search)
                - Outlines how to generate future predictions based on influencer views

                Respond with a clear, actionable plan."""
        
        planning_messages = [SystemMessage(content=planner_prompt)] + messages
        response = llm.invoke(planning_messages)
        return {"messages": [response]}
    
    # Define agent node
    def agent_node(state: OverallReportAgentState):
        """Agent node that processes messages and executes the plan."""
        messages = state["messages"]
        
        # Add system message with instructions if this is the first message
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            system_prompt = """You are an expert SEC Round Table Meeting analyst specializing in cross-meeting analysis and future prediction.

                **Your Capabilities:**
                - You can read multiple meeting report files
                - You have access to a RAG tool that searches SEC Crypto knowledge base
                - You have a web search tool to find additional context about trends, future plans, or speaker backgrounds
                - You can analyze and aggregate information across multiple meeting reports

                **Overall Report Requirements:**

                1. **Speaker Aggregation Across Meetings:**
                - Identify all speakers who appeared in multiple meetings
                - Combine their views and opinions across all meetings they participated in
                - Note any evolution or consistency in their positions
                - Track their influence ratings across meetings

                2. **Topic Tagging for Speakers:**
                - For each speaker, identify all topics they discussed or showed interest in
                - Create a comprehensive list of topics (e.g., "DeFi regulation", "Custody", "Tokenization", "Smart contracts", "Intermediaries", etc.)
                - Tag each speaker with their relevant topics
                - Note the depth of their engagement with each topic

                3. **Overall View of Each Person on Different Topics:**
                - For each speaker, provide their overall stance/view on each topic they engaged with
                - Note any nuanced positions or changes over time
                - Highlight areas where speakers have strong, consistent views

                4. **Most Influential Person Identification:**
                - Analyze influence ratings across all meetings
                - Consider both formal authority (Commissioners, Chair) and substantive influence (panelists with strong arguments)
                - Identify the person with the strongest overall influence across all round table meetings
                - Justify the selection with evidence from multiple meetings

                5. **Future Predictions:**
                - **Decisions on Hold or Planned:**
                    * Identify any decisions mentioned as "under consideration", "on hold", or "planned for future"
                    * Note any timelines or conditions mentioned
                    * Identify which meetings discussed these future actions
                
                - **SEC-Crypto Future Predictions:**
                    * Based on patterns across meetings, predict likely future directions
                    * Consider the views of the most influential person(s)
                    * Consider regulatory trends and policy directions indicated
                    * Note any emerging themes or consensus points
                
                - **Future Steps/Decisions Based on Influencers:**
                    * Analyze how the most influential person's views might shape future SEC actions
                    * Predict specific regulatory actions or policy directions
                    * Consider the intersection of influencer views and topic priorities
                    * Note any potential conflicts or alignment with SEC mission

                **Important Guidelines:**
                - Always cite sources (report files, RAG results, web search)
                - Be objective and evidence-based
                - Structure the report clearly with sections and subsections
                - Use specific quotes and examples from meeting reports
                - When making predictions, clearly distinguish between:
                * Explicitly stated future plans
                * Inferred likely actions based on patterns
                * Speculative predictions based on influencer views

                **Report Format:**
                - Use clear headings and sections
                - Include speaker names, affiliations, and meeting participation
                - Provide topic tags as a clear list or table
                - Structure predictions clearly with confidence levels where appropriate
                - List all sources at the end"""
            
            messages = [SystemMessage(content=system_prompt)] + messages
        
        # Get response from LLM
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Define routing logic
    def should_continue(state: OverallReportAgentState):
        """Determine if we should continue or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If the last message has tool calls, continue to tool execution
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        # Otherwise, end
        return END
    
    # Build the graph
    workflow = StateGraph(OverallReportAgentState)
    
    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    # After planner, go to agent
    workflow.add_edge("planner", "agent")
    
    # Add conditional edges from agent
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


def generate_overall_report(
    report_directory: str = ".",
    output_format: str = "txt"
) -> str:
    """
    Generate an overall SEC Round Table Meeting report from all available meeting reports.
    
    Args:
        report_directory: Directory containing meeting report files (default: current directory)
        output_format: Output format - "txt", "docx", or "pdf" (default: "txt")
    
    Returns:
        Path to the generated overall report file
    """
    # Find all meeting reports
    pattern = os.path.join(report_directory, "SEC_Meeting_Report_*.txt")
    report_files = glob.glob(pattern)
    
    if not report_files:
        raise ValueError(f"No meeting report files found in {report_directory}. Pattern: SEC_Meeting_Report_*.txt")
    
    # Sort by modification time (newest first)
    report_files.sort(key=os.path.getmtime, reverse=True)
    
    # Read all report contents
    report_contents = {}
    for file_path in report_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                report_contents[file_path] = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
    
    if not report_contents:
        raise ValueError("No meeting reports could be read successfully.")
    
    # Create agent
    app = create_overall_report_agent()
    
    # Initialize state
    initial_message = f"""Please generate a comprehensive overall SEC Round Table Meeting report that combines insights from all available meeting reports.

            I have found {len(report_files)} meeting report file(s) to analyze:
            {chr(10).join([f"- {os.path.basename(f)}" for f in report_files])}

            Please follow these steps:
            1. First, use find_all_meeting_reports to confirm all available reports
            2. Read all meeting report files using read_meeting_report tool
            3. Analyze and aggregate information across all reports to:
            - Combine views of the same speaker across all meetings
            - Tag speakers with topics they're interested in or spoke about
            - Provide overall view of each person on different topics
            - Identify the most strongly influenced person across all round table meetings
            4. If you need additional context about SEC regulations, trends, or future plans, use rag_search or web_search tools
            5. Generate comprehensive future predictions based on:
            - Decisions mentioned as on hold or planned for future
            - Patterns and trends across meetings
            - Views of the most influential person(s)
            6. Generate a structured overall report with all required sections

            Report Structure Required:
            ==========================================
            SEC ROUND TABLE MEETINGS - OVERALL REPORT
            ==========================================

            1. EXECUTIVE SUMMARY
            - Overview of all meetings analyzed
            - Key themes across meetings
            - Summary of findings

            2. SPEAKER AGGREGATION ACROSS MEETINGS
            For each speaker who appeared in multiple meetings:
            - Name and affiliation
            - Meetings participated in
            - Combined views and opinions across meetings
            - Evolution or consistency in positions
            - Overall influence rating across meetings

            3. TOPIC TAGGING FOR SPEAKERS
            - Comprehensive list of topics discussed
            - For each speaker:
                * Topics they engaged with
                * Depth of engagement with each topic
                * Overall stance on each topic

            4. MOST INFLUENTIAL PERSON ACROSS ALL MEETINGS
            - Identification of the most influential person
            - Justification with evidence from multiple meetings
            - Analysis of their influence across different topics

            5. FUTURE PREDICTIONS
            A. Decisions on Hold or Planned for Future Action
                - List of decisions mentioned as under consideration
                - Timelines or conditions mentioned
                - Meetings where these were discussed
            
            B. SEC-Crypto Future Predictions
                - Likely future directions based on patterns
                - Emerging themes and consensus points
                - Regulatory trends indicated
            
            C. Future Steps/Decisions Based on Influencers
                - How most influential person's views might shape future actions
                - Specific regulatory actions or policy directions predicted
                - Alignment with SEC mission

            6. SOURCES
            - List of all meeting report files analyzed
            - Additional sources from RAG or web search

            Remember:
            - Be thorough and analyze ALL meeting reports
            - Use specific quotes and examples from reports
            - Clearly distinguish between stated plans and predictions
            - Cite all sources properly
            - Structure the report clearly with proper headings"""
    
    initial_state = {
        "messages": [HumanMessage(content=initial_message)],
        "report_files": report_files,
        "report_contents": report_contents,
        "overall_report": "",
        "sources": report_files.copy()
    }
    
    # Run the agent
    final_state = app.invoke(initial_state)
    
    # Extract the final response
    final_messages = final_state["messages"]
    
    # Find the last AI message (the report)
    report_content = ""
    sources = final_state.get("sources", report_files.copy())
    
    # Collect sources from tool calls
    for msg in final_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.get("name") == "read_meeting_report":
                    args = tool_call.get("args", {})
                    if "file_path" in args and args["file_path"] not in sources:
                        sources.append(args["file_path"])
                elif tool_call.get("name") == "rag_search":
                    args = tool_call.get("args", {})
                    if "query" in args:
                        sources.append(f"RAG search: {args['query']}")
                elif tool_call.get("name") == "web_search":
                    args = tool_call.get("args", {})
                    if "query" in args:
                        sources.append(f"Web search: {args['query']}")
    
    # Find the final report content
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage):
            if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                report_content = msg.content
                break
    
    if not report_content:
        report_content = "Error: Could not generate overall report. Please check the agent execution."
    
    # Add sources section if not already present
    if "SOURCES" not in report_content.upper():
        sources_section = "\n\n" + "=" * 80 + "\n"
        sources_section += "SOURCES\n"
        sources_section += "=" * 80 + "\n"
        sources_section += "Meeting Reports Analyzed:\n"
        for idx, source in enumerate(report_files, 1):
            sources_section += f"{idx}. {os.path.basename(source)}\n"
        if len(sources) > len(report_files):
            sources_section += "\nAdditional Sources:\n"
            for idx, source in enumerate(sources[len(report_files):], len(report_files) + 1):
                sources_section += f"{idx}. {source}\n"
        
        report_content += sources_section
    
    # Save report
    output_file = save_overall_report(report_content, output_format)
    
    return output_file


def save_overall_report(content: str, output_format: str = "txt") -> str:
    """
    Save the overall report to a file in the specified format.
    
    Args:
        content: Report content
        output_format: Output format - "txt", "docx", or "pdf"
    
    Returns:
        Path to the saved file
    """
    if output_format.lower() == "txt":
        filename = "SEC_Overall_Report_All_Meetings.txt"
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    elif output_format.lower() == "docx":
        try:
            from docx import Document
            filename = "SEC_Overall_Report_All_Meetings.docx"
            filepath = os.path.join(os.getcwd(), filename)
            
            doc = Document()
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    doc.add_paragraph(para.strip())
            
            doc.save(filepath)
            return filepath
        except ImportError:
            print("Warning: python-docx not installed. Saving as .txt instead.")
            return save_overall_report(content, "txt")
    
    elif output_format.lower() == "pdf":
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            
            filename = "SEC_Overall_Report_All_Meetings.pdf"
            filepath = os.path.join(os.getcwd(), filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    if para.startswith('=') or (len(para) < 100 and para.isupper()):
                        story.append(Paragraph(para.strip(), styles['Heading1']))
                    else:
                        story.append(Paragraph(para.strip(), styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))
            
            doc.build(story)
            return filepath
        except ImportError:
            print("Warning: reportlab not installed. Saving as .txt instead.")
            return save_overall_report(content, "txt")
    
    else:
        return save_overall_report(content, "txt")


if __name__ == "__main__":
    # Example usage
    print("SEC Round Table Meetings - Overall Report Agent")
    print("=" * 80)
    
    print("\nGenerating overall report from all meeting reports...")
    print("(This may take several minutes as the agent analyzes all reports)")
    print("-" * 80)
    
    try:
        output_file = generate_overall_report(
            report_directory=".",
            output_format="txt"
        )
        
        print(f"\n✓ Overall report generated successfully!")
        print(f"✓ Output file: {output_file}")
        print(f"\nYou can now view the report at: {os.path.abspath(output_file)}")
        
    except Exception as e:
        print(f"\n✗ Error generating overall report: {str(e)}")
        import traceback
        traceback.print_exc()
