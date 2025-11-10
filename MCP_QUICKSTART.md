# MCP Endpoint Quick Start Guide

## TL;DR

DeepWiki now has MCP endpoints with SSE streaming at `/mcp/*` and `/sse/*` (legacy).

**Three main tools:**
1. `read_wiki_structure` - List documentation topics
2. `read_wiki_contents` - View documentation pages  
3. `ask_question` - AI-powered Q&A with RAG

## Quick Test

```bash
# 1. Start the server
python -m api.main

# 2. Test in another terminal
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

## Endpoints

- `POST /mcp/info` - Get tool metadata
- `GET /mcp/ping` - Health check
- `POST /mcp/stream` - Invoke tools (SSE)
- `POST /sse/stream` - Legacy endpoint (same)

## Tool Request Format

```json
{
  "tool": "tool_name",
  "params": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

## Response Format (SSE)

```
event: start
data: {"status": "started"}

event: data
data: {"text": "response chunk"}

event: done
data: {"status": "completed"}
```

## Tools Reference

### read_wiki_structure
```json
{
  "tool": "read_wiki_structure",
  "params": {
    "owner": "AsyncFuncAI",
    "repo": "deepwiki-open"
  }
}
```

### read_wiki_contents
```json
{
  "tool": "read_wiki_contents",
  "params": {
    "owner": "AsyncFuncAI",
    "repo": "deepwiki-open",
    "page_id": "overview"  // optional
  }
}
```

### ask_question
```json
{
  "tool": "ask_question",
  "params": {
    "repo_url": "https://github.com/owner/repo",
    "question": "Your question here",
    "provider": "google"  // optional: google, openai, ollama
  }
}
```

## Python Client Example

```python
import requests
import json

response = requests.post(
    "http://localhost:8001/mcp/stream",
    json={
        "tool": "ask_question",
        "params": {
            "repo_url": "https://github.com/AsyncFuncAI/deepwiki-open",
            "question": "How does RAG work here?"
        }
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data:'):
            data = json.loads(line[5:])
            print(data)
```

## Files Added

- `api/mcp_server.py` - MCP implementation
- `api/MCP_README.md` - Full documentation
- `api/mcp_example.py` - Working example
- `test_mcp_import.py` - Validation script
- `MCP_IMPLEMENTATION_SUMMARY.md` - Complete details
- `MCP_QUICKSTART.md` - This file

## Next Steps

1. **Test it**: Run `python api/mcp_example.py`
2. **Read more**: See `api/MCP_README.md` for full docs
3. **Integrate**: Use with your LLM framework

## Notes

- Requires wiki cache for `read_wiki_*` tools (generate via UI first)
- `ask_question` works with any repository (generates cache on-the-fly)
- Supports Google, OpenAI, and Ollama providers
- Real-time SSE streaming for all tools
