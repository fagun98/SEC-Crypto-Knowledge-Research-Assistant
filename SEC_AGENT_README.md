# SEC Round Table Meeting Report Agent

This agent generates detailed reports from SEC Round Table Meeting transcripts using LangGraph.

## Architecture

The agent uses a simple LangGraph architecture with:

1. **Planner Node**: Creates a step-by-step plan for analyzing the meeting
2. **Agent Node**: Executes the plan using available tools
3. **Tools**:
   - **RAG Tool**: Searches SEC Crypto knowledge base for relevant regulations and context
   - **URL Parser Tool**: Extracts information from SEC meeting web pages
   - **Web Search Tool**: Finds additional information about speakers, topics, or events

## Features

The generated report includes:

1. **Key Speakers Analysis**
   - List of all key speakers
   - Influence rating (1-10 scale)
   - Activity level assessment
   - Argument strength rating (1-10 scale)
   - Identification of the most influential speaker

2. **Views on Topics**
   - Main topics discussed
   - Different viewpoints expressed
   - Consensus and disagreements

3. **Meeting Conclusion**
   - Overall outcome
   - Action items or next steps

4. **Key Points and Main Arguments/Events**
   - Important points made
   - Main arguments presented
   - Significant events or moments

5. **Sources**
   - Meeting URL
   - Transcript file
   - Additional sources from RAG and web searches

## Usage

### Basic Usage

```python
from sec_meeting_agent import generate_meeting_report

# Generate a report
output_file = generate_meeting_report(
    meeting_url="https://www.sec.gov/newsroom/meetings-events/defi-american-spirit",
    transcript_file="june_9_2025.txt",
    output_format="txt"  # Options: "txt", "docx", or "pdf"
)

print(f"Report saved to: {output_file}")
```

### Running the Test Script

```bash
python test_sec_agent.py
```

### Command Line Usage

```bash
python sec_meeting_agent.py
```

## Output Formats

The agent supports three output formats:

- **txt**: Plain text file (default, always available)
- **docx**: Microsoft Word document (requires `python-docx`)
- **pdf**: PDF document (requires `reportlab`)

## Dependencies

Required packages (already in requirements.txt):
- `langchain-core`
- `langchain-openai`
- `langgraph`
- `beautifulsoup4`
- `requests`
- `duckduckgo-search`
- `python-docx` (for docx output)
- `reportlab` (for pdf output)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Environment Variables

Make sure you have the following environment variables set:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_LLM_MODEL`: (Optional) LLM model to use (default: gpt-4o-mini)
- `PINECONE_API_KEY`: (Optional) For RAG search functionality
- `PINECONE_INDEX`: (Optional) Pinecone index name

## How It Works

1. **Input**: The agent receives a meeting URL and transcript file path
2. **Planning**: The planner node creates an analysis plan
3. **Execution**: The agent node:
   - Parses the meeting URL to get context
   - Analyzes the full transcript
   - Uses RAG search for SEC regulation context
   - Uses web search for additional information about speakers/topics
   - Generates a structured report
4. **Output**: Saves the report in the requested format

## Example Output Structure

```
==========================================
SEC ROUND TABLE MEETING REPORT
==========================================

1. EXECUTIVE SUMMARY
   [Brief overview]

2. KEY SPEAKERS ANALYSIS
   [Detailed speaker analysis with ratings]

3. VIEWS ON TOPICS
   [Topic-by-topic analysis]

4. MEETING CONCLUSION
   [Outcomes and next steps]

5. KEY POINTS AND MAIN ARGUMENTS/EVENTS
   [Key highlights]

6. SOURCES
   [List of all sources used]
```

## Notes

- The agent analyzes the complete transcript, so processing may take a few minutes for long transcripts
- All sources are cited at the end of the report
- The agent uses OpenAI's GPT models, so API costs apply
- For best results, ensure the transcript file is properly formatted
