#!/usr/bin/env python3
"""
Baserow -> StrictDoc sync (Requirements Engineering Pipeline, Task 4).

Reads the Baserow REST API and writes StrictDoc 0.30.x .sdoc files:

    docs/sdoc/needs.sdoc          [NEED]          approved stakeholder needs
    docs/sdoc/requirements.sdoc   [REQUIREMENT]   Parent -> NEED, File <- code
    docs/sdoc/elements.sdoc       [ELEMENT]       Parent -> REQUIREMENT (role Implements)
    docs/sdoc/verification.sdoc   [VERIFICATION]  Parent -> REQUIREMENT (role Verifies)

Commands
    python3 sync/sync.py export      # Baserow -> .sdoc (default)
    python3 sync/sync.py baseline    # mark requirements found in Git as Baselined in Baserow
    python3 sync/sync.py check       # run all link/ID checks, write nothing

Exit codes: 0 ok, 1 configuration/API error, 2 data errors (nothing is written).

Format rules this script obeys (verified against the StrictDoc 0.30.4 grammar):
  * [SECTION] is no longer supported; sections are [[SECTION]] ... [[/SECTION]].
  * Every node type and field must be declared in the document [GRAMMAR].
  * Fields must appear in exactly the order the grammar declares them.
  * Relations need a matching RELATIONS entry (type + role) in the grammar.
  * Values: single line "FIELD: value" (never empty, starts with a non-space),
    or multi-line "FIELD: >>>" ... "<<<".

Only the Python standard library is used, so it runs on the VPS host as is.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Configuration (.env in the repository root, or real environment variables)
# --------------------------------------------------------------------------


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env(ROOT / ".env")

BASEROW_URL = os.environ.get("BASEROW_URL", "http://127.0.0.1:8000").rstrip("/")
BASEROW_TOKEN = os.environ.get("BASEROW_TOKEN", "")  # database token (preferred)
BASEROW_EMAIL = os.environ.get("BASEROW_EMAIL", "")  # JWT fallback
BASEROW_PASSWORD = os.environ.get("BASEROW_PASSWORD", "")

TABLES = {
    "need": int(os.environ.get("TABLE_STAKEHOLDER_NEED", "709")),
    "requirement": int(os.environ.get("TABLE_REQUIREMENT", "703")),
    "element": int(os.environ.get("TABLE_SYSTEM_ELEMENT", "701")),
    "allocation": int(os.environ.get("TABLE_ALLOCATION", "706")),
    "verification": int(os.environ.get("TABLE_VERIFICATION", "707")),
}

OUT_DIR = ROOT / os.environ.get("SDOC_OUT_DIR", "docs/sdoc")

# Status values used in Baserow single-select fields.
NEED_EXPORT_STATUSES = {"Approved"}
# Approved = ready to baseline, Baselined = already in Git,
# Obsolete = removed but kept so the ID is never reused (Task 6).
REQ_EXPORT_STATUSES = {"Approved", "Baselined", "Obsolete"}
REQ_ID_PATTERN = re.compile(r"^REQ-\d{3,}$")

# Candidate Baserow field names (first one present wins). Adjust if yours differ.
F = {
    "need_title": ["Title", "Name"],
    "need_statement": ["Statement", "Description"],
    "need_priority": ["Priority"],
    "need_rationale": ["Rationale"],
    "need_status": ["Status"],
    "need_stakeholder": ["Stakeholder"],
    "need_source": ["Source"],
    "req_id": ["Requirement ID", "ID", "Req ID", "Name"],
    "req_title": ["Title"],
    "req_statement": ["Statement", "Description", "Text"],
    "req_rationale": ["Rationale"],
    "req_status": ["Status"],
    "req_need": ["Need", "StakeholderNeed", "Stakeholder Need", "Parent Need"],
    "elem_name": ["Name", "Title", "Element"],
    "elem_description": ["Description"],
    "alloc_req": ["Requirement"],
    "alloc_elem": ["SystemElement", "System Element", "Element"],
    "ver_id": ["Verification ID", "ID", "Name"],
    "ver_req": ["Requirement"],
    "ver_method": ["Method"],
    "ver_criteria": ["Acceptance Criteria", "AcceptanceCriteria"],
    "ver_result": ["Result"],
}


class ConfigError(Exception):
    pass


# --------------------------------------------------------------------------
# Baserow API
# --------------------------------------------------------------------------


class Baserow:
    def __init__(self) -> None:
        if BASEROW_TOKEN:
            self.auth = f"Token {BASEROW_TOKEN}"
        elif BASEROW_EMAIL and BASEROW_PASSWORD:
            data = self._call(
                "POST",
                "/api/user/token-auth/",
                {"email": BASEROW_EMAIL, "password": BASEROW_PASSWORD},
                auth=None,
            )
            self.auth = f"JWT {data.get('access_token') or data['token']}"
        else:
            raise ConfigError("Set BASEROW_TOKEN (preferred) or BASEROW_EMAIL/BASEROW_PASSWORD in .env")

    def _call(self, method: str, path: str, body=None, auth: str | None = "self"):
        headers = {"Content-Type": "application/json", "User-Agent": "requirements-sync/1.0"}
        if auth == "self":
            headers["Authorization"] = self.auth
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(BASEROW_URL + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise ConfigError(f"Baserow {method} {path} -> HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
        except urllib.error.URLError as e:
            raise ConfigError(f"Cannot reach Baserow at {BASEROW_URL}: {e.reason}")

    def rows(self, table_id: int) -> list[dict]:
        out, page = [], 1
        while True:
            q = urllib.parse.urlencode({"user_field_names": "true", "size": 200, "page": page})
            data = self._call("GET", f"/api/database/rows/table/{table_id}/?{q}")
            out.extend(data["results"])
            if not data.get("next"):
                return out
            page += 1

    def select_option_id(self, table_id: int, field_name: str, value: str):
        for field in self._call("GET", f"/api/database/fields/table/{table_id}/"):
            if field["name"] == field_name:
                for opt in field.get("select_options", []):
                    if opt["value"] == value:
                        return opt["id"]
                raise ConfigError(f'Field "{field_name}" in table {table_id} has no option "{value}". Add it in Baserow.')
        raise ConfigError(f'Field "{field_name}" not found in table {table_id}')

    def update_row(self, table_id: int, row_id: int, values: dict) -> None:
        self._call("PATCH", f"/api/database/rows/table/{table_id}/{row_id}/?user_field_names=true", values)


# --------------------------------------------------------------------------
# Row helpers
# --------------------------------------------------------------------------


def field_name(row: dict, key: str, table: str, required: bool = True) -> str | None:
    for name in F[key]:
        if name in row:
            return name
    if required:
        raise ConfigError(
            f"Table {table}: none of the fields {F[key]} exist. Available fields: {sorted(row)}. "
            f'Edit F["{key}"] in sync.py.'
        )
    return None


def text(row: dict, key: str, table: str, required: bool = False) -> str:
    name = field_name(row, key, table, required)
    if name is None:
        return ""
    v = row.get(name)
    if v is None:
        return ""
    if isinstance(v, dict):  # single select
        return str(v.get("value") or "").strip()
    if isinstance(v, list):  # link row / multiple select / lookup
        return ", ".join(str(i.get("value", "")) if isinstance(i, dict) else str(i) for i in v).strip()
    return str(v).strip()


def links(row: dict, key: str, table: str) -> list[int]:
    name = field_name(row, key, table, required=True)
    return [i["id"] for i in (row.get(name) or []) if isinstance(i, dict) and "id" in i]


# --------------------------------------------------------------------------
# Model building + validation (Task 4 error checks)
# --------------------------------------------------------------------------


def build_model(data: dict[str, list[dict]]) -> tuple[dict, list[str]]:
    errors: list[str] = []
    needs_all = {r["id"]: r for r in data["need"]}
    needs = {
        rid: {
            "uid": f"NEED-{rid}",
            "status": text(r, "need_status", "StakeholderNeed", True),
            "title": text(r, "need_title", "StakeholderNeed", True),
            "statement": text(r, "need_statement", "StakeholderNeed"),
            "priority": text(r, "need_priority", "StakeholderNeed"),
            "stakeholder": text(r, "need_stakeholder", "StakeholderNeed"),
            "source": text(r, "need_source", "StakeholderNeed"),
            "rationale": text(r, "need_rationale", "StakeholderNeed"),
        }
        for rid, r in needs_all.items()
        if text(r, "need_status", "StakeholderNeed", True) in NEED_EXPORT_STATUSES
    }

    # Requirements: duplicate IDs are checked across ALL rows (any status),
    # so an Obsolete ID can never be reused by a new row.
    seen: dict[str, int] = {}
    reqs: dict[int, dict] = {}
    for r in data["requirement"]:
        uid = text(r, "req_id", "Requirement", True)
        status = text(r, "req_status", "Requirement", True)
        if not uid:
            if status in REQ_EXPORT_STATUSES:
                errors.append(f"Requirement row {r['id']}: empty requirement ID")
            continue
        if uid in seen:
            errors.append(f"DUPLICATE ID: {uid} is used by Requirement rows {seen[uid]} and {r['id']}")
            continue
        seen[uid] = r["id"]
        if status not in REQ_EXPORT_STATUSES:
            continue  # Draft / In review: not exported
        if not REQ_ID_PATTERN.match(uid):
            errors.append(f"{uid}: ID does not match {REQ_ID_PATTERN.pattern}")
        parent_ids = links(r, "req_need", "Requirement")
        if not parent_ids:
            errors.append(f"NO NEED: {uid} is not linked to any stakeholder need")
        for nid in parent_ids:
            if nid not in needs_all:
                errors.append(f"BROKEN LINK: {uid} -> need row {nid} does not exist")
            elif nid not in needs:
                errors.append(
                    f"BROKEN LINK: {uid} -> NEED-{nid} is not Approved "
                    f'(status "{text(needs_all[nid], "need_status", "StakeholderNeed")}")'
                )
        title = text(r, "req_title", "Requirement") if field_name(r, "req_title", "Requirement", False) else ""
        reqs[r["id"]] = {
            "uid": uid,
            "status": status,
            "title": title if title and title != uid else "",
            "statement": text(r, "req_statement", "Requirement"),
            "rationale": text(r, "req_rationale", "Requirement"),
            "parents": [f"NEED-{n}" for n in parent_ids if n in needs],
            "row_id": r["id"],
        }
        if not reqs[r["id"]]["statement"]:
            errors.append(f"{uid}: empty statement")

    all_req_rows = {r["id"] for r in data["requirement"]}
    elements = {
        r["id"]: {
            "uid": f"ELEM-{r['id']}",
            "title": text(r, "elem_name", "SystemElement", True) or f"Element {r['id']}",
            "statement": text(r, "elem_description", "SystemElement"),
            "implements": [],
        }
        for r in data["element"]
    }
    for a in data["allocation"]:
        for rq in links(a, "alloc_req", "Allocation"):
            for el in links(a, "alloc_elem", "Allocation"):
                if rq not in all_req_rows:
                    errors.append(f"BROKEN LINK: Allocation row {a['id']} -> requirement row {rq} does not exist")
                elif el not in elements:
                    errors.append(f"BROKEN LINK: Allocation row {a['id']} -> element row {el} does not exist")
                elif rq in reqs and reqs[rq]["uid"] not in elements[el]["implements"]:
                    elements[el]["implements"].append(reqs[rq]["uid"])
        if not links(a, "alloc_req", "Allocation") or not links(a, "alloc_elem", "Allocation"):
            errors.append(f"BROKEN LINK: Allocation row {a['id']} is missing its requirement or element")

    vers: list[dict] = []
    ver_seen: dict[str, int] = {}
    for v in data["verification"]:
        vid = text(v, "ver_id", "Verification", True) or f"VER-{v['id']}"
        if vid in ver_seen:
            errors.append(f"DUPLICATE ID: {vid} is used by Verification rows {ver_seen[vid]} and {v['id']}")
            continue
        ver_seen[vid] = v["id"]
        targets = links(v, "ver_req", "Verification")
        if not targets:
            errors.append(f"BROKEN LINK: {vid} is not linked to a requirement")
        for rq in targets:
            if rq not in all_req_rows:
                errors.append(f"BROKEN LINK: {vid} -> requirement row {rq} does not exist")
        exported = [reqs[rq]["uid"] for rq in targets if rq in reqs]
        if exported:
            vers.append(
                {
                    "uid": vid,
                    "method": text(v, "ver_method", "Verification"),
                    "criteria": text(v, "ver_criteria", "Verification"),
                    "result": text(v, "ver_result", "Verification") or "Not run",
                    "verifies": exported,
                }
            )

    # UIDs must be unique across all documents (StrictDoc rejects duplicates).
    all_uids: dict[str, str] = {}
    for kind, items in (
        ("need", needs.values()),
        ("requirement", reqs.values()),
        ("element", elements.values()),
        ("verification", vers),
    ):
        for it in items:
            if it["uid"] in all_uids:
                errors.append(f"DUPLICATE ID: {it['uid']} used by a {all_uids[it['uid']]} and a {kind}")
            all_uids[it["uid"]] = kind

    errors += check_against_git(reqs)
    return {"needs": needs, "reqs": reqs, "elements": elements, "vers": vers}, errors


def check_against_git(reqs: dict[int, dict]) -> list[str]:
    """IDs already in Git must never disappear or be reused (Task 6)."""
    path = OUT_DIR / "requirements.sdoc"
    if not path.exists():
        return []
    in_git = dict(re.findall(r"^UID: (\S+)\nSTATUS: (\S+)", path.read_text(encoding="utf-8"), re.M))
    now = {r["uid"]: r["status"] for r in reqs.values()}
    errors = []
    for uid, old in in_git.items():
        if uid not in now:
            errors.append(f"REMOVED: {uid} is in Git but no longer exported. Set it to Obsolete instead of deleting it.")
        elif old == "Obsolete" and now[uid] != "Obsolete":
            errors.append(f"ID REUSE: {uid} is Obsolete in Git and may not be reused (now {now[uid]}).")
    return errors


# --------------------------------------------------------------------------
# SDoc writer
# --------------------------------------------------------------------------


def sdoc_field(name: str, value: str) -> str:
    """One field. Empty values are skipped (the grammar marks them optional)."""
    value = (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not value:
        return ""
    if "\n" in value or value.startswith(">>>"):
        # A line that is exactly <<< would end the block early.
        body = "\n".join(" <<<" if ln.strip() == "<<<" else ln for ln in value.split("\n"))
        return f"{name}: >>>\n{body}\n<<<\n"
    return f"{name}: {value}\n"


def relations(items: list[tuple[str, str | None]]) -> str:
    if not items:
        return ""
    out = "RELATIONS:\n"
    for uid, role in items:
        out += f"- TYPE: Parent\n  VALUE: {uid}\n"
        if role:
            out += f"  ROLE: {role}\n"
    return out


SECTION_ELEMENT = """\
- TAG: SECTION
  PROPERTIES:
    IS_COMPOSITE: True
  FIELDS:
  - TITLE: UID
    TYPE: String
    REQUIRED: False
  - TITLE: TITLE
    TYPE: String
    REQUIRED: True
