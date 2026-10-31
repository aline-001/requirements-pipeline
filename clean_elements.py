"""Delete completely empty rows from the SystemElement table. Dry run unless --delete is given."""
import sys
sys.path.insert(0, "sync")
import sync

api = sync.Baserow()
table = sync.TABLES["element"]
rows = api.rows(table)

def is_empty(value):
    return value in (None, "", [], {}, False)

blank = [r["id"] for r in rows if all(is_empty(v) for k, v in r.items() if k not in ("id", "order"))]
keep = [r for r in rows if r["id"] not in blank]

print(f"{len(rows)} rows: {len(keep)} with data, {len(blank)} completely empty")
for r in keep:
    print("  keep:", r.get("Name"))

if "--delete" in sys.argv and blank:
    for i in range(0, len(blank), 200):
        api._call("POST", f"/api/database/rows/table/{table}/batch-delete/", {"items": blank[i:i + 200]})
    print(f"deleted {len(blank)} empty rows (they are in Baserow's Trash)")
elif blank:
    print("Nothing deleted. Run again with --delete to remove the empty rows.")
