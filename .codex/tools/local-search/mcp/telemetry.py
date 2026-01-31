#!/usr/bin/env python3
"""
Telemetry and logging for Local Search MCP Server.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class TelemetryLogger:
    """Handles logging and telemetry for MCP server."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize telemetry logger.
        
        Args:
            log_dir: Directory for log files. If None, uses global log dir.
        """
        self.log_dir = log_dir
    
    def log_error(self, message: str) -> None:
        """Log error message to stderr."""
        print(f"[local-search] ERROR: {message}", file=sys.stderr, flush=True)
    
    def log_info(self, message: str) -> None:
        """Log info message to stderr."""
        print(f"[local-search] INFO: {message}", file=sys.stderr, flush=True)
    
    def log_telemetry(self, message: str) -> None:
        """
        Log telemetry to file.
        
        Args:
            message: Telemetry message to log
        """
        if not self.log_dir:
            return
        
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            log_file = self.log_dir / "local-search.log"
            
            timestamp = datetime.now().astimezone().isoformat()
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            self.log_error(f"Failed to log telemetry: {e}")
