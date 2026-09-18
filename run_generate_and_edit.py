"""
End-to-End Generator, Editor & Uploader Orchestrator
----------------------------------------------------
1. Runs 10 iterations of video generation for 100 Popular Cars via Google Flow.
2. Automatically triggers batch editing with watermark logo, intro SFX, and outro (NO mid sound).
3. Cleans up raw downloaded video folders once edited versions are verified.
4. Uploads all newly edited videos directly to YouTube Studio as PUBLIC Shorts.
5. Synchronizes all master spreadsheets and trackers.
"""

import os
import sys
import time
import subprocess

os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

root_dir = os.path.dirname(os.path.abspath(__file__))
yt_dir = os.path.join(root_dir, "youtube-automation")
ve_dir = os.path.join(root_dir, "video-editor")
uploader_dir = os.path.join(root_dir, "youtube-uploader")

import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate, edit, and upload vehicle Shorts.")
    parser.add_argument("-n", "--count", type=int, default=3, help="Number of videos to generate, edit, and upload.")
    args = parser.parse_args()
    target_count = args.count

    print("=" * 70)
    print(f"[*] STARTING END-TO-END PIPELINE: GENERATE, EDIT & UPLOAD {target_count} CARS")
    print("=" * 70)

    # 1. Video Generation Loop
    print(f"\n[PHASE 1/3] Generating {target_count} Videos via Google Flow...")
    gen_cmd = [sys.executable, "run_main_loop.py", "-n", str(target_count), "-d", "10", "--100-cars"]
    gen_result = subprocess.run(gen_cmd, cwd=yt_dir)
    print(f"\n[PHASE 1 COMPLETE] Generation process returned code: {gen_result.returncode}")

    # Small cooldown
    time.sleep(5)

    # 2. Batch Editing
    print("\n[PHASE 2/3] Running Batch Video Editor with Logo Overlays & Cleanup...")
    edit_cmd = [sys.executable, "batch_editor.py", "--delete-original"]
    edit_result = subprocess.run(edit_cmd, cwd=ve_dir)
    print(f"\n[PHASE 2 COMPLETE] Batch editor returned code: {edit_result.returncode}")

    # Synchronize all trackers
    print("\n[*] Synchronizing master spreadsheets...")
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    try:
        from manage_status import sync_all_trackers
        sync_all_trackers()
    except Exception as e:
        print(f"[-] Tracker sync error: {e}")

    time.sleep(5)

    # 3. Upload to YouTube Studio
    print(f"\n[PHASE 3/3] Uploading {target_count} Videos to YouTube Studio...")
    up_cmd = [sys.executable, "uploader.py", "--limit", str(target_count), "--visibility", "PUBLIC"]
    up_result = subprocess.run(up_cmd, cwd=uploader_dir)
    print(f"\n[PHASE 3 COMPLETE] Upload process returned code: {up_result.returncode}")

    print("\n" + "=" * 70)
    print(f" ALL {target_count} VIDEOS GENERATED, EDITED, AND UPLOADED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
