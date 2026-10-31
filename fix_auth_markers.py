"""Move @relation("REQ-x") decorators into StrictDoc docstring markers."""
import ast, shutil, sys

TAGS = {
    "login": ["REQ-001"],
    "enforce_session_timeout": ["REQ-002"],
    "reset_password": None,
    "login_via_sso": ["REQ-004"],
}
NOTES = {"reset_password": "Implements REQ-003, which is still Draft. Add the StrictDoc relation tag for REQ-003 once it is approved and synced."}

path = sys.argv[1]
src = open(path, encoding="utf-8").read()
lines = src.split("\n")
tree = ast.parse(src)
funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in TAGS]

for fn in sorted(funcs, key=lambda n: n.lineno, reverse=True):
    body_indent = " " * fn.body[0].col_offset
    text_lines = []
    if TAGS[fn.name]:
        text_lines.append(f"@relation({', '.join(TAGS[fn.name])}, scope=function)")
    if fn.name in NOTES:
        text_lines.append(NOTES[fn.name])
    first = fn.body[0]
    has_doc = isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str)
    if has_doc:
        end = first.end_lineno - 1
        closing = lines[end]
        q = '"""' if closing.rstrip().endswith('"""') else "'''"
        before = closing[: closing.rstrip().rfind(q)]
        new = []
        if before.strip():
            new.append(before.rstrip())
        new.append("")
        new += [body_indent + t for t in text_lines]
        new.append(body_indent + q)
        lines[end:end + 1] = new
    else:
        at = first.lineno - 1
        lines[at:at] = [body_indent + '"""'] + [body_indent + t for t in text_lines] + [body_indent + '"""']
    for dec in sorted(fn.decorator_list, key=lambda d: d.lineno, reverse=True):
        if isinstance(dec, ast.Call) and getattr(dec.func, "id", "") == "relation":
            del lines[dec.lineno - 1: dec.end_lineno]

new_src = "\n".join(lines)
ast.parse(new_src)
shutil.copy(path, path + ".bak")
open(path, "w", encoding="utf-8").write(new_src)
print(f"updated {path} (backup: {path}.bak)")
