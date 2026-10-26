import json
import urllib.request

# --- CONFIGURATION ---
BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"      # <-- Your actual Baserow password
DATABASE_ID = "169"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

def api_request(method, url, data=None, jwt_token=None):
    headers = HEADERS.copy()
    if jwt_token:
        headers["Authorization"] = f"JWT {jwt_token}"
    req = urllib.request.Request(url, method=method, headers=headers)
    if data:
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"ERROR {e.code}: {e.read().decode()[:200]}")
        raise

def get_jwt_token():
    url = f"{BASEROW_URL}/api/user/token-auth/"
    data = {"email": EMAIL, "password": PASSWORD}
    resp = api_request("POST", url, data)
    return resp["token"]

def create_table(name, jwt):
    url = f"{BASEROW_URL}/api/database/tables/database/{DATABASE_ID}/"
    table = api_request("POST", url, {"name": name}, jwt)
    print(f"✅ Created table: {name} (ID: {table['id']})")
    return table

def create_field(table_id, name, field_type, options, jwt):
    url = f"{BASEROW_URL}/api/database/fields/table/{table_id}/"
    data = {"name": name, "type": field_type}
    if field_type == "single_select" and options:
        data["select_options"] = [{"value": opt} for opt in options]
    try:
        field = api_request("POST", url, data, jwt)
        print(f"   Added field: {name} ({field_type})")
        return field
    except urllib.error.HTTPError as e:
        if e.code == 400:
            print(f"   ⚠️  Skipped field '{name}' (already exists)")
            return None
        raise

def insert_row(table_id, data, jwt):
    url = f"{BASEROW_URL}/api/database/rows/table/{table_id}/?user_field_names=true"
    try:
        api_request("POST", url, data, jwt)
    except urllib.error.HTTPError as e:
        if e.code == 400:
            print(f"   ⚠️  Skipped duplicate row")
            return
        raise

print("Logging in with JWT...")
JWT = get_jwt_token()
print("✅ JWT obtained\n")

print("Starting Database Setup...\n")

# 1. System Elements
ele = create_table("SystemElement", JWT)
create_field(ele["id"], "Name", "text", None, JWT)
create_field(ele["id"], "Type", "single_select", ["Subsystem", "Component", "Interface"], JWT)
create_field(ele["id"], "Description", "long_text", None, JWT)
insert_row(ele["id"], {"Name": "Auth Subsystem", "Type": "Subsystem", "Description": "Handles login"}, JWT)
insert_row(ele["id"], {"Name": "Login Component", "Type": "Component", "Description": "Login UI"}, JWT)
insert_row(ele["id"], {"Name": "Session Manager", "Type": "Component", "Description": "Session timeout"}, JWT)

# 2. Stakeholder Needs
need = create_table("StakeholderNeed", JWT)
create_field(need["id"], "Title", "text", None, JWT)
create_field(need["id"], "Statement", "long_text", None, JWT)
create_field(need["id"], "Priority", "single_select", ["Must", "Should", "Could", "Wont"], JWT)
create_field(need["id"], "Rationale", "long_text", None, JWT)
create_field(need["id"], "Status", "single_select", ["Proposed", "Approved", "Rejected"], JWT)
create_field(need["id"], "Source", "text", None, JWT)
insert_row(need["id"], {"Title": "Secure user login", "Statement": "Users must be able to log in securely.", "Priority": "Must", "Rationale": "Compliance requirement.", "Status": "Approved", "Source": "Meeting"}, JWT)
insert_row(need["id"], {"Title": "Session timeout", "Statement": "Idle sessions must expire after 15 minutes.", "Priority": "Should", "Rationale": "Security risk.", "Status": "Approved", "Source": "Review"}, JWT)
insert_row(need["id"], {"Title": "Password reset", "Statement": "Users must be able to reset passwords.", "Priority": "Must", "Rationale": "Reduce support tickets.", "Status": "Approved", "Source": "Support"}, JWT)

# 3. Requirements
req = create_table("Requirement", JWT)
create_field(req["id"], "Req ID", "text", None, JWT)
create_field(req["id"], "Statement", "long_text", None, JWT)
create_field(req["id"], "Type", "single_select", ["Functional", "Non-Functional"], JWT)
create_field(req["id"], "Status", "single_select", ["Draft", "Approved", "Baselined", "Obsolete"], JWT)
insert_row(req["id"], {"Req ID": "REQ-001", "Statement": "Authenticate users via username/password.", "Type": "Functional", "Status": "Approved"}, JWT)
insert_row(req["id"], {"Req ID": "REQ-002", "Statement": "Expire idle sessions after 15 minutes.", "Type": "Functional", "Status": "Approved"}, JWT)
insert_row(req["id"], {"Req ID": "REQ-003", "Statement": "Allow password reset via email.", "Type": "Functional", "Status": "Draft"}, JWT)

# 4. Reviews
rev = create_table("Review", JWT)
create_field(rev["id"], "Review Title", "text", None, JWT)
create_field(rev["id"], "Decision", "single_select", ["Approved", "Rejected", "Needs Work"], JWT)
create_field(rev["id"], "Comments", "long_text", None, JWT)

# 5. Allocations
alloc = create_table("Allocation", JWT)
create_field(alloc["id"], "Allocation", "text", None, JWT)
create_field(alloc["id"], "Notes", "long_text", None, JWT)

# 6. Verifications
ver = create_table("Verification", JWT)
create_field(ver["id"], "Verification ID", "text", None, JWT)
create_field(ver["id"], "Method", "single_select", ["Test", "Analysis", "Inspection", "Demo"], JWT)
create_field(ver["id"], "Acceptance Criteria", "long_text", None, JWT)
create_field(ver["id"], "Result", "single_select", ["Pass", "Fail", "Pending"], JWT)

# 7. Change Requests
cr = create_table("ChangeRequest", JWT)
create_field(cr["id"], "Title", "text", None, JWT)
create_field(cr["id"], "Description", "long_text", None, JWT)
create_field(cr["id"], "Status", "single_select", ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Implemented"], JWT)
create_field(cr["id"], "Impact", "long_text", None, JWT)

print("\n✅ Setup complete! You can now add the Link fields in the UI.")
