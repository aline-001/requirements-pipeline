#!/usr/bin/env python3
"""Build a Requirements Traceability Matrix (RTM) from .sdoc files and code @relation tags."""
import re
import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
SDOC_DIR = ROOT / "docs" / "generated"
SRC_DIR = ROOT / "src"
RTM_CSV = ROOT / "rtm.csv"
RTM_HTML = ROOT / "rtm.html"
COVERAGE_TXT = ROOT / "coverage.txt"


def parse_sdoc(path):
    text = path.read_text()
    reqs = []
    for block in re.split(r'\[REQUIREMENT\]', text)[1:]:
        req = {}
        for field in ("UID", "TITLE", "STATEMENT", "STATUS", "PRIORITY", "RATIONALE"):
            m = re.search(rf'^{field}:\s*(.+)$', block, re.MULTILINE)
            if m:
                req[field] = m.group(1).strip()
        pm = re.search(r'-\s*TYPE:\s*Parent\s*\n\s*VALUE:\s*(\S+)', block)
        if pm:
            req["PARENT"] = pm.group(1)
        if req.get("UID"):
            reqs.append(req)
    return reqs


def parse_code_relations():
    links = defaultdict(list)
    if not SRC_DIR.exists():
        return links
    for py in SRC_DIR.rglob("*.py"):
        lines = py.read_text().splitlines()
        for i, line in enumerate(lines):
            m = re.search(r'@relation\(([^)]+)\)', line)
            if m:
                uids = re.findall(r'"([^"]+)"', m.group(1))
                for uid in uids:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        fm = re.match(r'\s*def\s+(\w+)', lines[j])
                        if fm:
                            links[uid].append(f"{py.name}:{fm.group(1)}")
                            break
    return links


def build_rtm():
    """Return (needs, requirements) — two lists."""
    needs = []
    requirements = []
    for f in sorted(SDOC_DIR.glob("*.sdoc")):
        for r in parse_sdoc(f):
            if r["UID"].startswith("NEED-"):
                needs.append(r)
            elif r["UID"].startswith("REQ-"):
                requirements.append(r)

    code_links = parse_code_relations()
    rows = []
    for r in requirements:
        uid = r["UID"]
        rows.append({
            "UID": uid,
            "Title": r.get("TITLE", ""),
            "Statement": r.get("STATEMENT", ""),
            "Status": r.get("STATUS", ""),
            "ParentNeed": r.get("PARENT", ""),
            "CodeLink": ", ".join(code_links.get(uid, [])),
        })
    return needs, rows


def write_csv(rows):
    with RTM_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["UID", "Title", "Statement", "Status", "ParentNeed", "CodeLink"])
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_html(rows):
    total = len(rows)
    with_code = sum(1 for r in rows if r["CodeLink"])
    with_parent = sum(1 for r in rows if r["ParentNeed"])
    passed = sum(1 for r in rows if r["Status"] in ("Approved", "Baselined"))
    pass_rate = (passed / total * 100) if total else 0

    html = ['<!DOCTYPE html><html><head><meta charset="utf-8">',
            '<title>Requirements Traceability Matrix</title>',
            '<style>',
            'body{font-family:sans-serif;margin:2em}',
            'table{border-collapse:collapse;width:100%}',
            'th,td{border:1px solid #ccc;padding:6px 10px;text-align:left;vertical-align:top}',
            'th{background:#f0f0f0}',
            '.ok{color:#0a0}.miss{color:#c00}',
            '.summary{margin:1em 0;padding:1em;background:#f9f9f9;border-left:4px solid #06c}',
            '</style></head><body>',
            '<h1>Requirements Traceability Matrix</h1>',
            '<div class="summary">',
            f'<p><strong>Total requirements:</strong> {total}</p>',
            f'<p><strong>With parent need:</strong> {with_parent} ({with_parent/total*100 if total else 0:.1f}%)</p>',
            f'<p><strong>With code link:</strong> {with_code} ({with_code/total*100 if total else 0:.1f}%)</p>',
            f'<p><strong>Pass rate (Approved or Baselined):</strong> {passed}/{total} = {pass_rate:.1f}%</p>',
            '</div>',
            '<table>',
            '<tr><th>UID</th><th>Title</th><th>Statement</th><th>Status</th><th>Parent Need</th><th>Code Link</th></tr>']
    for r in rows:
        p = r["ParentNeed"]
        c = r["CodeLink"]
        html.append(f"<tr><td>{r['UID']}</td><td>{r['Title']}</td><td>{r['Statement']}</td>")
        html.append(f"<td>{r['Status']}</td>")
        html.append(f"<td class='{'ok' if p else 'miss'}'>{p or 'NONE'}</td>")
        html.append(f"<td class='{'ok' if c else 'miss'}'>{c or 'NONE'}</td></tr>")
    html.append('</table></body></html>')
    RTM_HTML.write_text("".join(html))


def write_coverage(needs, rows):
    total = len(rows)
    no_parent = [r["UID"] for r in rows if not r["ParentNeed"]]
    no_code = [r["UID"] for r in rows if not r["CodeLink"]]
    no_status = [r["UID"] for r in rows if not r["Status"]]
    passed = sum(1 for r in rows if r["Status"] in ("Approved", "Baselined"))
    rate = (passed / total * 100) if total else 0
    lines = [
        f"Total stakeholder needs: {len(needs)}",
        f"Total requirements: {total}",
        f"Requirements with no parent need: {len(no_parent)} {no_parent}",
        f"Requirements with no code link: {len(no_code)} {no_code}",
        f"Requirements with no status: {len(no_status)} {no_status}",
        f"Pass rate (Approved or Baselined): {passed}/{total} = {rate:.1f}%",
    ]
    COVERAGE_TXT.write_text("\n".join(lines) + "\n")
    return "\n".join(lines)


def main():
    needs, rows = build_rtm()
    write_csv(rows)
    write_html(rows)
    print(write_coverage(needs, rows))
    print(f"\nWrote {RTM_CSV.name}, {RTM_HTML.name}, {COVERAGE_TXT.name}")


if __name__ == "__main__":
    main()