"""


def grammar_element(tag: str, fields: list[tuple[str, bool]], rels: list[tuple[str, str | None]]) -> str:
    out = f"- TAG: {tag}\n  FIELDS:\n"
    for name, required in fields:
        out += f"  - TITLE: {name}\n    TYPE: String\n    REQUIRED: {required}\n"
    if rels:
        out += "  RELATIONS:\n"
        for rtype, role in rels:
            out += f"  - TYPE: {rtype}\n"
            if role:
                out += f"    ROLE: {role}\n"
    return out


def document(title: str, uid: str, element: str, sections: list[tuple[str, list[str]]]) -> str:
    out = f"[DOCUMENT]\nTITLE: {title}\nUID: {uid}\n\n[GRAMMAR]\nELEMENTS:\n{SECTION_ELEMENT}{element}"
    for sec_title, nodes in sections:
        out += f"\n[[SECTION]]\nTITLE: {sec_title}\n"
        for node in nodes:
            out += "\n" + node
        out += "\n[[/SECTION]]\n"
    return out


# Field order below IS the order written in the nodes. Do not reorder one without the other.
NEED_FIELDS = [("UID", True), ("STATUS", True), ("TITLE", True), ("STATEMENT", True),
               ("PRIORITY", False), ("STAKEHOLDER", False), ("SOURCE", False), ("RATIONALE", False)]
REQ_FIELDS = [("UID", True), ("STATUS", True), ("TITLE", False), ("STATEMENT", True), ("RATIONALE", False)]
ELEM_FIELDS = [("UID", True), ("TITLE", True), ("STATEMENT", False)]
VER_FIELDS = [("UID", True), ("TITLE", True), ("METHOD", True), ("ACCEPTANCE_CRITERIA", True), ("RESULT", True)]


def render(model: dict) -> dict[str, str]:
    needs, reqs, elements, vers = model["needs"], model["reqs"], model["elements"], model["vers"]
    files = {}

    need_nodes = []
    for n in sorted(needs.values(), key=lambda n: int(n["uid"].split("-")[1])):
        need_nodes.append(
            "[NEED]\n"
            + sdoc_field("UID", n["uid"])
            + sdoc_field("STATUS", n["status"])
            + sdoc_field("TITLE", n["title"])
            + sdoc_field("STATEMENT", n["statement"] or n["title"])
            + sdoc_field("PRIORITY", n["priority"])
            + sdoc_field("STAKEHOLDER", n["stakeholder"])
            + sdoc_field("SOURCE", n["source"])
            + sdoc_field("RATIONALE", n["rationale"])
        )
    files["needs.sdoc"] = document(
        "Stakeholder Needs", "DOC-NEEDS",
        grammar_element("NEED", NEED_FIELDS, []),
        [("Approved stakeholder needs", need_nodes)] if need_nodes else [],
    )

    # Requirements grouped by their (first) parent need; Obsolete in its own section.
    groups: dict[str, list[dict]] = {}
    for r in sorted(reqs.values(), key=lambda r: r["uid"]):
        key = "Obsolete requirements" if r["status"] == "Obsolete" else (
            f"{r['parents'][0]}: {needs_by_uid(needs)[r['parents'][0]]['title']}" if r["parents"] else "Unlinked"
        )
        groups.setdefault(key, []).append(r)
    req_sections = []
    for key in sorted(groups, key=lambda k: (k.startswith("Obsolete"), k)):
        nodes = []
        for r in groups[key]:
            nodes.append(
                "[REQUIREMENT]\n"
                + sdoc_field("UID", r["uid"])
                + sdoc_field("STATUS", r["status"])
                + sdoc_field("TITLE", r["title"])
                + sdoc_field("STATEMENT", r["statement"])
                + sdoc_field("RATIONALE", r["rationale"])
                + relations([(p, None) for p in r["parents"]])
            )
        req_sections.append((key, nodes))
    files["requirements.sdoc"] = document(
        "System Requirements", "DOC-REQS",
        grammar_element("REQUIREMENT", REQ_FIELDS, [("Parent", None), ("File", None)]),
        req_sections,
    )

    elem_nodes = []
    for e in sorted(elements.values(), key=lambda e: int(e["uid"].split("-")[1])):
        elem_nodes.append(
            "[ELEMENT]\n"
            + sdoc_field("UID", e["uid"])
            + sdoc_field("TITLE", e["title"])
            + sdoc_field("STATEMENT", e["statement"])
            + relations([(u, "Implements") for u in sorted(e["implements"])])
        )
    files["elements.sdoc"] = document(
        "System Elements and Allocation", "DOC-ELEMENTS",
        grammar_element("ELEMENT", ELEM_FIELDS, [("Parent", "Implements"), ("File", None)]),
        [("System elements", elem_nodes)] if elem_nodes else [],
    )

    ver_nodes = []
    for v in sorted(vers, key=lambda v: v["uid"]):
        ver_nodes.append(
            "[VERIFICATION]\n"
            + sdoc_field("UID", v["uid"])
            + sdoc_field("TITLE", f"Verification of {', '.join(v['verifies'])}")
            + sdoc_field("METHOD", v["method"] or "Not specified")
            + sdoc_field("ACCEPTANCE_CRITERIA", v["criteria"] or "Not specified")
            + sdoc_field("RESULT", v["result"])
            + relations([(u, "Verifies") for u in v["verifies"]])
        )
    files["verification.sdoc"] = document(
        "Verification Records", "DOC-VERIFICATION",
        grammar_element("VERIFICATION", VER_FIELDS, [("Parent", "Verifies")]),
        [("Verification results", ver_nodes)] if ver_nodes else [],
    )
    return files


def needs_by_uid(needs: dict) -> dict[str, dict]:
    return {n["uid"]: n for n in needs.values()}


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def fetch(api: Baserow) -> dict[str, list[dict]]:
    return {k: api.rows(t) for k, t in TABLES.items()}


def cmd_export(args) -> int:
    data = json.loads(Path(args.from_json).read_text()) if args.from_json else fetch(Baserow())
    if args.dump_json:
        Path(args.dump_json).write_text(json.dumps(data, indent=2))
    model, errors = build_model(data)
    if errors:
        print(f"SYNC FAILED: {len(errors)} error(s). Nothing was written.", file=sys.stderr)
        for e in errors:
            print("  ERROR", e, file=sys.stderr)
        return 2
    if args.command == "check":
        print("CHECK OK")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in render(model).items():
        (OUT_DIR / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {OUT_DIR.relative_to(ROOT) / name}")
    for stale in OUT_DIR.glob("need_*.sdoc"):  # old one-file-per-need layout
        stale.unlink()
        print(f"removed old {stale.name}")
    r = model["reqs"].values()
    print(f"needs={len(model['needs'])} requirements={len(r)} "
          f"(approved={sum(x['status'] == 'Approved' for x in r)}, "
          f"baselined={sum(x['status'] == 'Baselined' for x in r)}, "
          f"obsolete={sum(x['status'] == 'Obsolete' for x in r)}) "
          f"elements={len(model['elements'])} verifications={len(model['vers'])}")
    return 0


def cmd_baseline(args) -> int:
    """Run after the sync Pull Request is merged: the merged commit is the baseline."""
    path = OUT_DIR / "requirements.sdoc"
    if not path.exists():
        print("No requirements.sdoc in the working tree; nothing to baseline.")
        return 0
    in_git = dict(re.findall(r"^UID: (\S+)\nSTATUS: (\S+)", path.read_text(encoding="utf-8"), re.M))
    api = Baserow()
    rows = api.rows(TABLES["requirement"])
    if not rows:
        return 0
    status_field = field_name(rows[0], "req_status", "Requirement")
    option = api.select_option_id(TABLES["requirement"], status_field, "Baselined")
    changed = 0
    for r in rows:
        uid = text(r, "req_id", "Requirement", True)
        if text(r, "req_status", "Requirement") == "Approved" and uid in in_git:
            api.update_row(TABLES["requirement"], r["id"], {status_field: option})
            print(f"{uid}: Approved -> Baselined")
            changed += 1
    print(f"baselined {changed} requirement(s)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", nargs="?", default="export", choices=["export", "check", "baseline"])
    p.add_argument("--from-json", help="read rows from a JSON dump instead of the API (testing)")
    p.add_argument("--dump-json", help="also save the fetched rows to this JSON file")
    args = p.parse_args()
    try:
        return cmd_baseline(args) if args.command == "baseline" else cmd_export(args)
    except ConfigError as e:
        print(f"CONFIG ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
