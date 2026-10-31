#!/usr/bin/env python3
"""
Compute the Requirements Traceability Matrix from the Git repository (Task 5).

Nothing here is typed by hand: everything is read from
    docs/sdoc/*.sdoc   needs, requirements, elements, verification (written by sync.py)
    src/**/*.py        functions tagged with @relation(REQ-xxx, scope=function)

Outputs (default: site/)
    rtm.csv        one row per requirement
    index.html     the RTM as a browsable page (published together with the StrictDoc export)
    coverage.txt   gap counts and verification pass rate

Usage:  python3 rtm.py [--out site] [--fail-on-gaps]
"""

from __future__ import annotations

import argparse
import ast
import csv
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SDOC_DIR = ROOT / "docs" / "sdoc"
SRC_DIR = ROOT / "src"
STRICTDOC_LINK = "strictdoc/index.html"  # relative link to the StrictDoc export
MARKER = re.compile(r"@relation\(\s*([^)]*?)\s*\)")


# ---------------------------------------------------------------- .sdoc reading


def parse_sdoc(path: Path) -> list[dict]:
    """Return the nodes of a generated .sdoc file (grammar block skipped)."""
    nodes: list[dict] = []
    text = path.read_text(encoding="utf-8")
    body = text.split("\n[[SECTION]]", 1)
    if len(body) < 2:
        return nodes
    cur: dict | None = None
    lines = ("[[SECTION]]" + body[1]).split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\[([A-Z_]+)\]$", line)
        if m:
            cur = {"_type": m.group(1), "_rel": []}
            nodes.append(cur)
        elif line.startswith("[["):
            cur = None
        elif cur is not None and line.startswith("- TYPE: "):
            rel = {"type": line[8:].strip()}
            while i + 1 < len(lines) and lines[i + 1].startswith("  "):
                i += 1
                k, _, v = lines[i].strip().partition(": ")
                rel[k.lower()] = v
            cur["_rel"].append(rel)
        elif cur is not None and re.match(r"^[A-Z_]+: >>>$", line):
            key = line.split(":")[0]
            buf = []
            i += 1
            while i < len(lines) and lines[i] != "<<<":
                buf.append(lines[i])
                i += 1
            cur[key] = "\n".join(buf)
        elif cur is not None and re.match(r"^[A-Z_]+: ", line):
            key, _, value = line.partition(": ")
            cur[key] = value
        i += 1
    return nodes


def load_repo() -> dict:
    nodes = []
    for f in sorted(SDOC_DIR.glob("*.sdoc")):
        nodes += parse_sdoc(f)
    by_type: dict[str, list[dict]] = {}
    for n in nodes:
        by_type.setdefault(n["_type"], []).append(n)
    return by_type


# ---------------------------------------------------------------- code scanning


def scan_code() -> tuple[dict[str, list[str]], list[str]]:
    """Map requirement UID -> ['src/auth.py:login_via_sso', ...]."""
    links: dict[str, list[str]] = {}
    problems: list[str] = []
    for f in sorted(SRC_DIR.rglob("*.py")) if SRC_DIR.exists() else []:
        rel = f.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as e:
            problems.append(f"{rel}: cannot parse ({e})")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            uids: list[str] = []
            # StrictDoc form (preferred): docstring contains @relation(REQ-002, scope=function)
            for m in MARKER.finditer(ast.get_docstring(node) or ""):
                args = [a.strip() for a in m.group(1).split(",")]
                uids += [a for a in args if a and "=" not in a]
                if not any(a.startswith("scope=") for a in args):
                    problems.append(f"{rel}:{node.name}: @relation without scope= is ignored by StrictDoc")
            # Legacy decorator form: @relation("REQ-001") - counted, but not seen by StrictDoc
            for dec in getattr(node, "decorator_list", []):
                if isinstance(dec, ast.Call) and getattr(dec.func, "id", "") == "relation":
                    for a in dec.args:
                        if isinstance(a, ast.Constant) and isinstance(a.value, str):
                            uids.append(a.value)
                    problems.append(
                        f"{rel}:{node.name}: decorator @relation(...) is not read by StrictDoc; "
                        "move it into the docstring as @relation(REQ-xxx, scope=function)"
                    )
            for uid in uids:
                links.setdefault(uid, []).append(f"{rel}:{node.name}")
    return links, problems


# ---------------------------------------------------------------- RTM


