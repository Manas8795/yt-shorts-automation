"""
Original Vehicle Folders Cleanup Utility
-----------------------------------------
Safely deletes original raw vehicle folders from youtube-automation/output if and only if
the final edited video exists in video-editor/output and is verified intact (>500KB).

When an original video is deleted after editing, the ENTIRE folder associated with that
vehicle (including prompt.txt, status.json, screenshots, etc.) is permanently deleted.

Features:
- Strict safety verification: checks edited video file exists and size > 500KB.
- Dry-run preview: shows all folders to be deleted and total disk space reclaimable.
- Interactive confirmation (or --force / -y for automated pipelines).
- Deletes empty parent date folders (e.g. 2026-09-04, 2026-09-05) automatically.
- Works across both 50 vehicles and 100 Popular Cars pipelines.

Usage:
  python cleanup_original_videos.py --dry-run
  python cleanup_original_videos.py
  python cleanup_original_videos.py --force (or -y)
  python cleanup_original_videos.py --vehicle 5
"""

import os
import re
import sys
import json
import glob
import shutil
import argparse
from typing import List, Dict, Any, Tuple


def format_bytes(bytes_count: int) -> str:
    if bytes_count >= 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"
    elif bytes_count >= 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.2f} MB"
    elif bytes_count >= 1024:
        return f"{bytes_count / 1024:.2f} KB"
    return f"{bytes_count} bytes"


def get_folder_size_and_count(folder_path: str) -> Tuple[int, int]:
    total_size = 0
    file_count = 0
    try:
        for dirpath, _, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    pass
    except Exception:
        pass
    return total_size, file_count


