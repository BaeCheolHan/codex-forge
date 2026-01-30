
import os
import sys
import tempfile
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".codex" / "tools" / "local-search" / "app"))

from db import LocalSearchDB, SearchOptions

def setup_test_db(db_path):
    db = LocalSearchDB(db_path)
    # Add dummy data
    files = [
        ("src/main.py", "repo1", 1000, 100, "print('hello')"),
        ("src/utils.py", "repo1", 1001, 200, "def util(): pass"),
        ("tests/test_main.py", "repo1", 1002, 150, "def test_hello(): pass"),
        ("docs/index.md", "repo1", 1003, 500, "# Welcome"),
        ("README.md", "__root__", 1004, 300, "Project info"),
        ("package.json", "repo2", 1005, 400, '{"name": "test"}'),
        ("src/app.ts", "repo2", 1006, 600, "console.log('hi')"),
    ]
    db.upsert_files(files)
    return db

def test_file_type_filter():
    with tempfile.NamedTemporaryFile() as tmp:
        db = setup_test_db(tmp.name)
        
        # Test .py files
        opts = SearchOptions(query="def", file_types=["py"])
        hits, meta = db.search_v2(opts)
        assert all(h.path.endswith(".py") for h in hits)
        assert len(hits) == 2 # utils.py, test_main.py
        print("✓ File type filter (.py) passed")
        
        # Test .md files
        opts = SearchOptions(query="Welcome", file_types=["md"])
        hits, meta = db.search_v2(opts)
        assert len(hits) == 1
        assert hits[0].path == "docs/index.md"
        print("✓ File type filter (.md) passed")
        db.close()

def test_path_pattern_filter():
    with tempfile.NamedTemporaryFile() as tmp:
        db = setup_test_db(tmp.name)
        
        # Test src/**
        opts = SearchOptions(query="o", path_pattern="src/**")
        hits, meta = db.search_v2(opts)
        assert all(h.path.startswith("src/") for h in hits)
        print("✓ Path pattern filter (src/**) passed")
        
        # Test **/test*
        opts = SearchOptions(query="def", path_pattern="**/test*")
        hits, meta = db.search_v2(opts)
        assert all("test" in h.path for h in hits)
        assert len(hits) == 1
        assert hits[0].path == "tests/test_main.py"
        print("✓ Path pattern filter (**/test*) passed")
        db.close()

def test_pagination():
    with tempfile.NamedTemporaryFile() as tmp:
        db = setup_test_db(tmp.name)
        
        # 'def' is in utils.py and test_main.py (2 results)
        opts = SearchOptions(query="def", limit=1, offset=0)
        hits1, meta1 = db.search_v2(opts)
        assert len(hits1) == 1
        
        opts = SearchOptions(query="def", limit=1, offset=1)
        hits2, meta2 = db.search_v2(opts)
        assert len(hits2) == 1
        
        # Ensure no overlap
        assert hits1[0].path != hits2[0].path
        
        print("✓ Pagination (offset/limit) passed")
        db.close()

def test_total_mode():
    with tempfile.NamedTemporaryFile() as tmp:
        db = setup_test_db(tmp.name)
        
        opts = SearchOptions(query="def", total_mode="exact")
        hits, meta = db.search_v2(opts)
        assert meta["total"] == 2
        assert meta["total_mode"] == "exact"
        print("✓ Total mode (exact) passed")
        db.close()

if __name__ == "__main__":
    try:
        test_file_type_filter()
        test_path_pattern_filter()
        test_pagination()
        test_total_mode()
        print("\nAll Search v2 tests passed!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
