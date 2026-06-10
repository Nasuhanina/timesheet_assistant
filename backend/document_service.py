import io
import json
import os
import tempfile
from datetime import datetime
from flask import session
import requests
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from config import Config
from onedrive_service import _headers, _handle_errors

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


COMBINED_HEADERS = [
    "Name",
    "Date",
    "Project ID",
    "Doc Task Type",
    "Doc ID",
    "Doc Version",
    "Doc Type",
    "Work Time",
    "Reviewer Time",
    "Doc Status",
    "Activity Code",
    "Activity Time",
    "Work Location",
    "Total Time",
]
HEADER_FILL = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
HEADER_FILL_GRAY = PatternFill(start_color="D1D5DB", end_color="D1D5DB", fill_type="solid")

# Two-row template column layout (row 1 = category, row 2 = field names)
TEMPLATE_2ROW_LAYOUT = [
    # (group_label, [(field_name, column_number), ...])
    ("Name", [("user_name", 1)]),
    ("Date", [("date", 2)]),
    ("Project Document Work #1", [
        ("project_id", 3), ("doc_task_type", 4), ("doc_id", 5),
        ("doc_version", 6), ("doc_type", 7), ("work_time", 8),
        ("reviewer_time", 9), ("doc_status", 10),
    ]),
    ("Project Document Work #2", [
        ("project_id", 11), ("doc_task_type", 12), ("doc_id", 13),
        ("doc_version", 14), ("doc_type", 15), ("work_time", 16),
        ("reviewer_time", 17), ("doc_status", 18),
    ]),
    ("Activity #1", [
        ("activity_code", 19), ("project_id", 20), ("activity_time", 21),
    ]),
    ("Activity #2", [
        ("activity_code", 22), ("project_id", 23), ("activity_time", 24),
    ]),
    ("Activity #3", [
        ("activity_code", 25), ("project_id", 26), ("activity_time", 27),
    ]),
    ("Summary", [
        ("work_location", 28), ("leave_travel", 29),
        ("act_time_sum", 30), ("total_hours", 31), ("remarks", 32),
    ]),
]

TEMPLATE_2ROW_ROW1_LABELS = {
    1: "Name",
    2: "Date",
    3: "Project Document Work (Prepare, Check, Review, Mentoring)-#1",
    11: "Project Document Work (Prepare, Check, Review, Mentoring)-#2",
    19: "Other Project Activity or Non-Revenue Activity",
    28: "Leave/Travel Time",
    30: "Total",
    32: "Remarks",
}

HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def _ensure_documents_folder():
    path = Config.ONEDRIVE_ROOT_PATH.strip("/")
    parts = path.split("/")
    folder_id = None

    for part in parts:
        if not folder_id:
            resp = requests.get(
                f"{GRAPH_BASE}/me/drive/root:/{path}",
                headers=_headers(),
            )
            if resp.ok:
                folder_id = resp.json().get("id")
                continue

        create_resp = requests.post(
            f"{GRAPH_BASE}/me/drive/items/{folder_id or 'root'}/children",
            headers=_headers(),
            json={"name": part, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"},
        )
        if create_resp.status_code in (200, 201):
            folder_id = create_resp.json().get("id")
        else:
            existing = requests.get(
                f"{GRAPH_BASE}/me/drive/root:/{path}",
                headers=_headers(),
            )
            if existing.ok:
                folder_id = existing.json().get("id")
    return folder_id


def _excel_filename(user_email, is_macro=False):
    safe = user_email.replace("@", "_at_").replace(".", "_dot_")
    ext = ".xlsm" if is_macro else ".xlsx"
    return f"timesheet_{safe}{ext}"


def _is_xlsm(template_bytes):
    return (
        b"xl/macrosheets" in template_bytes
        or b"xl/vbaProject.bin" in template_bytes
        or template_bytes[:2] == b"PK" and b"vbaProject" in template_bytes
    )


DOC_HEADER_MAP = {
    "user_name": ["name", "Name", "User Name", "user name"],
    "date": ["date", "Date"],
    "project_id": ["project id", "project", "Project ID", "Project Id"],
    "doc_task_type": ["task type", "document task type", "doc task type", "Task Type", "Doc Task Type"],
    "doc_id": ["doc id", "document id", "doc Id", "Doc ID", "Document ID"],
    "doc_version": ["doc version", "target doc version", "drs", "version", "Doc Version", "Version"],
    "doc_type": ["doc type", "document type", "Doc Type", "Document Type"],
    "work_time": ["work time", "work time on document", "Work Time"],
    "reviewer_time": ["reviewer time", "reviewer's / mentor's time", "mentor time", "Reviewer Time"],
    "doc_status": ["doc status", "doc. status", "document status", "status", "Doc Status"],
    "work_location": ["work location", "location", "Work Location"],
}

OTHER_HEADER_MAP = {
    "date": ["date", "Date"],
    "activity_code": ["activity code", "Activity Code"],
    "project_id": ["project id", "Project ID"],
    "activity_time": ["activity time", "Activity Time"],
    "work_location": ["work location", "location", "Work Location"],
}


def _has_two_row_header(ws):
    if ws.max_row < 2:
        return False
    row1_vals = [str(cell.value or "").strip() for cell in ws[1]]
    keywords = ["Project Document Work", "Other Project Activity",
                "Leave/Travel", "Total", "Remarks"]
    for val in row1_vals:
        for kw in keywords:
            if kw.lower() in val.lower():
                return True
    return False


def _build_column_map_two_row(ws, field_map):
    col_map = {}
    for cell in ws[2]:
        if cell.value:
            val = str(cell.value).strip().lower()
            for field, candidates in field_map.items():
                if val in [c.lower() for c in candidates]:
                    col_map.setdefault(field, []).append(cell.column)
                    break
    return col_map


def _build_column_map(ws, field_map):
    col_map = {}
    for cell in ws[1]:
        if cell.value:
            val = str(cell.value).strip().lower()
            for field, candidates in field_map.items():
                if val in [c.lower() for c in candidates]:
                    col_map[field] = cell.column
                    break
    return col_map


HEADER_TO_FIELD = {}
for field, candidates in DOC_HEADER_MAP.items():
    for c in candidates:
        HEADER_TO_FIELD[c.lower()] = field


def _ensure_doc_headers(ws, doc_map):
    next_col = ws.max_column + 1 if ws.max_column else 1
    def style_cell(c):
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = HEADER_ALIGNMENT
        c.border = THIN_BORDER
    existing_headers = set(doc_map.keys())
    for header in DEFAULT_HEADERS:
        field = HEADER_TO_FIELD.get(header.lower())
        if field and field not in existing_headers:
            cell = ws.cell(row=1, column=next_col, value=header)
            style_cell(cell)
            doc_map[field] = next_col
            next_col += 1
    return doc_map


OTHER_HEADER_TO_FIELD = {}
for field, candidates in OTHER_HEADER_MAP.items():
    for c in candidates:
        OTHER_HEADER_TO_FIELD[c.lower()] = field


def _ensure_other_headers(ws, other_map):
    OTHER_HEADERS = ["Date", "Activity Code", "Project ID", "Activity Time", "Work Location"]
    next_col = ws.max_column + 1 if ws.max_column else 1
    def style_cell(c):
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = HEADER_ALIGNMENT
        c.border = THIN_BORDER
    existing_headers = set(other_map.keys())
    for header in OTHER_HEADERS:
        field = OTHER_HEADER_TO_FIELD.get(header.lower())
        if field and field not in existing_headers:
            cell = ws.cell(row=1, column=next_col, value=header)
            style_cell(cell)
            other_map[field] = next_col
            next_col += 1
    return other_map


ALL_HEADER_MAP = {}
for field, candidates in DOC_HEADER_MAP.items():
    ALL_HEADER_MAP[field] = list(candidates)
for field, candidates in OTHER_HEADER_MAP.items():
    if field in ALL_HEADER_MAP:
        seen = set(ALL_HEADER_MAP[field])
        for c in candidates:
            if c not in seen:
                ALL_HEADER_MAP[field].append(c)
                seen.add(c)
    else:
        ALL_HEADER_MAP[field] = list(candidates)

ALL_HEADER_MAP.setdefault("total_time", ["Total Time", "total time", "Total", "total"])
ALL_HEADER_MAP.setdefault("total_hours", ["Total Hours", "total hours"])
ALL_HEADER_MAP.setdefault("remarks", ["Remarks"])
ALL_HEADER_MAP.setdefault("leave_travel", ["Leave/Travel"])
ALL_HEADER_MAP.setdefault("act_summary_time", ["Activity Time Total", "activity time total", "Total Activity Time"])

TEMPLATE_2ROW_EXTRA = {
    "user_name": ["Name", "User Name"],
    "project_id": ["Project ID #1", "Project ID #2", "Project ID (If Proj. Activity)"],
    "doc_task_type": ["Document Task Type (P= Prepare or C=Check)"],
    "doc_id": ["Doc ID"],
    "doc_version": ["Target Doc Version / DRS for doc. Version"],
    "doc_type": ["Doc Type N=New Doc U=Update"],
    "work_time": ["Work time on Document"],
    "reviewer_time": ["Reviewer's / Mentor's time"],
    "doc_status": ["Doc. Status"],
    "activity_code": ["Activity Code #1", "Activity Code #2", "Activity Code #3"],
    "activity_time": ["Activity Time"],
    "work_location": ["Work location"],
    "date": ["dd/mm/yy"],
}
for field, variants in TEMPLATE_2ROW_EXTRA.items():
    if field in ALL_HEADER_MAP:
        seen = set(c.lower() for c in ALL_HEADER_MAP[field])
        for v in variants:
            if v.lower() not in seen:
                ALL_HEADER_MAP[field].append(v)
                seen.add(v.lower())


def _build_from_template(entries, template_bytes):
    try:
        wb = load_workbook(template_bytes, keep_vba=True)
    except Exception:
        return _build_from_scratch(entries)
    ws = wb.active

    if _has_two_row_header(ws):
        return _build_from_template_2row(entries, wb, template_bytes)

    col_map = _build_column_map(ws, ALL_HEADER_MAP)
    if not col_map:
        return _build_from_scratch(entries)

    next_row = 2
    for row in ws.iter_rows(min_row=2, values_only=True):
        if any(cell is not None for cell in row):
            next_row += 1
        else:
            break

    for entry in entries:
        for field, col_list in col_map.items():
            col = col_list[0]
            if field == "total_time":
                wt = float(entry.get("work_time", 0) or 0)
                rt = float(entry.get("reviewer_time", 0) or 0)
                at = float(entry.get("activity_time", 0) or 0)
                val = wt + rt + at
            else:
                val = entry.get(field, "")
                if val is None:
                    val = ""
            ws.cell(row=next_row, column=col, value=val)
        next_row += 1

    is_macro = _is_xlsm(template_bytes)
    ext = ".xlsm" if is_macro else ".xlsx"

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        tmp.close()
        wb.save(tmp.name)
        with open(tmp.name, "rb") as f:
            output = io.BytesIO(f.read())
        output.seek(0)
    finally:
        os.unlink(tmp.name)

    return output, is_macro


def _build_from_template_2row(entries, wb, template_bytes):
    ws = wb.active

    col_map = _build_column_map_two_row(ws, ALL_HEADER_MAP)
    if not col_map:
        return _build_from_scratch(entries)

    grouped = {}
    for e in entries:
        d = e.get("date", "")
        if d not in grouped:
            grouped[d] = []
        grouped[d].append(e)

    sorted_dates = sorted(grouped.keys())

    next_row = 3
    for row in ws.iter_rows(min_row=3, values_only=True):
        if any(cell is not None for cell in row):
            next_row += 1
        else:
            break

    for date_str in sorted_dates:
        day_entries = grouped[date_str]
        doc_entries = [e for e in day_entries if e.get("activity_type") not in ("other", "leave_travel")]
        other_entries = [e for e in day_entries if e.get("activity_type") == "other"]
        leave_entries = [e for e in day_entries if e.get("activity_type") == "leave_travel"]

        if "date" in col_map and col_map["date"]:
            ws.cell(row=next_row, column=col_map["date"][0], value=date_str)

        if "user_name" in col_map and col_map["user_name"]:
            name_val = doc_entries[0].get("user_name", "") if doc_entries else (other_entries[0].get("user_name", "") if other_entries else (leave_entries[0].get("user_name", "") if leave_entries else ""))
            ws.cell(row=next_row, column=col_map["user_name"][0], value=name_val)

        if "leave_travel" in col_map and col_map["leave_travel"]:
            leave_val = ", ".join(e.get("leave_travel_type", "") for e in leave_entries) if leave_entries else ""
            ws.cell(row=next_row, column=col_map["leave_travel"][0], value=leave_val)

        doc_fields = ["project_id", "doc_task_type", "doc_id", "doc_version",
                      "doc_type", "work_time", "reviewer_time", "doc_status"]

        def get_col(field, slot_index):
            lst = col_map.get(field, [])
            if slot_index < len(lst):
                return lst[slot_index]
            return None

        for slot_i in range(2):
            entry = doc_entries[slot_i] if slot_i < len(doc_entries) else None
            for field in doc_fields:
                col = get_col(field, slot_i)
                if col is None:
                    continue
                if entry:
                    val = entry.get(field, "")
                    if val is None:
                        val = ""
                else:
                    val = ""
                ws.cell(row=next_row, column=col, value=val)

        act_fields = ["activity_code", "project_id", "activity_time"]

        for slot_i in range(3):
            entry = other_entries[slot_i] if slot_i < len(other_entries) else None
            for field in act_fields:
                col = get_col(field, 2 + slot_i)
                if col is None:
                    continue
                if entry:
                    val = entry.get(field, "")
                    if val is None:
                        val = ""
                else:
                    val = ""
                ws.cell(row=next_row, column=col, value=val)

        work_location = ""
        locations = set()
        for e in day_entries:
            loc = e.get("work_location", "")
            if loc:
                locations.add(loc)
        if locations:
            work_location = ", ".join(sorted(locations))

        total_work = sum(float(e.get("work_time", 0) or 0) for e in doc_entries)
        total_review = sum(float(e.get("reviewer_time", 0) or 0) for e in doc_entries)
        total_activity = sum(float(e.get("activity_time", 0) or 0) for e in other_entries)
        total_leave = sum(float(e.get("time", 0) or 0) for e in leave_entries)
        grand_total = total_work + total_review + total_activity + total_leave

        if "work_location" in col_map and col_map["work_location"]:
            ws.cell(row=next_row, column=col_map["work_location"][0], value=work_location)

        if "total_hours" in col_map and col_map["total_hours"]:
            ws.cell(row=next_row, column=col_map["total_hours"][0], value=grand_total)

        if "act_summary_time" in col_map and col_map["act_summary_time"]:
            ws.cell(row=next_row, column=col_map["act_summary_time"][0], value=total_activity)
        else:
            ws.cell(row=next_row, column=30, value=total_activity).border = THIN_BORDER

        next_row += 1

    is_macro = _is_xlsm(template_bytes) if template_bytes else False
    ext = ".xlsm" if is_macro else ".xlsx"

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        tmp.close()
        wb.save(tmp.name)
        with open(tmp.name, "rb") as f:
            output = io.BytesIO(f.read())
        output.seek(0)
    finally:
        os.unlink(tmp.name)

    return output, is_macro


def _write_scratch_headers(ws):
    row1_groups = [
        (1, 1, "Name"),
        (2, 2, "Date"),
        (3, 10, "Project Document Work (Prepare, Check, Review, Mentoring)-#1"),
        (11, 18, "Project Document Work (Prepare, Check, Review, Mentoring)-#2"),
        (19, 27, "Other Project Activity or Non-Revenue Activity"),
        (28, 30, "Leave/Travel Time"),
        (31, 31, "Total"),
        (32, 32, "Remarks"),
    ]
    for start, end, label in row1_groups:
        if start < end:
            ws.merge_cells(start_row=1, start_column=start, end_row=1, end_column=end)
        cell = ws.cell(row=1, column=start, value=label)
        cell.font = Font(bold=True, size=10)
        cell.fill = HEADER_FILL_GRAY
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        if start < end:
            for c in range(start + 1, end + 1):
                ws.cell(row=1, column=c).border = THIN_BORDER

    row2_headers = [
        ("Name", 1),
        ("Date", 2),
        ("Project ID #1", 3),
        ("Document Task Type (P= Prepare or C=Check)", 4),
        ("Doc ID", 5),
        ("Target Doc Version / DRS for doc. Version", 6),
        ("Doc Type N=New Doc U=Update", 7),
        ("Work time on Document", 8),
        ("Reviewer's / Mentor's time", 9),
        ("Doc. Status", 10),
        ("Project ID #2", 11),
        ("Document Task Type (P= Prepare or C=Check)", 12),
        ("Doc ID", 13),
        ("Target Doc Version / DRS for doc. Version", 14),
        ("Doc Type N=New Doc U=Update", 15),
        ("Work time on Document", 16),
        ("Reviewer's / Mentor's time", 17),
        ("Doc. Status", 18),
        ("Activity Code #1", 19),
        ("Project ID (If Proj. Activity)", 20),
        ("Activity Time", 21),
        ("Activity Code #2", 22),
        ("Project ID (If Proj. Activity)", 23),
        ("Activity Time", 24),
        ("Activity Code #3", 25),
        ("Project ID (If Proj. Activity)", 26),
        ("Activity Time", 27),
        ("Work location", 28),
        ("Leave/Travel", 29),
        ("Activity Time", 30),
        ("Total Hours", 31),
        ("Remarks", 32),
    ]

    for header, col in row2_headers:
        cell = ws.cell(row=2, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER

    widths = [20, 14, 14, 16, 22, 14, 12, 12, 14, 14, 14, 16, 22, 14, 12, 12, 14, 14, 18, 18, 14, 18, 18, 14, 18, 18, 14, 14, 14, 14, 14, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def _build_from_scratch(entries):
    wb = Workbook()
    ws = wb.active
    ws.title = "Timesheet"
    _write_scratch_headers(ws)

    grouped = {}
    for e in entries:
        d = e.get("date", "")
        if d not in grouped:
            grouped[d] = []
        grouped[d].append(e)

    sorted_dates = sorted(grouped.keys())
    row = 3

    for date_str in sorted_dates:
        day_entries = grouped[date_str]
        doc_entries = [e for e in day_entries if e.get("activity_type") not in ("other", "leave_travel")]
        other_entries = [e for e in day_entries if e.get("activity_type") == "other"]
        leave_entries = [e for e in day_entries if e.get("activity_type") == "leave_travel"]

        user_name = next((e.get("user_name", "") for e in day_entries if e.get("user_name")), "")

        def set_cell(col, val):
            c = ws.cell(row=row, column=col, value=val)
            c.border = THIN_BORDER
            c.alignment = Alignment(vertical="center")

        set_cell(1, user_name)
        set_cell(2, date_str)

        doc_fields = ["project_id", "doc_task_type", "doc_id", "doc_version",
                      "doc_type", "work_time", "reviewer_time", "doc_status"]

        for slot_i in range(2):
            entry = doc_entries[slot_i] if slot_i < len(doc_entries) else None
            base_col = 3 + slot_i * 8
            if entry:
                for fi, field in enumerate(doc_fields):
                    val = entry.get(field, "")
                    if val is None:
                        val = ""
                    set_cell(base_col + fi, val)
            else:
                for fi in range(8):
                    set_cell(base_col + fi, "")

        act_fields = ["activity_code", "project_id", "activity_time"]

        for slot_i in range(3):
            entry = other_entries[slot_i] if slot_i < len(other_entries) else None
            base_col = 19 + slot_i * 3
            if entry:
                for fi, field in enumerate(act_fields):
                    val = entry.get(field, "")
                    if val is None:
                        val = ""
                    set_cell(base_col + fi, val)
            else:
                for fi in range(3):
                    set_cell(base_col + fi, "")

        locations = set()
        for e in day_entries:
            loc = e.get("work_location", "")
            if loc:
                locations.add(loc)
        work_location = ", ".join(sorted(locations)) if locations else ""

        total_work = sum(float(e.get("work_time", 0) or 0) for e in doc_entries)
        total_review = sum(float(e.get("reviewer_time", 0) or 0) for e in doc_entries)
        total_activity = sum(float(e.get("activity_time", 0) or 0) for e in other_entries)
        total_leave = sum(float(e.get("time", 0) or 0) for e in leave_entries)
        grand_total = total_work + total_review + total_activity + total_leave

        leave_val = ", ".join(e.get("leave_travel_type", "") for e in leave_entries) if leave_entries else ""

        set_cell(28, work_location)
        set_cell(29, leave_val)
        set_cell(30, total_activity)
        set_cell(31, grand_total)
        set_cell(32, "")

        row += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output, False


def _build_workbook(entries, template_bytes=None):
    if template_bytes:
        return _build_from_template(entries, template_bytes)
    return _build_from_scratch(entries)


def generate_excel(entries, upload_template_bytes=None):
    user = session.get("user", {})
    email = user.get("email", "unknown")
    folder_id = _ensure_documents_folder()

    workbook_bytes, is_macro = _build_workbook(entries, upload_template_bytes)
    filename = _excel_filename(email, is_macro)
    content = workbook_bytes.read()

    folder_children = requests.get(
        f"{GRAPH_BASE}/me/drive/items/{folder_id}/children",
        headers=_headers(),
    )
    existing_id = None
    if folder_children.ok:
        for child in folder_children.json().get("value", []):
            if child.get("name") == filename:
                existing_id = child["id"]
                break

    if existing_id:
        resp = requests.put(
            f"{GRAPH_BASE}/me/drive/items/{existing_id}/content",
            headers=_headers(), data=content,
        )
    else:
        resp = requests.put(
            f"{GRAPH_BASE}/me/drive/items/{folder_id}:/{filename}:/content",
            headers=_headers(), data=content,
        )

    if _handle_errors(resp):
        return generate_excel(entries, upload_template_bytes)

    return resp.ok, resp.json().get("id") if resp.ok else None


def download_excel():
    user = session.get("user", {})
    email = user.get("email", "unknown")
    folder_id = _ensure_documents_folder()

    for is_macro in (False, True):
        filename = _excel_filename(email, is_macro)
        resp = requests.get(
            f"{GRAPH_BASE}/me/drive/items/{folder_id}:/{filename}:/content",
            headers=_headers(),
        )
        if resp.ok:
            meta_resp = requests.get(
                f"{GRAPH_BASE}/me/drive/items/{folder_id}:/{filename}",
                headers=_headers(),
            )
            meta = meta_resp.json() if meta_resp.ok else {}
            return resp.content, meta
        if resp.status_code != 404:
            if _handle_errors(resp):
                return download_excel()

    return None, None


def upload_template(file_bytes, filename):
    user = session.get("user", {})
    email = user.get("email", "unknown")
    folder_id = _ensure_documents_folder()
    is_macro = filename.lower().endswith(".xlsm") if filename else False
    template_name = f"template_{_excel_filename(email, is_macro)}"

    folder_children = requests.get(
        f"{GRAPH_BASE}/me/drive/items/{folder_id}/children",
        headers=_headers(),
    )
    existing_id = None
    if folder_children.ok:
        for child in folder_children.json().get("value", []):
            if child.get("name") == template_name:
                existing_id = child["id"]
                break

    if existing_id:
        resp = requests.put(
            f"{GRAPH_BASE}/me/drive/items/{existing_id}/content",
            headers=_headers(), data=file_bytes,
        )
    else:
        resp = requests.put(
            f"{GRAPH_BASE}/me/drive/items/{folder_id}:/{template_name}:/content",
            headers=_headers(), data=file_bytes,
        )

    if _handle_errors(resp):
        return upload_template(file_bytes, filename)
    return resp.ok


def download_template():
    user = session.get("user", {})
    email = user.get("email", "unknown")
    folder_id = _ensure_documents_folder()

    for ext in (".xlsm", ".xlsx"):
        template_name = f"template_{_excel_filename(email, ext == '.xlsm')}"
        resp = requests.get(
            f"{GRAPH_BASE}/me/drive/items/{folder_id}:/{template_name}:/content",
            headers=_headers(),
        )
        if resp.ok:
            return resp.content
        if resp.status_code != 404:
            if _handle_errors(resp):
                return download_template()

    return None


def get_document_info():
    user = session.get("user", {})
    email = user.get("email", "unknown")
    folder_id = _ensure_documents_folder()

    info = {"has_document": False, "has_template": False, "document_name": "", "entries_count": 0}

    for ext_is_macro, ext in [(False, ".xlsx"), (True, ".xlsm")]:
        filename = _excel_filename(email, ext_is_macro)
        template_name = f"template_{filename}"

        resp = requests.get(
            f"{GRAPH_BASE}/me/drive/items/{folder_id}:/{filename}",
            headers=_headers(),
        )
        if resp.ok:
            data = resp.json()
            info["has_document"] = True
            info["document_name"] = data.get("name", filename)
            info["document_size"] = data.get("size", 0)
            info["document_modified"] = data.get("lastModifiedDateTime", "")
            info["document_id"] = data.get("id", "")
            break

    for ext_is_macro, ext in [(False, ".xlsx"), (True, ".xlsm")]:
        template_name = f"template_{_excel_filename(email, ext_is_macro)}"
        template_resp = requests.get(
            f"{GRAPH_BASE}/me/drive/items/{folder_id}:/{template_name}",
            headers=_headers(),
        )
        if template_resp.ok:
            info["has_template"] = True
            break

    return info