def build(by_type: dict) -> tuple[list[dict], dict]:
    needs = {n["UID"]: n for n in by_type.get("NEED", [])}
    reqs = by_type.get("REQUIREMENT", [])
    alloc: dict[str, list[str]] = {}
    for e in by_type.get("ELEMENT", []):
        for r in e["_rel"]:
            alloc.setdefault(r.get("value", ""), []).append(f"{e['UID']} {e.get('TITLE', '')}".strip())
    ver: dict[str, list[dict]] = {}
    for v in by_type.get("VERIFICATION", []):
        for r in v["_rel"]:
            ver.setdefault(r.get("value", ""), []).append(v)
    code, code_problems = scan_code()

    req_uids = {r["UID"] for r in reqs}
    rows = []
    for r in sorted(reqs, key=lambda r: r["UID"]):
        uid = r["UID"]
        parents = [x["value"] for x in r["_rel"] if x["type"] == "Parent"]
        vs = ver.get(uid, [])
        results = [v.get("RESULT", "Not run") for v in vs]
        rows.append(
            {
                "Requirement": uid,
                "Statement": r.get("STATEMENT", ""),
                "Status": r.get("STATUS", ""),
                "Need": "; ".join(parents),
                "Need title": "; ".join(needs.get(p, {}).get("TITLE", "?") for p in parents),
                "Element": "; ".join(alloc.get(uid, [])),
                "Code": "; ".join(code.get(uid, [])),
                "Verification": "; ".join(v["UID"] for v in vs),
                "Method": "; ".join(v.get("METHOD", "") for v in vs),
                "Acceptance criteria": "; ".join(v.get("ACCEPTANCE_CRITERIA", "") for v in vs),
                "Result": "; ".join(results),
                "Verified": "Pass" if results and all(x.lower() == "pass" for x in results)
                else ("Fail" if any(x.lower() == "fail" for x in results) else "Not verified"),
            }
        )

    active = [x for x in rows if x["Status"] != "Obsolete"]
    cov = {
        "needs": len(needs),
        "requirements": len(rows),
        "active": len(active),
        "obsolete": len(rows) - len(active),
        "no_need": [x["Requirement"] for x in active if not x["Need"]],
        "no_allocation": [x["Requirement"] for x in active if not x["Element"]],
        "no_code": [x["Requirement"] for x in active if not x["Code"]],
        "no_verification": [x["Requirement"] for x in active if not x["Verification"]],
        "passed": [x["Requirement"] for x in active if x["Verified"] == "Pass"],
        "needs_without_req": sorted(set(needs) - {p for x in rows for p in x["Need"].split("; ") if p}),
        "code_to_unknown": sorted(u for u in code if u not in req_uids),
        "code_to_obsolete": sorted(x["Requirement"] for x in rows if x["Status"] == "Obsolete" and x["Code"]),
        "code_problems": code_problems,
    }
    cov["pass_rate"] = round(100.0 * len(cov["passed"]) / len(active), 1) if active else 0.0
    return rows, cov


def coverage_text(cov: dict, stamp: str) -> str:
    def line(label, items):
        return f"{label:<40} {len(items)}" + (f"   {', '.join(items)}" if items else "")

    out = [
        f"Coverage report (computed from Git, {stamp})",
        "",
        f"{'Stakeholder needs':<40} {cov['needs']}",
        f"{'Requirements (rows in RTM)':<40} {cov['requirements']}",
        f"{'  active (excluding Obsolete)':<40} {cov['active']}",
        f"{'  obsolete':<40} {cov['obsolete']}",
        "",
        "Gaps (active requirements only)",
        line("  no need", cov["no_need"]),
        line("  no allocation to an element", cov["no_allocation"]),
        line("  no code link", cov["no_code"]),
        line("  no verification", cov["no_verification"]),
        "",
        f"{'Verification pass rate':<40} {len(cov['passed'])}/{cov['active']} = {cov['pass_rate']}%",
        "  (a requirement passes when it has at least one verification and all of them are Pass)",
        "",
        "Warnings",
        line("  needs with no requirement", cov["needs_without_req"]),
        line("  code tags to unknown IDs", cov["code_to_unknown"]),
        line("  code still tagged to Obsolete IDs", cov["code_to_obsolete"]),
    ]
    out += [f"  {p}" for p in cov["code_problems"]]
    return "\n".join(out) + "\n"


