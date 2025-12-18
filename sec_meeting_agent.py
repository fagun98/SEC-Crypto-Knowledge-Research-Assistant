"""
SEC Round Table Meeting Report Agent

This module implements a LangGraph agent to generate detailed SEC Round Table Meeting reports.
The agent analyzes meeting transcripts and URLs to produce structured reports with:
- Key speakers and their influence ratings
- Views on topics discussed
- Meeting conclusions
- Key points and main arguments/events
"""

from typing import Annotated, List, Dict, Any, Optional, TypedDict
import operator
import os
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
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
class MeetingAgentState(TypedDict):
    """State of the meeting report agent."""
    messages: Annotated[List[BaseMessage], operator.add]
    meeting_url: str
    transcript_file: str
    transcript_content: str
    url_content: str
    report_content: str
    sources: List[str]


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
    that might be relevant to the meeting discussion.
    
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
def parse_url(url: str) -> str:
    """
    Parse and extract content from a SEC meeting URL.
    
    This tool fetches the webpage content from the provided URL and extracts
    relevant information about the meeting, including title, description, participants, etc.
    
    Args:
        url: The URL of the SEC meeting page to parse
    
    Returns:
        Extracted content from the URL including title, description, and any relevant metadata.
    """
    try:
        headers = {
            "User-Agent": "NumInformaticsBot/1.0 (+https://numinformatics.com; contact: fraithatha@numinformatics.com)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.sec.gov/about/crypto-task-force",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else "No title found"
        
        # Extract main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main_content:
            content_text = main_content.get_text(separator='\n', strip=True)
        else:
            # Fallback: get all paragraph text
            paragraphs = soup.find_all('p')
            content_text = '\n'.join([p.get_text(strip=True) for p in paragraphs])
        
        # Extract metadata
        metadata = []
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata.append(f"{name}: {content}")
        
        result = f"URL: {url}\n"
        result += f"Title: {title_text}\n"
        result += "=" * 80 + "\n"
        result += "Content:\n" + content_text[:5000]  # Limit content length
        if metadata:
            result += "\n\nMetadata:\n" + "\n".join(metadata[:10])
        
        return result
    
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL {url}: {str(e)}"
    except Exception as e:
        return f"Error parsing URL {url}: {str(e)}"


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for additional information about SEC meetings, speakers, or topics.
    
    This tool uses DuckDuckGo search to find current information that might not be
    in the knowledge base or transcript.
    
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
        # Fallback: return message about installing duckduckgo-search
        return f"Web search tool requires 'duckduckgo-search' package. Install with: pip install duckduckgo-search\nQuery: {query}"
    except Exception as e:
        return f"Error performing web search: {str(e)}"


def read_transcript_file(file_path: str) -> str:
    """Read transcript content from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading transcript file: {str(e)}"


def create_meeting_report_agent():
    """
    Create and configure the LangGraph agent for SEC meeting report generation.
    
    Returns:
        Compiled LangGraph graph ready for execution.
    """
    # Initialize LLM
    llm = get_llm(streaming=False)
    
    # Bind tools to the LLM
    tools = [rag_search, parse_url, web_search]
    llm_with_tools = llm.bind_tools(tools)
    
    # Create tool node for executing tools
    tool_node = ToolNode(tools)
    
    # Define planner node
    def planner_node(state: MeetingAgentState):
        """Planner node that creates a plan for analyzing the meeting."""
        messages = state["messages"]
        transcript_content = state.get("transcript_content", "")
        meeting_url = state.get("meeting_url", "")
        
        planner_prompt = f"""You are a planning assistant for SEC Round Table Meeting analysis.

            Your task is to create a detailed plan for analyzing a SEC meeting transcript and generating a comprehensive report.

            Meeting URL: {meeting_url}
            Transcript length: {len(transcript_content)} characters

            The report must include:
            1. List all key speakers and rate them on:
            - Most influential speaker
            - How active they were in the meeting
            - How strong their arguments were
            2. Views on topics discussed during the meeting
            3. Conclusion of the meeting
            4. Key points and main arguments/events

            Create a step-by-step plan that:
            - Identifies what information needs to be extracted from the transcript
            - Determines what additional context might be needed (from RAG search or web search)
            - Outlines how to structure the final report

            Respond with a clear, actionable plan."""
        
        planning_messages = [SystemMessage(content=planner_prompt)] + messages
        response = llm.invoke(planning_messages)
        return {"messages": [response]}
    
    # Define agent node
    def agent_node(state: MeetingAgentState):
        """Agent node that processes messages and executes the plan."""
        messages = state["messages"]
        transcript_content = state.get("transcript_content", "")
        meeting_url = state.get("meeting_url", "")
        
        # Add system message with instructions if this is the first message
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            system_prompt = """You are an expert SEC Round Table Meeting analyst. Your role is to analyze meeting transcripts and generate detailed, structured reports.

            **Your Capabilities:**
            - You have access to a RAG tool that searches SEC Crypto knowledge base
            - You have a URL parser tool to extract information from SEC meeting pages
            - You have a web search tool to find additional context about speakers, topics, or events
            - You can analyze meeting transcripts to extract key information

            **Report Requirements:**
            1. **Key Speakers Analysis:**
            - List all key speakers who participated significantly
            - Rate each speaker on:
                * Influence: How influential were their contributions? (1-10 scale)
                * Activity: How active were they? (number of contributions, speaking time)
                * Strength: How strong were their arguments? (1-10 scale)
            - Identify the most influential speaker overall

            2. **Views on Topics:**
            - Identify main topics discussed
            - Summarize different viewpoints expressed
            - Note any consensus or disagreements

            3. **Meeting Conclusion:**
            - What was the overall conclusion or outcome?
            - Were there any action items or next steps mentioned?

            4. **Key Points and Main Arguments/Events:**
            - List the most important points made
            - Highlight main arguments presented
            - Note any significant events or moments

            **Important Guidelines:**
            - Always cite sources (transcript, URL, RAG results, web search)
            - Be objective and factual
            - Structure the report clearly with sections and subsections
            - Use specific quotes from the transcript when relevant
            - If you need additional context, use the appropriate tools

            **Report Format:**
            - Use clear headings and sections
            - Include speaker names, titles, and affiliations when available
            - Provide ratings with brief justifications
            - List sources at the end"""
            
            messages = [SystemMessage(content=system_prompt)] + messages
        
        # Add transcript context to messages if not already present
        transcript_context_added = any("FULL TRANSCRIPT" in str(msg.content) for msg in messages)
        if transcript_content and not transcript_context_added:
            # Add transcript as context message
            transcript_msg = f"""FULL TRANSCRIPT CONTENT (for your analysis):
            
            {transcript_content}

            Meeting URL: {meeting_url}

            Please analyze this complete transcript thoroughly."""
            messages.append(HumanMessage(content=transcript_msg))
        
        # Get response from LLM
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Define routing logic
    def should_continue(state: MeetingAgentState):
        """Determine if we should continue or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If the last message has tool calls, continue to tool execution
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        # Otherwise, end
        return END
    
    # Build the graph
    workflow = StateGraph(MeetingAgentState)
    
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


def generate_meeting_report(
    meeting_url: str,
    transcript_file: str,
    output_format: str = "txt"
) -> str:
    """
    Generate a detailed SEC Round Table Meeting report.
    
    Args:
        meeting_url: URL of the SEC meeting page
        transcript_file: Path to the transcript file
        output_format: Output format - "txt", "docx", or "pdf" (default: "txt")
    
    Returns:
        Path to the generated report file
    """
    # Read transcript
    transcript_content = read_transcript_file(transcript_file)
    
    # Create agent
    app = create_meeting_report_agent()
    
    # Initialize state with full transcript
    initial_message = f"""Please analyze this SEC Round Table Meeting and generate a comprehensive report.

                    Meeting URL: {meeting_url}
                    Transcript File: {transcript_file}

                    The full transcript has been loaded ({len(transcript_content)} characters). You have access to the complete transcript content in the state.

                    Please follow these steps:
                    1. First, parse the meeting URL using the parse_url tool to get context about the meeting (title, description, participants, etc.)
                    2. Analyze the FULL transcript to identify:
                    - All key speakers and their contributions
                    - Main topics discussed
                    - Different viewpoints expressed
                    - Meeting conclusions and outcomes
                    - Key arguments and events
                    3. If you need additional context about SEC regulations, policies, or historical context, use the rag_search tool
                    4. If you need information about speakers, their backgrounds, or related events, use the web_search tool
                    5. Generate a comprehensive, structured report with all required sections

                    Report Structure Required:
                    ==========================================
                    SEC ROUND TABLE MEETING REPORT
                    ==========================================

                    1. EXECUTIVE SUMMARY
                    - Brief overview of the meeting

                    2. KEY SPEAKERS ANALYSIS
                    For each key speaker:
                    - Name and affiliation
                    - Influence Rating (1-10): [rating] - [justification]
                    - Activity Level: [description of participation]
                    - Argument Strength (1-10): [rating] - [justification]
                    - Key Contributions: [summary]
                    
                    Most Influential Speaker: [name] - [reasoning]

                    3. VIEWS ON TOPICS
                    For each main topic:
                    - Topic: [topic name]
                    - Viewpoints: [different perspectives expressed]
                    - Consensus/Disagreements: [summary]

                    4. MEETING CONCLUSION
                    - Overall outcome
                    - Action items or next steps
                    - Key takeaways

                    5. KEY POINTS AND MAIN ARGUMENTS/EVENTS
                    - [List of key points]
                    - [Main arguments presented]
                    - [Significant events or moments]

                    6. SOURCES
                    - Meeting URL: {meeting_url}
                    - Transcript File: {transcript_file}
                    - [Any additional sources from RAG or web search]

                    Remember:
                    - Be thorough and analyze the ENTIRE transcript
                    - Use specific quotes and examples from the transcript
                    - Rate speakers objectively based on their actual contributions
                    - Cite all sources properly
                    - Structure the report clearly with proper headings"""
    
    initial_state = {
        "messages": [HumanMessage(content=initial_message)],
        "meeting_url": meeting_url,
        "transcript_file": transcript_file,
        "transcript_content": transcript_content,
        "url_content": "",
        "report_content": "",
        "sources": [meeting_url, transcript_file]
    }
    
    # Run the agent
    final_state = app.invoke(initial_state)
    
    # Extract the final response and collect sources
    final_messages = final_state["messages"]
    
    # Find the last AI message (the report)
    report_content = ""
    sources = final_state.get("sources", [meeting_url, transcript_file])
    
    # Collect sources from tool calls
    for msg in final_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.get("name") == "parse_url":
                    # Extract URL from tool call
                    args = tool_call.get("args", {})
                    if "url" in args:
                        if args["url"] not in sources:
                            sources.append(args["url"])
                elif tool_call.get("name") == "web_search":
                    # Add web search query as source
                    args = tool_call.get("args", {})
                    if "query" in args:
                        sources.append(f"Web search: {args['query']}")
                elif tool_call.get("name") == "rag_search":
                    # Add RAG search query as source
                    args = tool_call.get("args", {})
                    if "query" in args:
                        sources.append(f"RAG search: {args['query']}")
    
    # Find the final report content
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage):
            if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                report_content = msg.content
                break
    
    if not report_content:
        report_content = "Error: Could not generate report. Please check the agent execution."
    
    # Add sources section if not already present
    if "SOURCES" not in report_content.upper():
        sources_section = "\n\n" + "=" * 80 + "\n"
        sources_section += "SOURCES\n"
        sources_section += "=" * 80 + "\n"
        for idx, source in enumerate(sources, 1):
            sources_section += f"{idx}. {source}\n"
        
        report_content += sources_section
    
    # Save report
    output_file = save_report(report_content, meeting_url, output_format)
    
    return output_file


