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
import os
import pathlib
import re

MARKER_DEFAULT = ".claude/.cerberus-pending"

# "C:/x/y.py" after _norm. Without this it reads as a relative path.
DRIVE_LETTER = re.compile(r"^[A-Za-z]:/")

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

    @staticmethod
    def _is_absolute(fp: str) -> bool:
        """Absolute in any form the harness might send.

        `PurePosixPath` calls "C:/x/y.py" relative, and a path judged relative
        gets joined onto the project root and then looks like it is inside it.
        """
        return bool(fp.startswith("/") or DRIVE_LETTER.match(fp))

    @staticmethod
    def _contains(root: pathlib.Path, target: pathlib.Path) -> bool:
        return target == root or root in target.parents

    def _under_root(self, fp: str) -> bool:
        """Is this file part of the project the gate is guarding?

        An edit outside the project cannot change what this project ships, and
        marking it arms the gate during ordinary work: a note written to a
        scratch directory would go on to block the next readiness claim about
        unrelated code. Reproduced 2026-08-15 — a real marker held six paths and
        two were plain scratch files outside the repository.

        Two comparisons, and a file is inside if **either** says so, because
        each alone loses a real case:

        - **Lexical**, after normalising `..` away but without resolving
          symlinks. A package inside the project that is a symlink to a shared
          directory elsewhere — the vendored layout — is still part of the
          project, and resolution alone would call it foreign.
        - **Resolved**, which catches a project reached *through* a symlink,
          where the lexical form would call the whole tree foreign.

        `..` is normalised in the lexical arm precisely so it cannot be used to
        walk out and back in: `root/../escaped.py` normalises to a path that is
        not under the root.
        """
        fp = os.path.expanduser(fp)
        target = pathlib.Path(fp) if self._is_absolute(fp) else self.root / fp

        lexical_root = pathlib.Path(os.path.normpath(str(self.root)))
        lexical_target = pathlib.Path(os.path.normpath(str(target)))
        if self._contains(lexical_root, lexical_target):
            return True

        try:
            return self._contains(self.root.resolve(), target.resolve())
        except (OSError, ValueError):
            # Unresolvable is not provably inside, and the gate must not be
            # armed by a path nobody can place.
            return False

    def is_source_file(self, file_path: str) -> bool:
        """Does editing this file put runtime behaviour at risk?"""
        fp = self._norm(file_path)
        if not fp:
            return False
        if not self._under_root(fp):
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
