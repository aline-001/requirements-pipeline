import json, urllib.request, time

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"
DATABASE_ID = 169
STAKEHOLDER_TABLE = 683
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
        print(f"ERROR {e.code}: {e.read().decode()[:300]}")
        return None

JWT = api("POST", f"{BASEROW_URL}/api/user/token-auth/",
          {"email": EMAIL, "password": PASSWORD})["token"]
print("✅ Logged in\n")

# STEP 1: Create StakeholderNeed table
print("--- Creating StakeholderNeed table ---")
url = f"{BASEROW_URL}/api/database/tables/database/{DATABASE_ID}/"
new_need = api("POST", url, {"name": "StakeholderNeed", "primary_field_name": "Title"}, JWT)
NEED_TABLE = new_need["id"]
print(f"✅ Created StakeholderNeed (id={NEED_TABLE})\n")

# STEP 2: Add fields
print("--- Adding fields ---")
time.sleep(2)

fields_to_add = [
    ("Statement", "long_text", None),
    ("Priority", "single_select", ["Must", "Should", "Could", "Wont"]),
    ("Rationale", "long_text", None),
    ("Status", "single_select", ["Proposed", "Approved", "Rejected"]),
    ("Source", "text", None),
]

for name, ftype, opts in fields_to_add:
    data = {"name": name, "type": ftype}
    if ftype == "single_select" and opts:
        colors = ["light-blue","light-green","light-yellow","light-red","light-purple","light-orange"]
        data["select_options"] = [{"value": o, "color": colors[i % 6]} for i, o in enumerate(opts)]
    result = api("POST", f"{BASEROW_URL}/api/database/fields/table/{NEED_TABLE}/", data, JWT)
    if result:
        print(f"  ✅ {name}")
    time.sleep(0.5)

# STEP 3: Add link to Stakeholder
print("\n--- Adding Stakeholder link ---")
result = api("POST", f"{BASEROW_URL}/api/database/fields/table/{NEED_TABLE}/",
             {"name": "Stakeholder", "type": "link_row", "link_row_table_id": STAKEHOLDER_TABLE}, JWT)
if result:
    print(f"  ✅ Stakeholder link")
time.sleep(1)

# STEP 4: Add link to Requirement (on StakeholderNeed side)
print("\n--- Adding Requirement link (reverse) ---")
result = api("POST", f"{BASEROW_URL}/api/database/fields/table/{NEED_TABLE}/",
             {"name": "Requirement", "type": "link_row", "link_row_table_id": REQ_TABLE}, JWT)
if result:
    print(f"  ✅ Requirement link")

# STEP 5: Add link to Review (on StakeholderNeed side)
print("\n--- Adding Review link (reverse) ---")
result = api("POST", f"{BASEROW_URL}/api/database/fields/table/{NEED_TABLE}/",
             {"name": "Review", "type": "link_row", "link_row_table_id": REVIEW_TABLE}, JWT)
if result:
    print(f"  ✅ Review link")

# STEP 6: Insert test data
print("\n--- Inserting test data ---")
# Get stakeholder IDs
stakeholder_rows = api("GET", f"{BASEROW_URL}/api/database/rows/table/{STAKEHOLDER_TABLE}/?size=100", jwt=JWT)["results"]
s1_id = stakeholder_rows[0]["id"] if stakeholder_rows else None

needs_data = [
    {"Title": "Secure user login", "Statement": "Users must log in securely.", "Priority": "Must", "Rationale": "Compliance.", "Status": "Approved", "Source": "Meeting"},
    {"Title": "Session timeout", "Statement": "Idle sessions must expire.", "Priority": "Should", "Rationale": "Security.", "Status": "Approved", "Source": "Review"},
    {"Title": "Password reset", "Statement": "Users must reset passwords.", "Priority": "Must", "Rationale": "Support.", "Status": "Approved", "Source": "Support"},
]

if s1_id:
    for n in needs_data:
        n["Stakeholder"] = [s1_id]
        result = api("POST", f"{BASEROW_URL}/api/database/rows/table/{NEED_TABLE}/?user_field_names=true", n, JWT)
        if result:
            print(f"  ✅ {n['Title']}")

# STEP 7: Re-add Need link to Requirement table
print("\n--- Adding Need link to Requirement table ---")
result = api("POST", f"{BASEROW_URL}/api/database/fields/table/{REQ_TABLE}/",
             {"name": "Need", "type": "link_row", "link_row_table_id": NEED_TABLE}, JWT)
if result:
    print(f"  ✅ Need link added to Requirement")

# STEP 8: Re-link requirements to needs
print("\n--- Re-linking requirements to needs ---")
# Get requirement rows and need rows
req_rows = api("GET", f"{BASEROW_URL}/api/database/rows/table/{REQ_TABLE}/?size=100", jwt=JWT)["results"]
need_rows = api("GET", f"{BASEROW_URL}/api/database/rows/table/{NEED_TABLE}/?size=100", jwt=JWT)["results"]

for i, req_row in enumerate(req_rows):
    if i < len(need_rows):
        req_id = req_row["id"]
        need_id = need_rows[i]["id"]
        update = {"Need": [need_id]}
        api("PATCH", f"{BASEROW_URL}/api/database/rows/table/{REQ_TABLE}/{req_id}/?user_field_names=true", update, JWT)
        print(f"  ✅ Linked REQ {req_row.get('Req ID', req_id)} → Need {need_id}")

print("\n" + "="*50)
print("✅ COMPLETE")
print("="*50)
print(f"StakeholderNeed table ID: {NEED_TABLE}")
print(f"Requirement table ID: {REQ_TABLE}")
