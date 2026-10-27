#!/usr/bin/env python3
"""
Sync approved requirements from Baserow to StrictDoc .sdoc files.
Fetches StakeholderNeed, Requirement, Allocation, Verification tables.
"""
import os, sys, json, urllib.request
from pathlib import Path

BASEROW_URL = os.environ.get("BASEROW_URL", "http://127.0.0.1:8000")
EMAIL = os.environ.get("BASEROW_EMAIL", "asimwealine2004@gmail.com")
PASSWORD = os.environ.get("BASEROW_PASSWORD", "12345678")
NEEDS_TABLE = int(os.environ.get("NEEDS_TABLE_ID", "709"))
REQS_TABLE = int(os.environ.get("REQS_TABLE_ID", "703"))
ALLOC_TABLE = int(os.environ.get("ALLOC_TABLE_ID", "706"))
VER_TABLE = int(os.environ.get("VER_TABLE_ID", "707"))
OUT_DIR = os.environ.get("OUT_DIR", "/tmp/sdoc_out")

def get_jwt():
    req = urllib.request.Request(
        f"{BASEROW_URL}/api/user/token-auth/",
        data=json.dumps({"email": EMAIL, "password": PASSWORD}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        method="POST"
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["token"]

def fetch_table(table_id, jwt):
    rows = []
    url = f"{BASEROW_URL}/api/database/rows/table/{table_id}/?size=200&user_field_names=true"
    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"JWT {jwt}",
            "User-Agent": "Mozilla/5.0"
        })
        data = json.loads(urllib.request.urlopen(req, timeout=30).read())
        rows.extend(data.get("results", []))
        url = data.get("next")
    return rows

def get_link_ids(value):
    if isinstance(value, list):
        return [item.get("id") for item in value if isinstance(item, dict)]
    return []

def get_link_values(value):
    if isinstance(value, list):
        return [item.get("value", "") for item in value if isinstance(item, dict)]
    return []

def get_select_value(value):
    if isinstance(value, dict):
        return value.get("value", "")
    return str(value) if value else ""

def write_sdoc(needs, reqs, allocs, verifs, outdir):
    Path(outdir).mkdir(parents=True, exist_ok=True)

    # Map: requirement baserow_id → list of allocations
    alloc_by_req = {}
    for a in allocs:
        req_ids = get_link_ids(a.get("Requirement"))
        for rid in req_ids:
            alloc_by_req.setdefault(rid, []).append(a)

    # Map: requirement baserow_id → list of verifications
    ver_by_req = {}
    for v in verifs:
        req_ids = get_link_ids(v.get("Requirement"))
        for rid in req_ids:
            ver_by_req.setdefault(rid, []).append(v)

    # Group requirements by need
    by_need = {}
    for r in reqs:
        rid = r.get("Req ID")
        if not rid:
            continue
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

        title = n.get("Title") or n.get("Name") or "Untitled"
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
            rid = r.get("Req ID")
            status = get_select_value(r.get("Status"))
            baserow_id = r["id"]
            content += "[REQUIREMENT]\n"
            content += f"UID: {rid}\n"
            content += f"TITLE: {rid}\n"
            content += f"STATEMENT: {r.get('Statement', '')}\n"
            content += f"STATUS: {status}\n"
            content += "RELATIONS:\n"
            content += f"- TYPE: Parent\n  VALUE: NEED-{nid}\n"

            # Add allocation links
            for a in alloc_by_req.get(baserow_id, []):
                element_values = get_link_values(a.get("Element"))
                element_name = element_values[0] if element_values else f"ALLOC-{a['id']}"
                content += f"- TYPE: AllocatedTo\n  VALUE: {element_name}\n"

            # Add verification links
            for v in ver_by_req.get(baserow_id, []):
                ver_id = v.get("Verification ID") or f"VER-{v['id']}"
                content += f"- TYPE: VerifiedBy\n  VALUE: {ver_id}\n"

            content += "\n"

        (Path(outdir) / f"need_{nid}.sdoc").write_text(content)
        written += 1
    return written

def main():
    print(f"Connecting to Baserow at {BASEROW_URL}...")
    jwt = get_jwt()
    print("✅ JWT obtained")

    print(f"Fetching needs (table {NEEDS_TABLE})...")
    needs = fetch_table(NEEDS_TABLE, jwt)

    print(f"Fetching requirements (table {REQS_TABLE})...")
    reqs = fetch_table(REQS_TABLE, jwt)

    print(f"Fetching allocations (table {ALLOC_TABLE})...")
    allocs = fetch_table(ALLOC_TABLE, jwt)

    print(f"Fetching verifications (table {VER_TABLE})...")
    verifs = fetch_table(VER_TABLE, jwt)

    count = write_sdoc(needs, reqs, allocs, verifs, OUT_DIR)
    print(f"✅ Wrote {count} .sdoc files to {OUT_DIR}")

if __name__ == "__main__":
    main()
