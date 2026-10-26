import json
import urllib.request

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"

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

def get_jwt():
    resp = api_request("POST", f"{BASEROW_URL}/api/user/token-auth/",
                       {"email": EMAIL, "password": PASSWORD})
    return resp["token"]

# Colors Baserow accepts: light-blue, light-green, light-red, etc. -- use hex fallback
COLORS = ["light-blue", "light-green", "light-yellow", "light-red",
          "light-purple", "light-orange", "light-cyan", "light-gray"]

def create_select_field(table_id, name, values, jwt):
    url = f"{BASEROW_URL}/api/database/fields/table/{table_id}/"
    data = {
        "name": name,
        "type": "single_select",
        "select_options": [
            {"value": v, "color": COLORS[i % len(COLORS)]}
            for i, v in enumerate(values)
        ]
    }
    try:
        field = api_request("POST", url, data, jwt)
        print(f"   ✅ Added {name}")
    except urllib.error.HTTPError as e:
        if e.code == 400:
            print(f"   ⚠️  {name} already exists (skipped)")
        else:
            print(f"   ❌ {name} failed")

JWT = get_jwt()
print("✅ JWT obtained\n")

# Fix missing select fields per table
tables = {
    685: [("Type", ["Subsystem", "Component", "Interface"])],
    686: [("Priority", ["Must", "Should", "Could", "Wont"]),
          ("Status", ["Proposed", "Approved", "Rejected"])],
    687: [("Type", ["Functional", "Non-Functional"]),
          ("Status", ["Draft", "Approved", "Baselined", "Obsolete"])],
    688: [("Decision", ["Approved", "Rejected", "Needs Work"])],
    690: [("Method", ["Test", "Analysis", "Inspection", "Demo"]),
          ("Result", ["Pass", "Fail", "Pending"])],
    691: [("Status", ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Implemented"])],
}

for table_id, fields in tables.items():
    print(f"Table {table_id}:")
    for name, values in fields:
        create_select_field(table_id, name, values, JWT)

print("\n✅ Fix complete.")
