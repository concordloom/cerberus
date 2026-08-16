#!/usr/bin/env python3
"""Shared configuration for the cerberus hooks.

Both hooks read the same optional config file so that a project can describe
its own layout without editing the hook scripts. Everything has a default —
including `enforce`, which is off, so a project that never asked is never
interrupted. That is a deliberate trade and the argument on both sides is at
``ENFORCE_DEFAULT`` below.

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

#: Enforcement is off until a project asks for it. The hooks are installed and
#: silent: nothing is recorded, nothing is refused, and the skills are there to
#: invoke by name.
#:
#: This reverses an argument this project used to make — that a gate which stays
#: inert until configured is indistinguishable from no gate. The counter-evidence
#: is that a gate firing on ordinary words five times an hour does not get tuned,
#: it gets uninstalled, and then it is worth even less than an advisory one.
ENFORCE_DEFAULT = False

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
    "/.claude/", "/.codex/", "/.agents/", "/.github/", "/vendor/", "/node_modules/",
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
        # Not `bool()`: `"false"` is a truthy string and the commonest typo for
        # this key, and it would have read as on. Only a real boolean counts;
        # anything else falls back to the default rather than guessing.
        declared = raw.get("enforce", ENFORCE_DEFAULT)
        malformed = "enforce" in raw and not isinstance(declared, bool)
        # `"true"`, `1` and `"yes"` are somebody asking for enforcement, not
        # somebody declining it. Falling back to the default there switched the
        # gate off on the commonest typo for a boolean key — the same defect as
        # a broken file, one level down. Treat it as asked-for, and say why.
        self.enforce = True if malformed else (
            declared if isinstance(declared, bool) else ENFORCE_DEFAULT
        )
        self.enforce_malformed = malformed
        #: Set when the config could not be parsed. A project that asked for
        #: enforcement and then broke its config must keep being refused —
        #: falling back to "off" would let a typo switch the gate off, which is
        #: the defect this default otherwise avoids, wearing opposite clothes.
        self.unreadable = False

    @staticmethod
    def _norm(p: str) -> str:
        return str(p).replace("\\", "/")

    #: Searched in order. A project uses whichever agent directory it has, and
    #: a project using both keeps one config rather than two that can disagree.
    CONFIG_PATHS = (".claude/cerberus.json", ".codex/cerberus.json")

    @classmethod
    def load(cls, root: pathlib.Path) -> "Config":
        for relative in cls.CONFIG_PATHS:
            path = root / relative
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                continue
            except Exception:
                # Somebody configured something here, so this is not a project
                # that never asked. Enforce on defaults and say the file cannot
                # be read — falling back to "off" would let a typo switch the
                # gate off, which is the defect the opt-in default otherwise
                # avoids, wearing the opposite clothes.
                broken = cls(root)
                broken.enforce = True
                broken.unreadable = True
                if relative.startswith(".codex"):
                    broken.marker = ".codex/.cerberus-pending"
                return broken
            if not isinstance(raw, dict):
                # Valid JSON, wrong shape — `null`, `false`, `0`, `[]`, `""` and
                # `[{...}]` all reach here. `raw or {}` used to swallow the
                # falsy ones into defaults, which under an opt-in default means
                # the gate quietly switches off; the truthy ones crashed both
                # hooks with an AttributeError and failed open. The file exists,
                # so this is a configured project with a broken file.
                broken = cls(root)
                broken.enforce = True
                broken.unreadable = True
                if relative.startswith(".codex"):
                    broken.marker = ".codex/.cerberus-pending"
                return broken
            cfg = cls(root, raw)
            if relative.startswith(".codex") and "marker" not in raw:
                # The marker belongs beside the config that declared it, or a
                # Codex-only project writes session state into a .claude
                # directory it does not otherwise have.
                cfg.marker = ".codex/.cerberus-pending"
            return cfg
        if (root / ".codex").is_dir() and not (root / ".claude").is_dir():
            cfg = cls(root)
            cfg.marker = ".codex/.cerberus-pending"
            return cfg
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

        `..` is normalised in the lexical arm so the obvious escape does not
        work: `root/../escaped.py` normalises to a path outside the root. The
        claim stops there. A `..` that traverses an in-project symlink pointing
        out — `link/../secret.py` where `link` leaves the tree — normalises
        lexically back inside and marks, while the real target is elsewhere.
        That is inherent to accepting either arm, and marking one file too many
        is the safe direction for a gate.
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
