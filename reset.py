import json, urllib.request

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"

login = urllib.request.Request(
    f"{BASEROW_URL}/api/user/token-auth/",
    data=json.dumps({"email": EMAIL, "password": PASSWORD}).encode(),
    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    method="POST"
)
JWT = json.loads(urllib.request.urlopen(login).read())["token"]

tables = [692, 693, 694, 695, 696, 697, 698]
for tid in tables:
    req = urllib.request.Request(
        f"{BASEROW_URL}/api/database/tables/{tid}/",
        headers={"Authorization": f"JWT {JWT}", "User-Agent": "Mozilla/5.0"},
        method="DELETE"
    )
    try:
        urllib.request.urlopen(req)
        print(f"✅ Deleted {tid}")
    except Exception as e:
        print(f"❌ {tid}: {e}")
