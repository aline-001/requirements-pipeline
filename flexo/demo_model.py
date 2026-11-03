#!/usr/bin/env python3
"""
Put the pipeline's requirements into Flexo as a SysML v2 model, and prepare a model pull request.

  1. logs in (first LDAP user in .env) and finds the SysML v2 project "Pipeline demo"
  2. commits every non-Obsolete requirement from ../docs/sdoc/requirements.sdoc to the main branch
     as a SysML v2 RequirementDefinition (declaredShortName = REQ id, declaredName = statement)
  3. creates the branch "cr-session-timeout" and commits a proposed change on it
     (REQ-002: 15 -> 30 minutes, the open change request "Increase session timeout")
  4. prints what to choose in the PR Manager to open the pull request cr-session-timeout -> main

Safe to run again: element ids are derived from the requirement ids, so a rerun updates the same
elements, and the branch is only created once. Standard library only; uses the local ports.
"""
import base64
import json
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUTH = "http://127.0.0.1:8082"
API = "http://127.0.0.1:8083"
PROJECT = "Pipeline demo"
BRANCH = "cr-session-timeout"
NS = uuid.UUID("5d1f6a52-3c1e-4a8e-9a57-2f7b6e0c4d11")  # fixed namespace -> stable element ids


def env() -> dict:
    out = {}
    for line in (HERE / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k] = v.strip()
    return out


def call(method, url, token=None, body=None, basic=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if basic:
        req.add_header("Authorization", "Basic " + base64.b64encode(basic.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR {method} {url} -> HTTP {e.code}: {e.read().decode(errors='replace')[:400]}")


def items(payload):
    return payload if isinstance(payload, list) else payload.get("elements", payload.get("@graph", []))


def requirements() -> list[dict]:
    text = (HERE.parent / "docs" / "sdoc" / "requirements.sdoc").read_text(encoding="utf-8")
    reqs = []
    for block in text.split("[REQUIREMENT]")[1:]:
        block = re.split(r"\n(?:RELATIONS:|\[)", block, maxsplit=1)[0]   # this node's fields only
        f = dict(re.findall(r"^([A-Z_]+): (.+)$", block, re.M))
        if f.get("UID") and f.get("STATUS") != "Obsolete":
            reqs.append(f)
    if not reqs:
        sys.exit("No requirements found in docs/sdoc/requirements.sdoc - run the sync first.")
    return reqs


def element(req: dict, statement: str) -> dict:
    eid = str(uuid.uuid5(NS, req["UID"]))
    return {
        "payload": {
            "@type": "RequirementDefinition",
            "elementId": eid,
            "declaredShortName": req["UID"],
            "declaredName": statement or req["UID"],
            "isLibraryElement": False,
            "aliasIds": [],
        },
        "identity": {"@id": eid},
    }


def commit(token, project_id, changes, branch_id=None, description=""):
    url = f"{API}/projects/{project_id}/commits"
    q = [f"branchId={branch_id}"] if branch_id else []
    if description:
        q.append("description=" + urllib.request.quote(description))
    if q:
        url += "?" + "&".join(q)
    return call("POST", url, token, {"@type": "Commit", "change": changes})


def main():
    e = env()
    user, pw = e["LDAP_USERS"].split(",")[0], e["LDAP_PASSWORDS"].split(",")[0]
    token = call("GET", f"{AUTH}/login", basic=f"{user}:{pw}")["token"]

    project = next((p for p in items(call("GET", f"{API}/projects", token)) if p.get("name") == PROJECT), None)
    if not project:
        sys.exit(f'Project "{PROJECT}" not found - run ./smoke_test.sh --create-demo first.')
    pid = project["@id"]
    print(f'project "{PROJECT}": {pid}')

    reqs = requirements()
    c1 = commit(token, pid, [element(r, r.get("STATEMENT", "")) for r in reqs],
                description="Baselined requirements from the Git pipeline")
    print(f"main: committed {len(reqs)} requirements ({', '.join(r['UID'] for r in reqs)}) -> commit {c1.get('@id')}")

    branches = items(call("GET", f"{API}/projects/{pid}/branches", token))
    br = next((b for b in branches if b.get("name") == BRANCH), None)
    if not br:
        br = call("POST", f"{API}/projects/{pid}/branches", token, {"@type": "Branch", "name": BRANCH, "head": {"@id": c1["@id"]}})
        print(f'created branch "{BRANCH}": {br.get("@id")}')
    else:
        print(f'branch "{BRANCH}" already exists: {br.get("@id")}')

    target = next((r for r in reqs if r["UID"] == "REQ-002"), reqs[0])
    changed = target.get("STATEMENT", "").replace("15 minutes", "30 minutes") or "Changed statement"
    c2 = commit(token, pid, [element(target, changed)], branch_id=br["@id"],
                description=f"CR Increase session timeout: {target['UID']}")
    print(f'{BRANCH}: committed proposed change to {target["UID"]} -> commit {c2.get("@id")}')

    print("\nIn the PR Manager (https://pr.darho.net): New pull request ->")
    print(f'  project "{PROJECT}", source branch "{BRANCH}", target branch the main branch (master/main)')


if __name__ == "__main__":
    main()
