# SEC Round Table Meetings - Overall Report Agent

This agent generates a comprehensive overall report that combines insights from all SEC Round Table Meeting reports.

## Overview

The overall report agent analyzes multiple individual meeting reports to:
- Combine views of the same speaker across all meetings
- Tag speakers with topics they're interested in or spoke about
- Identify the most influential person across all round table meetings
- Predict future SEC actions and decisions based on influencer views

## Architecture

Similar to the individual meeting report agent, this uses a LangGraph architecture with:

1. **Planner Node**: Creates a plan for analyzing all meeting reports
2. **Agent Node**: Executes the plan using available tools
3. **Tools**:
   - **Report Reader Tool**: Reads individual meeting report files
   - **Report Finder Tool**: Finds all available meeting report files
   - **RAG Tool**: Searches SEC Crypto knowledge base for context
   - **Web Search Tool**: Finds additional information about trends or future plans

## Features

The generated overall report includes:

1. **Executive Summary**
   - Overview of all meetings analyzed
   - Key themes across meetings
   - Summary of findings

2. **Speaker Aggregation Across Meetings**
   - For each speaker who appeared in multiple meetings:
     * Combined views and opinions across meetings
     * Evolution or consistency in positions
     * Overall influence rating across meetings

3. **Topic Tagging for Speakers**
   - Comprehensive list of topics discussed
   - For each speaker:
     * Topics they engaged with
     * Depth of engagement with each topic
     * Overall stance on each topic

4. **Most Influential Person Identification**
   - Identification of the most influential person across all meetings
   - Justification with evidence from multiple meetings
   - Analysis of their influence across different topics

5. **Future Predictions**
   - **Decisions on Hold or Planned**: List of decisions mentioned as under consideration
   - **SEC-Crypto Future Predictions**: Likely future directions based on patterns
   - **Future Steps Based on Influencers**: How most influential person's views might shape future actions

6. **Sources**
   - List of all meeting report files analyzed
   - Additional sources from RAG or web search

## Usage

### Basic Usage

```python
from sec_overall_report_agent import generate_overall_report

# Generate overall report from all meeting reports in current directory
output_file = generate_overall_report(
    report_directory=".",  # Directory containing SEC_Meeting_Report_*.txt files
    output_format="txt"    # Options: "txt", "docx", or "pdf"
)

print(f"Report saved to: {output_file}")
```

### Running the Test Script

```bash
python test_overall_agent.py
```

### Command Line Usage

```bash
python sec_overall_report_agent.py
```

## Prerequisites

Before using this agent, you need to have generated individual meeting reports using `sec_meeting_agent.py`. The overall report agent looks for files matching the pattern:
- `SEC_Meeting_Report_*.txt`

## Output Formats

The agent supports three output formats:

- **txt**: Plain text file (default, always available)
- **docx**: Microsoft Word document (requires `python-docx`)
- **pdf**: PDF document (requires `reportlab`)

## How It Works

1. **Discovery**: Finds all meeting report files in the specified directory
2. **Reading**: Reads all meeting report files
3. **Analysis**: The agent:
   - Identifies speakers across all meetings
   - Aggregates their views and opinions
   - Tags speakers with topics
   - Identifies the most influential person
   - Analyzes patterns and trends
4. **Prediction**: Generates future predictions based on:
   - Explicitly stated future plans
   - Patterns across meetings
   - Views of the most influential person(s)
5. **Output**: Saves the comprehensive overall report

## Example Workflow

```
1. Generate individual meeting reports:
   python test_sec_agent.py  # (run for each meeting)

2. Generate overall report:
   python test_overall_agent.py

3. Review the overall report:
   SEC_Overall_Report_All_Meetings.txt
```

## Key Differences from Individual Report Agent

| Feature | Individual Report Agent | Overall Report Agent |
|---------|------------------------|---------------------|
| Input | URL + Transcript file | Multiple report files |
| Focus | Single meeting analysis | Cross-meeting analysis |
| Speaker Analysis | Per meeting | Aggregated across meetings |
| Topic Tagging | Per meeting | Across all meetings |
| Future Prediction | Limited to one meeting | Based on all meetings + influencers |
| Output | Per meeting report | Overall comprehensive report |

## Notes

- The agent analyzes all available meeting reports automatically
- Processing time increases with the number of reports
- All sources are cited at the end of the report
- Predictions are clearly labeled as stated plans vs. inferred predictions
- The agent uses OpenAI's GPT models, so API costs apply

## Dependencies

Same as the individual meeting report agent:
- `langchain-core`
- `langchain-openai`
- `langgraph`
- `duckduckgo-search`
- `python-docx` (for docx output)
- `reportlab` (for pdf output)

All dependencies are listed in `requirements.txt`.
