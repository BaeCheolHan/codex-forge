
import os
import sys
from pathlib import Path
import sqlite3

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / ".codex" / "tools" / "local-search" / "data" / "index.db"

def test_root_files_excluded():
    """Verify that root-level files like AGENTS.md are NOT in the database."""
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping check.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Check for AGENTS.md or GEMINI.md in root
    cursor.execute("SELECT path FROM files WHERE path IN ('AGENTS.md', 'GEMINI.md', 'install.sh', 'uninstall.sh')")
    results = cursor.fetchall()
    
    conn.close()
    
    if results:
        print(f"✗ Found root files in DB: {results}")
        sys.exit(1)
    else:
        print("✓ Root files (AGENTS.md, etc.) are correctly excluded from DB.")

if __name__ == "__main__":
    test_root_files_excluded()
