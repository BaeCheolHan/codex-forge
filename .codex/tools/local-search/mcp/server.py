#!/usr/bin/env python3
"""
MCP Server for Local Search (STDIO mode)
Follows Model Context Protocol specification: https://modelcontextprotocol.io/specification/2025-11-25

v2.3.1 enhancements:
- File type filtering (file_types)
- Path pattern matching (path_pattern)
- Exclude patterns (exclude_patterns)
- Recency boost (recency_boost)
- Regex search mode (use_regex)
- Enhanced search results with metadata

Usage:
  python3 .codex/tools/local-search/mcp/server.py

Environment:
  CODEX_WORKSPACE_ROOT - Workspace root directory (default: cwd)
"""
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directories to path for imports
SCRIPT_DIR = Path(__file__).parent
APP_DIR = SCRIPT_DIR.parent / "app"
sys.path.insert(0, str(APP_DIR))

from config import Config
from db import LocalSearchDB, SearchOptions
from indexer import Indexer


class LocalSearchMCPServer:
    """MCP Server for Local Search - STDIO mode."""
    
    PROTOCOL_VERSION = "2025-11-25"
    SERVER_NAME = "local-search"
    SERVER_VERSION = "2.3.3"  # Updated for enhanced search
    
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.cfg: Optional[Config] = None
        self.db: Optional[LocalSearchDB] = None
        self.indexer: Optional[Indexer] = None
        self._indexer_thread: Optional[threading.Thread] = None
        self._initialized = False
    
    def _ensure_initialized(self) -> None:
        """Lazy initialization of database and indexer."""
        if self._initialized:
            return
        
        try:
            os.environ["LOCAL_SEARCH_WORKSPACE_ROOT"] = self.workspace_root
            
            config_path = Path(self.workspace_root) / ".codex" / "tools" / "local-search" / "config" / "config.json"
            if config_path.exists():
                self.cfg = Config.load(str(config_path))
            else:
                self.cfg = Config(
                    workspace_root=self.workspace_root,
                    server_host="127.0.0.1",
                    server_port=47777,
                    scan_interval_seconds=180,
                    snippet_max_lines=5,
                    max_file_bytes=800000,
                    db_path=str(Path(self.workspace_root) / ".codex" / "tools" / "local-search" / "data" / "index.db"),
                    include_ext=[".py", ".js", ".ts", ".java", ".kt", ".go", ".rs", ".md", ".json", ".yaml", ".yml", ".sh"],
                    include_files=["pom.xml", "package.json", "Dockerfile", "Makefile", "build.gradle", "settings.gradle"],
                    exclude_dirs=[".git", "node_modules", "__pycache__", ".venv", "venv", "target", "build", "dist"],
                    exclude_globs=["*.min.js", "*.min.css", "*.map", "*.lock"],
                    redact_enabled=True,
                    commit_batch_size=500,
                )
            
            # v2.3.2: Use config db_path for consistency with HTTP mode
            db_path_str = os.path.expanduser(
                os.environ.get("LOCAL_SEARCH_DB_PATH") or self.cfg.db_path
            )
            db_path = Path(db_path_str)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db = LocalSearchDB(str(db_path))
            
            self.indexer = Indexer(self.cfg, self.db)
            
            self._indexer_thread = threading.Thread(target=self.indexer.run_forever, daemon=True)
            self._indexer_thread.start()
            
            init_timeout = float(os.environ.get("LOCAL_SEARCH_INIT_TIMEOUT", "5"))
            if init_timeout > 0:
                wait_iterations = int(init_timeout * 10)
                for _ in range(wait_iterations):
                    if self.indexer.status.index_ready:
                        break
                    time.sleep(0.1)
            
            self._initialized = True
        except Exception as e:
            self._log_error(f"Initialization failed: {e}")
            raise
    
    def _log_error(self, message: str) -> None:
        print(f"[local-search] ERROR: {message}", file=sys.stderr, flush=True)
    
    def _log_info(self, message: str) -> None:
        print(f"[local-search] INFO: {message}", file=sys.stderr, flush=True)
    
    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "serverInfo": {
                "name": self.SERVER_NAME,
                "version": self.SERVER_VERSION,
            },
            "capabilities": {
                "tools": {},
            },
        }
    
    def handle_initialized(self, params: Dict[str, Any]) -> None:
        self._ensure_initialized()
    
    def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request - v2.3.1 enhanced schema."""
        return {
            "tools": [
                {
                    "name": "search",
                    "description": "Enhanced search for code/files. Use BEFORE file exploration to save tokens. Supports file type filtering, path patterns, regex, and recency boost.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (keywords, function names, class names, or regex pattern)",
                            },
                            "repo": {
                                "type": "string",
                                "description": "Limit search to specific repository",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 10, max: 50)",
                                "default": 10,
                            },
                            # v2.3.1 new options
                            "file_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by file extensions, e.g., ['py', 'ts', 'java']",
                            },
                            "path_pattern": {
                                "type": "string",
                                "description": "Glob pattern for path matching, e.g., 'src/**/*.ts'",
                            },
                            "exclude_patterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Patterns to exclude, e.g., ['node_modules', 'test']",
                            },
                            "recency_boost": {
                                "type": "boolean",
                                "description": "Boost recently modified files (default: false)",
                                "default": False,
                            },
                            "use_regex": {
                                "type": "boolean",
                                "description": "Treat query as regex pattern (default: false)",
                                "default": False,
                            },
                            "case_sensitive": {
                                "type": "boolean",
                                "description": "Case-sensitive search for regex mode (default: false)",
                                "default": False,
                            },
                            "context_lines": {
                                "type": "integer",
                                "description": "Number of context lines in snippet (default: 5)",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "status",
                    "description": "Get indexer status (index ready, scanned files, etc.)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                    },
                },
                {
                    "name": "repo_candidates",
                    "description": "Find candidate repositories for a query. Use when user doesn't specify which repo to work on.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Query to find relevant repositories",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum candidates (default: 3)",
                                "default": 3,
                            },
                        },
                        "required": ["query"],
                    },
                },
            ],
        }
    
    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_initialized()
        
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "search":
            return self._tool_search(args)
        elif tool_name == "status":
            return self._tool_status(args)
        elif tool_name == "repo_candidates":
            return self._tool_repo_candidates(args)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _tool_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enhanced search tool (v2.3.1)."""
        query = args.get("query", "")
        
        if not query.strip():
            return {
                "content": [{"type": "text", "text": "Error: query is required"}],
                "isError": True,
            }
        
        # Build SearchOptions from args
        opts = SearchOptions(
            query=query,
            repo=args.get("repo"),
            limit=min(int(args.get("limit", 10)), 50),
            snippet_lines=int(args.get("context_lines", 5)),
            file_types=args.get("file_types", []),
            path_pattern=args.get("path_pattern"),
            exclude_patterns=args.get("exclude_patterns", []),
            recency_boost=bool(args.get("recency_boost", False)),
            use_regex=bool(args.get("use_regex", False)),
            case_sensitive=bool(args.get("case_sensitive", False)),
        )
        
        hits, meta = self.db.search_v2(opts)
        
        results: List[Dict[str, Any]] = []
        for hit in hits:
            result = {
                "repo": hit.repo,
                "path": hit.path,
                "score": round(hit.score, 3),
                "snippet": hit.snippet,
            }
            # Include enhanced metadata
            if hit.mtime > 0:
                result["mtime"] = hit.mtime
            if hit.size > 0:
                result["size"] = hit.size
            if hit.match_count > 0:
                result["match_count"] = hit.match_count
            if hit.file_type:
                result["file_type"] = hit.file_type
            results.append(result)
        
        output = {
            "query": query,
            "total": len(results),
            "results": results,
            "meta": {
                "fallback_used": meta.get("fallback_used", False),
                "total_scanned": meta.get("total_scanned", 0),
                "regex_mode": meta.get("regex_mode", False),
            },
        }
        
        # Add filter info if used
        filters_used = []
        if opts.file_types:
            filters_used.append(f"file_types={opts.file_types}")
        if opts.path_pattern:
            filters_used.append(f"path_pattern={opts.path_pattern}")
        if opts.exclude_patterns:
            filters_used.append(f"exclude={opts.exclude_patterns}")
        if opts.recency_boost:
            filters_used.append("recency_boost=true")
        if opts.use_regex:
            filters_used.append("regex=true")
        if filters_used:
            output["filters"] = filters_used
        
        return {
            "content": [{"type": "text", "text": json.dumps(output, indent=2, ensure_ascii=False)}],
        }
    
    def _tool_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        status = {
            "index_ready": self.indexer.status.index_ready if self.indexer else False,
            "last_scan_ts": self.indexer.status.last_scan_ts if self.indexer else 0,
            "scanned_files": self.indexer.status.scanned_files if self.indexer else 0,
            "indexed_files": self.indexer.status.indexed_files if self.indexer else 0,
            "errors": self.indexer.status.errors if self.indexer else 0,
            "fts_enabled": self.db.fts_enabled if self.db else False,
            "workspace_root": self.workspace_root,
            "server_version": self.SERVER_VERSION,
        }
        
        return {
            "content": [{"type": "text", "text": json.dumps(status, indent=2)}],
        }
    
    def _tool_repo_candidates(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query", "")
        limit = min(int(args.get("limit", 3)), 5)
        
        if not query.strip():
            return {
                "content": [{"type": "text", "text": "Error: query is required"}],
                "isError": True,
            }
        
        candidates = self.db.repo_candidates(q=query, limit=limit)
        
        output = {
            "query": query,
            "candidates": candidates,
        }
        
        return {
            "content": [{"type": "text", "text": json.dumps(output, indent=2, ensure_ascii=False)}],
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request.get("method")
        params = request.get("params", {})
        msg_id = request.get("id")
        
        is_notification = msg_id is None
        
        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "initialized":
                self.handle_initialized(params)
                return None
            elif method == "tools/list":
                result = self.handle_tools_list(params)
            elif method == "tools/call":
                result = self.handle_tools_call(params)
            elif method == "ping":
                result = {}
            else:
                if is_notification:
                    return None
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
            
            if is_notification:
                return None
            
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            }
        except Exception as e:
            self._log_error(f"Error handling {method}: {e}")
            if is_notification:
                return None
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32000,
                    "message": str(e),
                },
            }
    
    def run(self) -> None:
        self._log_info(f"Starting MCP server (workspace: {self.workspace_root})")
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = self.handle_request(request)
                    
                    if response is not None:
                        print(json.dumps(response), flush=True)
                except json.JSONDecodeError as e:
                    self._log_error(f"JSON decode error: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                        },
                    }
                    print(json.dumps(error_response), flush=True)
        except KeyboardInterrupt:
            self._log_info("Shutting down...")
        finally:
            if self.indexer:
                self.indexer.stop()
            if self.db:
                self.db.close()


def main() -> None:
    workspace_root = os.environ.get("CODEX_WORKSPACE_ROOT")
    
    if not workspace_root:
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            if (parent / ".codex-root").exists():
                workspace_root = str(parent)
                break
        else:
            workspace_root = str(cwd)
    
    server = LocalSearchMCPServer(workspace_root)
    server.run()


if __name__ == "__main__":
    main()
