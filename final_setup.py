import json, urllib.request, time

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"
DATABASE_ID = 169
STAKEHOLDER_TABLE_ID = 683

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
    time.sleep(2)  # Wait for table lock to release
    return t

def add_field(table_id, name, ftype, options=None):
    data = {"name": name, "type": ftype}
    if ftype == "single_select" and options:
        colors = ["light-blue","light-green","light-yellow","light-red","light-purple","light-orange","light-cyan","light-gray"]
        data["select_options"] = [{"value": o, "color": colors[i % 8]} for i, o in enumerate(options)]
    api("POST", f"{BASEROW_URL}/api/database/fields/table/{table_id}/", data, JWT)
    print(f"   + {name}")
    time.sleep(0.3)  # Small delay between fields

def add_link(table_id, name, target_id):
    api("POST", f"{BASEROW_URL}/api/database/fields/table/{table_id}/",
        {"name": name, "type": "link_row", "link_row_table_id": target_id}, JWT)
    print(f"   + {name} → link to {target_id}")

def insert(table_id, data):
    return api("POST", f"{BASEROW_URL}/api/database/rows/table/{table_id}/?user_field_names=true", data, JWT)

# --- 1. Stakeholder (already exists, add rows only) ---
s1 = insert(STAKEHOLDER_TABLE_ID, {"Name": "Jane Smith", "Role": "Product Manager", "Organisation": "Acme Corp", "Contact": "jane@acme.com"})
s2 = insert(STAKEHOLDER_TABLE_ID, {"Name": "Keza Kelly", "Role": "Reviewer", "Organisation": "Acme Corp", "Contact": "keza@acme.com"})

# --- 2. SystemElement ---
ele = create_table("SystemElement", "Name")
add_field(ele["id"], "Type", "single_select", ["Subsystem", "Component", "Interface"])
add_field(ele["id"], "Description", "long_text")
e1 = insert(ele["id"], {"Name": "Auth Subsystem", "Type": "Subsystem", "Description": "Handles login"})
e2 = insert(ele["id"], {"Name": "Login Component", "Type": "Component", "Description": "Login UI"})
e3 = insert(ele["id"], {"Name": "Session Manager", "Type": "Component", "Description": "Session tracking"})

# --- 3. StakeholderNeed ---
need = create_table("StakeholderNeed", "Title")
add_field(need["id"], "Statement", "long_text")
add_field(need["id"], "Priority", "single_select", ["Must", "Should", "Could", "Wont"])
add_field(need["id"], "Rationale", "long_text")
add_field(need["id"], "Status", "single_select", ["Proposed", "Approved", "Rejected"])
add_field(need["id"], "Source", "text")
add_link(need["id"], "Stakeholder", STAKEHOLDER_TABLE_ID)

n1 = insert(need["id"], {"Title": "Secure user login", "Statement": "Users must log in securely.", "Priority": "Must", "Rationale": "Compliance.", "Status": "Approved", "Source": "Meeting", "Stakeholder": [s1["id"]]})
n2 = insert(need["id"], {"Title": "Session timeout", "Statement": "Idle sessions must expire.", "Priority": "Should", "Rationale": "Security.", "Status": "Approved", "Source": "Review", "Stakeholder": [s1["id"]]})
n3 = insert(need["id"], {"Title": "Password reset", "Statement": "Users must reset passwords.", "Priority": "Must", "Rationale": "Support.", "Status": "Approved", "Source": "Support", "Stakeholder": [s1["id"]]})

# --- 4. Requirement ---
req = create_table("Requirement", "Req ID")
add_field(req["id"], "Statement", "long_text")
add_field(req["id"], "Type", "single_select", ["Functional", "Non-Functional"])
add_field(req["id"], "Status", "single_select", ["Draft", "Approved", "Baselined", "Obsolete"])
add_link(req["id"], "Need", need["id"])

