"""
Batch Video Editor & Output Organizer
--------------------------------------
Automates:
1. Reading completed vehicle videos from youtube-automation (read-only).
2. Covering the Gemini watermark with the channel logo at (x=545, y=1106).
3. Preserving high-quality audio with lossless stream copy.
4. Organizing into: video-editor/output/<ID>_<Vehicle_Name>/<Vehicle_Name>.mp4.
5. Deleting the entire vehicle folder associated with that vehicle if --delete-original is set.
6. Maintaining independent Excel & JSON trackers in video-editor, master tracker, and 100 cars tracker.
"""

import os
import re
import sys
import json
import glob
import shutil
import argparse
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_BIN = "ffmpeg"

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def sanitize_filename(name: str) -> str:
    """Sanitize vehicle name for safe Windows folder and file naming."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name)
    clean = re.sub(r'[\s]+', '_', clean)
    clean = clean.strip(" ._")
    return clean


def resolve_source_video(vehicle: Dict[str, Any], yt_base_dir: str) -> Optional[str]:
    """Find the source video file for a vehicle record."""
    raw_path = vehicle.get("output_video_path")
    
    if raw_path:
        # Check direct path (absolute or relative)
        if os.path.isabs(raw_path) and os.path.exists(raw_path):
            return raw_path
        
        candidate = os.path.join(yt_base_dir, raw_path)
        if os.path.exists(candidate):
            return candidate

    # Fallback: scan by job ID / vehicle name in youtube-automation/output
    vid_id = vehicle.get("id")
    v_name = sanitize_filename(vehicle.get("vehicle_name", ""))
    if vid_id is not None:
        patterns = [
            f"*{vid_id:02d}_{v_name}",
            f"*{vid_id}_{v_name}",
            f"{vid_id:02d}_{v_name}",
            f"{vid_id}_{v_name}",
            f"*{vid_id:02d}_{v_name}*",
            f"*{vid_id}_{v_name}*",
            f"job_{vid_id:04d}*",
            f"*_{v_name}"
        ]
        for pat in patterns:
            matches = glob.glob(os.path.join(yt_base_dir, "output", "**", pat), recursive=True)
            for job_dir in matches:
                if os.path.isdir(job_dir):
                    # Verify job folder name contains the exact vid_id if available
                    base_folder = os.path.basename(job_dir)
                    if f"_{vid_id:02d}_" in base_folder or f"_{vid_id}_" in base_folder or base_folder.startswith(f"{vid_id:02d}_") or base_folder.startswith(f"{vid_id}_"):
                        mp4s = glob.glob(os.path.join(job_dir, "*.mp4"))
                        if mp4s:
                            for m in mp4s:
                                if os.path.basename(m) == "video.mp4":
                                    return m
                            return mp4s[0]
                    elif v_name.lower() in base_folder.lower():
                        # Verify it doesn't just match a prefix of a longer vehicle name (e.g. Land Cruiser vs Land Cruiser Prado)
                        clean_folder_tail = base_folder.split(f"_{vid_id:02d}_")[-1] if f"_{vid_id:02d}_" in base_folder else base_folder
                        if clean_folder_tail.endswith(v_name) or clean_folder_tail == v_name:
                            mp4s = glob.glob(os.path.join(job_dir, "*.mp4"))
                            if mp4s:
                                for m in mp4s:
                                    if os.path.basename(m) == "video.mp4":
                                        return m
                                return mp4s[0]

    return None


def delete_vehicle_job_folder(source_video_path: str, yt_dir: str) -> bool:
    """
    Safely deletes the ENTIRE original vehicle folder containing the raw video.
    Also cleans up empty parent date directory (e.g. 2026-09-04, 2026-09-05).
    """
    try:
        if not source_video_path:
            return False
        job_folder = os.path.abspath(os.path.dirname(os.path.abspath(source_video_path)))
        abs_yt_out = os.path.abspath(os.path.join(yt_dir, "output"))

        # Strict safety checks: must be inside youtube-automation/output and NOT output itself
        if os.path.commonpath([abs_yt_out, job_folder]) == abs_yt_out and job_folder != abs_yt_out:
            if os.path.exists(job_folder) and os.path.isdir(job_folder):
                shutil.rmtree(job_folder)
                print(f"    [CLEANUP] Deleted original vehicle folder: {os.path.basename(job_folder)}")

                # Check and clean empty parent date directory if applicable
                parent_dir = os.path.dirname(job_folder)
                if (parent_dir != abs_yt_out
                    and os.path.commonpath([abs_yt_out, parent_dir]) == abs_yt_out
                    and os.path.exists(parent_dir)):
                    try:
                        if not os.listdir(parent_dir):
                            os.rmdir(parent_dir)
                            print(f"    [CLEANUP] Removed empty date folder: {os.path.basename(parent_dir)}")
                    except Exception:
                        pass
                return True
    except Exception as e:
        print(f"    [!] Note on vehicle folder deletion: {e}")
    return False


def edit_video_with_audio(
    source_video: str,
    output_video: str,
    logo_path: str,
    outro_path: Optional[str] = None,
    sound_intro_path: Optional[str] = None,
    sound_mid_path: Optional[str] = None
) -> bool:
    """
    Renders the complete final video according to samplefull.mp4:
    1. Overlays channel logo at (545, 1106).
    2. Scales unboxing video to 1080x1920 at 30 fps (first 10 seconds).
    3. Mixes pokeball.mp3 at 0.02s (first second sound effect).
    4. Appends the 4-second pikarev final outro video (with Pokemon caught music).
    Note: pikachu_message.mp3 is disabled by default per user request.
    """
    out_dir = os.path.dirname(output_video)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    
    use_outro = bool(outro_path and os.path.exists(outro_path))
    use_intro = bool(sound_intro_path and os.path.exists(sound_intro_path))
    # Middle sound (pika message) strictly disabled per user instruction
    sound_mid_path = None
    use_mid = False

    inputs = [source_video, logo_path]
    
    poke_idx = -1
    if use_intro:
        inputs.append(sound_intro_path)
        poke_idx = len(inputs) - 1

    pika_idx = -1
    if use_mid:
        inputs.append(sound_mid_path)
        pika_idx = len(inputs) - 1

    outro_idx = -1
    if use_outro:
        inputs.append(outro_path)
        outro_idx = len(inputs) - 1

    filter_parts = []
    # 1. Main video: trim first 10s, overlay logo at (545, 1106), scale to 1080x1920 30fps
    filter_parts.append("[0:v]trim=0:10,setpts=PTS-STARTPTS[v_trim];")
    filter_parts.append("[1:v]scale=110:-1[logo];")
    filter_parts.append("[v_trim][logo]overlay=545:1106[v_branded];")
    filter_parts.append("[v_branded]scale=1080:1920:flags=lanczos,fps=30,format=yuv420p,setsar=1[v0];")

    # 2. Main audio: trim first 10s, resample to 48kHz stereo
    filter_parts.append("[0:a]atrim=0:10,asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a_main];")

    # 3. Audio SFX mixing
    amix_inputs = ["[a_main]"]
    if use_intro:
        filter_parts.append(f"[{poke_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,adelay=20|20[a_poke];")
        amix_inputs.append("[a_poke]")
    if use_mid:
        filter_parts.append(f"[{pika_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,adelay=3588|3588[a_pika];")
        amix_inputs.append("[a_pika]")

    if len(amix_inputs) > 1:
        filter_parts.append(f"{''.join(amix_inputs)}amix=inputs={len(amix_inputs)}:duration=first:normalize=0[a0];")
    else:
        filter_parts.append("[a_main]acopy[a0];")

    # 4. Outro concatenation
    if use_outro:
        filter_parts.append(f"[{outro_idx}:v]scale=1080:1920,fps=30,format=yuv420p,setsar=1[v1];")
        filter_parts.append(f"[{outro_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a1];")
        filter_parts.append("[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]")

    cmd = [FFMPEG_BIN, "-y"]
    for inp in inputs:
        cmd.extend(["-i", inp])
    cmd.extend([
        "-filter_complex", "".join(filter_parts),
        "-map", "[outv]" if use_outro else "[v0]",
        "-map", "[outa]" if use_outro else "[a0]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        output_video
    ])
    
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            print(f"[-] FFmpeg error: {res.stderr[-300:]}")
            return False
        return True
    except Exception as e:
        print(f"[-] Execution error: {e}")
        return False


def save_editor_trackers(records: List[Dict[str, Any]], tracker_json_path: str, tracker_xlsx_path: str):
    """Saves records to both JSON and formatted Excel tracker."""
    # 1. JSON Tracker
    with open(tracker_json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    # 2. Excel Tracker
    if not HAS_OPENPYXL:
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Edited Videos"

    # Styling
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    
    status_success_fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
    status_success_font = Font(name="Segoe UI", size=10, bold=True, color="274E13")

    status_failed_fill = PatternFill(start_color="FCE5CD", end_color="FCE5CD", fill_type="solid")
    status_failed_font = Font(name="Segoe UI", size=10, bold=True, color="783F04")

    data_font = Font(name="Segoe UI", size=10)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )

    headers = [
        "ID", "Vehicle Name", "Category", "Source Excel", "Edit Status",
        "Edited Video Path", "Original Video Path", "Edited Date"
    ]
    ws.append(headers)

    for col_num, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    for row_idx, r in enumerate(records, start=2):
        status = r.get("edit_status", "UNKNOWN")
        row_data = [
            r.get("id"),
            r.get("vehicle_name"),
            r.get("type", "").capitalize(),
            r.get("source_excel", "-"),
            status,
            r.get("edited_video_path", "-"),
            r.get("source_video_path", "-"),
            r.get("edited_date", "-")
        ]
        ws.append(row_data)

        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(row=row_idx, column=col_idx)
            c.font = data_font
            c.border = thin_border
            c.alignment = center_align if col_idx in [1, 3, 4, 5, 8] else left_align

            if col_idx == 5:  # Edit Status
                if status == "EDITED":
                    c.fill = status_success_fill
                    c.font = status_success_font
                else:
                    c.fill = status_failed_fill
                    c.font = status_failed_font

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(tracker_xlsx_path)


def main():
    parser = argparse.ArgumentParser(description="Batch edit videos and organize into vehicle folders.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of videos to process.")
    parser.add_argument("--force", action="store_true", help="Force re-rendering even if output exists.")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be done.")
    parser.add_argument("--vehicle", type=str, default=None, help="Filter by specific vehicle name or ID.")
    parser.add_argument("--delete-original", action="store_true", help="Delete original raw vehicle folder after verified successful edit.")
    parser.add_argument("--database", type=str, default=None, help="Path to vehicles.json database (default: auto-checks all).")
    parser.add_argument("--outro", type=str, default=None, help="Custom path to outro video (default: pikarev final.mp4).")
    parser.add_argument("--no-outro", action="store_true", help="Disable appending the 4-second outro video.")
    parser.add_argument("--sound-intro", type=str, default=None, help="Custom intro SFX at 0.0s (default: pokeball.mp3).")
    parser.add_argument("--sound-mid", type=str, default=None, help="Custom mid SFX at 3.6s (default: None; pikachu message disabled).")
    parser.add_argument("--no-sounds", action="store_true", help="Disable adding sound effects (pokeball SFX).")
    parser.add_argument("--with-pikachu-message", action="store_true", help="Explicitly re-enable the pikachu message SFX at 3.6s.")
    args = parser.parse_args()

    # Base paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    yt_dir = os.path.join(root_dir, "youtube-automation")
    logo_path = os.path.join(script_dir, "channel_logo_transparent.png")
    
    # Outro video path (prefers pikarev final.mp4, fallback to pikarev.mp4)
    default_outro = os.path.join(script_dir, "pikarev final.mp4")
    if not os.path.exists(default_outro):
        default_outro = os.path.join(script_dir, "pikarev.mp4")
    outro_path = None if args.no_outro else (args.outro if args.outro else default_outro)

    # Sound effects
    default_intro = os.path.join(script_dir, "pokeball.mp3")
    sound_intro_path = None if args.no_sounds else (args.sound_intro if args.sound_intro else default_intro)

    # Mid SFX (Pikachu message): STRICTLY DISABLED per user instruction ("donot add anymiddle sound of pika message")
    sound_mid_path = None

    output_base_dir = os.path.join(script_dir, "output")
    tracker_json = os.path.join(script_dir, "edited_vehicles.json")
    tracker_xlsx = os.path.join(script_dir, "editor_tracker.xlsx")

    if not os.path.exists(logo_path):
        print(f"[-] Error: Logo not found at {logo_path}")
        sys.exit(1)

    # Determine vehicles to process
    vehicles = []
    if args.database:
        if not os.path.exists(args.database):
            print(f"[-] Error: database not found at {args.database}")
            sys.exit(1)
        with open(args.database, "r", encoding="utf-8") as f:
            vehicles = json.load(f)
    else:
        # Auto-load 50 vehicles, 100 Popular Cars, and Popular Cars USA Canada Top 50
        db_original = os.path.join(yt_dir, "data", "vehicles.json")
        db_100 = os.path.join(yt_dir, "100 popular cars", "vehicles.json")
        db_usa = os.path.join(yt_dir, "popular_cars_usa_canada", "vehicles.json")

        if os.path.exists(db_original):
            try:
                with open(db_original, "r", encoding="utf-8") as f:
                    for v in json.load(f):
                        v["_source_db"] = "50_vehicles"
                        vehicles.append(v)
            except Exception:
                pass

        if os.path.exists(db_100):
            try:
                with open(db_100, "r", encoding="utf-8") as f:
                    for v in json.load(f):
                        v["_source_db"] = "100_popular_cars"
                        vehicles.append(v)
            except Exception:
                pass

        if os.path.exists(db_usa):
            try:
                with open(db_usa, "r", encoding="utf-8") as f:
                    for v in json.load(f):
                        v["_source_db"] = "Popular_Cars_USA_Canada_Top_50"
                        vehicles.append(v)
            except Exception:
                pass

    # Load existing tracker if present
    existing_tracker = {}
    if os.path.exists(tracker_json):
        try:
            with open(tracker_json, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for item in loaded:
                    # Key by vehicle_name for unique identification across databases
                    k = item.get("vehicle_name", "").strip().lower()
                    if k:
                        existing_tracker[k] = item
        except Exception:
            existing_tracker = {}

    # Filter completed vehicles
    completed_vehicles = [v for v in vehicles if v.get("status") == "COMPLETED"]
    
    if args.vehicle:
        query = args.vehicle.lower()
        completed_vehicles = [
            v for v in completed_vehicles
            if str(v.get("id")) == query or query in v.get("vehicle_name", "").lower()
        ]

    print("=" * 65)
    print("BATCH VIDEO EDITOR & OUTPUT ORGANIZER")
    print("=" * 65)
    print(f"[*] Found {len(completed_vehicles)} completed vehicles eligible for editing.")
    print(f"[*] Target output directory: {output_base_dir}")
    print(f"[*] Watermark overlay logo: {os.path.basename(logo_path)} at (545, 1106)")
    if sound_intro_path and os.path.exists(sound_intro_path):
        print(f"[*] Intro SFX enabled: {os.path.basename(sound_intro_path)} (at 0.0s)")
    print("[*] Mid SFX (Pikachu message): Disabled (no middle sound added)")
    if outro_path and os.path.exists(outro_path):
        print(f"[*] Outro video attached: {os.path.basename(outro_path)} (4s CTA appended at 10.0s)")
    else:
        print("[*] Outro video: Disabled")
    if args.delete_original:
        print("[*] Option enabled: Original vehicle folder will be deleted after verified edit.")
    print("-" * 65)

    processed_count = 0
    skipped_count = 0
    failed_count = 0

    records_to_save = list(existing_tracker.values())

    for idx, v in enumerate(completed_vehicles, start=1):
        if args.limit and processed_count >= args.limit:
            print(f"[*] Limit of {args.limit} reached. Stopping batch.")
            break

        vid_id = v.get("id")
        raw_name = v.get("vehicle_name", f"vehicle_{vid_id}")
        clean_name = sanitize_filename(raw_name)
        v_type = v.get("type", "unknown")
        v_key = raw_name.strip().lower()

        # Determine source excel origin
        source_excel = v.get("source_excel")
        if not source_excel:
            if v.get("_source_db") == "Popular_Cars_USA_Canada_Top_50" or "popular_cars_usa_canada" in str(v.get("output_video_path", "")):
                source_excel = "Popular_Cars_USA_Canada_Top_50"
            elif v.get("_source_db") == "100_popular_cars" or "100 popular cars" in str(v.get("output_video_path", "")):
                source_excel = "100_popular_cars_in_India"
            else:
                source_excel = "master_vehicles_tracker"

        # Unique key across databases
        v_key = f"{source_excel}_{vid_id:02d}_{clean_name}"

        # Output folder & file: video-editor/output/<Source_Excel>_<ID>_<Vehicle_Name>/<Vehicle_Name>.mp4
        vehicle_folder_name = f"{source_excel}_{vid_id:02d}_{clean_name}"
        vehicle_dir = os.path.join(output_base_dir, vehicle_folder_name)
        dest_video = os.path.join(vehicle_dir, f"{clean_name}.mp4")

        # Migration check: if older variants exist, rename them to prefix format
        old_candidates = [
            os.path.join(output_base_dir, f"{vid_id:02d}_{clean_name}_{source_excel}"),
            os.path.join(output_base_dir, f"{vid_id:02d}_{clean_name}"),
            os.path.join(output_base_dir, clean_name),
            os.path.join(output_base_dir, f"{vid_id}_{clean_name}")
        ]
        for old_dir in old_candidates:
            if os.path.exists(old_dir) and not os.path.exists(vehicle_dir):
                try:
                    os.rename(old_dir, vehicle_dir)
                    print(f"[*] Migrated folder: {os.path.basename(old_dir)} -> {vehicle_folder_name}")
                    break
                except Exception as e:
                    print(f"[-] Could not rename {os.path.basename(old_dir)} to {vehicle_folder_name}: {e}")

        # Check if already edited
        if os.path.exists(dest_video) and not args.force:
            print(f"[{idx}/{len(completed_vehicles)}] [EXISTS] Already edited: {clean_name} ({source_excel})")
            skipped_count += 1
            
            # If user requested --delete-original, delete raw vehicle folder if still present
            if args.delete_original:
                try:
                    source_video = resolve_source_video(v, yt_dir)
                    if source_video and os.path.getsize(dest_video) >= 500 * 1024:
                        delete_vehicle_job_folder(source_video, yt_dir)
                except Exception:
                    pass

            if v_key not in existing_tracker:
                source_video = resolve_source_video(v, yt_dir)
                rec = {
                    "id": vid_id,
                    "vehicle_name": raw_name,
                    "type": v_type,
                    "source_excel": source_excel,
                    "edit_status": "EDITED",
                    "edited_video_path": os.path.relpath(dest_video, script_dir),
                    "source_video_path": os.path.relpath(source_video, root_dir) if source_video else "-",
                    "edited_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                existing_tracker[v_key] = rec
                records_to_save.append(rec)
            continue

        source_video = resolve_source_video(v, yt_dir)
        if not source_video or not os.path.exists(source_video):
            print(f"[{idx}/{len(completed_vehicles)}] [SKIP] Source video not found for: {raw_name} (ID: {vid_id})")
            skipped_count += 1
            continue

        if args.dry_run:
            print(f"[{idx}/{len(completed_vehicles)}] [DRY-RUN] Would process:")
            print(f"    Source: {source_video}")
            print(f"    Target: {dest_video}")
            processed_count += 1
            continue

        print(f"[{idx}/{len(completed_vehicles)}] [EDITING] {raw_name} -> {vehicle_folder_name}/{clean_name}.mp4 ...")
        success = edit_video_with_audio(
            source_video=source_video,
            output_video=dest_video,
            logo_path=logo_path,
            outro_path=outro_path,
            sound_intro_path=sound_intro_path,
            sound_mid_path=sound_mid_path
        )

        if success:
            file_size_mb = os.path.getsize(dest_video) / (1024 * 1024)
            print(f"    [+] Successfully generated ({file_size_mb:.2f} MB)")
            rec = {
                "id": vid_id,
                "vehicle_name": raw_name,
                "type": v_type,
                "source_excel": source_excel,
                "edit_status": "EDITED",
                "edited_video_path": os.path.relpath(dest_video, script_dir),
                "source_video_path": os.path.relpath(source_video, root_dir),
                "edited_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            existing_tracker[v_key] = rec
            records_to_save = [r for r in records_to_save if f"{r.get('source_excel', '')}_{r.get('id', 0):02d}_{sanitize_filename(r.get('vehicle_name', ''))}" != v_key]
            records_to_save.append(rec)
            processed_count += 1

            # Save progress incrementally after each success
            records_to_save.sort(key=lambda x: (x.get("source_excel", ""), x.get("id") or 999, x.get("vehicle_name", "")))
            save_editor_trackers(records_to_save, tracker_json, tracker_xlsx)

            # Synchronize parent master tracker & 100 cars tracker
            try:
                if root_dir not in sys.path:
                    sys.path.insert(0, root_dir)
                from sync_master_tracker import update_master_tracker
                update_master_tracker(root_dir)
            except Exception:
                pass

            try:
                if root_dir not in sys.path:
                    sys.path.insert(0, root_dir)
                from sync_100_cars_tracker import update_100_cars_tracker
                update_100_cars_tracker(root_dir)
            except Exception:
                pass

            # Auto-delete original raw vehicle folder if requested
            if args.delete_original:
                try:
                    if os.path.exists(dest_video) and os.path.getsize(dest_video) >= 500 * 1024:
                        delete_vehicle_job_folder(source_video, yt_dir)
                except Exception as e:
                    print(f"    [!] Note on vehicle folder deletion: {e}")
        else:
            print(f"    [-] Failed to process {raw_name}")
            failed_count += 1

    # Final summary
    print("\n" + "="*60)
    print("BATCH EDITING COMPLETE")
    print(f"Processed: {processed_count}")
    print(f"Skipped/Already existed: {skipped_count}")
    print(f"Failed: {failed_count}")
    print(f"Editor Tracker Excel: {tracker_xlsx}")
    print(f"Editor Tracker JSON: {tracker_json}")
    print("="*60)


if __name__ == "__main__":
    main()
