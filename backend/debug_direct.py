"""Run directly: python debug_direct.py"""
import sys, os, io, json
sys.path.insert(0, ".")
os.environ["K_SERVICE"] = ""

from document_service import *

from flask import Flask
app = Flask(__name__)
app.secret_key = "test"
app.config["SESSION_TYPE"] = "filesystem"

with app.test_request_context():
    from flask import session
    session["user"] = {"email": "test@test.com"}

    data = {"entries": []}
    entries = data.get("entries", [])
    template_bytes = download_template()

    if not template_bytes:
        print("No template found")
        sys.exit(1)

    wb = load_workbook(io.BytesIO(template_bytes))
    ws = wb.active

    is_2row = _has_two_row_header(ws)
    print(f"is_2row_header: {is_2row}")

    if is_2row:
        col_map = _build_column_map_two_row(ws, ALL_HEADER_MAP)
        print("Column map (2-row):")
        for field, cols in sorted(col_map.items()):
            vals = []
            for c in cols:
                v = str(ws.cell(row=2, column=c).value or "")[:35]
                vals.append(f"col{c}={v}")
            print(f"  {field}: {vals}")

        act_fields = ["activity_code", "project_id", "activity_time"]
        print("\nActivity slot mapping:")
        for slot_i in range(3):
            print(f"  Slot {slot_i}:")
            for fi, field in enumerate(act_fields):
                if field == "project_id":
                    act_ids = [c for c in col_map.get("project_id", []) if c >= 19]
                    col = act_ids[slot_i] if slot_i < len(act_ids) else None
                else:
                    lst = col_map.get(field, [])
                    col = lst[slot_i] if slot_i < len(lst) else None
                expected = 19 + slot_i * 3 + fi
                print(f"    {field} -> col {col} (expected {expected}) {'OK' if col == expected else 'DIFF'}")
    else:
        col_map = _build_column_map(ws, ALL_HEADER_MAP)
        print("Column map (1-row):")
        for field, col in sorted(col_map.items()):
            v = str(ws.cell(row=1, column=col).value or "")[:35]
            print(f"  {field}: col {col} = {v}")

    print("\nRow 2 cols 19-27:")
    for c in range(19, 28):
        v = str(ws.cell(row=2, column=c).value or "")[:40]
        print(f"  col {c}: '{v}'")

    print("\nRow 1 cols 1-32 (non-empty):")
    for c in range(1, 33):
        v = str(ws.cell(row=1, column=c).value or "")
        if v.strip():
            print(f"  col {c}: '{v[:60]}'")
