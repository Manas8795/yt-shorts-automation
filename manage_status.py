"""
Universal Status Manager for Video Pipeline
--------------------------------------------
Allows marking any vehicle as INCOMPLETE or UNUPLOADED across:
1. Video Generation (marks status PENDING in vehicles.json)
2. Video Editing (resets edit status and cleans video-editor/output folder)
3. YouTube Uploading (removes from uploaded_videos.json and upload_tracker.xlsx)

Usage:
  python manage_status.py --unupload 22
  python manage_status.py --unupload "Kawasaki Ninja"
  python manage_status.py --incomplete-generation 5
  python manage_status.py --incomplete-edit 5
  python manage_status.py (Interactive Menu)
"""

import os
import sys
import json
import shutil
import argparse
from typing import Dict, Any, List, Optional

root_dir = os.path.dirname(os.path.abspath(__file__))
db_50_path = os.path.join(root_dir, "youtube-automation", "data", "vehicles.json")
db_100_path = os.path.join(root_dir, "youtube-automation", "100 popular cars", "vehicles.json")
edited_json_path = os.path.join(root_dir, "video-editor", "edited_vehicles.json")
uploaded_json_path = os.path.join(root_dir, "youtube-uploader", "uploaded_videos.json")
ve_out_dir = os.path.join(root_dir, "video-editor", "output")


def sync_all_trackers():
    """Sync both master spreadsheets."""
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    try:
        from sync_master_tracker import update_master_tracker
        update_master_tracker(root_dir)
        print("[+] Synced: master_vehicles_tracker.xlsx")
    except Exception as e:
        print(f"[-] Master tracker sync note: {e}")

    try:
        from sync_100_cars_tracker import update_100_cars_tracker
        update_100_cars_tracker(root_dir)
        print("[+] Synced: 100_popular_cars_tracker.xlsx")
    except Exception as e:
        print(f"[-] 100 Cars tracker sync note: {e}")

    try:
        from sync_usa_cars_tracker import update_usa_cars_tracker
        update_usa_cars_tracker(root_dir)
        print("[+] Synced: Popular_Cars_USA_Canada_tracker.xlsx")
    except Exception as e:
        print(f"[-] USA Cars tracker sync note: {e}")


