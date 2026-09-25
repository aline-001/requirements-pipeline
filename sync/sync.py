#!/usr/bin/env python3
"""
Sync approved requirements from Baserow to StrictDoc .sdoc files.
Runs INSIDE the Baserow container (invoked via docker exec).
"""
import os
import sys
import json
import urllib.request
from pathlib import Path

BASEROW_URL = os.environ.get("BASEROW_URL", "http://127.0.0.1:8000")
BASEROW_TOKEN = os.environ.get("BASEROW_TOKEN", "")
NEEDS_TABLE = os.environ.get("NEEDS_TABLE_ID", "700")
REQS_TABLE = os.environ.get("REQS_TABLE_ID", "702")
OUT_DIR = os.environ.get("OUT_DIR", "/tmp/sdoc_out")

NEED_FIELDS = {
    "Title": "field_6698",
    "Statement": "field_6699",
    "Priority": "field_6700",
    "Rationale": "field_6701",
    "Status": "field_6702",
    "Source": "field_6703",
    "Stakeholder": "field_6704",
}

REQ_FIELDS = {
    "ReqID": "field_6714",
    "Statement": "field_6715",
    "Type": "field_6716",
    "Status": "field_6717",
    "Need": "field_6718",
    "Allocations": "field_6723",
    "Verifications": "field_6729",
}

def fetch_table(table_id):
    rows = []
    url = f"{BASEROW_URL}/api/database/rows/table/{table_id}/?size=200"
    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Token {BASEROW_TOKEN}",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        rows.extend(data.get("results", []))
        url = data.get("next")
    return rows

def rename_row(row, field_map):
    out = {"id": row["id"]}
    for human, internal in field_map.items():
        out[human] = row.get(internal)
    return out

def get_link_ids(value):
    if isinstance(value, list):
        return [item.get("id") for item in value if isinstance(item, dict)]
    return []

def get_select_value(value):
    if isinstance(value, dict):
        return value.get("value", "")
    return ""

def validate(needs, reqs):
    """Return list of error strings. Warns about rows to skip; errors about fatal issues."""
    errors = []
    warnings = []
    need_ids = {n["id"] for n in needs}
    seen = set()
    for r in reqs:
        rid = r.get("ReqID")
        if not rid:
            warnings.append(f"Skipping requirement id={r['id']}: no Req ID")
            continue
        if rid in seen:
            errors.append(f"Duplicate Req ID: {rid}")
        seen.add(rid)
        need_refs = get_link_ids(r.get("Need"))
        if not need_refs:
            errors.append(f"Requirement {rid} has no need")
        else:
            for nid in need_refs:
                if nid not in need_ids:
                    errors.append(f"Requirement {rid} links to missing need id={nid}")
    return errors, warnings

def write_sdoc(needs, reqs, outdir):
    Path(outdir).mkdir(parents=True, exist_ok=True)

    by_need = {}
    for r in reqs:
        rid = r.get("ReqID")
        if not rid:
            continue  # skip incomplete
        status = get_select_value(r.get("Status"))
        if status not in ("Approved", "Baselined"):
            continue
        for nid in get_link_ids(r.get("Need")):
            by_need.setdefault(nid, []).append(r)

    written = 0
    for n in needs:
        nid = n["id"]
        need_status = get_select_value(n.get("Status"))
        reqs_for_need = by_need.get(nid, [])
        if need_status != "Approved" and not reqs_for_need:
            continue

        title = n.get("Title") or "Untitled"
        content = f"[DOCUMENT]\nTITLE: {title}\n\n"
        content += "[SECTION]\nTITLE: Stakeholder Need\n\n"
        content += "[REQUIREMENT]\n"
        content += f"UID: NEED-{nid}\n"
        content += f"TITLE: {title}\n"
        content += f"STATEMENT: {n.get('Statement', '')}\n"
        content += f"PRIORITY: {get_select_value(n.get('Priority'))}\n"
        content += f"RATIONALE: {n.get('Rationale', '')}\n"
        content += f"STATUS: {need_status}\n\n"

        for r in reqs_for_need:
            rid = r.get("ReqID")
            status = get_select_value(r.get("Status"))
            content += "[REQUIREMENT]\n"
            content += f"UID: {rid}\n"
            content += f"TITLE: {rid}\n"
            content += f"STATEMENT: {r.get('Statement', '')}\n"
            content += f"STATUS: {status}\n"
            content += "RELATIONS:\n"
            content += f"- TYPE: Parent\n  VALUE: NEED-{nid}\n"
            allocs = get_link_ids(r.get("Allocations"))
            for aid in allocs:
                content += f"- TYPE: AllocatedTo\n  VALUE: ELEM-{aid}\n"
            verifs = get_link_ids(r.get("Verifications"))
            for vid in verifs:
                content += f"- TYPE: VerifiedBy\n  VALUE: VER-{vid}\n"
            content += "\n"

        (Path(outdir) / f"need_{nid}.sdoc").write_text(content)
        written += 1

    return written

