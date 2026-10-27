import json, urllib.request, time

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"

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

# ============================================================
# Create Form for StakeholderNeed (table 702)
# ============================================================
print("--- Creating 'Submit a Need' form ---")
url = f"{BASEROW_URL}/api/database/views/table/702/"
data = {"name": "Submit a Need", "type": "form"}
form1 = api("POST", url, data, JWT)

if form1:
    print(f"✅ Form created: id={form1['id']}, name='{form1['name']}'")
    time.sleep(2)
    
    # Get fields
    fields = api("GET", f"{BASEROW_URL}/api/database/fields/table/702/", jwt=JWT)
    field_map = {f["name"]: f["id"] for f in fields}
    print(f"   Fields available: {list(field_map.keys())}")
    
    # Configure each field
    configs = {
        "Title": {"required": True, "description": "Short summary of the need (one need per submission)."},
        "Statement": {"required": True, "description": "Describe exactly what the stakeholder requires. Be specific."},
        "Priority": {"required": True, "description": "Must = non-negotiable; Should = important; Could = nice-to-have; Wont = out of scope."},
        "Rationale": {"required": True, "description": "Why is this needed? What problem does it solve?"},
        "Source": {"required": True, "description": "Where did this come from? Meeting, email, interview, ticket."},
        "Stakeholder": {"required": True, "description": "Who is raising this need?"},
        "Status": {"required": False, "visible": False},
        "Requirement": {"required": False, "visible": False},
        "Review": {"required": False, "visible": False},
    }
    
    for fname, cfg in configs.items():
        if fname not in field_map:
            print(f"   ⚠️  {fname} not in table")
            continue
        f_id = field_map[fname]
        update = {
            "name": cfg.get("description", ""),
            "required": cfg.get("required", False),
            "enabled": cfg.get("visible", True),
        }
        result = api("PATCH", f"{BASEROW_URL}/api/database/views/form/{form1['id']}/field-options/{f_id}/", update, JWT)
        status = "✓" if result else "✗"
        print(f"   {status} {fname}")
    
    # Set submit message
    api("PATCH", f"{BASEROW_URL}/api/database/views/form/{form1['id']}/",
        {"submit_text": "Thank you — your need has been submitted and will be reviewed."}, JWT)
    
    # Get updated view with slug
    time.sleep(1)
    updated = api("GET", f"{BASEROW_URL}/api/database/views/{form1['id']}/", jwt=JWT)
    print(f"\n   Form URL: https://baserow.darho.net/form/{updated.get('slug', form1['id'])}")
else:
    print("❌ Failed to create form 1")

print()

# ============================================================
# Create Form for Review (table 704)
# ============================================================
print("--- Creating 'Review a Need' form ---")
url = f"{BASEROW_URL}/api/database/views/table/704/"
data = {"name": "Review a Need", "type": "form"}
form2 = api("POST", url, data, JWT)

if form2:
    print(f"✅ Form created: id={form2['id']}, name='{form2['name']}'")
    time.sleep(2)
    
    fields = api("GET", f"{BASEROW_URL}/api/database/fields/table/704/", jwt=JWT)
    field_map = {f["name"]: f["id"] for f in fields}
    print(f"   Fields available: {list(field_map.keys())}")
    
    configs = {
        "Review Title": {"required": True, "description": "Short label for this review."},
        "Decision": {"required": True, "description": "Approved, Rejected, or Needs Work."},
        "Comments": {"required": True, "description": "Explain your decision."},
        "Reviewer": {"required": True, "description": "Your name."},
        "Need": {"required": True, "description": "Which need are you reviewing?"},
    }
    
    for fname, cfg in configs.items():
        if fname not in field_map:
            print(f"   ⚠️  {fname} not in table")
            continue
        f_id = field_map[fname]
        update = {
            "name": cfg.get("description", ""),
            "required": cfg.get("required", False),
            "enabled": True,
        }
        result = api("PATCH", f"{BASEROW_URL}/api/database/views/form/{form2['id']}/field-options/{f_id}/", update, JWT)
        status = "✓" if result else "✗"
        print(f"   {status} {fname}")
    
    api("PATCH", f"{BASEROW_URL}/api/database/views/form/{form2['id']}/",
        {"submit_text": "Thank you — your review has been recorded."}, JWT)
    
    time.sleep(1)
    updated = api("GET", f"{BASEROW_URL}/api/database/views/{form2['id']}/", jwt=JWT)
    print(f"\n   Form URL: https://baserow.darho.net/form/{updated.get('slug', form2['id'])}")
else:
    print("❌ Failed to create form 2")

print("\n" + "="*50)
print("DONE")
print("="*50)