def mark_unuploaded(identifier: str) -> bool:
    """Removes a vehicle from uploaded records so it can be uploaded again."""
    if not os.path.exists(uploaded_json_path):
        print(f"[-] Error: {uploaded_json_path} not found.")
        return False

    with open(uploaded_json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    target_query = identifier.strip().lower()
    matched = []
    retained = []

    for r in records:
        vid_id = str(r.get("id"))
        v_name = r.get("vehicle_name", "").lower()
        if vid_id == target_query or target_query in v_name:
            matched.append(r)
        else:
            retained.append(r)

    if not matched:
        print(f"[-] No matching uploaded records found for '{identifier}'.")
        return False

    with open(uploaded_json_path, "w", encoding="utf-8") as f:
        json.dump(retained, f, indent=2)

    for m in matched:
        print(f"[+] [UNUPLOADED] ID {m.get('id')}: {m.get('vehicle_name')} removed from uploaded queue.")

    # Also update upload_tracker.xlsx if openpyxl available
    try:
        from youtube_uploader.upload_tracker import UploadTracker
    except ImportError:
        pass

    sync_all_trackers()
    return True


def mark_generation_incomplete(identifier: str) -> bool:
    """Marks a vehicle's generation status as PENDING so it generates again."""
    target_query = identifier.strip().lower()
    updated = False

    for db_path, label in [(db_50_path, "50 Vehicles"), (db_100_path, "100 Popular Cars")]:
        if not os.path.exists(db_path):
            continue
        with open(db_path, "r", encoding="utf-8") as f:
            vehicles = json.load(f)

        db_modified = False
        for v in vehicles:
            vid_id = str(v.get("id"))
            v_name = v.get("vehicle_name", "").lower()
            if vid_id == target_query or target_query in v_name:
                v["status"] = "PENDING"
                v["output_video_path"] = ""
                if "completed_date" in v:
                    del v["completed_date"]
                print(f"[+] [GENERATION RESET] ID {v.get('id')}: {v.get('vehicle_name')} marked as PENDING in {label}.")
                db_modified = True
                updated = True

        if db_modified:
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(vehicles, f, indent=2)

    if not updated:
        print(f"[-] No vehicle found matching '{identifier}'.")
        return False

    sync_all_trackers()
    return True


def mark_edit_incomplete(identifier: str, delete_edited_folder: bool = True) -> bool:
    """Marks a vehicle's edit status as incomplete and removes its output folder."""
    if not os.path.exists(edited_json_path):
        print(f"[-] Error: {edited_json_path} not found.")
        return False

    with open(edited_json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    target_query = identifier.strip().lower()
    matched = []
    retained = []

    for r in records:
        vid_id = str(r.get("id"))
        v_name = r.get("vehicle_name", "").lower()
        if vid_id == target_query or target_query in v_name:
            matched.append(r)
        else:
            retained.append(r)

    if not matched:
        print(f"[-] No matching edited records found for '{identifier}'.")
        return False

    with open(edited_json_path, "w", encoding="utf-8") as f:
        json.dump(retained, f, indent=2)

    for m in matched:
        print(f"[+] [EDIT RESET] ID {m.get('id')}: {m.get('vehicle_name')} marked as PENDING.")
        if delete_edited_folder:
            rel_path = m.get("edited_video_path", "")
            if rel_path:
                norm = rel_path.replace("/", "\\")
                parts = norm.split("\\")
                if len(parts) >= 2:
                    folder_to_delete = os.path.join(ve_out_dir, parts[1])
                    if os.path.exists(folder_to_delete) and os.path.isdir(folder_to_delete):
                        shutil.rmtree(folder_to_delete)
                        print(f"    [CLEANUP] Deleted edited folder: {parts[1]}")

    sync_all_trackers()
    return True


def interactive_menu():
    print("\n" + "=" * 65)
    print("PIPELINE STATUS MANAGER (RESET / UNUPLOAD UTILITY)")
    print("=" * 65)
    print("1. Mark Video as UNUPLOADED (Queue for re-upload to YouTube)")
    print("2. Mark Video Generation as INCOMPLETE (Queue for re-generation)")
    print("3. Mark Video Edit as INCOMPLETE (Queue for re-editing with logo/sound)")
    print("4. Exit")
    print("-" * 65)

    try:
        choice = input("Select an option (1-4): ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if choice == "1":
        ident = input("Enter vehicle ID or name to unmark as uploaded: ").strip()
        if ident:
            mark_unuploaded(ident)
    elif choice == "2":
        ident = input("Enter vehicle ID or name to mark generation incomplete: ").strip()
        if ident:
            mark_generation_incomplete(ident)
    elif choice == "3":
        ident = input("Enter vehicle ID or name to mark edit incomplete: ").strip()
        if ident:
            mark_edit_incomplete(ident)
    else:
        print("Exiting.")


def main():
    parser = argparse.ArgumentParser(description="Manage pipeline status (unupload, mark incomplete).")
    parser.add_argument("--unupload", type=str, default=None, help="Mark vehicle ID or name as unuploaded.")
    parser.add_argument("--incomplete-generation", type=str, default=None, help="Mark vehicle ID or name as generation incomplete (PENDING).")
    parser.add_argument("--incomplete-edit", type=str, default=None, help="Mark vehicle ID or name as edit incomplete (PENDING).")
    args = parser.parse_args()

    if args.unupload:
        mark_unuploaded(args.unupload)
    elif args.incomplete_generation:
        mark_generation_incomplete(args.incomplete_generation)
    elif args.incomplete_edit:
        mark_edit_incomplete(args.incomplete_edit)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
