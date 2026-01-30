import fnmatch
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

# Support script mode and package mode
try:
    from .config import Config  # type: ignore
    from .db import LocalSearchDB  # type: ignore
except ImportError:
    from config import Config  # type: ignore
    from db import LocalSearchDB  # type: ignore


@dataclass
class IndexStatus:
    index_ready: bool = False
    last_scan_ts: float = 0.0
    scanned_files: int = 0
    indexed_files: int = 0
    errors: int = 0


_REDACT_PATTERNS = [
    # key=value / key: value (line-based assignments)
    re.compile(
        r"(?im)^(\s*(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret|private[_-]?key|refresh[_-]?token|id[_-]?token|session[_-]?token|aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*)(.+?)\s*$"
    ),
    # common spring property style: xxx.password=...
    re.compile(
        r"(?im)^(\s*[\w\.-]*(?:password|secret|token|api[_-]?key|client[_-]?secret|private[_-]?key|aws[_-]?secret[_-]?access[_-]?key)[\w\.-]*\s*=\s*)(.+?)\s*$"
    ),
    # JSON style: "password": "..." (or token/apiKey/...)
    re.compile(
        r"(?im)^(\s*\"(?:password|secret|token|api[_-]?key|client[_-]?secret|private[_-]?key|refresh[_-]?token|id[_-]?token|session[_-]?token|aws[_-]?secret[_-]?access[_-]?key)\"\s*:\s*)\"(.*?)\"(\s*,?\s*)$"
    ),
    # Authorization header: Authorization: Bearer <token>
    re.compile(r"(?im)^(\s*authorization\s*:\s*bearer\s+)(.+?)\s*$"),
    # Inline Bearer token patterns (defensive; keep narrow)
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-\._~\+/]+=*"),
]


def _redact(text: str) -> str:
    # Keep this conservative: only redact obvious assignments.
    for pat in _REDACT_PATTERNS:
        # JSON pattern has 3 groups: prefix, value, suffix.
        if pat.groups == 3:
            text = pat.sub(lambda m: f"{m.group(1)}\"***\"{m.group(3)}", text)
            continue
        # Most patterns: group(1)=prefix, group(2)=value
        if pat.groups >= 1:
            text = pat.sub(lambda m: f"{m.group(1)}***", text)
    return text


class Indexer:
    def __init__(self, cfg: Config, db: LocalSearchDB):
        self.cfg = cfg
        self.db = db
        self.status = IndexStatus()
        self._stop = threading.Event()
        self._rescan = threading.Event()
        self._root_repo_name = "__root__"

    def stop(self) -> None:
        self._stop.set()
        self._rescan.set()

    def request_rescan(self) -> None:
        """Trigger an immediate scan outside the normal interval."""
        self._rescan.set()

    def run_forever(self) -> None:
        # first scan ASAP
        self._scan_once()
        self.status.index_ready = True

        while not self._stop.is_set():
            # Wait for either a rescan request or the interval.
            self._rescan.wait(timeout=max(1, int(self.cfg.scan_interval_seconds)))
            self._rescan.clear()
            if self._stop.is_set():
                break
            self._scan_once()

    def _scan_once(self) -> None:
        root = Path(os.path.expanduser(self.cfg.workspace_root)).resolve()
        if not root.exists() or not root.is_dir():
            self.status.errors += 1
            return

        scanned = 0
        indexed = 0
        batch: List[Tuple[str, str, int, int, str]] = []
        batch_size = max(50, int(getattr(self.cfg, "commit_batch_size", 500)))

        for file_path in self._iter_files(root):
            scanned += 1
            try:
                rel = str(file_path.relative_to(root))
                # Repo = 1depth subdirectory; root-level files use a dedicated repo name
                if os.sep not in rel:
                    repo = self._root_repo_name
                else:
                    repo = rel.split(os.sep, 1)[0]
                if not repo:
                    continue

                st = file_path.stat()
                if st.st_size > self.cfg.max_file_bytes:
                    continue

                # Skip unchanged files (mtime/size)
                prev = self.db.get_file_meta(rel)
                if prev is not None:
                    prev_mtime, prev_size = prev
                    if int(st.st_mtime) == int(prev_mtime) and int(st.st_size) == int(prev_size):
                        continue

                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                if getattr(self.cfg, "redact_enabled", True):
                    text = _redact(text)

                batch.append((rel, repo, int(st.st_mtime), int(st.st_size), text))

                if len(batch) >= batch_size:
                    self.db.upsert_files(batch)
                    indexed += len(batch)
                    batch.clear()

            except Exception:
                self.status.errors += 1

        if batch:
            try:
                self.db.upsert_files(batch)
                indexed += len(batch)
            except Exception:
                self.status.errors += 1

        self.status.last_scan_ts = time.time()
        self.status.scanned_files = scanned
        self.status.indexed_files = indexed

    def _iter_files(self, root: Path) -> Iterable[Path]:
        include_ext = set((self.cfg.include_ext or []))
        include_files = set((self.cfg.include_files or []))
        exclude_dirs = set((self.cfg.exclude_dirs or []))
        exclude_globs = list((getattr(self.cfg, "exclude_globs", []) or []))

        for dirpath, dirnames, filenames in os.walk(root):
            # prune excluded dirs (in-place)
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

            for fn in filenames:
                # Fast path filename-only excludes
                if exclude_globs and any(fnmatch.fnmatch(fn, g) for g in exclude_globs):
                    continue

                p = Path(dirpath) / fn
                rel = str(p.relative_to(root))
                if exclude_globs and any(fnmatch.fnmatch(rel, g) for g in exclude_globs):
                    continue

                if include_files and fn in include_files:
                    yield p
                    continue

                if include_ext:
                    suf = p.suffix.lower()
                    if suf in include_ext:
                        yield p
