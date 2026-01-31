#!/usr/bin/env python3
"""
MCP Server for Local Search (STDIO mode)
Follows Model Context Protocol specification: https://modelcontextprotocol.io/specification/2025-11-25

v2.5.0 enhancements:
- Search pagination (offset, total, has_more)
- Detailed status stats (repo_stats)
- Improved UX (root display, fallback reasons)

Usage:
  python3 .codex/tools/local-search/mcp/server.py

Environment:
  LOCAL_SEARCH_WORKSPACE_ROOT - Workspace root directory (default: cwd)
"""
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

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
    SERVER_VERSION = "2.5.0"  # DB Isolation & Pagination
    
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
                    exclude_dirs=[".git", "node_modules", "__pycache__", ".venv", "venv", "target", "build", "dist", "coverage", "vendor"],
                    exclude_globs=["*.min.js", "*.min.css", "*.map", "*.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
                    redact_enabled=True,
                    commit_batch_size=500,
                )
            
            workspace_db_path = Path(self.workspace_root) / ".codex" / "tools" / "local-search" / "data" / "index.db"
            
            debug_db_path = os.environ.get("LOCAL_SEARCH_DB_PATH", "").strip()
            if debug_db_path:
                self._log_info(f"Using debug DB path override: {debug_db_path}")
                db_path = Path(os.path.expanduser(debug_db_path))
            else:
                db_path = workspace_db_path
            
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db = LocalSearchDB(str(db_path))
            self._log_info(f"DB path: {db_path}")
            
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

    def _log_telemetry(self, message: str) -> None:
        """Log telemetry to .codex/log/local-search.log"""
        try:
            log_dir = Path(self.workspace_root) / ".codex" / "log"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "local-search.log"
            
            timestamp = datetime.now().astimezone().isoformat()
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            self._log_error(f"Failed to log telemetry: {e}")
    
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
        """Handle tools/list request - v2.5.0 enhanced schema."""
        return {
            "tools": [
                {
                    "name": "search",
                    "description": "Enhanced search for code/files with pagination. Use BEFORE file exploration to save tokens.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (keywords, function names, regex)",
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
                            "offset": {
                                "type": "integer",
                                "description": "Pagination offset (default: 0)",
                                "default": 0,
                            },
                            "file_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by file extensions, e.g., ['py', 'ts']",
                            },
                            "path_pattern": {
                                "type": "string",
                                "description": "Glob pattern for path matching, e.g., 'src/**/*.ts'",
                            },
                            "exclude_patterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Patterns to exclude, e.g., ['node_modules']",
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
                                "description": "Case-sensitive search (default: false)",
                                "default": False,
                            },
                            "context_lines": {
                                "type": "integer",
                                "description": "Number of context lines in snippet (default: 5)",
                                "default": 5,
                             },
                            "scope": {
                                "type": "string",
                                "description": "Alias for 'repo'",
                            },
                            "type": {
                                "type": "string",
                                "enum": ["docs", "code"],
                                "description": "Filter by type: 'docs' or 'code'",
                            },
                         },
                        "required": ["query"],
                    },
                },
                {
                    "name": "status",
                    "description": "Get indexer status. Use details=true for per-repo stats.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "details": {
                                "type": "boolean",
                                "description": "Include detailed repo stats (default: false)",
                                "default": False,
                            }
                        },
                    },
                },
                {
                    "name": "repo_candidates",
                    "description": "Find candidate repositories for a query.",
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
                {
                    "name": "list_files",
                    "description": "List indexed files for debugging.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "repo": {
                                "type": "string",
                                "description": "Filter by repository name",
                            },
                            "path_pattern": {
                                "type": "string",
                                "description": "Glob pattern for path matching",
                            },
                            "file_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by file extensions",
                            },
                            "include_hidden": {
                                "type": "boolean",
                                "description": "Include hidden directories (default: false)",
                                "default": False,
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 100)",
                                "default": 100,
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Pagination offset (default: 0)",
                                "default": 0,
                            },
                        },
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
        elif tool_name == "list_files":
            return self._tool_list_files(args)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _tool_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enhanced search tool (v2.5.0)."""
        start_ts = time.time()
        query = args.get("query", "")
        
        if not query.strip():
            return {
                "content": [{"type": "text", "text": "Error: query is required"}],
                "isError": True,
            }
        
        repo = args.get("scope") or args.get("repo")
        if repo == "workspace":
            repo = None
        
        file_types = list(args.get("file_types", []))
        search_type = args.get("type")
        if search_type == "docs":
            doc_exts = ["md", "txt", "pdf", "docx", "rst", "pdf"]
            file_types.extend([e for e in doc_exts if e not in file_types])
        
        limit = min(int(args.get("limit", 10)), 50)
        offset = max(int(args.get("offset", 0)), 0)

        # Determine total_mode based on scale (v2.5.1)
        total_mode = "exact"
        if self.db:
            status = self.db.get_index_status()
            total_files = status.get("total_files", 0)
            repo_stats = self.db.get_repo_stats()
            total_repos = len(repo_stats)
            
            if total_repos > 50 or total_files > 150000:
                total_mode = "approx"
            elif total_repos > 20 or total_files > 50000:
                if args.get("path_pattern"):
                    total_mode = "approx"

        opts = SearchOptions(
            query=query,
            repo=repo,
            limit=limit,
            offset=offset,
            snippet_lines=int(args.get("context_lines", 5)),
            file_types=file_types,
            path_pattern=args.get("path_pattern"),
            exclude_patterns=args.get("exclude_patterns", []),
            recency_boost=bool(args.get("recency_boost", False)),
            use_regex=bool(args.get("use_regex", False)),
            case_sensitive=bool(args.get("case_sensitive", False)),
            total_mode=total_mode,
        )
        
        hits, db_meta = self.db.search_v2(opts)
        
        results: List[Dict[str, Any]] = []
        for hit in hits:
            # UX: Remap __root__ to (root)
            repo_display = hit.repo if hit.repo != "__root__" else "(root)"
            
            result = {
                "repo": hit.repo,
                "repo_display": repo_display,
                "path": hit.path,
                "score": hit.score,
                "reason": hit.hit_reason,
                "snippet": hit.snippet,
            }
            if hit.mtime > 0:
                result["mtime"] = hit.mtime
            if hit.size > 0:
                result["size"] = hit.size
            if hit.match_count > 0:
                result["match_count"] = hit.match_count
            if hit.file_type:
                result["file_type"] = hit.file_type
            results.append(result)
        
        # Result Grouping
        repo_groups = {}
        for r in results:
            repo = r["repo"]
            if repo not in repo_groups:
                repo_groups[repo] = {"count": 0, "top_score": 0.0}
            repo_groups[repo]["count"] += 1
            repo_groups[repo]["top_score"] = max(repo_groups[repo]["top_score"], r["score"])
        
        # Sort repos by top_score
        top_repos = sorted(repo_groups.keys(), key=lambda k: repo_groups[k]["top_score"], reverse=True)[:2]
        
        scope = f"repo:{opts.repo}" if opts.repo else "workspace"
        
        # Total/HasMore Logic (v2.5.1 Accuracy)
        total = db_meta.get("total", len(results))
        total_mode = db_meta.get("total_mode", "exact")
        
        # Even if SQL total is exact, exclude_patterns might reduce it further
        is_exact_total = (total_mode == "exact")
        if opts.exclude_patterns and total > 0:
             is_exact_total = False
        
        has_more = total > (offset + limit)
        
        warnings = []
        if has_more:
            next_offset = offset + limit
            warnings.append(f"More results available. Use offset={next_offset} to see next page.")
        if not opts.repo and total > 50:
            warnings.append("Many results found. Consider specifying 'repo' to filter.")
        
        # Determine fallback reason code
        fallback_reason_code = None
        if db_meta.get("fallback_used"):
            fallback_reason_code = "FTS_FAILED" # General fallback
        elif not results and total == 0:
            fallback_reason_code = "NO_MATCHES"

        regex_error = db_meta.get("regex_error")
        if regex_error:
             warnings.append(f"Regex Error: {regex_error}")

        output = {
            "query": query,
            "scope": scope,
            "total": total,
            "total_mode": total_mode,
            "is_exact_total": is_exact_total,
            "approx_total": total if total_mode == "approx" else None,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "next_offset": offset + limit if has_more else None,
            "warnings": warnings,
            "results": results,
            "repo_summary": repo_groups,
            "top_candidate_repos": top_repos,
            "meta": {
                "total_mode": total_mode,
                "fallback_used": db_meta.get("fallback_used", False),
                "fallback_reason_code": fallback_reason_code,
                "total_scanned": db_meta.get("total_scanned", 0),
                "regex_mode": db_meta.get("regex_mode", False),
                "regex_error": regex_error,
            },
        }
        
        if not results:
            reason = "No matches found."
            active_filters = []
            if opts.repo: active_filters.append(f"repo='{opts.repo}'")
            if opts.file_types: active_filters.append(f"file_types={opts.file_types}")
            if opts.path_pattern: active_filters.append(f"path_pattern='{opts.path_pattern}'")
            if opts.exclude_patterns: active_filters.append(f"exclude_patterns={opts.exclude_patterns}")
            
            if active_filters:
                reason = f"No matches found with filters: {', '.join(active_filters)}"
            
            output["meta"]["fallback_reason"] = reason
            
            hints = [
                "Try a broader query or remove filters.",
                "Check if the file is indexed using 'list_files' tool.",
                "If searching for a specific pattern, try 'use_regex=true'."
            ]
            if opts.file_types or opts.path_pattern:
                hints.insert(0, "Try removing 'file_types' or 'path_pattern' filters.")
            
            output["hints"] = hints
        
        
        # Telemetry: Log search stats
        latency_ms = int((time.time() - start_ts) * 1000)
        snippet_chars = sum(len(r.get("snippet", "")) for r in results)
        
        self._log_telemetry(f"tool=search query='{opts.query}' results={len(results)} snippet_chars={snippet_chars} latency={latency_ms}ms")

        return {
            "content": [{"type": "text", "text": json.dumps(output, indent=2, ensure_ascii=False)}],
        }
    
    def _tool_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        details = bool(args.get("details", False))
        
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
        
        # v2.5.2: Add config info for debugging
        if self.cfg:
            status["config"] = {
                "include_ext": self.cfg.include_ext,
                "exclude_dirs": self.cfg.exclude_dirs,
                "exclude_globs": getattr(self.cfg, "exclude_globs", []),
                "max_file_bytes": self.cfg.max_file_bytes,
            }
        
        if details and self.db:
            status["repo_stats"] = self.db.get_repo_stats()
        
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
        
        for candidate in candidates:
            score = candidate.get("score", 0)
            if score >= 10:
                reason = f"High match ({score} files contain '{query}')"
            elif score >= 5:
                reason = f"Moderate match ({score} files)"
            else:
                reason = f"Low match ({score} files)"
            candidate["reason"] = reason
        
        output = {
            "query": query,
            "candidates": candidates,
            "hint": "Use 'repo' parameter in search to narrow down scope after selection",
        }
        
        return {
            "content": [{"type": "text", "text": json.dumps(output, indent=2, ensure_ascii=False)}],
        }
    
    def _tool_list_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        start_ts = time.time()
        files, meta = self.db.list_files(
            repo=args.get("repo"),
            path_pattern=args.get("path_pattern"),
            file_types=args.get("file_types"),
            include_hidden=bool(args.get("include_hidden", False)),
            limit=int(args.get("limit", 100)),
            offset=int(args.get("offset", 0)),
        )
        
        output = {
            "files": files,
            "meta": meta,
        }
        
        json_output = json.dumps(output, indent=2, ensure_ascii=False)
        
        # Telemetry: Log list_files stats
        latency_ms = int((time.time() - start_ts) * 1000)
        payload_bytes = len(json_output.encode('utf-8'))
        repo_val = args.get("repo", "all")
        self._log_telemetry(f"tool=list_files repo='{repo_val}' files={len(files)} payload_bytes={payload_bytes} latency={latency_ms}ms")
        
        return {
            "content": [{"type": "text", "text": json_output}],
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
    workspace_root = os.environ.get("LOCAL_SEARCH_WORKSPACE_ROOT")
    
    if not workspace_root:
        # Search for .codex-root marker from cwd
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