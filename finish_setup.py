import json, urllib.request, time

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"
DATABASE_ID = 169

# Correct table IDs from the current database
STAKEHOLDER_TABLE = 683
ELE_TABLE = 701
NEED_TABLE = 702
REQ_TABLE = 703
REVIEW_TABLE = 704

HEADERS = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

def api(method, url, data=None, jwt=None):
    h = HEADERS.copy()
    if jwt: h["Authorization"] = f"JWT {jwt}"
    req = urllib.request.Request(url, method=method, headers=h)
    if data: req.data = json.dumps(data).encode()
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        print(f"ERROR {e.code}: {e.read().decode()[:200]}")
        raise

JWT = api("POST", f"{BASEROW_URL}/api/user/token-auth/", {"email": EMAIL, "password": PASSWORD})["token"]
print("✅ Logged in\n")

def create_table(name, primary):
    t = api("POST", f"{BASEROW_URL}/api/database/tables/database/{DATABASE_ID}/",
            {"name": name, "primary_field_name": primary}, JWT)
    print(f"✅ Table {name} (id={t['id']}, primary='{primary}')")
    time.sleep(2)
    return t

def add_field(table_id, name, ftype, options=None):
    data = {"name": name, "type": ftype}
    if ftype == "single_select" and options:
        colors = ["light-blue","light-green","light-yellow","light-red","light-purple","light-orange","light-cyan","light-gray"]
        data["select_options"] = [{"value": o, "color": colors[i % 8]} for i, o in enumerate(options)]
    api("POST", f"{BASEROW_URL}/api/database/fields/table/{table_id}/", data, JWT)
    print(f"   + {name}")
    time.sleep(0.3)

def add_link(table_id, name, target_id):
    api("POST", f"{BASEROW_URL}/api/database/fields/table/{table_id}/",
        {"name": name, "type": "link_row", "link_row_table_id": target_id}, JWT)
    print(f"   + {name} → link to {target_id}")
    time.sleep(0.3)

def insert(table_id, data):
    return api("POST", f"{BASEROW_URL}/api/database/rows/table/{table_id}/?user_field_names=true", data, JWT)

def fetch_rows(table_id):
    return api("GET", f"{BASEROW_URL}/api/database/rows/table/{table_id}/?size=200", jwt=JWT)["results"]

# Fetch existing row IDs for links
req_rows = fetch_rows(REQ_TABLE)
ele_rows = fetch_rows(ELE_TABLE)

# Print for debugging
print(f"Requirements rows: {[r['id'] for r in req_rows]}")
print(f"Elements rows: {[r['id'] for r in ele_rows]}\n")

# --- Allocation ---
alloc = create_table("Allocation", "Allocation")
add_link(alloc["id"], "Requirement", REQ_TABLE)
add_link(alloc["id"], "Element", ELE_TABLE)

r1_id = req_rows[0]["id"]  # REQ-001
r2_id = req_rows[1]["id"]  # REQ-002
e1_id = ele_rows[0]["id"]  # Auth Subsystem
e2_id = ele_rows[1]["id"]  # Login Component
e3_id = ele_rows[2]["id"]  # Session Manager

insert(alloc["id"], {"Allocation": "REQ-001 → Auth Subsystem", "Requirement": [r1_id], "Element": [e1_id]})
insert(alloc["id"], {"Allocation": "REQ-001 → Login Component", "Requirement": [r1_id], "Element": [e2_id]})
insert(alloc["id"], {"Allocation": "REQ-002 → Session Manager", "Requirement": [r2_id], "Element": [e3_id]})

# --- Verification ---
ver = create_table("Verification", "Verification ID")
add_field(ver["id"], "Method", "single_select", ["Test", "Analysis", "Inspection", "Demo"])
add_field(ver["id"], "Acceptance Criteria", "long_text")
add_field(ver["id"], "Result", "single_select", ["Pass", "Fail", "Pending"])
add_link(ver["id"], "Requirement", REQ_TABLE)

insert(ver["id"], {"Verification ID": "VER-001", "Requirement": [r1_id], "Method": "Test", "Acceptance Criteria": "User logs in.", "Result": "Pass"})
insert(ver["id"], {"Verification ID": "VER-002", "Requirement": [r2_id], "Method": "Test", "Acceptance Criteria": "Session expires.", "Result": "Pass"})

# --- ChangeRequest ---
cr = create_table("ChangeRequest", "Title")
add_field(cr["id"], "Description", "long_text")
add_field(cr["id"], "Status", "single_select", ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Implemented"])
add_field(cr["id"], "Impact", "long_text")
add_link(cr["id"], "Requirement", REQ_TABLE)

insert(cr["id"], {"Title": "Add SSO support", "Description": "Extend login.", "Status": "Approved", "Impact": "3 days effort.", "Requirement": [r1_id]})

print("\n" + "="*50)
print("✅✅✅ FINAL SETUP COMPLETE ✅✅✅")
print("="*50)
print(f"Stakeholder:     {STAKEHOLDER_TABLE}")
print(f"SystemElement:   {ELE_TABLE}")
print(f"StakeholderNeed: {NEED_TABLE}")
print(f"Requirement:     {REQ_TABLE}")
print(f"Review:          {REVIEW_TABLE}")
print(f"Allocation:      {alloc['id']}")
print(f"Verification:    {ver['id']}")
print(f"ChangeRequest:   {cr['id']}")