def save_report(content: str, meeting_url: str, output_format: str = "txt") -> str:
    """
    Save the report to a file in the specified format.
    
    Args:
        content: Report content
        meeting_url: Meeting URL (used for filename)
        output_format: Output format - "txt", "docx", or "pdf"
    
    Returns:
        Path to the saved file
    """
    # Extract meeting identifier from URL
    url_path = urlparse(meeting_url).path
    meeting_id = url_path.split('/')[-1] if url_path else "meeting"
    safe_meeting_id = "".join(c for c in meeting_id if c.isalnum() or c in ('-', '_'))[:50]
    
    if output_format.lower() == "txt":
        filename = f"SEC_Meeting_Report_{safe_meeting_id}.txt"
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    elif output_format.lower() == "docx":
        try:
            from docx import Document
            filename = f"SEC_Meeting_Report_{safe_meeting_id}.docx"
            filepath = os.path.join(os.getcwd(), filename)
            
            doc = Document()
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    doc.add_paragraph(para.strip())
            
            doc.save(filepath)
            return filepath
        except ImportError:
            # Fallback to txt if python-docx not available
            print("Warning: python-docx not installed. Saving as .txt instead.")
            return save_report(content, meeting_url, "txt")
    
    elif output_format.lower() == "pdf":
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            
            filename = f"SEC_Meeting_Report_{safe_meeting_id}.pdf"
            filepath = os.path.join(os.getcwd(), filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    # Check if it's a heading
                    if para.startswith('=') or (len(para) < 100 and para.isupper()):
                        story.append(Paragraph(para.strip(), styles['Heading1']))
                    else:
                        story.append(Paragraph(para.strip(), styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))
            
            doc.build(story)
            return filepath
        except ImportError:
            # Fallback to txt if reportlab not available
            print("Warning: reportlab not installed. Saving as .txt instead.")
            return save_report(content, meeting_url, "txt")
    
    else:
        # Default to txt
        return save_report(content, meeting_url, "txt")


if __name__ == "__main__":
    # Example usage
    print("SEC Round Table Meeting Report Agent")
    print("=" * 80)
    
    # Test with provided URL and transcript
    test_url = "https://www.sec.gov/newsroom/meetings-events/defi-american-spirit"
    test_transcript = "june_9_2025.txt"
    
    print(f"\nGenerating report for meeting: {test_url}")
    print(f"Transcript file: {test_transcript}")
    print("\nProcessing...")
    
    output_file = generate_meeting_report(
        meeting_url=test_url,
        transcript_file=test_transcript,
        output_format="txt"
    )
    
    print(f"\nReport generated successfully!")
    print(f"Output file: {output_file}")
