#!/usr/bin/env python3
"""Shared configuration for the cerberus hooks.

Both hooks read the same optional config file so that a project can describe
its own layout without editing the hook scripts. Everything has a default: a
gate that requires configuration before it does anything would be silently
inert in every project that forgot to configure it, which is the exact failure
this gate exists to prevent.

Config file, searched relative to the project root:

    .claude/cerberus.json

Every key is optional.

    {
      "watch_paths":       ["src/", "app/"],
      "source_extensions": [".py", ".ts"],
      "ignore_patterns":   ["/tests/", ".test."],
      "claim_patterns":    ["\\\\bdone\\\\b"],
      "marker":            ".claude/.cerberus-pending"
    }

`watch_paths` narrows by directory; empty means anywhere in the project.
`claim_patterns` REPLACES the defaults rather than extending them, so a project
can turn the gate down without editing this file.
"""

from __future__ import annotations

import json
import pathlib
import re

MARKER_DEFAULT = ".claude/.cerberus-pending"

# Deliberately extension-based rather than path-based. Path layouts differ per
# project; "a file of source code" travels.
SOURCE_EXTENSIONS_DEFAULT = [
    ".py", ".go", ".rs", ".java", ".kt", ".scala", ".rb", ".php", ".cs",
    ".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".swift",
    ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
    ".sql", ".tf", ".proto",
]

# Changes that cannot themselves break runtime behaviour. Tests are excluded on
# purpose: a test edit is not the thing the two stages verify.
IGNORE_PATTERNS_DEFAULT = [
    "/tests/", "/test/", "/testing/", "/__tests__/", "/spec/",
    "_test.", ".test.", ".spec.", "test_",
    "/docs/", "/doc/", "/examples/", "/example/",
    "/.claude/", "/.github/", "/vendor/", "/node_modules/",
    "/migrations/versions/",
]

# Strong readiness claims. Both languages are shipped by default: a Russian
# word cannot false-positive in an English project, and the reverse would only
# happen in a project already using the English word to mean readiness.
#
# These are intentionally narrow. Broad mid-work words ("deployed", "pushed",
# "e2e") are absent: the gate must fire at the moment of over-claiming, not
# during ongoing work, or it becomes noise and gets disabled.
CLAIM_PATTERNS_DEFAULT = [
    r"\bit works\b",
    r"\bworks now\b",
    r"\ball green\b",
    r"\bdone\b",
    r"\bready to (use|ship|merge)\b",
    r"\bworking as expected\b",
    r"\bverified and working\b",
    r"\bdeployed and working\b",
    r"\bfix works\b",
    r"\bработает\b",
    r"\bготово\b",
    r"\bготов\b",
    r"вс[её]\s+зел[её]н",
    r"подтвержд[её]н",
    r"задеплоен\w*\s+и\s+работает",
]


class Config:
    def __init__(self, root: pathlib.Path, raw: dict | None = None):
        raw = raw or {}
        self.root = root
        self.watch_paths = [self._norm(p) for p in raw.get("watch_paths", [])]
        self.source_extensions = [
            e.lower() for e in raw.get("source_extensions", SOURCE_EXTENSIONS_DEFAULT)
        ]
        self.ignore_patterns = [
            self._norm(p) for p in raw.get("ignore_patterns", IGNORE_PATTERNS_DEFAULT)
        ]
        self.claim_patterns = raw.get("claim_patterns", CLAIM_PATTERNS_DEFAULT)
        self.marker = raw.get("marker", MARKER_DEFAULT)

    @staticmethod
    def _norm(p: str) -> str:
        return str(p).replace("\\", "/")

    @classmethod
    def load(cls, root: pathlib.Path) -> "Config":
        path = root / ".claude" / "cerberus.json"
        try:
            return cls(root, json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return cls(root)
        except Exception:
            # A malformed config must not disable the gate: falling back to
            # defaults keeps it loud, whereas returning early would make a typo
            # silently switch verification off.
            return cls(root)

    def marker_path(self) -> pathlib.Path:
        return self.root / self.marker

    def is_source_file(self, file_path: str) -> bool:
        """Does editing this file put runtime behaviour at risk?"""
        fp = self._norm(file_path)
        if not fp:
            return False
        # Compare against a leading-slash form so that "/tests/" also matches a
        # path that begins with "tests/".
        probe = fp if fp.startswith("/") else "/" + fp
        if any(pat in probe for pat in self.ignore_patterns):
            return False
        if self.source_extensions:
            suffix = pathlib.PurePosixPath(fp).suffix.lower()
            if suffix not in self.source_extensions:
                return False
        if self.watch_paths and not any(w in probe for w in self.watch_paths):
            return False
        return True

    def claims_readiness(self, text: str) -> bool:
        lowered = text.lower()
        return any(re.search(p, lowered) for p in self.claim_patterns)
