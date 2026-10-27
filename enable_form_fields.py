import json, urllib.request, time

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"

# Correct view IDs and table IDs
FORM_SUBMIT_NEED_ID = 3064
FORM_REVIEW_NEED_ID = 3065
NEED_TABLE = 709
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
        return None

JWT = api("POST", f"{BASEROW_URL}/api/user/token-auth/",
          {"email": EMAIL, "password": PASSWORD})["token"]
print("✅ Logged in\n")

def enable_all_fields(view_id, table_id, hide_names=None, required_names=None):
    """
    Enable all fields in the form. Optionally hide specific fields and mark required.
    """
    hide_names = hide_names or []
    required_names = required_names or []
    
    # Get all fields of the table
    fields = api("GET", f"{BASEROW_URL}/api/database/fields/table/{table_id}/", jwt=JWT)
    
    for f in fields:
        field_id = f["id"]
        name = f["name"]
        
        # Enable field, hide if in hide_names, mark required if in required_names
        data = {
            "enabled": name not in hide_names,
            "required": name in required_names,
        }
        
        url = f"{BASEROW_URL}/api/database/views/form/{view_id}/field-options/{field_id}/"
        result = api("PATCH", url, data, JWT)
        if result:
            status = "✓"
            if name in hide_names:
                status = "👁‍🗨 hidden"
            elif name in required_names:
                status = "✓ required"
            print(f"  {status:12s} {name}")
        else:
            print(f"  ❌ failed: {name}")
        time.sleep(0.2)

# ============================================================
# Enable fields in Submit a Need form (id 3064, table 709)
# ============================================================
print("--- Submit a Need form (id 3064) ---")
hide = ["Status", "Requirement", "Review"]
required = ["Title", "Statement", "Priority", "Rationale", "Source", "Stakeholder"]
enable_all_fields(3064, 709, hide_names=hide, required_names=required)
time.sleep(1)

# ============================================================
# Enable fields in Review a Need form (id 3065, table 704)
# ============================================================
print("\n--- Review a Need form (id 3065) ---")
hide = ["Reviewed At"]
required = ["Review Title", "Decision", "Comments", "Reviewer", "Need"]
enable_all_fields(3065, 704, hide_names=hide, required_names=required)

print("\n✅ Done. Forms now have fields.")
