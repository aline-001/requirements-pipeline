import json
import urllib.request

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
        return None

# Login
JWT = api("POST", f"{BASEROW_URL}/api/user/token-auth/", {"email": EMAIL, "password": PASSWORD})["token"]
print("✅ Logged in\n")

def create_table(name, primary_field_name):
    url = f"{BASEROW_URL}/api/database/tables/database/{DATABASE_ID}/"
    t = api("POST", url, {"name": name, "primary_field_name": primary_field_name}, JWT)
    print(f"✅ Created table: {name} (id {t['id']}, primary='{primary_field_name}')")
    return t

def create_field(table_id, name, field_type, options=None):
    url = f"{BASEROW_URL}/api/database/fields/table/{table_id}/"
    data = {"name": name, "type": field_type}
    if field_type == "single_select" and options:
        data["select_options"] = [
            {"value": o, "color": ["light-blue","light-green","light-yellow","light-red","light-purple","light-orange","light-cyan","light-gray"][i % 8]}
            for i, o in enumerate(options)
        ]
    try:
        api("POST", url, data, JWT)
        print(f"   + {name} ({field_type})")
    except: pass

def create_link_field(table_id, name, target_table_id):
    url = f"{BASEROW_URL}/api/database/fields/table/{table_id}/"
    data = {"name": name, "type": "link_row", "link_row_table_id": target_table_id}
    try:
        api("POST", url, data, JWT)
        print(f"   + {name} (link -> table {target_table_id})")
    except: pass

def insert(table_id, data):
    url = f"{BASEROW_URL}/api/database/rows/table/{table_id}/?user_field_names=true"
    r = api("POST", url, data, JWT)
    return r

# --- 1. SystemElement ---
ele = create_table("SystemElement", "Name")
create_field(ele["id"], "Type", "single_select", ["Subsystem", "Component", "Interface"])
create_field(ele["id"], "Description", "long_text")
el1 = insert(ele["id"], {"Name": "Auth Subsystem", "Type": "Subsystem", "Description": "Handles login"})
el2 = insert(ele["id"], {"Name": "Login Component", "Type": "Component", "Description": "Login UI"})
el3 = insert(ele["id"], {"Name": "Session Manager", "Type": "Component", "Description": "Sessions"})

# --- 2. StakeholderNeed ---
need = create_table("StakeholderNeed", "Title")
create_field(need["id"], "Statement", "long_text")
create_field(need["id"], "Priority", "single_select", ["Must", "Should", "Could", "Wont"])
create_field(need["id"], "Rationale", "long_text")
create_field(need["id"], "Status", "single_select", ["Proposed", "Approved", "Rejected"])
create_field(need["id"], "Source", "text")
create_link_field(need["id"], "Stakeholder", STAKEHOLDER_TABLE_ID)

n1 = insert(need["id"], {"Title": "Secure user login", "Statement": "Users must log in securely.", "Priority": "Must", "Rationale": "Compliance.", "Status": "Approved", "Source": "Meeting", "Stakeholder": [1]})
n2 = insert(need["id"], {"Title": "Session timeout", "Statement": "Idle sessions must expire.", "Priority": "Should", "Rationale": "Security.", "Status": "Approved", "Source": "Review", "Stakeholder": [1]})
n3 = insert(need["id"], {"Title": "Password reset", "Statement": "Users must reset passwords.", "Priority": "Must", "Rationale": "Support.", "Status": "Approved", "Source": "Support", "Stakeholder": [1]})

# --- 3. Requirement ---
req = create_table("Requirement", "Req ID")
create_field(req["id"], "Statement", "long_text")
create_field(req["id"], "Type", "single_select", ["Functional", "Non-Functional"])
create_field(req["id"], "Status", "single_select", ["Draft", "Approved", "Baselined", "Obsolete"])
create_link_field(req["id"], "Need", need["id"])

r1 = insert(req["id"], {"Req ID": "REQ-001", "Statement": "Authenticate users via username/password.", "Type": "Functional", "Status": "Approved", "Need": [n1["id"]]})
r2 = insert(req["id"], {"Req ID": "REQ-002", "Statement": "Expire idle sessions after 15 min.", "Type": "Functional", "Status": "Approved", "Need": [n2["id"]]})
r3 = insert(req["id"], {"Req ID": "REQ-003", "Statement": "Allow password reset via email.", "Type": "Functional", "Status": "Draft", "Need": [n3["id"]]})

# --- 4. Review ---
rev = create_table("Review", "Review Title")
create_field(rev["id"], "Decision", "single_select", ["Approved", "Rejected", "Needs Work"])
create_field(rev["id"], "Comments", "long_text")
create_link_field(rev["id"], "Reviewer", STAKEHOLDER_TABLE_ID)
create_link_field(rev["id"], "Need", need["id"])

insert(rev["id"], {"Review Title": "Review of login", "Decision": "Approved", "Comments": "Good.", "Reviewer": [2], "Need": [n1["id"]]})
insert(rev["id"], {"Review Title": "Review of timeout", "Decision": "Approved", "Comments": "OK.", "Reviewer": [2], "Need": [n2["id"]]})

# --- 5. Allocation ---
alloc = create_table("Allocation", "Allocation")
create_field(alloc["id"], "Notes", "long_text")
create_link_field(alloc["id"], "Requirement", req["id"])
create_link_field(alloc["id"], "Element", ele["id"])

insert(alloc["id"], {"Allocation": "REQ-001 → Auth Subsystem", "Notes": "Auth subsys", "Requirement": [r1["id"]], "Element": [el1["id"]]})
insert(alloc["id"], {"Allocation": "REQ-001 → Login Component", "Notes": "UI", "Requirement": [r1["id"]], "Element": [el2["id"]]})
insert(alloc["id"], {"Allocation": "REQ-002 → Session Manager", "Notes": "Timeout", "Requirement": [r2["id"]], "Element": [el3["id"]]})

# --- 6. Verification ---
ver = create_table("Verification", "Verification ID")
create_field(ver["id"], "Method", "single_select", ["Test", "Analysis", "Inspection", "Demo"])
create_field(ver["id"], "Acceptance Criteria", "long_text")
create_field(ver["id"], "Result", "single_select", ["Pass", "Fail", "Pending"])
create_link_field(ver["id"], "Requirement", req["id"])

insert(ver["id"], {"Verification ID": "VER-001", "Requirement": [r1["id"]], "Method": "Test", "Acceptance Criteria": "User logs in.", "Result": "Pass"})
insert(ver["id"], {"Verification ID": "VER-002", "Requirement": [r2["id"]], "Method": "Test", "Acceptance Criteria": "Session expires.", "Result": "Pass"})

# --- 7. ChangeRequest ---
cr = create_table("ChangeRequest", "Title")
create_field(cr["id"], "Description", "long_text")
create_field(cr["id"], "Status", "single_select", ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Implemented"])
create_field(cr["id"], "Impact", "long_text")
create_link_field(cr["id"], "Requirement", req["id"])

insert(cr["id"], {"Title": "Add SSO support", "Description": "Extend login.", "Status": "Approved", "Impact": "3 days effort.", "Requirement": [r1["id"]]})

print("\n✅✅✅ ALL TABLES CREATED AND POPULATED ✅✅✅")
print(f"Stakeholder: 683")
print(f"SystemElement: {ele['id']}")
print(f"StakeholderNeed: {need['id']}")
print(f"Requirement: {req['id']}")
print(f"Review: {rev['id']}")
print(f"Allocation: {alloc['id']}")
print(f"Verification: {ver['id']}")
print(f"ChangeRequest: {cr['id']}")
