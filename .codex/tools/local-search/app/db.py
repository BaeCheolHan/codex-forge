import fnmatch
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional


@dataclass
class SearchHit:
    """Enhanced search result with metadata."""
    repo: str
    path: str
    score: float
    snippet: str
    # v2.3.1: Added metadata
    mtime: int = 0
    size: int = 0
    match_count: int = 0
    file_type: str = ""


@dataclass
class SearchOptions:
    """Search configuration options (v2.3.1)."""
    query: str = ""
    repo: Optional[str] = None
    limit: int = 20
    snippet_lines: int = 5
    # New in v2.3.1
    file_types: list[str] = field(default_factory=list)  # e.g., ["py", "ts"]
    path_pattern: Optional[str] = None  # e.g., "src/**/*.ts"
    exclude_patterns: list[str] = field(default_factory=list)  # e.g., ["node_modules", "build"]
    recency_boost: bool = False  # Boost recently modified files
    use_regex: bool = False  # Use regex instead of FTS
    case_sensitive: bool = False  # Case-sensitive regex


class LocalSearchDB:
    """SQLite + optional FTS5 backed index.

    Design goals:
    - Low IO overhead: batch writes, WAL.
    - Thread safety: separate read/write connections.
    - Safer defaults: DB stored under user cache dir by default.
    
    v2.3.1 enhancements:
    - File type filtering
    - Path pattern matching (glob)
    - Exclude patterns
    - Recency boost
    - Regex search mode
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Separate connections: writer (indexer) and reader (HTTP).
        self._write = sqlite3.connect(db_path, check_same_thread=False)
        self._read = sqlite3.connect(db_path, check_same_thread=False)
        self._write.row_factory = sqlite3.Row
        self._read.row_factory = sqlite3.Row

        self._lock = threading.Lock()

        self._apply_pragmas(self._write)
        self._apply_pragmas(self._read)

        self._fts_enabled = self._try_enable_fts(self._write)
        self._init_schema()

    @staticmethod
    def _apply_pragmas(conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA busy_timeout=2000;")
        conn.execute("PRAGMA cache_size=-20000;")

    @property
    def fts_enabled(self) -> bool:
        return self._fts_enabled

    def close(self) -> None:
        for c in (self._read, self._write):
            try:
                c.close()
            except Exception:
                pass

    def _try_enable_fts(self, conn: sqlite3.Connection) -> bool:
        try:
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS __fts_test USING fts5(x)")
            conn.execute("DROP TABLE IF EXISTS __fts_test")
            return True
        except Exception:
            return False

    def _init_schema(self) -> None:
        with self._lock:
            cur = self._write.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                  path TEXT PRIMARY KEY,
                  repo TEXT NOT NULL,
                  mtime INTEGER NOT NULL,
                  size INTEGER NOT NULL,
                  content TEXT NOT NULL
                );
                """
            )
            # Index for efficient filtering
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repo);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_mtime ON files(mtime DESC);")
            
            if self._fts_enabled:
                cur.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS files_fts
                    USING fts5(path, repo, content, content='files', content_rowid='rowid');
                    """
                )
                cur.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
                      INSERT INTO files_fts(rowid, path, repo, content) VALUES (new.rowid, new.path, new.repo, new.content);
                    END;
                    """
                )
                cur.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
                      INSERT INTO files_fts(files_fts, rowid, path, repo, content) VALUES('delete', old.rowid, old.path, old.repo, old.content);
                    END;
                    """
                )
                cur.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
                      INSERT INTO files_fts(files_fts, rowid, path, repo, content) VALUES('delete', old.rowid, old.path, old.repo, old.content);
                      INSERT INTO files_fts(rowid, path, repo, content) VALUES (new.rowid, new.path, new.repo, new.content);
                    END;
                    """
                )
            self._write.commit()

    def upsert_files(self, rows: Iterable[tuple[str, str, int, int, str]]) -> int:
        rows_list = list(rows)
        if not rows_list:
            return 0
        with self._lock:
            cur = self._write.cursor()
            cur.execute("BEGIN")
            cur.executemany(
                """
                INSERT INTO files(path, repo, mtime, size, content)
                VALUES(?,?,?,?,?)
                ON CONFLICT(path) DO UPDATE SET
                  repo=excluded.repo,
                  mtime=excluded.mtime,
                  size=excluded.size,
                  content=excluded.content;
                """,
                rows_list,
            )
            self._write.commit()
        return len(rows_list)

    def delete_files(self, paths: Iterable[str]) -> int:
        paths_list = list(paths)
        if not paths_list:
            return 0
        with self._lock:
            cur = self._write.cursor()
            cur.execute("BEGIN")
            cur.executemany("DELETE FROM files WHERE path=?", [(p,) for p in paths_list])
            self._write.commit()
        return len(paths_list)

    def get_file_meta(self, path: str) -> Optional[tuple[int, int]]:
        row = self._read.execute("SELECT mtime, size FROM files WHERE path=?", (path,)).fetchone()
        if not row:
            return None
        return int(row["mtime"]), int(row["size"])

    def get_index_status(self) -> dict[str, Any]:
        """Get index metadata for debugging/UI (v2.4.2)."""
        row = self._read.execute("SELECT COUNT(1) AS c, MAX(mtime) AS last_mtime FROM files").fetchone()
        count = int(row["c"]) if row and row["c"] else 0
        last_mtime = int(row["last_mtime"]) if row and row["last_mtime"] else 0
        
        return {
            "total_files": count,
            "last_scan_time": last_mtime,
            "db_size_bytes": Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
        }

    def count_files(self) -> int:
        row = self._read.execute("SELECT COUNT(1) AS c FROM files").fetchone()
        return int(row["c"]) if row else 0

    def list_files(
        self, 
        repo: Optional[str] = None,
        path_pattern: Optional[str] = None,
        file_types: Optional[list[str]] = None,
        include_hidden: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """List indexed files for debugging (v2.4.0).
        
        Args:
            repo: Filter by repository
            path_pattern: Glob pattern for path matching
            file_types: Filter by file extensions
            include_hidden: Include hidden directories like .codex
            limit: Maximum results (max 500)
            offset: Pagination offset
            
        Returns:
            tuple of (files, metadata)
        """
        limit = min(int(limit), 500)
        offset = max(int(offset), 0)
        
        where_clauses = []
        params: list[Any] = []
        
        if repo:
            where_clauses.append("f.repo = ?")
            params.append(repo)
        
        if not include_hidden:
            # Exclude hidden directories by default
            where_clauses.append("f.path NOT LIKE '%/.%'")
            where_clauses.append("f.path NOT LIKE '.%'")
        
        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        sql = f"""
            SELECT f.repo AS repo,
                   f.path AS path,
                   f.mtime AS mtime,
                   f.size AS size
            FROM files f
            WHERE {where}
            ORDER BY f.repo, f.path
            LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])
        
        rows = self._read.execute(sql, params).fetchall()
        
        # Apply in-memory filters that SQL can't handle well
        files: list[dict[str, Any]] = []
        for r in rows:
            path = r["path"]
            
            # File type filter
            if file_types:
                if not self._matches_file_types(path, file_types):
                    continue
            
            # Path pattern filter
            if path_pattern:
                if not self._matches_path_pattern(path, path_pattern):
                    continue
            
            files.append({
                "repo": r["repo"],
                "path": path,
                "mtime": int(r["mtime"]),
                "size": int(r["size"]),
                "file_type": self._get_file_extension(path),
            })
        
        # Get total count for pagination info
        count_sql = f"SELECT COUNT(1) AS c FROM files f WHERE {where}"
        count_params = params[:-2]  # Remove limit/offset
        total = self._read.execute(count_sql, count_params).fetchone()["c"]
        
        # Get repo breakdown
        repo_sql = """
            SELECT repo, COUNT(1) AS file_count
            FROM files
            GROUP BY repo
            ORDER BY file_count DESC;
        """
        repo_rows = self._read.execute(repo_sql).fetchall()
        repos = [{"repo": r["repo"], "file_count": r["file_count"]} for r in repo_rows]
        
        meta = {
            "total": total,
            "returned": len(files),
            "offset": offset,
            "limit": limit,
            "repos": repos,
            "include_hidden": include_hidden,
        }
        
        return files, meta

    # ========== Helper Methods ==========
    
    def _get_file_extension(self, path: str) -> str:
        """Extract file extension without dot."""
        ext = Path(path).suffix
        return ext[1:].lower() if ext else ""
    
    def _matches_file_types(self, path: str, file_types: list[str]) -> bool:
        """Check if path matches any of the file types."""
        if not file_types:
            return True
        ext = self._get_file_extension(path)
        return ext in [ft.lower().lstrip('.') for ft in file_types]
    
    def _matches_path_pattern(self, path: str, pattern: Optional[str]) -> bool:
        """Check if path matches glob pattern."""
        if not pattern:
            return True
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, f"**/{pattern}")
    
    def _matches_exclude_patterns(self, path: str, patterns: list[str]) -> bool:
        """Check if path matches any exclude pattern."""
        if not patterns:
            return False
        for p in patterns:
            if p in path or fnmatch.fnmatch(path, f"*{p}*"):
                return True
        return False
    
    def _count_matches(self, content: str, query: str, use_regex: bool, case_sensitive: bool) -> int:
        """Count number of matches in content."""
        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                return len(re.findall(query, content, flags))
            except re.error:
                return 0
        else:
            if case_sensitive:
                return content.count(query)
            return content.lower().count(query.lower())
    
    def _calculate_recency_score(self, mtime: int, base_score: float) -> float:
        """Apply recency boost to score. Recent files get higher scores."""
        now = time.time()
        age_days = (now - mtime) / 86400  # seconds -> days
        
        # Boost factor: 1.5x for today, decreasing over time
        if age_days < 1:
            boost = 1.5
        elif age_days < 7:
            boost = 1.3
        elif age_days < 30:
            boost = 1.1
        else:
            boost = 1.0
        
        return base_score * boost

    def _extract_terms(self, q: str) -> list[str]:
        raw = [t.strip().strip('"\'') for t in (q or "").split()]
        out: list[str] = []
        for t in raw:
            if not t or t in {"AND", "OR", "NOT"}:
                continue
            if ":" in t and len(t.split(":", 1)[0]) <= 10:
                t = t.split(":", 1)[1]
            t = t.strip()
            if t:
                out.append(t)
        return out

    def _snippet_around(self, content: str, terms: list[str], max_lines: int, 
                        highlight: bool = True) -> str:
        """Extract snippet around match with optional highlighting."""
        if max_lines <= 0:
            return ""
        lines = content.splitlines()
        if not lines:
            return ""

        lower = content.lower()
        pos = -1
        matched_term = ""
        for t in terms:
            p = lower.find(t.lower())
            if p != -1:
                pos = p
                matched_term = t
                break

        if pos == -1:
            slice_lines = lines[:max_lines]
            return "\n".join(f"L{i+1}: {ln}" for i, ln in enumerate(slice_lines))

        line_idx = lower[:pos].count("\n")
        half = max_lines // 2
        start = max(0, line_idx - half)
        end = min(len(lines), start + max_lines)
        start = max(0, end - max_lines)

        out_lines = []
        for i in range(start, end):
            line = lines[i]
            # Highlight matched term
            if highlight and matched_term:
                pattern = re.compile(re.escape(matched_term), re.IGNORECASE)
                line = pattern.sub(f">>>{matched_term}<<<", line)
            prefix = "→" if i == line_idx else " "
            out_lines.append(f"{prefix}L{i+1}: {line}")
        return "\n".join(out_lines)

    # ========== Main Search Methods ==========

    def search_v2(self, opts: SearchOptions) -> tuple[list[SearchHit], dict[str, Any]]:
        """Enhanced search with all options (v2.3.1).
        
        Returns:
            tuple of (hits, metadata)
        """
        q = (opts.query or "").strip()
        if not q:
            return [], {"fallback_used": False, "total_scanned": 0}

        terms = self._extract_terms(q)
        meta: dict[str, Any] = {"fallback_used": False, "total_scanned": 0}
        
        # Regex mode: scan all matching files
        if opts.use_regex:
            return self._search_regex(opts, terms, meta)
        
        # FTS mode (default)
        if self._fts_enabled:
            result = self._search_fts(opts, terms, meta)
            if result is not None:
                return result
            # Fall through to LIKE if FTS fails
        
        # LIKE fallback
        return self._search_like(opts, terms, meta)

    def _search_fts(self, opts: SearchOptions, terms: list[str], 
                    meta: dict[str, Any]) -> Optional[tuple[list[SearchHit], dict[str, Any]]]:
        """FTS5 search with BM25 scoring."""
        where = "files_fts MATCH ?"
        params: list[Any] = [opts.query]
        
        if opts.repo:
            where += " AND f.repo = ?"
            params.append(opts.repo)

        # Need to fetch more to filter, then limit
        fetch_limit = opts.limit * 5 if (opts.file_types or opts.path_pattern or opts.exclude_patterns) else opts.limit
        
        sql = f"""
            SELECT f.repo AS repo,
                   f.path AS path,
                   f.mtime AS mtime,
                   f.size AS size,
                   bm25(files_fts) AS score,
                   f.content AS content
            FROM files_fts
            JOIN files f ON f.rowid = files_fts.rowid
            WHERE {where}
            ORDER BY {"f.mtime DESC, score" if opts.recency_boost else "score"}
            LIMIT ?;
        """
        params.append(int(fetch_limit))
        
        try:
            rows = self._read.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            return None  # Fall back to LIKE
        
        hits = self._process_rows(rows, opts, terms)
        meta["total_scanned"] = len(rows)
        return hits[:opts.limit], meta

    def _search_like(self, opts: SearchOptions, terms: list[str], 
                     meta: dict[str, Any]) -> tuple[list[SearchHit], dict[str, Any]]:
        """LIKE fallback search."""
        meta["fallback_used"] = True
        
        like_q = opts.query.replace("%", "\\%").replace("_", "\\_")
        where = "f.content LIKE ? ESCAPE '\\'"
        params: list[Any] = [f"%{like_q}%"]
        
        if opts.repo:
            where += " AND f.repo = ?"
            params.append(opts.repo)

        fetch_limit = opts.limit * 5 if (opts.file_types or opts.path_pattern or opts.exclude_patterns) else opts.limit
        
        sql = f"""
            SELECT f.repo AS repo,
                   f.path AS path,
                   f.mtime AS mtime,
                   f.size AS size,
                   0.0 AS score,
                   f.content AS content
            FROM files f
            WHERE {where}
            ORDER BY {"f.mtime DESC" if opts.recency_boost else "f.path"}
            LIMIT ?;
        """
        params.append(int(fetch_limit))
        rows = self._read.execute(sql, params).fetchall()
        
        hits = self._process_rows(rows, opts, terms)
        meta["total_scanned"] = len(rows)
        return hits[:opts.limit], meta

    def _search_regex(self, opts: SearchOptions, terms: list[str], 
                      meta: dict[str, Any]) -> tuple[list[SearchHit], dict[str, Any]]:
        """Regex search mode."""
        meta["regex_mode"] = True
        
        # Validate regex
        flags = 0 if opts.case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(opts.query, flags)
        except re.error as e:
            meta["regex_error"] = str(e)
            return [], meta
        
        where = "1=1"
        params: list[Any] = []
        if opts.repo:
            where = "f.repo = ?"
            params.append(opts.repo)
        
        # Scan files (limited for performance)
        sql = f"""
            SELECT f.repo AS repo,
                   f.path AS path,
                   f.mtime AS mtime,
                   f.size AS size,
                   f.content AS content
            FROM files f
            WHERE {where}
            ORDER BY {"f.mtime DESC" if opts.recency_boost else "f.path"}
            LIMIT 5000;
        """
        rows = self._read.execute(sql, params).fetchall()
        meta["total_scanned"] = len(rows)
        
        hits: list[SearchHit] = []
        for r in rows:
            path = r["path"]
            content = r["content"] or ""
            
            # Apply filters
            if not self._matches_file_types(path, opts.file_types):
                continue
            if not self._matches_path_pattern(path, opts.path_pattern):
                continue
            if self._matches_exclude_patterns(path, opts.exclude_patterns):
                continue
            
            # Check regex match
            matches = pattern.findall(content)
            if not matches:
                continue
            
            match_count = len(matches)
            score = float(match_count)
            if opts.recency_boost:
                score = self._calculate_recency_score(int(r["mtime"]), score)
            
            snippet = self._snippet_around(content, [opts.query], opts.snippet_lines, highlight=True)
            
            hits.append(SearchHit(
                repo=r["repo"],
                path=path,
                score=score,
                snippet=snippet,
                mtime=int(r["mtime"]),
                size=int(r["size"]),
                match_count=match_count,
                file_type=self._get_file_extension(path),
            ))
        
        # Sort by score (match count + recency)
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:opts.limit], meta

    def _process_rows(self, rows: list, opts: SearchOptions, 
                      terms: list[str]) -> list[SearchHit]:
        """Process raw DB rows into SearchHit objects with filtering."""
        hits: list[SearchHit] = []
        
        for r in rows:
            path = r["path"]
            content = r["content"] or ""
            mtime = int(r["mtime"])
            size = int(r["size"])
            
            # Apply filters
            if not self._matches_file_types(path, opts.file_types):
                continue
            if not self._matches_path_pattern(path, opts.path_pattern):
                continue
            if self._matches_exclude_patterns(path, opts.exclude_patterns):
                continue
            
            # Calculate score
            base_score = float(r["score"]) if r["score"] is not None else 0.0
            score = -base_score  # BM25 returns negative, so negate
            if opts.recency_boost:
                score = self._calculate_recency_score(mtime, score)
            
            # Count matches
            match_count = self._count_matches(content, opts.query, False, opts.case_sensitive)
            
            # Generate snippet
            snippet = self._snippet_around(content, terms, opts.snippet_lines, highlight=True)
            
            hits.append(SearchHit(
                repo=r["repo"],
                path=path,
                score=score,
                snippet=snippet,
                mtime=mtime,
                size=size,
                match_count=match_count,
                file_type=self._get_file_extension(path),
            ))
        
        # Sort by score
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits

    # ========== Legacy Search (backward compatible) ==========

    def search(
        self,
        q: str,
        repo: Optional[str],
        limit: int = 20,
        snippet_max_lines: int = 5,
    ) -> tuple[list[SearchHit], dict[str, Any]]:
        """Legacy search method for backward compatibility."""
        opts = SearchOptions(
            query=q,
            repo=repo,
            limit=limit,
            snippet_lines=snippet_max_lines,
        )
        return self.search_v2(opts)

    def repo_candidates(self, q: str, limit: int = 3) -> list[dict[str, Any]]:
        """Return top candidate repos for a query with tiny evidence."""
        q = (q or "").strip()
        if not q:
            return []

        limit = max(1, min(int(limit), 5))

        if self._fts_enabled:
            sql = """
                SELECT f.repo AS repo,
                       COUNT(1) AS c
                FROM files_fts
                JOIN files f ON f.rowid = files_fts.rowid
                WHERE files_fts MATCH ?
                GROUP BY f.repo
                ORDER BY c DESC
                LIMIT ?;
            """
            try:
                rows = self._read.execute(sql, (q, limit)).fetchall()
                out: list[dict[str, Any]] = []
                for r in rows:
                    repo = str(r["repo"])
                    c = int(r["c"])
                    hits, _ = self.search(q=q, repo=repo, limit=1, snippet_max_lines=2)
                    evidence = hits[0].snippet.replace("\n", " ")[:200] if hits else ""
                    out.append({"repo": repo, "score": c, "evidence": evidence})
                return out
            except sqlite3.OperationalError:
                pass

        # LIKE fallback
        like_q = q.replace("%", "\\%").replace("_", "\\_")
        sql = """
            SELECT repo, COUNT(1) AS c
            FROM files
            WHERE content LIKE ? ESCAPE '\\'
            GROUP BY repo
            ORDER BY c DESC
            LIMIT ?;
        """
        rows = self._read.execute(sql, (f"%{like_q}%", limit)).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            repo = str(r["repo"])
            c = int(r["c"])
            hits, _ = self.search(q=q, repo=repo, limit=1, snippet_max_lines=2)
            evidence = hits[0].snippet.replace("\n", " ")[:200] if hits else ""
            out.append({"repo": repo, "score": c, "evidence": evidence})
        return out
