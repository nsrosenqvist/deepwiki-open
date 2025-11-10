import os
import logging
import json
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.rag import RAG
from api.config import get_model_config

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPToolRequest(BaseModel):
    """Request for MCP tool invocation with SSE streaming."""
    tool: str
    params: Optional[Dict[str, Any]] = None


def _wiki_cache_dir() -> str:
    """Get the wiki cache directory path."""
    return os.path.join(os.path.expanduser(os.path.join("~", ".adalflow")), "wikicache")


def _format_sse(data: Dict[str, Any], event: str = "message") -> str:
    """Format data as Server-Sent Events (SSE)."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_error(message: str) -> AsyncGenerator[str, None]:
    """Stream an error message as SSE."""
    yield _format_sse({"error": message}, event="error")


async def _stream_tool_read_wiki_structure(params: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Tool: read_wiki_structure
    Get a list of documentation topics for a repository.
    
    Required params:
    - owner: Repository owner
    - repo: Repository name
    - repo_type: Repository type (e.g., 'github')
    - language: Language code (e.g., 'en')
    """
    try:
        owner = params.get("owner")
        repo = params.get("repo")
        repo_type = params.get("repo_type", "github")
        language = params.get("language", "en")
        
        if not all([owner, repo]):
            async for chunk in _stream_error("owner and repo are required"):
                yield chunk
            return
        
        # Stream start event
        yield _format_sse({"status": "started", "tool": "read_wiki_structure"}, event="start")
        
        # Get wiki cache
        filename = f"deepwiki_cache_{repo_type}_{owner}_{repo}_{language}.json"
        path = os.path.join(_wiki_cache_dir(), filename)
        
        if not os.path.exists(path):
            async for chunk in _stream_error(f"Wiki cache not found for {owner}/{repo}"):
                yield chunk
            return
        
        # Load and parse cache
        with open(path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        wiki_structure = cache_data.get("wiki_structure", {})
        
        # Extract topics (sections and pages)
        topics = []
        
        # Add sections if they exist
        sections = wiki_structure.get("sections", [])
        for section in sections:
            topics.append({
                "id": section.get("id"),
                "title": section.get("title"),
                "type": "section",
                "pages": section.get("pages", []),
                "subsections": section.get("subsections", [])
            })
        
        # Add root pages
        pages = wiki_structure.get("pages", [])
        for page in pages:
            topics.append({
                "id": page.get("id"),
                "title": page.get("title"),
                "type": "page",
                "importance": page.get("importance", "medium"),
                "relatedPages": page.get("relatedPages", [])
            })
        
        # Stream the structure
        result = {
            "id": wiki_structure.get("id"),
            "title": wiki_structure.get("title"),
            "description": wiki_structure.get("description"),
            "topics": topics,
            "rootSections": wiki_structure.get("rootSections", [])
        }
        
        yield _format_sse(result, event="data")
        yield _format_sse({"status": "completed"}, event="done")
        
    except Exception as e:
        logger.exception("Error in read_wiki_structure")
        async for chunk in _stream_error(str(e)):
            yield chunk


async def _stream_tool_read_wiki_contents(params: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Tool: read_wiki_contents
    View documentation about a repository.
    
    Required params:
    - owner: Repository owner
    - repo: Repository name
    - page_id: Page ID to read (optional, if omitted returns all pages)
    - repo_type: Repository type (default: 'github')
    - language: Language code (default: 'en')
    """
    try:
        owner = params.get("owner")
        repo = params.get("repo")
        page_id = params.get("page_id")
        repo_type = params.get("repo_type", "github")
        language = params.get("language", "en")
        
        if not all([owner, repo]):
            async for chunk in _stream_error("owner and repo are required"):
                yield chunk
            return
        
        # Stream start event
        yield _format_sse({"status": "started", "tool": "read_wiki_contents"}, event="start")
        
        # Get wiki cache
        filename = f"deepwiki_cache_{repo_type}_{owner}_{repo}_{language}.json"
        path = os.path.join(_wiki_cache_dir(), filename)
        
        if not os.path.exists(path):
            async for chunk in _stream_error(f"Wiki cache not found for {owner}/{repo}"):
                yield chunk
            return
        
        # Load cache
        with open(path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        generated_pages = cache_data.get("generated_pages", {})
        
        # If page_id is specified, return that page
        if page_id:
            if page_id not in generated_pages:
                async for chunk in _stream_error(f"Page '{page_id}' not found"):
                    yield chunk
                return
            
            page = generated_pages[page_id]
            yield _format_sse({"page": page}, event="data")
        else:
            # Return all pages (stream them one by one)
            for pid, page in generated_pages.items():
                yield _format_sse({"page_id": pid, "page": page}, event="data")
                # Small delay to allow proper streaming
                await asyncio.sleep(0.01)
        
        yield _format_sse({"status": "completed"}, event="done")
        
    except Exception as e:
        logger.exception("Error in read_wiki_contents")
        async for chunk in _stream_error(str(e)):
            yield chunk


async def _stream_tool_ask_question(params: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Tool: ask_question
    Ask any question about a repository and get an AI-powered, context-grounded response.
    
    Required params:
    - repo_url: Repository URL
    - question: Question to ask
    
    Optional params:
    - provider: Model provider (default: 'google')
    - model: Model name
    - type: Repository type (default: 'github')
    - token: Access token for private repos
    - language: Language code (default: 'en')
    """
    try:
        repo_url = params.get("repo_url")
        question = params.get("question")
        provider = params.get("provider", "google")
        model = params.get("model")
        repo_type = params.get("type", "github")
        token = params.get("token")
        language = params.get("language", "en")
        
        if not repo_url or not question:
            async for chunk in _stream_error("repo_url and question are required"):
                yield chunk
            return
        
        # Stream start event
        yield _format_sse({"status": "started", "tool": "ask_question"}, event="start")
        
        # Initialize RAG
        rag = RAG(provider=provider, model=model)
        
        # Prepare retriever
        yield _format_sse({"status": "preparing_retriever"}, event="progress")
        rag.prepare_retriever(repo_url_or_path=repo_url, type=repo_type, access_token=token)
        
        # Retrieve relevant documents
        yield _format_sse({"status": "retrieving_context"}, event="progress")
        retrieved = rag.call(question, language=language)
        
        # Format context
        context_parts = []
        if retrieved and retrieved[0].documents:
            docs = retrieved[0].documents
            for doc in docs:
                meta = getattr(doc, "meta_data", {})
                text = getattr(doc, "text", "")
                file_path = meta.get("file_path", "unknown")
                context_parts.append(f"**File: {file_path}**\n\n{text}")
        
        context_text = "\n\n---\n\n".join(context_parts) if context_parts else ""
        
        # Stream the context being used
        yield _format_sse({
            "status": "generating_answer",
            "context_documents": len(context_parts)
        }, event="progress")
        
        # Build prompt for the generator
        from api.config import configs
        
        # Get repo name
        repo_name = repo_url.split("/")[-1] if "/" in repo_url else repo_url
        
        # Get language information
        supported_langs = configs["lang_config"]["supported_languages"]
        language_name = supported_langs.get(language, "English")
        
        system_prompt = f"""You are an AI assistant specialized in explaining code and documentation for the {repo_type} repository: {repo_url}

Repository: {repo_name}
Language: {language_name}

Your task is to answer questions about this repository based on the provided context. Be accurate, concise, and helpful. Format your response in markdown for readability."""
        
        prompt = f"{system_prompt}\n\n"
        
        if context_text:
            prompt += f"<context>\n{context_text}\n</context>\n\n"
        
        prompt += f"<question>\n{question}\n</question>\n\nAnswer:"
        
        # Get model configuration
        model_config = get_model_config(provider, model)
        model_kwargs = model_config["model_kwargs"]
        
        # Stream the answer
        if provider == "google":
            import google.generativeai as genai
            gen_model = genai.GenerativeModel(
                model_name=model_kwargs["model"],
                generation_config={
                    "temperature": model_kwargs.get("temperature", 0.7),
                    "top_p": model_kwargs.get("top_p", 0.8),
                    "top_k": model_kwargs.get("top_k", 40)
                }
            )
            
            response = gen_model.generate_content(prompt, stream=True)
            
            for chunk in response:
                if hasattr(chunk, 'text'):
                    yield _format_sse({"text": chunk.text}, event="data")
        
        elif provider == "ollama":
            from adalflow.components.model_client.ollama_client import OllamaClient
            from adalflow.core.types import ModelType
            
            model_client = OllamaClient()
            model_kwargs_ollama = {
                "model": model_kwargs["model"],
                "stream": True,
                "options": {
                    "temperature": model_kwargs.get("temperature", 0.7),
                    "top_p": model_kwargs.get("top_p", 0.8),
                    "num_ctx": model_kwargs.get("num_ctx", 8192)
                }
            }
            
            api_kwargs = model_client.convert_inputs_to_api_kwargs(
                input=prompt,
                model_kwargs=model_kwargs_ollama,
                model_type=ModelType.LLM
            )
            
            response = await model_client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
            
            async for chunk in response:
                text = getattr(chunk, 'response', None) or getattr(chunk, 'text', None) or str(chunk)
                if text and not text.startswith('model=') and not text.startswith('created_at='):
                    yield _format_sse({"text": text}, event="data")
        
        elif provider == "openai":
            from api.openai_client import OpenAIClient
            from adalflow.core.types import ModelType
            
            model_client = OpenAIClient()
            model_kwargs_openai = {
                "model": model,
                "stream": True,
                "temperature": model_kwargs.get("temperature", 0.7),
                "top_p": model_kwargs.get("top_p", 0.8)
            }
            
            api_kwargs = model_client.convert_inputs_to_api_kwargs(
                input=prompt,
                model_kwargs=model_kwargs_openai,
                model_type=ModelType.LLM
            )
            
            response = await model_client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
            
            async for chunk in response:
                choices = getattr(chunk, "choices", [])
                if len(choices) > 0:
                    delta = getattr(choices[0], "delta", None)
                    if delta is not None:
                        text = getattr(delta, "content", None)
                        if text is not None:
                            yield _format_sse({"text": text}, event="data")
        
        else:
            # Fallback for other providers
            async for chunk in _stream_error(f"Provider '{provider}' streaming not yet implemented"):
                yield chunk
            return
        
        yield _format_sse({"status": "completed"}, event="done")
        
    except Exception as e:
        logger.exception("Error in ask_question")
        async for chunk in _stream_error(str(e)):
            yield chunk


@router.post("/info")
async def mcp_info():
    """Return MCP server metadata and available tools."""
    return {
        "name": "deepwiki-mcp",
        "version": "1.0",
        "description": "MCP adapter for DeepWiki with streaming support",
        "protocol": "sse",
        "tools": [
            {
                "name": "read_wiki_structure",
                "description": "Get a list of documentation topics for a repository",
                "parameters": {
                    "owner": "Repository owner (required)",
                    "repo": "Repository name (required)",
                    "repo_type": "Repository type (default: 'github')",
                    "language": "Language code (default: 'en')"
                }
            },
            {
                "name": "read_wiki_contents",
                "description": "View documentation about a repository",
                "parameters": {
                    "owner": "Repository owner (required)",
                    "repo": "Repository name (required)",
                    "page_id": "Specific page ID (optional, returns all if omitted)",
                    "repo_type": "Repository type (default: 'github')",
                    "language": "Language code (default: 'en')"
                }
            },
            {
                "name": "ask_question",
                "description": "Ask any question about a repository and get an AI-powered, context-grounded response",
                "parameters": {
                    "repo_url": "Repository URL (required)",
                    "question": "Question to ask (required)",
                    "provider": "Model provider (default: 'google')",
                    "model": "Model name (optional)",
                    "type": "Repository type (default: 'github')",
                    "token": "Access token for private repos (optional)",
                    "language": "Language code (default: 'en')"
                }
            }
        ]
    }


@router.get("/ping")
async def mcp_ping():
    """Health check endpoint."""
    return {"ok": True}


@router.post("/stream")
async def mcp_stream(request: MCPToolRequest):
    """
    Invoke a tool with SSE streaming response.
    
    Supported tools:
    - read_wiki_structure
    - read_wiki_contents
    - ask_question
    """
    tool = request.tool
    params = request.params or {}
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            if tool == "read_wiki_structure":
                async for chunk in _stream_tool_read_wiki_structure(params):
                    yield chunk
            elif tool == "read_wiki_contents":
                async for chunk in _stream_tool_read_wiki_contents(params):
                    yield chunk
            elif tool == "ask_question":
                async for chunk in _stream_tool_ask_question(params):
                    yield chunk
            else:
                async for chunk in _stream_error(f"Unknown tool: {tool}"):
                    yield chunk
        except Exception as e:
            logger.exception("Error in event generator")
            async for chunk in _stream_error(str(e)):
                yield chunk
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Legacy SSE endpoint (same functionality as /mcp/stream)
@router.post("/sse")
async def sse_stream(request: MCPToolRequest):
    """
    Legacy SSE endpoint for backward compatibility.
    Uses the same tool invocation as /mcp/stream.
    """
    return await mcp_stream(request)