r1 = insert(req["id"], {"Req ID": "REQ-001", "Statement": "Authenticate users via username/password.", "Type": "Functional", "Status": "Approved", "Need": [n1["id"]]})
r2 = insert(req["id"], {"Req ID": "REQ-002", "Statement": "Expire idle sessions after 15 min.", "Type": "Functional", "Status": "Approved", "Need": [n2["id"]]})
r3 = insert(req["id"], {"Req ID": "REQ-003", "Statement": "Allow password reset via email.", "Type": "Functional", "Status": "Draft", "Need": [n3["id"]]})

# --- 5. Review ---
rev = create_table("Review", "Review Title")
add_field(rev["id"], "Decision", "single_select", ["Approved", "Rejected", "Needs Work"])
add_field(rev["id"], "Comments", "long_text")
add_link(rev["id"], "Reviewer", STAKEHOLDER_TABLE_ID)
add_link(rev["id"], "Need", need["id"])

insert(rev["id"], {"Review Title": "Review of login", "Decision": "Approved", "Comments": "Good.", "Reviewer": [s2["id"]], "Need": [n1["id"]]})
insert(rev["id"], {"Review Title": "Review of timeout", "Decision": "Approved", "Comments": "OK.", "Reviewer": [s2["id"]], "Need": [n2["id"]]})

# --- 6. Allocation ---
alloc = create_table("Allocation", "Allocation")
add_field(alloc["id"], "Notes", "long_text")
add_link(alloc["id"], "Requirement", req["id"])
add_link(alloc["id"], "Element", ele["id"])

insert(alloc["id"], {"Allocation": "REQ-001 → Auth Subsystem", "Notes": "Auth subsys", "Requirement": [r1["id"]], "Element": [e1["id"]]})
insert(alloc["id"], {"Allocation": "REQ-001 → Login Component", "Notes": "UI", "Requirement": [r1["id"]], "Element": [e2["id"]]})
insert(alloc["id"], {"Allocation": "REQ-002 → Session Manager", "Notes": "Timeout", "Requirement": [r2["id"]], "Element": [e3["id"]]})

# --- 7. Verification ---
ver = create_table("Verification", "Verification ID")
add_field(ver["id"], "Method", "single_select", ["Test", "Analysis", "Inspection", "Demo"])
add_field(ver["id"], "Acceptance Criteria", "long_text")
add_field(ver["id"], "Result", "single_select", ["Pass", "Fail", "Pending"])
add_link(ver["id"], "Requirement", req["id"])

insert(ver["id"], {"Verification ID": "VER-001", "Requirement": [r1["id"]], "Method": "Test", "Acceptance Criteria": "User logs in.", "Result": "Pass"})
insert(ver["id"], {"Verification ID": "VER-002", "Requirement": [r2["id"]], "Method": "Test", "Acceptance Criteria": "Session expires.", "Result": "Pass"})

# --- 8. ChangeRequest ---
cr = create_table("ChangeRequest", "Title")
add_field(cr["id"], "Description", "long_text")
add_field(cr["id"], "Status", "single_select", ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Implemented"])
add_field(cr["id"], "Impact", "long_text")
add_link(cr["id"], "Requirement", req["id"])

insert(cr["id"], {"Title": "Add SSO support", "Description": "Extend login.", "Status": "Approved", "Impact": "3 days effort.", "Requirement": [r1["id"]]})

print("\n" + "="*50)
print("✅✅✅ FINAL SETUP COMPLETE ✅✅✅")
print("="*50)
print(f"Stakeholder:     {STAKEHOLDER_TABLE_ID}")
print(f"SystemElement:   {ele['id']}")
print(f"StakeholderNeed: {need['id']}")
print(f"Requirement:     {req['id']}")
print(f"Review:          {rev['id']}")
print(f"Allocation:      {alloc['id']}")
print(f"Verification:    {ver['id']}")
print(f"ChangeRequest:   {cr['id']}")
print("\nSave these IDs — you'll need them for the sync script.")
