#!/usr/bin/env python3
"""
Build SUBMISSION.md from docs/SUBMISSION.template.md and the repository itself:
Mermaid diagrams from docs/diagrams/*.mmd (title, code, then diagram), the generated
.sdoc excerpt, the RTM and coverage computed by rtm.py, and README.md.

Run after ./publish.sh so site/rtm.csv and site/coverage.txt are current:
    python3 docs/build_submission.py
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import rtm  # noqa: E402  (reuse its .sdoc parser)

GENERATED = {
    "generated/requirements.sdoc": ROOT / "docs/sdoc/requirements.sdoc",
    "generated/rtm.csv": ROOT / "site/rtm.csv",
    "generated/coverage.txt": ROOT / "site/coverage.txt",
}


def path_for(name: str) -> Path:
    return GENERATED.get(name, ROOT / name)


def diagram(match: re.Match) -> str:
    name, title = match.group(1), match.group(2)
    code = (ROOT / "docs/diagrams" / f"{name}.mmd").read_text(encoding="utf-8").rstrip()
    return f"#### {title}\n\n**Code**\n\n```text\n{code}\n```\n\n**Diagram**\n\n```mermaid\n{code}\n```"


def file_block(match: re.Match) -> str:
    text = path_for(match.group(1)).read_text(encoding="utf-8").rstrip()
    if match.group(1).endswith(".sdoc"):  # show the content, not the 30-line grammar header
        text = text[text.index("[[SECTION]]"):] if "[[SECTION]]" in text else text
        text = "(the [GRAMMAR] block at the top of the file is omitted here)\n\n" + text
    return f"```{match.group(2)}\n{text}\n```"


def md_table(rows: list[dict], cols: list[str]) -> str:
    esc = lambda v: (v or "—").replace("|", "\\|").replace("\n", " ")  # noqa: E731
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(esc(r.get(c, "")) for c in cols) + " |" for r in rows]
    return "\n".join(out)


def csv_table(match: re.Match) -> str:
    with open(path_for(match.group(1)), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return md_table(rows, ["Requirement", "Status", "Statement", "Need", "Element", "Code", "Verification", "Result", "Verified"])


def verification_table() -> str:
    nodes = rtm.parse_sdoc(ROOT / "docs/sdoc/verification.sdoc")
    rows = [
        {
            "ID": n.get("UID"),
            "Requirement": ", ".join(r["value"] for r in n["_rel"]),
            "Method": n.get("METHOD"),
            "Acceptance criteria": n.get("ACCEPTANCE_CRITERIA"),
            "Result": n.get("RESULT"),
        }
        for n in nodes
        if n["_type"] == "VERIFICATION"
    ]
    return md_table(rows, ["ID", "Requirement", "Method", "Acceptance criteria", "Result"])


def main() -> int:
    s = (ROOT / "docs/SUBMISSION.template.md").read_text(encoding="utf-8")
    s = re.sub(r"\{\{DIAGRAM:([^|}]+)\|([^}]+)\}\}", diagram, s)
    s = re.sub(r"\{\{FILE:([^|}]+)\|([^}]*)\}\}", file_block, s)
    s = re.sub(r"\{\{CSV:([^}]+)\}\}", csv_table, s)
    s = s.replace("{{VERIFICATION}}", verification_table())
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme = re.sub(r"^# .*\n", "", readme, count=1)
    readme = re.sub(r"^## ", "### ", readme, flags=re.M)
    s = s.replace("{{README}}", readme.strip())
    left = re.findall(r"\{\{[^}]+\}\}", s)
    if left:
        print("Unresolved placeholders:", left)
        return 1
    (ROOT / "SUBMISSION.md").write_text(s, encoding="utf-8")
    todo = sorted(set(re.findall(r"⟨[A-Z_]+⟩", s)))
    print("wrote SUBMISSION.md")
    if todo:
        print("Still to fill in by hand:", ", ".join(todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
