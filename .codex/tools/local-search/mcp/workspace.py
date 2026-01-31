#!/usr/bin/env python3
"""
Workspace management for Local Search MCP Server.
Handles workspace detection and global path resolution.
"""
import os
from pathlib import Path
from typing import Optional


class WorkspaceManager:
    """Manages workspace detection and global paths."""
    
    @staticmethod
    def detect_workspace(root_uri: Optional[str] = None) -> str:
        """
        Detect workspace root directory.
        
        Priority:
        1. root_uri parameter (from MCP initialize)
        2. LOCAL_SEARCH_WORKSPACE_ROOT environment variable
        3. Search for .codex-root marker from cwd upward
        4. Fallback to cwd
        
        Args:
            root_uri: Optional URI from MCP initialize (file:// prefix will be stripped)
        
        Returns:
            Absolute path to workspace root
        """
        # 1. Use root_uri if provided
        if root_uri:
            if root_uri.startswith("file://"):
                return root_uri[7:]
            return root_uri
        
        # 2. Check environment variable
        workspace_root = os.environ.get("LOCAL_SEARCH_WORKSPACE_ROOT")
        if workspace_root:
            return workspace_root
        
        # 3. Search for .codex-root marker
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            if (parent / ".codex-root").exists():
                return str(parent)
        
        # 4. Fallback to cwd
        return str(cwd)
    
    @staticmethod
    def get_global_data_dir() -> Path:
        """Get global data directory: ~/.local/share/local-search/"""
        return Path.home() / ".local" / "share" / "local-search"
    
    @staticmethod
    def get_global_db_path() -> Path:
        """Get global DB path: ~/.local/share/local-search/index.db"""
        return WorkspaceManager.get_global_data_dir() / "index.db"
    
    @staticmethod
    def get_global_log_dir() -> Path:
        """Get global log directory: ~/.local/share/local-search/logs/"""
        return WorkspaceManager.get_global_data_dir() / "logs"
