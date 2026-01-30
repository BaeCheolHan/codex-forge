
import os
import tempfile
from pathlib import Path
import sys

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".codex" / "tools" / "local-search" / "app"))

from config import Config

def test_db_path_isolation():
    """Verify that the DB path is always within the workspace_root by default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_workspace = Path(tmpdir)
        config_path = tmp_workspace / "config.json"
        
        # Create a dummy config
        import json
        with open(config_path, "w") as f:
            json.dump({
                "workspace_root": str(tmp_workspace),
                "server_host": "127.0.0.1",
                "server_port": 47777
            }, f)
        
        # Load config
        config = Config.load(str(config_path))
        
        expected_db_path = tmp_workspace / ".codex" / "tools" / "local-search" / "data" / "index.db"
        
        print(f"Workspace: {tmp_workspace}")
        print(f"DB Path: {config.db_path}")
        print(f"Expected: {expected_db_path}")
        
        assert Path(config.db_path) == expected_db_path
        print("✓ DB Path is correctly isolated within workspace.")

def test_db_path_override_allowed():
    """Verify that absolute DB path override is still allowed (for debugging)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_workspace = Path(tmpdir)
        config_path = tmp_workspace / "config.json"
        
        custom_db_path = Path(tmpdir) / "custom" / "my.db"
        
        import json
        with open(config_path, "w") as f:
            json.dump({
                "workspace_root": str(tmp_workspace),
                "db_path": str(custom_db_path)
            }, f)
            
        config = Config.load(str(config_path))
        assert Path(config.db_path) == custom_db_path
        print("✓ Absolute DB Path override is allowed.")

if __name__ == "__main__":
    try:
        test_db_path_isolation()
        test_db_path_override_allowed()
        print("\nAll isolation tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
