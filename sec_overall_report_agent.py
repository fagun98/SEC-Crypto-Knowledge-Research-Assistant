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
        # Resolve directory relative to this file so it works regardless of CWD
        base_dir = os.path.dirname(os.path.abspath(__file__))
        search_dir = os.path.join(base_dir, directory)

        # Search for SEC meeting report files
        pattern = os.path.join(search_dir, "SEC_Meeting_Report_*.txt")
        report_files = glob.glob(pattern)
        
        print(f"Found {len(report_files)} meeting report file(s) in {search_dir}")
        
        if not report_files:
            return f"No meeting report files found in {search_dir}. Pattern used: SEC_Meeting_Report_*.txt"
        
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
        
        planner_prompt = f"""You are a planning assistant for generating a professional regulatory intelligence report from SEC Round Table Meeting reports.

                Your task is to create a detailed plan for analyzing multiple SEC meeting reports and generating a comprehensive regulatory intelligence report suitable for client briefings and compliance memos.

                Number of meeting reports to analyze: {len(report_files)}

                The report must follow this exact structure (in Markdown format):
                1. Executive Intelligence Brief (1 page) - 5-7 key takeaways, top 3 regulatory trajectories, most influential stakeholders
                2. Methodology Note - analysis approach, data sources, confidence scoring
                3. Cross-Meeting Evidence Summary - Topic × Meeting frequency table, Speaker × Topic matrix, recurring themes (≥3 meetings) vs isolated mentions
                4. Speaker Analysis - Clear separation of Authority vs Influence vs Policy Impact Likelihood, evidence-based indicators
                5. Topic Tagging - Comprehensive taxonomy, Speaker × Topic matrix in table format
                6. Most Influential Stakeholder - Evidence-based identification with explicit signals (repetition, alignment, directives)
                7. "What This Means For..." - Implications for Issuers, DeFi Protocols, Exchanges/ATSs, Custodians/Compliance Teams
                8. Unresolved Questions & Regulatory Gaps (NEW MANDATORY) - Doctrinal/Legal, Operational/Compliance, Market Structure, Inter-agency/Legislative gaps
                9. Future Predictions - All labeled as [EXPLICITLY STATED] / [STRONGLY INFERRED] / [SPECULATIVE], with confidence levels, plus "What Could Change These Predictions"
                10. Sources - All citations
                
                The entire report must be generated in clean, professional Markdown format suitable for GitHub/MkDocs rendering.

                Create a step-by-step plan that:
                - Identifies all meeting reports to read and analyze
                - Plans how to create tables and matrices (Topic × Meeting, Speaker × Topic)
                - Determines how to separate Authority from Influence from Policy Impact Likelihood
                - Outlines how to identify explicit signals (repetition across meetings, alignment with SEC actions, staff directives)
                - Plans how to label predictions with appropriate confidence levels
                - Determines what additional context might be needed (RAG search for SEC guidance, web search for trends)
                - Outlines how to structure the Executive Intelligence Brief for executives
                - Plans stakeholder-specific implications sections

                Focus on evidence-based analysis, not narrative summaries. Plan for tables and structured data over long paragraphs.

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
            system_prompt = """You are a **Regulatory Intelligence Analyst** generating an **SEC Crypto Roundtable Regulatory Intelligence Report** for institutional clients. Your role is to produce professional, evidence-based intelligence reports suitable for client briefings, compliance memos, and internal policy analysis.

                **CRITICAL OUTPUT REQUIREMENT:**
                - Generate the ENTIRE report using clean, professional Markdown format
                - Use hierarchical headings (#, ##, ###)
                - Use bullet lists for insights and implications
                - Use tables for Topic × Meeting frequency, Speaker × Topic engagement, Influence tiers
                - Use blockquotes (>) for direct quotations
                - Clearly distinguish sections as **FACTS**, **ANALYSIS**, or **INFERENCE**
                - The Markdown must be suitable for GitHub/MkDocs rendering, internal research repositories, and client-facing document export

                **Your Capabilities:**
                - You can read multiple meeting report files
                - You have access to a RAG tool that searches SEC Crypto knowledge base
                - You have a web search tool to find additional context about trends, future plans, or speaker backgrounds
                - You can analyze and aggregate information across multiple meeting reports

                **Tone & Style:**
                - Write as a regulatory intelligence analyst, NOT a meeting summarizer
                - Maintain SEC-neutral, non-advocacy tone
                - Use professional, executive-level language
                - Make the report skimmable for busy executives
                - Favor tables, bullet points, and structured data over long narrative blocks

                **Overall Report Structure (MUST FOLLOW THIS EXACT ORDER):**

                1. **EXECUTIVE INTELLIGENCE BRIEF (1 page maximum)**
                   - 5-7 key takeaways (bullet points)
                   - Top 3 regulatory trajectories with confidence levels (High/Medium/Low)
                   - Most influential stakeholders with supporting evidence (1-2 sentences each)
                   - This section should be immediately actionable for executives

                2. **METHODOLOGY NOTE**
                   - Brief explanation of analysis approach
                   - Number of meetings analyzed
                   - Data sources used
                   - Confidence scoring methodology

                3. **CROSS-MEETING EVIDENCE SUMMARY**
                   - Topic × Meeting frequency table (showing which topics appeared in which meetings)
                   - Speaker × Topic engagement matrix (table format)
                   - Identification of:
                     * Ideas appearing in ≥3 meetings (recurring themes)
                     * Single-meeting mentions (isolated ideas)
                   - Use tables, not narrative paragraphs

                4. **SPEAKER ANALYSIS WITH CLEAR INFLUENCE SEPARATION**
                   For each key speaker:
                   - **Authority**: Formal role (Chair, Commissioner, Panelist, etc.)
                   - **Influence**: Evidence-based indicators:
                     * Repetition across meetings (how many times they spoke on topic)
                     * Alignment with prior SEC actions or guidance
                     * Explicit staff directives or follow-up requests
                     * Agenda-setting power
                   - **Likelihood of Policy Impact**: High/Medium/Low with justification
                   - Meetings participated in
                   - Combined views and opinions across meetings
                   - Evolution or consistency in positions
                   - Use structured format, not long narratives

                5. **TOPIC TAGGING FOR SPEAKERS**
                   - Comprehensive list of topics (taxonomy early in report)
                   - For each speaker (table format preferred):
                     * Topics they engaged with
                     * Depth of engagement (High/Medium/Low)
                     * Overall stance on each topic (Support/Oppose/Neutral/Mixed)
                     * Number of meetings where topic was discussed
                   - Speaker × Topic matrix as a table

                6. **MOST INFLUENTIAL STAKEHOLDER IDENTIFICATION**
                   - Clear identification with evidence-based justification
                   - Separate analysis of:
                     * Formal authority (role-based)
                     * Substantive influence (agenda-setting, repetition, adoption)
                     * Policy impact likelihood
                   - Evidence from multiple meetings
                   - Explicit signals used (repetition, alignment, directives)

                7. **"WHAT THIS MEANS FOR..." SECTION**
                   Cover implications for each stakeholder group:
                   - **Issuers**: What they need to know/prepare for
                   - **DeFi Protocols**: Regulatory considerations
                   - **Exchanges / ATSs**: Compliance implications
                   - **Custodians / Compliance Teams**: Operational impacts
                   - Use bullet points and clear action items

                8. **UNRESOLVED QUESTIONS & REGULATORY GAPS** (NEW MANDATORY SECTION)
                   This section must explicitly identify open regulatory questions that the SEC has not yet resolved.
                   
                   Structure by subcategories:
                   - **Doctrinal / Legal Uncertainty**: Questions about legal definitions, jurisdiction, applicability of existing laws
                   - **Operational / Compliance Ambiguity**: Questions about how to comply, what standards apply, implementation details
                   - **Market Structure & Infrastructure Gaps**: Questions about market structure, infrastructure needs, technical requirements
                   - **Inter-agency / Legislative Gaps**: Questions requiring coordination with other agencies or legislative action
                   
                   For EACH identified gap, include:
                   - **Why it matters**: Business/regulatory impact
                   - **Which meetings raised it**: Date and/or topic (cross-meeting evidence)
                   - **Who raised it**: Commissioner, SEC staff, industry participant, academic
                   - **Potential paths to resolution**: Guidance, pilot programs, rulemaking, legislation
                   
                   - Ground in cross-meeting evidence OR clearly label as inference where applicable
                   - Avoid speculation unless explicitly labeled as such
                   - Use Markdown formatting: tables, bullet lists, blockquotes for quotes

                9. **FUTURE PREDICTIONS (WITH CLEAR LABELING)**
                   A. **Decisions on Hold or Planned for Future Action**
                      - List with explicit labeling:
                        * [EXPLICITLY STATED] - Direct quotes from meetings
                        * [STRONGLY INFERRED] - Based on patterns/evidence
                        * [SPECULATIVE] - Based on influencer views
                      - Timelines or conditions mentioned
                      - Meetings where discussed
                      - Confidence levels (High/Medium/Low)
                   
                   B. **SEC-Crypto Future Predictions**
                      - Label each prediction: [EXPLICITLY STATED] / [STRONGLY INFERRED] / [SPECULATIVE]
                      - Use probability ranges or conditional phrasing (avoid overly precise timelines)
                      - Based on patterns across meetings
                      - Consider views of most influential person(s)
                      - Regulatory trends and policy directions
                      - Emerging themes and consensus points
                   
                   C. **Future Steps/Decisions Based on Influencers**
                      - Label each: [EXPLICITLY STATED] / [STRONGLY INFERRED] / [SPECULATIVE]
                      - How most influential person's views might shape future actions
                      - Specific regulatory actions or policy directions predicted
                      - Alignment with SEC mission
                   
                   D. **What Could Change These Predictions**
                      - Litigation outcomes
                      - Elections
                      - Inter-agency conflicts
                      - Other external factors

                10. **SOURCES**
                    - List of all meeting report files analyzed
                    - Additional sources from RAG or web search
                    - Clear citations throughout the report

                **Critical Guidelines:**
                - ALWAYS cite sources (report files, RAG results, web search)
                - Be objective and evidence-based - flag claims based on inference without supporting evidence
                - Clearly distinguish between SEC staff authority and Commissioner authority
                - Reduce narrative influence language - replace with structured, evidence-based indicators
                - Use Markdown tables and matrices for cross-meeting analysis (proper Markdown table syntax)
                - Make predictions skimmable with clear labels
                - Ensure report is suitable for client briefings and compliance memos
                - Maintain visual hierarchy with clear section headers (Markdown headings)
                - Distinguish between Facts, Analysis, and Inference in section headers where appropriate
                - Use Markdown blockquotes (>) for all direct quotations
                - Format all tables using proper Markdown table syntax with pipes (|)
                - Ensure the entire report is valid Markdown that can be rendered on GitHub/MkDocs"""
            
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
    output_format: str = "md"
) -> str:
    """
    Generate an overall SEC Round Table Meeting report from all available meeting reports.
    
    Args:
        report_directory: Directory containing meeting report files (default: current directory)
        output_format: Output format - "txt", "docx", or "pdf" (default: "txt")
    
    Returns:
        Path to the generated overall report file
    """
    # Resolve report_directory relative to this file so it works regardless of CWD
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, report_directory)

    # Find all meeting reports
    pattern = os.path.join(input_dir, "SEC_Meeting_Report_*.txt")
    report_files = glob.glob(pattern)
    
    if not report_files:
        raise ValueError(f"No meeting report files found in {input_dir}. Pattern: SEC_Meeting_Report_*.txt")
    
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

            Report Structure Required (MUST FOLLOW THIS EXACT ORDER):
            ==========================================
            SEC ROUND TABLE MEETINGS - REGULATORY INTELLIGENCE REPORT
            ==========================================

            1. EXECUTIVE INTELLIGENCE BRIEF (1 page maximum)
               - 5-7 key takeaways (bullet points)
               - Top 3 regulatory trajectories with confidence levels (High/Medium/Low)
               - Most influential stakeholders with supporting evidence (1-2 sentences each)

            2. METHODOLOGY NOTE
               - Brief explanation of analysis approach
               - Number of meetings analyzed
               - Data sources used
               - Confidence scoring methodology

            3. CROSS-MEETING EVIDENCE SUMMARY
               - Topic × Meeting frequency table (table format)
               - Speaker × Topic engagement matrix (table format)
               - Ideas appearing in ≥3 meetings (recurring themes)
               - Single-meeting mentions (isolated ideas)

            4. SPEAKER ANALYSIS WITH CLEAR INFLUENCE SEPARATION
               For each key speaker:
               - Authority: Formal role
               - Influence: Evidence-based indicators (repetition, alignment, directives)
               - Likelihood of Policy Impact: High/Medium/Low with justification
               - Meetings participated in
               - Combined views across meetings
               - Evolution or consistency in positions

            5. TOPIC TAGGING FOR SPEAKERS
               - Comprehensive topic taxonomy (list early)
               - Speaker × Topic matrix (table format)
               - For each speaker: Topics, Depth of engagement, Overall stance

            6. MOST INFLUENTIAL STAKEHOLDER IDENTIFICATION
               - Clear identification with evidence-based justification
               - Separate: Formal authority vs. Substantive influence vs. Policy impact likelihood
               - Explicit signals used (repetition, alignment, directives)

            7. "WHAT THIS MEANS FOR..." SECTION
               Cover implications for:
               - Issuers
               - DeFi Protocols
               - Exchanges / ATSs
               - Custodians / Compliance Teams
               Use bullet points and clear action items

            8. UNRESOLVED QUESTIONS & REGULATORY GAPS (NEW MANDATORY SECTION)
               Structure by subcategories:
               - Doctrinal / Legal Uncertainty
               - Operational / Compliance Ambiguity
               - Market Structure & Infrastructure Gaps
               - Inter-agency / Legislative Gaps
               
               For EACH gap, include:
               - Why it matters
               - Which meetings raised it (date/topic)
               - Who raised it (Commissioner, staff, industry, academic)
               - Potential paths to resolution (guidance, pilot, rulemaking, legislation)
               - Ground in cross-meeting evidence OR label as inference
               - Use Markdown formatting (tables, bullets, blockquotes)

            9. FUTURE PREDICTIONS (WITH CLEAR LABELING)
               A. Decisions on Hold or Planned
                  - Label each: [EXPLICITLY STATED] / [STRONGLY INFERRED] / [SPECULATIVE]
                  - Confidence levels (High/Medium/Low)
                  - Timelines or conditions
                  - Meetings where discussed
               
               B. SEC-Crypto Future Predictions
                  - Label each: [EXPLICITLY STATED] / [STRONGLY INFERRED] / [SPECULATIVE]
                  - Use probability ranges (avoid overly precise timelines)
                  - Based on patterns, influencer views, regulatory trends
               
               C. Future Steps/Decisions Based on Influencers
                  - Label each: [EXPLICITLY STATED] / [STRONGLY INFERRED] / [SPECULATIVE]
                  - How influencer views might shape actions
               
               D. What Could Change These Predictions
                  - Litigation outcomes
                  - Elections
                  - Inter-agency conflicts
                  - Other external factors

            10. SOURCES
               - List of all meeting report files analyzed
               - Additional sources from RAG or web search

            Critical Requirements:
            - Write as a regulatory intelligence analyst, NOT a meeting summarizer
            - Maintain SEC-neutral, non-advocacy tone
            - Generate ENTIRE report in clean, professional Markdown format
            - Use Markdown tables (proper syntax with pipes |) for cross-meeting analysis
            - Use Markdown blockquotes (>) for all direct quotations
            - Use hierarchical Markdown headings (#, ##, ###)
            - Make report skimmable for executives
            - Clearly label all predictions: [EXPLICITLY STATED] / [STRONGLY INFERRED] / [SPECULATIVE]
            - Separate Authority vs. Influence vs. Policy Impact Likelihood
            - Use evidence-based indicators, not narrative influence language
            - Flag claims based on inference without supporting evidence
            - Distinguish between SEC staff authority and Commissioner authority
            - Ensure report is suitable for GitHub/MkDocs rendering, research repositories, client export
            - Use clear visual hierarchy with Markdown section headers
            - Distinguish Facts, Analysis, and Inference where appropriate
            - Include the new mandatory section: Unresolved Questions & Regulatory Gaps"""
    
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
    
    # Ensure content starts with proper Markdown title if not already present
    if not report_content.strip().startswith('#'):
        # Add title if missing
        title = "# SEC Crypto Roundtables Regulatory Intelligence Report\n\n"
        report_content = title + report_content
    
    # Save report
    output_file = save_overall_report(report_content, output_format)
    
    return output_file


def save_overall_report(content: str, output_format: str = "md") -> str:
    """
    Save the overall report to a file in the specified format.
    
    Args:
        content: Report content (should be in Markdown format)
        output_format: Output format - "md" (default), "txt", "docx", or "pdf"
    
    Returns:
        Path to the saved file
    """
    if output_format.lower() == "md" or output_format.lower() == "markdown":
        # Use the exact filename specified
        filename = "SEC_Overall_Report_All_Meetings.md"
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    elif output_format.lower() == "txt":
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
            output_format="md"
        )
        
        print(f"\n✓ Overall report generated successfully!")
        print(f"✓ Output file: {output_file}")
        print(f"\nYou can now view the report at: {os.path.abspath(output_file)}")
        
    except Exception as e:
        print(f"\n✗ Error generating overall report: {str(e)}")
        import traceback
        traceback.print_exc()
