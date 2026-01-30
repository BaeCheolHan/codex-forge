
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".codex" / "tools" / "local-search" / "app"))
sys.path.insert(0, str(PROJECT_ROOT / ".codex" / "tools" / "local-search" / "mcp"))

from server import LocalSearchMCPServer
from db import LocalSearchDB
from types import SimpleNamespace
from unittest.mock import MagicMock

class TestSearchUX(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace_root = Path(self.tmp_dir.name)
        
        # Setup DB
        db_path = self.workspace_root / ".codex" / "tools" / "local-search" / "data" / "index.db"
        self.db = LocalSearchDB(str(db_path))
        
        # Setup Server with mocked config
        self.server = LocalSearchMCPServer(str(self.workspace_root))
        self.server.db = self.db
        
        # Mock Config object using SimpleNamespace
        self.server.cfg = SimpleNamespace(
            workspace_root=str(self.workspace_root),
            include_ext=[".py", ".md"],
            exclude_dirs=[".git", "node_modules"],
            exclude_globs=["*.log"],
            max_file_bytes=1024 * 1024
        )
        # Mock indexer status using SimpleNamespace
        self.server.indexer = MagicMock()
        self.server.indexer.status = SimpleNamespace(
            index_ready=True,
            last_scan_ts=123456789.0,
            scanned_files=10,
            indexed_files=5,
            errors=0
        )
        
        # Add some dummy data
        self.db.upsert_files([
            ("src/main.py", "repo1", 1000, 100, "def main(): pass"),
            ("docs/readme.md", "repo1", 1000, 500, "# Readme")
        ])

    def tearDown(self):
        self.db.close()
        self.tmp_dir.cleanup()

    def test_status_includes_config(self):
        """Verify status command includes config details."""
        res = self.server._tool_status({})
        content = json.loads(res["content"][0]["text"])
        
        self.assertIn("config", content)
        self.assertEqual(content["config"]["include_ext"], [".py", ".md"])
        self.assertEqual(content["config"]["exclude_dirs"], [".git", "node_modules"])
        print("✓ Status includes config info")

    def test_zero_result_hints(self):
        """Verify hints are improved for zero results."""
        # Case 1: No match with filters
        args = {
            "query": "nonexistent_function", 
            "file_types": ["py"],
            "path_pattern": "src/**"
        }
        res = self.server._tool_search(args)
        content = json.loads(res["content"][0]["text"])
        
        self.assertEqual(content["total"], 0)
        self.assertIn("hints", content)
        hints = content["hints"]
        
        # Expect specific hint about filters
        filter_hint = "Try removing 'file_types' or 'path_pattern' filters."
        self.assertIn(filter_hint, hints)
        print("✓ Zero result hints include filter advice")
        
        # Case 2: No match without filters (generic hint)
        args = {"query": "nonexistent_function"}
        res = self.server._tool_search(args)
        content = json.loads(res["content"][0]["text"])
        hints = content["hints"]
        
        # Filter hint should NOT be present
        self.assertNotIn(filter_hint, hints)
        self.assertIn("Try a broader query or remove filters.", hints)
        print("✓ Generic hints for simple no-match")

if __name__ == "__main__":
    unittest.main()
