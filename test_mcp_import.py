#!/usr/bin/env python
"""
Simple test script to verify MCP server module can be imported.
Run this after installing dependencies with: poetry install
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from api import mcp_server
    print("✓ MCP server module imported successfully")
    
    # Check that the router exists
    assert hasattr(mcp_server, 'router'), "router not found"
    print("✓ Router found")
    
    # Check that key functions exist
    assert hasattr(mcp_server, 'mcp_info'), "mcp_info not found"
    assert hasattr(mcp_server, 'mcp_ping'), "mcp_ping not found"
    assert hasattr(mcp_server, 'mcp_stream'), "mcp_stream not found"
    assert hasattr(mcp_server, 'sse_stream'), "sse_stream not found"
    print("✓ All expected endpoints found")
    
    # Check internal functions
    assert hasattr(mcp_server, '_stream_tool_read_wiki_structure'), "_stream_tool_read_wiki_structure not found"
    assert hasattr(mcp_server, '_stream_tool_read_wiki_contents'), "_stream_tool_read_wiki_contents not found"
    assert hasattr(mcp_server, '_stream_tool_ask_question'), "_stream_tool_ask_question not found"
    print("✓ All tool implementation functions found")
    
    print("\n✅ All checks passed! MCP server is ready.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nPlease install dependencies first:")
    print("  poetry install")
    sys.exit(1)
except AssertionError as e:
    print(f"❌ Assertion failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
