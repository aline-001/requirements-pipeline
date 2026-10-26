import json
import urllib.request

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"

HEADERS = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

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
        print(f"ERROR {e.code}: {e.read().decode()[:100]}")
        return None

# Get JWT
resp = api_request("POST", f"{BASEROW_URL}/api/user/token-auth/", {"email": EMAIL, "password": PASSWORD})
JWT = resp["token"]
print("✅ Logged in")

# Fields to DELETE (default ones we don't need)
# Format: { table_id: [list of field names to delete] }
fields_to_delete = {
    685: ["Name", "Notes"],          # SystemElement - Baserow defaults (if any)
    686: ["Name"],                   # StakeholderNeed - remove default 'Name' if exists
    687: ["Name"],                   # Requirement - remove default 'Name'
    688: ["Name"],                   # Review - remove default 'Name'
    689: ["Name"],                   # Allocation - remove default 'Name'
    690: ["Name"],                   # Verification - remove default 'Name'
    691: ["Name"],                   # ChangeRequest - remove default 'Name'
    683: []                          # Stakeholder - keep Name, but remove reverse links?
}

# First, get all fields per table to find their IDs
print("\nFetching fields...")
all_fields = {}
for table_id in [683, 685, 686, 687, 688, 689, 690, 691]:
    url = f"{BASEROW_URL}/api/database/fields/table/{table_id}/"
    fields = api_request("GET", url, jwt_token=JWT)
    if fields:
        all_fields[table_id] = fields

# Delete unwanted fields
print("\nDeleting unwanted default fields...")
for table_id, names_to_delete in fields_to_delete.items():
    if table_id not in all_fields:
        continue
    for field in all_fields[table_id]:
        if field["name"] in names_to_delete:
            url = f"{BASEROW_URL}/api/database/fields/{field['id']}/"
            result = api_request("DELETE", url, jwt_token=JWT)
            if result is not None or result is True:
                print(f"   ✅ Deleted '{field['name']}' from table {table_id}")
            else:
                print(f"   ❌ Could not delete '{field['name']}' from table {table_id}")

print("\n✅ Cleanup complete.")

