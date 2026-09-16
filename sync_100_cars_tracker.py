"""
100 Popular Cars Dedicated Tracker
----------------------------------
Maintains the dedicated master tracking spreadsheet in the parent workspace directory:
d:/Temp/yt automation/100_popular_cars_tracker.xlsx

Tracks all 100 popular Indian cars across:
1. Video Generation (youtube-automation/100 popular cars)
2. Video Editing (video-editor)
3. YouTube Uploading (youtube-uploader)

Required Columns:
- No. / ID (1 to 100)
- Car Name
- Generated (COMPLETED / PENDING / FAILED)
- Edited (EDITED / PENDING)
- Uploaded (UPLOADED / PENDING)
- Overall Stage
- Color Scheme & Appearance
- Scale
- Local Video Location
- YouTube Short Link
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def update_100_cars_tracker(root_dir: str = None) -> str:
    """
    Synchronizes d:/Temp/yt automation/100_popular_cars_tracker.xlsx
    with live data from 100 popular cars pipeline.
    """
    if not root_dir:
        root_dir = os.path.dirname(os.path.abspath(__file__))

    xlsx_path = os.path.join(root_dir, "100_popular_cars_tracker.xlsx")
    cars_json = os.path.join(root_dir, "youtube-automation", "100 popular cars", "vehicles.json")
    edited_json = os.path.join(root_dir, "video-editor", "edited_vehicles.json")
    uploaded_json = os.path.join(root_dir, "youtube-uploader", "uploaded_videos.json")

    # 1. Load 100 Cars Database
    cars = []
    if os.path.exists(cars_json):
        try:
            with open(cars_json, "r", encoding="utf-8") as f:
                cars = json.load(f)
        except Exception:
            cars = []

    # 2. Load Edited Videos
    edited_map = {}
    if os.path.exists(edited_json):
        try:
            with open(edited_json, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    # Match either by vehicle_name or if custom flag
                    v_name = item.get("vehicle_name", "").lower()
                    if v_name:
                        edited_map[v_name] = item
        except Exception:
            edited_map = {}

    # 3. Load Uploaded Videos
    uploaded_map = {}
    if os.path.exists(uploaded_json):
        try:
            with open(uploaded_json, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    v_name = item.get("vehicle_name", "").lower()
                    if v_name:
                        uploaded_map[v_name] = item
        except Exception:
            uploaded_map = {}

    if not HAS_OPENPYXL:
        print("[-] openpyxl not installed, skipping Excel creation.")
        return xlsx_path

    wb = openpyxl.Workbook()

    # Style definitions
    font_family = "Segoe UI"
    title_font = Font(name=font_family, size=16, bold=True, color="003366")
    subtitle_font = Font(name=font_family, size=10, italic=True, color="595959")
    header_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid") # Classic Navy

    kpi_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
    data_font = Font(name=font_family, size=10)
    link_font = Font(name=font_family, size=10, color="0000EE", underline="single")

    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )
    thick_bottom = Border(bottom=Side(style="medium", color="003366"))

    ws = wb.active
    ws.title = "100 Popular Cars"
    ws.views.sheetView[0].showGridLines = True

    # Title Block
    ws["B2"] = "100 POPULAR CARS IN INDIA — SHORTS PIPELINE TRACKER"
    ws["B2"].font = title_font
    ws["B3"] = f"Generated & Maintained by Automated Pipeline | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ws["B3"].font = subtitle_font

    # Calculate Metrics
    total_cars = len(cars)
    gen_done = sum(1 for c in cars if c.get("status") == "COMPLETED")
    gen_failed = sum(1 for c in cars if c.get("status") == "FAILED")
    gen_pending = sum(1 for c in cars if c.get("status") in ["PENDING", None])

    # Count edited & uploaded matching this list
    edit_done = 0
    up_done = 0
    for c in cars:
        c_name = c.get("vehicle_name", "").lower()
        if c_name in edited_map and edited_map[c_name].get("edit_status") == "EDITED":
            edit_done += 1
        if c_name in uploaded_map and uploaded_map[c_name].get("upload_status") == "UPLOADED":
            up_done += 1

    gen_pct = (gen_done / total_cars * 100) if total_cars else 0
    edit_pct = (edit_done / total_cars * 100) if total_cars else 0
    up_pct = (up_done / total_cars * 100) if total_cars else 0

    # KPI Summary Cards (Row 5 - 6)
    kpis = [
        ("TOTAL CARS", f"{total_cars}", "B"),
        ("1. GENERATED", f"{gen_done} ({gen_pct:.0f}%)", "D"),
        ("2. EDITED", f"{edit_done} ({edit_pct:.0f}%)", "F"),
        ("3. UPLOADED", f"{up_done} ({up_pct:.0f}%)", "H"),
    ]

    for label, val, col in kpis:
        col_idx = openpyxl.utils.column_index_from_string(col)
        # Card Label
        cell_lbl = ws.cell(row=5, column=col_idx, value=label)
        cell_lbl.font = Font(name=font_family, size=9, bold=True, color="595959")
        cell_lbl.alignment = center_align
        cell_lbl.fill = kpi_fill
        cell_lbl.border = thin_border

        # Card Value
        cell_val = ws.cell(row=6, column=col_idx, value=val)
        cell_val.font = Font(name=font_family, size=14, bold=True, color="003366")
        cell_val.alignment = center_align
        cell_val.fill = kpi_fill
        cell_val.border = thin_border

    # Headers at Row 8
    headers = [
        "No. / ID",
        "Car Name",
        "Generated",
        "Edited",
        "Uploaded",
        "Overall Stage",
        "Color Scheme & Appearance",
        "Scale",
        "Local Output Location",
        "YouTube Short Link"
    ]

    for col_num, h_text in enumerate(headers, start=2): # Start at B
        c = ws.cell(row=8, column=col_num, value=h_text)
        c.font = header_font
        c.fill = header_fill
        c.alignment = center_align
        c.border = thin_border
    ws.row_dimensions[8].height = 24

    # Status Styling Tokens
    fill_completed = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid") # Soft Green
    font_completed = Font(name=font_family, size=10, bold=True, color="006100")

    fill_pending = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid") # Soft Yellow
    font_pending = Font(name=font_family, size=10, color="7F6000")

    fill_failed = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid") # Soft Red
    font_failed = Font(name=font_family, size=10, bold=True, color="9C0006")

    fill_blue = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid") # Soft Blue
    font_blue = Font(name=font_family, size=10, bold=True, color="1F497D")

    # Data Rows
    current_row = 9
    for c in cars:
        c_id = c.get("id")
        name = c.get("vehicle_name", "")
        color = c.get("color_scheme", "")
        scale = c.get("scale", "1:18")
        gen_status = c.get("status", "PENDING").upper()
        local_video = c.get("output_video_path", "")

        c_name_lower = name.lower()
        ed_rec = edited_map.get(c_name_lower, {})
        edit_status = "EDITED" if ed_rec.get("edit_status") == "EDITED" else "PENDING"
        if edit_status == "EDITED" and ed_rec.get("edited_video_path"):
            local_video = ed_rec.get("edited_video_path")

        up_rec = uploaded_map.get(c_name_lower, {})
        upload_status = "UPLOADED" if up_rec.get("upload_status") == "UPLOADED" else "PENDING"
        yt_url = up_rec.get("youtube_url", "")

        # Determine Overall Stage
        if upload_status == "UPLOADED":
            stage = "Published on YouTube"
        elif edit_status == "EDITED":
            stage = "Edited - Ready to Upload"
        elif gen_status == "COMPLETED":
            stage = "Generated - Pending Edit"
        elif gen_status == "FAILED":
            stage = "Generation Failed"
        else:
            stage = "Pending Generation"

        row_cells = [
            (c_id, center_align, None, None),
            (name, left_align, Font(name=font_family, size=10, bold=True), None),
            (gen_status, center_align, None, gen_status),
            (edit_status, center_align, None, edit_status),
            (upload_status, center_align, None, upload_status),
            (stage, center_align, None, stage),
            (color, left_align, None, None),
            (scale, center_align, None, None),
            (local_video if local_video else "-", left_align, None, None),
            (yt_url if yt_url else "-", center_align, None, None)
        ]

        for col_idx, (val, align, custom_font, status_key) in enumerate(row_cells, start=2):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.alignment = align
            cell.border = thin_border

            # Styling by status
            if status_key == "COMPLETED" or status_key == "EDITED" or status_key == "UPLOADED" or status_key == "Published on YouTube":
                cell.fill = fill_completed
                cell.font = font_completed
            elif status_key == "PENDING" or status_key == "Pending Generation":
                cell.fill = fill_pending
                cell.font = font_pending
            elif status_key == "FAILED" or status_key == "Generation Failed":
                cell.fill = fill_failed
                cell.font = font_failed
            elif status_key in ["Edited - Ready to Upload", "Generated - Pending Edit"]:
                cell.fill = fill_blue
                cell.font = font_blue
            elif custom_font:
                cell.font = custom_font
            else:
                cell.font = data_font

            # Hyperlink
            if col_idx == 11 and yt_url and yt_url.startswith("http"):
                cell.font = link_font
                cell.hyperlink = yt_url

        ws.row_dimensions[current_row].height = 20
        current_row += 1

    # Auto-fit Column Widths
    for col in ws.iter_cols(min_col=2, max_col=11):
        max_len = 0
        for cell in col[7:]: # inspect from row 8 down
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 10 # ID
    ws.column_dimensions["C"].width = 32 # Car Name
    ws.column_dimensions["D"].width = 14 # Generated
    ws.column_dimensions["E"].width = 14 # Edited
    ws.column_dimensions["F"].width = 14 # Uploaded
    ws.column_dimensions["G"].width = 24 # Overall Stage
    ws.column_dimensions["H"].width = 50 # Color Scheme
    ws.column_dimensions["I"].width = 10 # Scale
    ws.column_dimensions["J"].width = 35 # Local Location
    ws.column_dimensions["K"].width = 30 # YT Link

    try:
        wb.save(xlsx_path)
        print(f"[+] 100 Popular Cars tracker updated: {xlsx_path}")
    except PermissionError:
        alt_path = os.path.join(root_dir, "100_popular_cars_tracker_live.xlsx")
        wb.save(alt_path)
        print(f"[!] Primary tracker is locked by Excel. Saved live copy to: {alt_path}")
        return alt_path

    return xlsx_path


if __name__ == "__main__":
    update_100_cars_tracker()
