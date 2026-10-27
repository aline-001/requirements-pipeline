import json, urllib.request, time

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"
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

def create_form(table_id, name):
    url = f"{BASEROW_URL}/api/database/views/table/{table_id}/"
    form = api("POST", url, {"name": name, "type": "form"}, JWT)
    if form:
        print(f"✅ Created form '{name}' (view id={form['id']})")
        time.sleep(2)
        return form
    return None

def get_slug(view_id):
    v = api("GET", f"{BASEROW_URL}/api/database/views/{view_id}/", jwt=JWT)
    return v.get("slug") if v else None

# --- Form 1: Submit a Need ---
print("--- FORM 1: Submit a Need ---")
f1 = create_form(NEED_TABLE, "Submit a Need")
if f1:
    slug1 = get_slug(f1["id"])
    print(f"   URL: https://baserow.darho.net/form/{slug1}\n")

# --- Form 2: Review a Need ---
print("--- FORM 2: Review a Need ---")
f2 = create_form(REVIEW_TABLE, "Review a Need")
if f2:
    slug2 = get_slug(f2["id"])
    print(f"   URL: https://baserow.darho.net/form/{slug2}\n")

print("="*50)
print("FORMS READY")
print("="*50)
print(f"Submit a Need:  https://baserow.darho.net/form/{get_slug(f1['id'])}")
print(f"Review a Need:  https://baserow.darho.net/form/{get_slug(f2['id'])}")
