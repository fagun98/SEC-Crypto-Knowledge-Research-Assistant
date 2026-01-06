# How SEC Round Table Meeting Reports Are Generated

## Overview

This document explains how the AI agent automatically generates detailed reports from SEC Round Table Meeting transcripts. The process uses an intelligent agentic pipeline that analyzes transcripts, gathers context, and produces structured reports.

## The Agentic Pipeline

The report generation follows a simple three-step process:

### Step 1: Planning

The **Planner Node** creates a roadmap for analysis. It looks at:

- The meeting URL and transcript length
- What information needs to be extracted
- What additional context might be helpful

Think of this as creating a to-do list before starting the analysis.

### Step 2: Analysis & Information Gathering

The **Agent Node** executes the plan using three specialized tools:

1. **URL Parser Tool**

   - Fetches the SEC meeting webpage
   - Extracts meeting title, description, and participant information
   - Provides context about what the meeting was about
2. **RAG (Retrieval-Augmented Generation) Tool**

   - Searches the SEC Crypto knowledge base
   - Finds relevant regulations, policies, and historical context
   - Helps understand regulatory background and precedents
3. **Web Search Tool**

   - Searches the internet for additional information
   - Finds details about speakers, their backgrounds, or related events
   - Provides current context that might not be in the knowledge base

### Step 3: Report Generation

The agent analyzes all gathered information and the full transcript to create a structured report with:

- Key speakers and their ratings
- Views on topics discussed
- Meeting conclusions
- Key points and arguments
- Complete source citations

## Sources Used

The agent draws information from multiple sources:

1. **Meeting URL**: Official SEC webpage with meeting details
2. **Transcript File**: Complete meeting transcript (e.g., `june_9_2025.txt`)
3. **SEC Knowledge Base**: Internal database of SEC regulations and guidance (via RAG search)
4. **Web Search Results**: Publicly available information from the internet

All sources are automatically tracked and listed at the end of each report.

## How It Works Together

```
Input (URL + Transcript)
    ↓
Planner creates analysis plan
    ↓
Agent uses tools to gather information:
    ├─→ Parse URL for meeting context
    ├─→ Search SEC knowledge base for regulations
    └─→ Search web for speaker/topic information
    ↓
Agent analyzes full transcript + gathered context
    ↓
Generate structured report
    ↓
Output (TXT/DOCX/PDF file)
```

## Key Features

- **Automatic**: No manual analysis needed
- **Comprehensive**: Analyzes the entire transcript, not just summaries
- **Context-Aware**: Gathers relevant background information automatically
- **Transparent**: All sources are cited
- **Structured**: Reports follow a consistent format

## Report Sections

Every generated report includes:

1. **Executive Summary**: Brief overview
2. **Key Speakers Analysis**: Who spoke, their influence, activity, and argument strength
3. **Views on Topics**: Different perspectives and consensus points
4. **Meeting Conclusion**: Outcomes and next steps
5. **Key Points and Arguments**: Main highlights and significant events
6. **Sources**: Complete list of all information sources used

## Simple Analogy

Think of the agent like a research assistant who:

1. Reads the meeting transcript thoroughly
2. Looks up background information online
3. Checks relevant regulations and policies
4. Organizes everything into a clear, structured report
5. Lists all sources used

All of this happens automatically in minutes, saving hours of manual work.
