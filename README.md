# SEC Crypto Knowledge Research Assistant

A powerful Retrieval-Augmented Generation (RAG) application built with Streamlit and LangGraph for researching SEC cryptocurrency regulations, policies, and guidance. This tool combines hybrid semantic search with an intelligent conversational agent to help users dive deep into SEC Crypto knowledge.

## 🚀 Features

### 🔍 **Dual Interaction Modes**
- **Search Mode**: Direct semantic search across the SEC Crypto knowledge base with adjustable contextual search blending
- **Chat Mode**: Conversational interface powered by a LangGraph agent that can search, analyze, and provide evidence-backed answers

### 🎯 **Advanced Search Capabilities**
- **Hybrid Search**: Combines dense semantic embeddings (OpenAI) with sparse keyword search (SPLADE) for optimal retrieval
- **Adjustable Alpha Parameter**: Fine-tune the blend between keyword-style (alpha=0.0) and fully contextual semantic search (alpha=1.0)
- **Relevance Scoring**: Results ranked by semantic similarity with configurable score thresholds
- **Search History**: Track and review previous searches within each session

### 🤖 **Intelligent Agent**
- **LangGraph-Powered**: Uses LangGraph for structured agent workflows with tool calling
- **RAG Integration**: Agent automatically searches the knowledge base to provide evidence-backed responses
- **Conversation Context**: Maintains conversation history for coherent multi-turn dialogues
- **Deep Research Support**: Asks follow-up questions to understand research depth and context

### 💼 **Session Management**
- **Multiple Workspaces**: Create and manage multiple research sessions
- **Session Isolation**: Each session maintains its own search and chat history
- **Easy Switching**: Seamlessly switch between sessions without losing context

### 🎨 **Modern UI**
- **Dark Theme**: Beautiful glassmorphism-style dark interface
- **Responsive Design**: Clean, modern layout optimized for research workflows
- **Result Visualization**: Clear presentation of search results with metadata, scores, and source links

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/) - Python web framework
- **Agent Framework**: [LangGraph](https://github.com/langchain-ai/langgraph) - Build stateful, multi-actor applications
- **Vector Database**: [Pinecone](https://www.pinecone.io/) - Managed vector database
- **Embeddings**: 
  - Dense: OpenAI `text-embedding-3-small`
  - Sparse: SPLADE (via `pinecone-text`)
- **LLM**: OpenAI GPT-4o-mini (configurable)
- **Python**: 3.11+

## 📋 Prerequisites

- Python 3.11 or higher
- Pinecone account and API key
- OpenAI API key
- Access to a Pinecone index containing SEC Crypto documents

## 🔧 Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd SEC-Crypto-UI
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## ⚙️ Configuration

### Environment Variables

Create a `.streamlit/secrets.toml` file (or use environment variables) with the following configuration:

```toml
# OpenAI Configuration
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_LLM_MODEL = "gpt-4o-mini"
OPENAI_TEMPERATURE = "0.7"

# Pinecone Configuration
PINECONE_API_KEY = "your-pinecone-api-key"
PINECONE_INDEX = "your-index-name"
PINECONE_NAMESPACE = "your-namespace"  # Optional, leave empty for default namespace
```

Alternatively, you can use a `.env` file in the project root (see `env-example.txt` for reference).

### Streamlit Configuration

The app uses Streamlit's configuration system. You can customize the app appearance in `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#54a3ff"
backgroundColor = "#000000"
secondaryBackgroundColor = "#0f172a"
textColor = "#f5f5f5"
```

## 🚀 Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Using Search Mode

1. Select **Search** mode from the top navigation
2. Enter your query in the search box
3. Adjust the **Contextual Search** slider to control the blend between keyword and semantic search:
   - **0.0**: Pure keyword search (exact term matching)
   - **0.5**: Balanced hybrid search (recommended)
   - **1.0**: Pure semantic search (contextual understanding)
4. Set the number of results (5-50)
5. Click **Search** to retrieve relevant documents
6. Review results with relevance scores, snippets, and source links

### Using Chat Mode

1. Select **Chat** mode from the top navigation
2. Type your question or research query
3. The agent will automatically:
   - Search the knowledge base for relevant information
   - Analyze and synthesize the results
   - Provide evidence-backed answers with citations
4. Continue the conversation with follow-up questions
5. Use **Clear conversation** to start fresh

### Session Management

- Click **＋ New Session** to create a new workspace
- Use the session selector dropdown to switch between sessions
- Each session maintains independent search and chat history

## 📁 Project Structure

```
SEC-Crypto-UI/
├── app.py                 # Main Streamlit application
├── langgraph_agent.py     # LangGraph agent with RAG tool
├── pinecone_hybrid.py     # Pinecone hybrid search implementation
├── search_handler.py      # Search interface layer
├── utils.py               # Utility functions (embeddings, LLM)
├── requirements.txt       # Python dependencies
├── .streamlit/
│   ├── config.toml        # Streamlit configuration
│   └── secrets.toml        # Secrets (API keys) - not in git
├── env-example.txt        # Example environment variables
└── README.md              # This file
```

## 🏗️ Architecture

### Components

1. **Frontend (`app.py`)**
   - Streamlit UI with session management
   - Search and Chat mode interfaces
   - Result visualization and history tracking

2. **Agent Layer (`langgraph_agent.py`)**
   - LangGraph state machine for agent workflows
   - RAG search tool integration
   - Conversation context management

3. **Search Layer (`search_handler.py`)**
   - Interface between UI and Pinecone backend
   - Result formatting and structuring

4. **Vector Database (`pinecone_hybrid.py`)**
   - Hybrid search implementation
   - Dense + sparse embedding combination
   - Score normalization and filtering

5. **Utilities (`utils.py`)**
   - Embedding model initialization
   - LLM configuration
   - Helper functions

### Search Flow

```
User Query
    ↓
Search Handler
    ↓
Pinecone Hybrid DB
    ├── Dense Embedding (OpenAI)
    └── Sparse Embedding (SPLADE)
    ↓
Hybrid Score Normalization
    ↓
Pinecone Query
    ↓
Results with Scores
    ↓
Formatted Results
    ↓
UI Display
```

### Agent Flow

```
User Message
    ↓
LangGraph Agent
    ├── System Prompt
    └── Conversation History
    ↓
Agent Decides Action
    ├── Use RAG Tool → Search Pinecone
    └── Generate Response
    ↓
Tool Results → Agent
    ↓
Final Response
    ↓
UI Display
```

## 🔍 Example Queries

### Search Mode
- "Bitcoin ETF approval process"
- "SEC Form 10-K cryptocurrency disclosure requirements"
- "How does the SEC regulate stablecoins?"
- "Digital asset classification under securities law"

### Chat Mode
- "What are the requirements for cryptocurrency exchanges?"
- "I want to dive deep into how the SEC regulates Bitcoin ETFs. Can you help me research this comprehensively?"
- "Explain the difference between security tokens and utility tokens according to SEC guidance"

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

[Specify your license here]

## 🙏 Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- Powered by [Pinecone](https://www.pinecone.io/) for vector search
- Uses [Streamlit](https://streamlit.io/) for the web interface
- OpenAI for embeddings and language models## 📧 SupportFor issues, questions, or contributions, please open an issue on GitHub.---**Note**: This application requires access to a Pinecone index containing SEC Crypto documents. Ensure your index is properly configured and populated before use.
