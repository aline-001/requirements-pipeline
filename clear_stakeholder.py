import json, urllib.request

BASEROW_URL = "http://127.0.0.1:8000"
EMAIL = "asimwealine2004@gmail.com"
PASSWORD = "12345678"
STAKEHOLDER_TABLE = 683

login = urllib.request.Request(
    f"{BASEROW_URL}/api/user/token-auth/",
    data=json.dumps({"email": EMAIL, "password": PASSWORD}).encode(),
    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    method="POST"
)
JWT = json.loads(urllib.request.urlopen(login).read())["token"]

# List all rows
url = f"{BASEROW_URL}/api/database/rows/table/{STAKEHOLDER_TABLE}/?size=200"
req = urllib.request.Request(url, headers={"Authorization": f"JWT {JWT}", "User-Agent": "Mozilla/5.0"})
rows = json.loads(urllib.request.urlopen(req).read())["results"]

for row in rows:
    del_req = urllib.request.Request(
        f"{BASEROW_URL}/api/database/rows/table/{STAKEHOLDER_TABLE}/{row['id']}/",
        headers={"Authorization": f"JWT {JWT}", "User-Agent": "Mozilla/5.0"},
        method="DELETE"
    )
    urllib.request.urlopen(del_req)
    print(f"Deleted stakeholder row {row['id']}")

print("✅ Stakeholder table cleared")