def find_reclaimable_folders(
    root_dir: str,
    min_edited_size_bytes: int = 500 * 1024,
    vehicle_filter: str = None
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Finds all vehicle folders in youtube-automation/output whose edited video exists
    in video-editor/output and is verified intact (> min_edited_size_bytes).
    Returns (list of candidates, total_bytes).
    """
    ve_dir = os.path.join(root_dir, "video-editor")
    ve_out_dir = os.path.join(ve_dir, "output")
    yt_out_dir = os.path.abspath(os.path.join(root_dir, "youtube-automation", "output"))

    if not os.path.exists(ve_out_dir):
        print(f"[-] Error: {ve_out_dir} not found. Run batch_editor.py first.")
        return [], 0

    # Collect all verified edited videos: {clean_name_or_id: edited_video_path}
    verified_edited = {}
    for entry in os.listdir(ve_out_dir):
        sub_path = os.path.join(ve_out_dir, entry)
        if not os.path.isdir(sub_path):
            continue

        mp4_files = glob.glob(os.path.join(sub_path, "*.mp4"))
        for mp4 in mp4_files:
            try:
                sz = os.path.getsize(mp4)
                if sz >= min_edited_size_bytes:
                    verified_edited[entry.lower()] = {
                        "folder_name": entry,
                        "edited_path": mp4,
                        "edited_size": sz
                    }
                    break
            except OSError:
                continue

    # Also load edited_vehicles.json if present for additional metadata
    edited_json = os.path.join(ve_dir, "edited_vehicles.json")
    json_records = []
    if os.path.exists(edited_json):
        try:
            with open(edited_json, "r", encoding="utf-8") as f:
                json_records = json.load(f)
        except Exception:
            json_records = []

    candidates = []
    seen_job_folders = set()
    total_bytes = 0

    # 1. Scan from json_records first (gives exact source_video_path)
    for r in json_records:
        if r.get("edit_status") != "EDITED":
            continue

        vid_id = r.get("id")
        name = r.get("vehicle_name", f"Vehicle_{vid_id}")

        if vehicle_filter:
            q = vehicle_filter.lower()
            if str(vid_id) != q and q not in name.lower():
                continue

        rel_edited = r.get("edited_video_path", "")
        rel_source = r.get("source_video_path", "")

        abs_edited = os.path.join(ve_dir, rel_edited) if not os.path.isabs(rel_edited) else rel_edited
        abs_source = os.path.join(root_dir, rel_source) if not os.path.isabs(rel_source) else rel_source

        # Edited check
        if not os.path.exists(abs_edited):
            continue
        try:
            sz = os.path.getsize(abs_edited)
            if sz < min_edited_size_bytes:
                continue
        except OSError:
            continue

        job_folder = os.path.abspath(os.path.dirname(abs_source))
        if job_folder in seen_job_folders:
            continue

        # Check safety: must be inside youtube-automation/output and not equal to output dir itself
        if os.path.commonpath([yt_out_dir, job_folder]) == yt_out_dir and job_folder != yt_out_dir:
            if os.path.exists(job_folder) and os.path.isdir(job_folder):
                f_size, f_count = get_folder_size_and_count(job_folder)
                seen_job_folders.add(job_folder)
                candidates.append({
                    "id": vid_id,
                    "vehicle_name": name,
                    "job_folder": job_folder,
                    "folder_size": f_size,
                    "file_count": f_count,
                    "edited_path": abs_edited,
                    "edited_size": sz
                })
                total_bytes += f_size

    # 2. Check all folders in youtube-automation/output directly
    # This catches both new flat format (01_Swift_...) and date folders (2026-09-04/job_...)
    if os.path.exists(yt_out_dir):
        for root, dirs, _ in os.walk(yt_out_dir):
            if root == yt_out_dir:
                # Check top-level non-date directories (new naming scheme: 01_Maruti_Suzuki_Swift...)
                target_dirs = [d for d in dirs if not d.startswith("2026-")]
            elif os.path.dirname(root) == yt_out_dir and os.path.basename(root).startswith("2026-"):
                # Inside a date directory: check job subdirectories (job_0001, etc.)
                target_dirs = dirs
            else:
                continue

            for td in target_dirs:
                job_folder = os.path.abspath(os.path.join(root, td))
                if job_folder in seen_job_folders:
                    continue

                # Safety check
                if os.path.commonpath([yt_out_dir, job_folder]) != yt_out_dir or job_folder == yt_out_dir:
                    continue

                # Check if this folder corresponds to any verified edited video
                td_lower = td.lower()
                matched_edited = None
                matched_id = None
                matched_name = td

                for key, ed_info in verified_edited.items():
                    key_parts = key.split("_", 1)
                    k_id_str = key_parts[0]
                    k_name_str = key_parts[1] if len(key_parts) > 1 else ""

                    try:
                        k_id_int = int(k_id_str)
                    except ValueError:
                        k_id_int = None

                    # Strict name matching: ID alone is NEVER sufficient across different databases!
                    # Check if significant tokens of vehicle name are present in td_lower
                    name_tokens = [t for t in re.split(r'[^a-z0-9]+', k_name_str) if len(t) >= 3]
                    token_match = any(token in td_lower for token in name_tokens) if name_tokens else False

                    # a) job_xxxx with matching token (e.g. job_0008_Lamborghini_Aventador_SVJ)
                    if k_id_int is not None and f"job_{k_id_int:04d}" in td_lower and token_match:
                        matched_edited = ed_info
                        matched_id = k_id_int
                        matched_name = ed_info["folder_name"]
                        break
                    # b) starts with id AND name token matches (e.g. 01_Maruti_Suzuki_Swift...)
                    id_prefix_match = td_lower.startswith(f"{k_id_str}_") or (k_id_int is not None and td_lower.startswith(f"{k_id_int}_"))
                    if id_prefix_match and token_match:
                        matched_edited = ed_info
                        matched_id = k_id_int
                        matched_name = ed_info["folder_name"]
                        break
                    # c) exact name substring
                    if k_name_str and k_name_str in td_lower:
                        matched_edited = ed_info
                        matched_id = k_id_int
                        matched_name = ed_info["folder_name"]
                        break

                if matched_edited:
                    if vehicle_filter:
                        q = vehicle_filter.lower()
                        if str(matched_id) != q and q not in matched_name.lower():
                            continue

                    f_size, f_count = get_folder_size_and_count(job_folder)
                    seen_job_folders.add(job_folder)
                    candidates.append({
                        "id": matched_id if matched_id is not None else 0,
                        "vehicle_name": matched_name,
                        "job_folder": job_folder,
                        "folder_size": f_size,
                        "file_count": f_count,
                        "edited_path": matched_edited["edited_path"],
                        "edited_size": matched_edited["edited_size"]
                    })
                    total_bytes += f_size

    # Sort by ID
    candidates.sort(key=lambda x: (x.get("id") or 999, x.get("vehicle_name", "")))
    return candidates, total_bytes


def main():
    parser = argparse.ArgumentParser(description="Delete original vehicle folders after verified editing.")
    parser.add_argument("--dry-run", action="store_true", help="Preview vehicle folders to be deleted without removing them.")
    parser.add_argument("--force", "-y", action="store_true", help="Delete without asking for interactive confirmation.")
    parser.add_argument("--vehicle", type=str, default=None, help="Filter by vehicle name or ID.")
    parser.add_argument("--min-size-kb", type=int, default=500, help="Minimum edited file size in KB to consider valid (default: 500 KB).")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    abs_output_dir = os.path.abspath(os.path.join(root_dir, "youtube-automation", "output"))

    print("=" * 70)
    print("ORIGINAL VEHICLE FOLDERS CLEANUP UTILITY")
    print("=" * 70)

    candidates, total_bytes = find_reclaimable_folders(
        root_dir=root_dir,
        min_edited_size_bytes=args.min_size_kb * 1024,
        vehicle_filter=args.vehicle
    )

    if not candidates:
        print("[+] No original vehicle folders to delete. All originals are already cleaned up!")
        print("=" * 70)
        return 0

    print(f"Found {len(candidates)} verified edited video(s) with raw vehicle folder(s) on disk.")
    print(f"Total Disk Space Reclaimable: {format_bytes(total_bytes)}")
    print("-" * 70)

    for idx, c in enumerate(candidates, start=1):
        rel_folder = os.path.relpath(c["job_folder"], root_dir)
        print(f"[{idx:2d}/{len(candidates)}] ID {c['id']:2d}: {c['vehicle_name']}")
        print(f"     Folder to Delete: {rel_folder} ({format_bytes(c['folder_size'])}, {c['file_count']} files)")
        print(f"     Edited Video:     Verified OK ({format_bytes(c['edited_size'])})")

    print("-" * 70)

    if args.dry_run:
        print("\n[DRY RUN] No folders were deleted.")
        print(f"[DRY RUN] Total space that would be reclaimed: {format_bytes(total_bytes)}")
        print("=" * 70)
        return 0

    # Confirmation
    if not args.force:
        try:
            prompt = f"\nAre you sure you want to permanently delete these {len(candidates)} vehicle folder(s) [{format_bytes(total_bytes)}]? (y/N): "
            choice = input(prompt).strip().lower()
            if choice not in ["y", "yes"]:
                print("[-] Cleanup aborted by user. No folders deleted.")
                return 0
        except (KeyboardInterrupt, EOFError):
            print("\n[-] Cancelled. Exiting.")
            return 1

    # Execute folder deletion
    deleted_count = 0
    reclaimed_bytes = 0
    errors = 0

    print("\nDeleting original vehicle folders...")
    for idx, c in enumerate(candidates, start=1):
        folder = c["job_folder"]
        try:
            # Strict safety check before rmtree
            if (os.path.commonpath([abs_output_dir, folder]) == abs_output_dir
                and folder != abs_output_dir
                and os.path.exists(folder)):
                shutil.rmtree(folder)
                deleted_count += 1
                reclaimed_bytes += c["folder_size"]
                print(f"  [DELETED FOLDER] ID {c['id']:2d}: {c['vehicle_name']} -> {os.path.basename(folder)} ({format_bytes(c['folder_size'])})")

                # Clean up empty parent date directory if applicable
                parent_dir = os.path.dirname(folder)
                if (parent_dir != abs_output_dir
                    and os.path.commonpath([abs_output_dir, parent_dir]) == abs_output_dir
                    and os.path.exists(parent_dir)):
                    try:
                        if not os.listdir(parent_dir):
                            os.rmdir(parent_dir)
                            print(f"    [CLEANUP] Removed empty date folder: {os.path.basename(parent_dir)}")
                    except Exception:
                        pass
        except Exception as e:
            errors += 1
            print(f"  [-] Error deleting {folder}: {e}")

    print("\n" + "=" * 70)
    print("CLEANUP COMPLETED")
    print(f"Successfully deleted: {deleted_count}/{len(candidates)} vehicle folder(s)")
    print(f"Total disk space reclaimed: {format_bytes(reclaimed_bytes)}")
    if errors > 0:
        print(f"Errors encountered: {errors}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
