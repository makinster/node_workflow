"""Recheck PR B's local Markdown links and retained archive bodies.

Run with Python from any directory. Original source is pinned to 9d5455b;
this script is new PR B verification, not recovered external-audit evidence.
"""
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "AttackOfTheNodes" / "docs"
BASE = "9d5455b"
SESSION_BASE = "90182f0"
SESSION_CUTOFF = "2026-10-04"
ACTIVE_DOCS = {
    "README.md", "NEWCOMER_GUIDE.md", "VISION.md", "CURRENT_STATE.md",
    "CONTRIBUTING.md", "SESSION_LOG.md", "ARCHITECTURE.md",
    "BACKEND_FRONTEND_BOUNDARY.md", "NODE_STANDARDS.md", "NODE_HELPER.md",
    "NODE_CATALOG.md", "UI_QUICK_REFERENCE.md", "WORKFLOW_AUTHORING.md",
    "NODE_CONTRACT_PLAN.md", "DISTRIBUTED_BUILD_PLAN.md", "STASH_PROPOSAL.md",
    "PROJECT_BACKLOG.md",
}
# Approved Step 4 design; move to archive when Step 4 completes.
TEMPORARY_DOCS = {"SUBWORKFLOWS_PROPOSAL.md", "DELETION_REVIEW_PROPOSAL.md"}
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def headings(path):
    text = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
    found = set(re.findall(r"<a\s+(?:name|id)=[\"']([^\"']+)", text))
    counts = {}
    for title in re.findall(r"^#{1,6}\s+(.+?)\s*#*$", text, re.M):
        title = re.sub(r"<[^>]+>", "", title).lower()
        slug = "".join(c for c in title if c in "-_ " or unicodedata.category(c)[0] in "LN"
                       or unicodedata.category(c) == "Mn").replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        found.add(slug + (f"-{count}" if count else ""))
    return found


def original(name):
    return subprocess.check_output(
        ["git", "show", f"{BASE}:AttackOfTheNodes/docs/{name}"], cwd=ROOT, text=True
    )


def without_link_targets(text):
    return LINK.sub(lambda match: f"[{match[1]}](TARGET)", text)


def main():
    errors, links = [], 0
    files = [ROOT / "AGENTS.md", *sorted(DOCS.rglob("*.md"))]
    for path in files:
        text = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
        for match in LINK.finditer(text):
            url = match[2].strip("<>").split(' "')[0]
            if re.match(r"[a-zA-Z]+:", url):
                continue
            target, _, anchor = url.partition("#")
            resolved = (path.parent / unquote(target)).resolve() if target else path
            links += 1
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing {url}")
            elif anchor and resolved.suffix == ".md" and unquote(anchor) not in headings(resolved):
                errors.append(f"{path.relative_to(ROOT)}: missing anchor {url}")

    old_names = subprocess.check_output(
        ["git", "ls-tree", "--name-only", f"{BASE}:AttackOfTheNodes/docs"], cwd=ROOT, text=True
    ).splitlines()
    moved = [name for name in old_names if name.endswith(".md") and not (DOCS / name).exists()]
    for name in [*moved, "ARCHITECTURE.md"]:
        archive = "ARCHITECTURE_PRE_CONSOLIDATION.md" if name == "ARCHITECTURE.md" else name
        path = DOCS / "archive" / archive
        if not path.exists():
            errors.append(f"Missing whole archive: {name}")
            continue
        saved = path.read_text().split("\n\n", 1)[1]
        before, after = without_link_targets(original(name)), without_link_targets(saved)
        # PR C appends older session entries to the existing history, without
        # replacing its original body. The migration ledger is append-only too.
        intact = (after.startswith(before)
                  if name in {"DOCS_MIGRATION_NOTES.md", "SESSION_LOG_HISTORY.md"}
                  else after == before)
        if not intact:
            errors.append(f"Archive body changed beyond relative link targets: {name}")
    active = sorted(p.name for p in DOCS.glob("*.md"))
    missing = ACTIVE_DOCS - set(active)
    unexpected = set(active) - ACTIVE_DOCS - TEMPORARY_DOCS
    if missing or unexpected:
        errors.append(f"Active doc set: missing {sorted(missing)}, unexpected {sorted(unexpected)}")
    # Recheck the PR C transfer independently of its destination heading/line
    # numbers. Link targets may change with the directory, source text may not.
    session_before = subprocess.check_output(
        ["git", "show", f"{SESSION_BASE}:AttackOfTheNodes/docs/SESSION_LOG.md"],
        cwd=ROOT, text=True,
    ).split("## Older Entries", 1)[0]
    entries = re.split(r"(?m)(?=^## \d{4}-\d{2}-\d{2} — )", session_before)
    transferred = []
    for entry in entries:
        dated = re.match(r"## (\d{4}-\d{2}-\d{2}) — ", entry)
        if dated and dated[1] < SESSION_CUTOFF:
            transferred.append(entry)
    history = (DOCS / "archive" / "SESSION_LOG_HISTORY.md").read_text()
    if without_link_targets("".join(transferred).rstrip()) not in without_link_targets(history):
        errors.append("PR C session-history transfer differs from its complete source entries")
    print(f"{len(files)} Markdown files; {links} relative links/anchors; "
          f"{len(moved) + 1} whole archive bodies; {len(transferred)} transferred session entries; "
          f"{len(active)} active docs")
    print("\n".join(errors) if errors else "PASS")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