def mark_baselined(req_ids, approved_id, baselined_id):
    """After successful sync, mark requirements as Baselined in Baserow."""
    hdrs = {"Authorization": f"Token {BASEROW_TOKEN}", "Content-Type": "application/json"}
    base = f"{BASEROW_URL}/api/database/rows/table/{REQS_TABLE}/"
    for rid_baserow, req_uid in req_ids:
        body = json.dumps({"field_6717": baselined_id}).encode()
        req = urllib.request.Request(base + f"{rid_baserow}/", data=body, method="PATCH", headers=hdrs)
        try:
            urllib.request.urlopen(req, timeout=30)
            print(f"  Marked {req_uid} as Baselined")
        except Exception as e:
            print(f"  WARN: could not mark {req_uid} as Baselined: {e}")


def main():
    if not BASEROW_TOKEN:
        print("ERROR: BASEROW_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching needs from table {NEEDS_TABLE}...")
    raw_needs = fetch_table(NEEDS_TABLE)
    needs = [rename_row(r, NEED_FIELDS) for r in raw_needs]
    print(f"  {len(needs)} needs")

    print(f"Fetching requirements from table {REQS_TABLE}...")
    raw_reqs = fetch_table(REQS_TABLE)
    reqs = [rename_row(r, REQ_FIELDS) for r in raw_reqs]
    print(f"  {len(reqs)} requirements")

    errors, warnings = validate(needs, reqs)
    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    if errors:
        print("VALIDATION ERRORS:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    count = write_sdoc(needs, reqs, OUT_DIR)
    print(f"Wrote {count} .sdoc files to {OUT_DIR}")

    # Optionally mark baselined (disabled by default; set MARK_BASELINED=1)
    if os.environ.get("MARK_BASELINED") == "1":
        # We need the Baselined option id. Fetch a Baselined row if one exists.
        # Fallback: use Approved id if Baselined unknown — not ideal, warn.
        print("MARK_BASELINED requested — looking up Baselined option id...")
        try:
            sample = fetch_table(REQS_TABLE)
            baselined_id = None
            for r in sample:
                st = r.get("field_6717")
                if isinstance(st, dict) and st.get("value") == "Baselined":
                    baselined_id = st["id"]
                    break
            if baselined_id is None:
                print("  WARN: no Baselined option found in any row — skipping mark step.")
                print("  In Baserow UI, ensure the Status field has a 'Baselined' option and one row uses it.")
            else:
                # Build list of (baserow_row_id, req_uid) for approved reqs we wrote
                targets = []
                for r in raw_reqs:
                    rn = rename_row(r, REQ_FIELDS)
                    st = get_select_value(rn.get("Status"))
                    if st in ("Approved", "Baselined") and rn.get("ReqID"):
                        targets.append((r["id"], rn["ReqID"]))
                mark_baselined(targets, None, baselined_id)
        except Exception as e:
            print(f"  WARN: mark_baselined failed: {e}")

if __name__ == "__main__":
    main()