def html_page(rows: list[dict], cov: dict, stamp: str) -> str:
    e = html.escape
    cols = ["Requirement", "Status", "Statement", "Need", "Element", "Code", "Verification", "Method", "Result", "Verified"]

    def cell(c, v):
        if c == "Verified":
            return f'<td><span class="pill {v.split()[0].lower()}">{e(v)}</span></td>'
        if c == "Need" and v:
            return f"<td><b>{e(v)}</b></td>"
        return f"<td>{e(v) if v else '<span class=gap>—</span>'}</td>"

    body = "\n".join(
        f'<tr class="{e(r["Status"].lower())}">' + "".join(cell(c, r[c]) for c in cols) + "</tr>" for r in rows
    )
    tiles = [
        ("Active requirements", f"{cov['active']}", f"{cov['obsolete']} obsolete"),
        ("Pass rate", f"{cov['pass_rate']}%", f"{len(cov['passed'])} of {cov['active']} verified Pass"),
        ("No need", str(len(cov["no_need"])), ", ".join(cov["no_need"]) or "none"),
        ("No allocation", str(len(cov["no_allocation"])), ", ".join(cov["no_allocation"]) or "none"),
        ("No code link", str(len(cov["no_code"])), ", ".join(cov["no_code"]) or "none"),
        ("No verification", str(len(cov["no_verification"])), ", ".join(cov["no_verification"]) or "none"),
    ]
    tiles_html = "".join(
        f'<div class="tile"><div class="k">{e(k)}</div><div class="v">{e(v)}</div><div class="s">{e(s)}</div></div>'
        for k, v, s in tiles
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Requirements Traceability Matrix</title>
<style>
body{{font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1d2433;background:#f6f7f9}}
header{{background:#fff;border-bottom:1px solid #e3e6ea;padding:20px 32px}}
h1{{margin:0;font-size:22px}} header p{{margin:4px 0 0;color:#5b6576}}
main{{padding:24px 32px;max-width:1400px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:24px}}
.tile{{background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:12px 14px}}
.k{{color:#5b6576;font-size:13px}} .v{{font-size:26px;font-weight:600}} .s{{color:#5b6576;font-size:12px}}
table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #e3e6ea;border-radius:8px;overflow:hidden}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #eef0f3;vertical-align:top;font-size:14px}}
th{{background:#f0f2f5;font-weight:600;position:sticky;top:0}}
td:nth-child(1),td:nth-child(2),td:nth-child(4),td:nth-child(7),td:nth-child(10){{white-space:nowrap}}
tr.obsolete td{{color:#8a93a3;text-decoration:line-through}} tr.obsolete td:last-child{{text-decoration:none}}
.gap{{color:#c0392b}} .pill{{padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600}}
.pass{{background:#e3f4e8;color:#1e7b3c}} .fail{{background:#fbe5e3;color:#b3261e}} .not{{background:#eef0f3;color:#5b6576}}
a{{color:#2557d6}}
</style></head><body>
<header><h1>Requirements Traceability Matrix</h1>
<p>Computed from the Git repository on {e(stamp)}. Need &rarr; Requirement &rarr; Element &rarr; Code &rarr; Verification.
Full documents: <a href="{STRICTDOC_LINK}">StrictDoc export</a> &middot; <a href="rtm.csv">rtm.csv</a> &middot; <a href="coverage.txt">coverage.txt</a></p></header>
<main><div class="tiles">{tiles_html}</div>
<table><thead><tr>{''.join(f'<th>{c}</th>' for c in cols)}</tr></thead><tbody>
{body}
</tbody></table></main></body></html>
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="site")
    p.add_argument("--fail-on-gaps", action="store_true", help="exit 3 if any active requirement has a gap")
    a = p.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows, cov = build(load_repo())
    with open(out / "rtm.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["Requirement"])
        w.writeheader()
        w.writerows(rows)
    (out / "coverage.txt").write_text(coverage_text(cov, stamp), encoding="utf-8")
    (out / "index.html").write_text(html_page(rows, cov, stamp), encoding="utf-8")
    print(coverage_text(cov, stamp))
    gaps = cov["no_need"] + cov["no_allocation"] + cov["no_code"] + cov["no_verification"]
    return 3 if a.fail_on_gaps and gaps else 0


if __name__ == "__main__":
    sys.exit(main())
