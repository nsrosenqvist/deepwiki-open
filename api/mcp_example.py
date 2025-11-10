"""Example client for the MCP adapter with SSE streaming support.

This script demonstrates calling the /mcp/stream endpoint with various tools.
"""
import requests
import json
import sys


BASE = "http://localhost:8001"


def stream_tool(tool, params=None):
    """
    Call a tool with SSE streaming and print events as they arrive.
    """
    payload = {"tool": tool, "params": params or {}}
    
    print(f"\n{'='*60}")
    print(f"Tool: {tool}")
    print(f"Params: {json.dumps(params, indent=2)}")
    print(f"{'='*60}\n")
    
    try:
        response = requests.post(
            f"{BASE}/mcp/stream",
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return
        
        # Parse SSE events
        event_type = None
        data_buffer = []
        
        for line in response.iter_lines():
            if not line:
                # Empty line signals end of event
                if event_type and data_buffer:
                    data = "".join(data_buffer)
                    try:
                        parsed = json.loads(data)
                        print(f"[{event_type}] {json.dumps(parsed, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"[{event_type}] {data}")
                
                event_type = None
                data_buffer = []
                continue
            
            line = line.decode('utf-8')
            
            if line.startswith('event:'):
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                data_buffer.append(line[5:].strip())
        
        print()
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except KeyboardInterrupt:
        print("\nStream interrupted by user")


def main():
    print("DeepWiki MCP Adapter - SSE Streaming Example")
    print("=" * 60)
    
    # Example 1: Read wiki structure
    print("\n### Example 1: Read Wiki Structure ###")
    stream_tool("read_wiki_structure", {
        "owner": "AsyncFuncAI",
        "repo": "deepwiki-open",
        "repo_type": "github",
        "language": "en"
    })
    
    # Example 2: Read wiki contents (specific page)
    print("\n### Example 2: Read Wiki Contents ###")
    stream_tool("read_wiki_contents", {
        "owner": "AsyncFuncAI",
        "repo": "deepwiki-open",
        "page_id": "overview",  # Change this to an actual page ID from your cache
        "repo_type": "github",
        "language": "en"
    })
    
    # Example 3: Ask a question (with streaming answer)
    print("\n### Example 3: Ask Question (Streaming) ###")
    stream_tool("ask_question", {
        "repo_url": "https://github.com/AsyncFuncAI/deepwiki-open",
        "question": "What does this repository do?",
        "provider": "google"  # Change to your configured provider
    })
    
    print("\n" + "=" * 60)
    print("Examples completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
        sys.exit(0)
