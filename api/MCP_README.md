# MCP (Model Context Protocol) Adapter for DeepWiki

This file documents the MCP-compatible adapter with Server-Sent Events (SSE) streaming support.

## Overview

DeepWiki's MCP adapter provides three main tools for LLM integration:

1. **read_wiki_structure** - Get a list of documentation topics for a repository
2. **read_wiki_contents** - View documentation about a repository
3. **ask_question** - Ask any question about a repository and get an AI-powered, context-grounded response

## Endpoints

All endpoints support SSE streaming for real-time responses.

### MCP Endpoints (Primary)

- `POST /mcp/info` — Returns server metadata and available tools
- `GET  /mcp/ping` — Health check
- `POST /mcp/stream` — Invoke a tool with SSE streaming (primary endpoint)

### Legacy SSE Endpoints

For backward compatibility, the same functionality is available at:

- `POST /sse/stream` — Same as /mcp/stream
- `POST /sse/info` — Same as /mcp/info
- `GET  /sse/ping` — Same as /mcp/ping

## Tools

### 1. read_wiki_structure

Get a list of documentation topics for a repository.

**Parameters:**
- `owner` (required) - Repository owner
- `repo` (required) - Repository name
- `repo_type` (optional) - Repository type (default: 'github')
- `language` (optional) - Language code (default: 'en')

**Response Events:**
- `start` - Tool execution started
- `data` - Wiki structure data (sections, pages, topics)
- `done` - Tool execution completed
- `error` - Error occurred

**Example Request:**
```json
{
  "tool": "read_wiki_structure",
  "params": {
    "owner": "AsyncFuncAI",
    "repo": "deepwiki-open",
    "repo_type": "github",
    "language": "en"
  }
}
```

### 2. read_wiki_contents

View documentation pages from the wiki cache.

**Parameters:**
- `owner` (required) - Repository owner
- `repo` (required) - Repository name
- `page_id` (optional) - Specific page ID (if omitted, returns all pages)
- `repo_type` (optional) - Repository type (default: 'github')
- `language` (optional) - Language code (default: 'en')

**Response Events:**
- `start` - Tool execution started
- `data` - Page content (may stream multiple events for multiple pages)
- `done` - Tool execution completed
- `error` - Error occurred

**Example Request:**
```json
{
  "tool": "read_wiki_contents",
  "params": {
    "owner": "AsyncFuncAI",
    "repo": "deepwiki-open",
    "page_id": "overview"
  }
}
```

### 3. ask_question

Ask any question about a repository with AI-powered RAG.

**Parameters:**
- `repo_url` (required) - Repository URL
- `question` (required) - Question to ask
- `provider` (optional) - Model provider (default: 'google')
- `model` (optional) - Model name
- `type` (optional) - Repository type (default: 'github')
- `token` (optional) - Access token for private repos
- `language` (optional) - Language code (default: 'en')

**Response Events:**
- `start` - Tool execution started
- `progress` - Status updates (preparing_retriever, retrieving_context, generating_answer)
- `data` - Answer text chunks (streams as generated)
- `done` - Tool execution completed
- `error` - Error occurred

**Example Request:**
```json
{
  "tool": "ask_question",
  "params": {
    "repo_url": "https://github.com/AsyncFuncAI/deepwiki-open",
    "question": "How does the RAG system work?",
    "provider": "google"
  }
}
```

## SSE Event Format

All responses follow the Server-Sent Events specification:

```
event: start
data: {"status": "started", "tool": "tool_name"}

event: data
data: {"key": "value"}

event: done
data: {"status": "completed"}
```

Error events:
```
event: error
data: {"error": "error message"}
```

## Usage Example

### From Command Line (curl)

```bash
# Get wiki structure
curl -X POST http://localhost:8001/mcp/stream \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "read_wiki_structure",
    "params": {
      "owner": "AsyncFuncAI",
      "repo": "deepwiki-open"
    }
  }'

# Ask a question
curl -X POST http://localhost:8001/mcp/stream \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "ask_question",
    "params": {
      "repo_url": "https://github.com/AsyncFuncAI/deepwiki-open",
      "question": "What does this repository do?"
    }
  }'
```

### From Python

See `api/mcp_example.py` for a complete example using the `requests` library with SSE support.

## Setup

1. Start the API server:

```bash
python -m api.main
```

2. The MCP endpoints will be available at:
   - Primary: `http://localhost:8001/mcp/*`
   - Legacy: `http://localhost:8001/sse/*`

## Notes

- All tools use SSE for streaming responses, allowing real-time feedback
- The `ask_question` tool supports multiple LLM providers (Google, OpenAI, Ollama)
- Wiki structure and contents are read from cached data (must be generated first via the main UI)
- The system maintains backward compatibility with the `/sse` prefix
