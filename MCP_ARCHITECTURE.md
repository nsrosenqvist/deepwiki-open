# MCP Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LLM / Client Application                      │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐   │
│  │  LangChain   │  │   AutoGen    │  │  Custom HTTP Client     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬──────────────┘   │
│         │                 │                      │                   │
└─────────┼─────────────────┼──────────────────────┼───────────────────┘
          │                 │                      │
          └─────────────────┴──────────────────────┘
                            │
                            │ HTTP POST with SSE
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DeepWiki MCP Endpoints                          │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  POST /mcp/stream  (primary SSE endpoint)                      │ │
│  │  POST /sse/stream  (legacy SSE endpoint)                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  GET /mcp/ping     (health check)                              │ │
│  │  POST /mcp/info    (tool metadata)                             │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────┬─────────────────────────────────┘
                                      │
                                      │ Tool Invocation
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          MCP Tool Router                             │
│                       (api/mcp_server.py)                            │
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ read_wiki_       │  │ read_wiki_       │  │  ask_question    │  │
│  │ structure        │  │ contents         │  │                  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                      │             │
└───────────┼─────────────────────┼──────────────────────┼─────────────┘
            │                     │                      │
            ▼                     ▼                      ▼
┌───────────────────┐  ┌───────────────────┐  ┌────────────────────┐
│  Wiki Cache       │  │  Wiki Cache       │  │  RAG Pipeline      │
│  (~/.adalflow/    │  │  (~/.adalflow/    │  │                    │
│   wikicache/)     │  │   wikicache/)     │  │  ┌──────────────┐  │
│                   │  │                   │  │  │  Retriever   │  │
│  - Structure      │  │  - Pages          │  │  └──────┬───────┘  │
│  - Sections       │  │  - Content        │  │         │          │
│  - Topics         │  │  - Metadata       │  │         ▼          │
└───────────────────┘  └───────────────────┘  │  ┌──────────────┐  │
                                              │  │  Embeddings  │  │
                                              │  └──────┬───────┘  │
                                              │         │          │
                                              │         ▼          │
                                              │  ┌──────────────┐  │
                                              │  │  Generator   │  │
                                              │  │  (LLM)       │  │
                                              │  └──────────────┘  │
                                              └────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        SSE Event Flow                                │
│                                                                       │
│  Client Request                                                       │
│       │                                                              │
│       ▼                                                              │
│  event: start ───────────────────────────────────────────────►      │
│  data: {"status": "started"}                                         │
│                                                                       │
│  event: progress ─────────────────────────────────────────────►     │
│  data: {"status": "preparing_retriever"}                            │
│                                                                       │
│  event: progress ─────────────────────────────────────────────►     │
│  data: {"status": "retrieving_context"}                             │
│                                                                       │
│  event: progress ─────────────────────────────────────────────►     │
│  data: {"status": "generating_answer", "context_documents": 5}      │
│                                                                       │
│  event: data ─────────────────────────────────────────────────►     │
│  data: {"text": "The RAG system"}                                    │
│                                                                       │
│  event: data ─────────────────────────────────────────────────►     │
│  data: {"text": " works by"}                                         │
│                                                                       │
│  event: data ─────────────────────────────────────────────────►     │
│  data: {"text": " retrieving relevant..."}                          │
│                                                                       │
│  event: done ─────────────────────────────────────────────────►     │
│  data: {"status": "completed"}                                       │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### MCP Endpoints Layer
- Receives HTTP POST requests from LLM clients
- Routes to appropriate tool handler
- Returns Server-Sent Events (SSE) stream

### Tool Router
- Three main tools: `read_wiki_structure`, `read_wiki_contents`, `ask_question`
- Each tool is an async generator that yields SSE events
- Handles errors and streams them as error events

### Data Sources
- **Wiki Cache**: Pre-generated documentation stored locally
- **RAG Pipeline**: Real-time retrieval and generation for questions
- **Embeddings**: Vector search for relevant code context

### SSE Event Types
- `start`: Tool execution begins
- `progress`: Status updates during processing
- `data`: Actual content (structure, pages, or answer chunks)
- `done`: Tool execution completes successfully
- `error`: Error occurred during processing

## Data Flow Examples

### Example 1: read_wiki_structure
```
Client → POST /mcp/stream → Router → Cache → Structure Data → SSE Stream → Client
```

### Example 2: ask_question
```
Client → POST /mcp/stream → Router → RAG Pipeline → Retriever → Embeddings
                                                   → Generator → LLM
                                                   → SSE Stream → Client
```

## Integration Points

1. **LangChain**: Create custom tools wrapping MCP endpoints
2. **AutoGen**: Define conversable agents using MCP tools
3. **Direct HTTP**: Use any HTTP client with SSE support
4. **Claude/GPT-4**: Function calling with tool definitions from `/mcp/info`

## Provider Support

The `ask_question` tool supports multiple LLM providers:

- **Google Gemini** (default): Full streaming, no setup
- **OpenAI**: GPT-4, GPT-3.5 with streaming
- **Ollama**: Local models (Llama, Mistral, etc.)
- **Azure AI**: Azure OpenAI service
- **AWS Bedrock**: Claude, Titan, Jurassic
- **OpenRouter**: Access to multiple providers

## Key Features

✅ **Real-time Streaming**: See results as they generate  
✅ **Progress Updates**: Know what's happening during long operations  
✅ **Error Handling**: Graceful error messages via SSE  
✅ **Async/Await**: Efficient resource usage  
✅ **Multi-Provider**: Support for multiple LLM backends  
✅ **Backward Compatible**: Legacy `/sse` endpoints  
✅ **Production Ready**: Logging, error handling, validation  
