"""
Auto Edit & Upload Watcher
--------------------------
Watches for newly generated raw videos from the active generation loop (Cars #91 to #100).
As soon as each car finishes generation:
1. Immediately runs batch_editor.py with --delete-original to edit with watermark, intro SFX, outro CTA.
2. Synchronizes all master spreadsheets.
3. Automatically triggers uploader.py to publish the Short as PUBLIC on manasagrawal8791@gmail.com with 100% upload verification.
4. Terminates automatically once Car #100 is uploaded.
"""

import os
import sys
import json
import time
import subprocess

root_dir = os.path.dirname(os.path.abspath(__file__))
yt_dir = os.path.join(root_dir, "youtube-automation")
ve_dir = os.path.join(root_dir, "video-editor")
up_dir = os.path.join(root_dir, "youtube-uploader")

def get_uploaded_count():
    up_json = os.path.join(up_dir, "uploaded_videos.json")
    if os.path.exists(up_json):
        try:
            with open(up_json, "r", encoding="utf-8") as f:
                ups = json.load(f)
            c100 = [u for u in ups if u.get("source_excel") == "100_popular_cars_in_India"]
            return len(c100)
        except Exception:
            pass
    return 0

def main():
    print("=" * 70)
    print("[*] STARTING AUTO EDIT & UPLOAD WATCHER (CARS #91 TO #100)")
    print("=" * 70)

    while True:
        uploaded_now = get_uploaded_count()
        print(f"\n[*] Current Upload Progress: {uploaded_now}/100 Cars Uploaded")
        if uploaded_now >= 100:
            print("\n" + "=" * 70)
            print("[SUCCESS] ALL 100 CARS HAVE BEEN GENERATED, EDITED, AND UPLOADED!")
            print("=" * 70)
            break

        # 1. Run batch editor
        edit_cmd = [sys.executable, "batch_editor.py", "--delete-original"]
        subprocess.run(edit_cmd, cwd=ve_dir, capture_output=True)

        # 2. Sync master spreadsheets
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        try:
            from manage_status import sync_all_trackers
            sync_all_trackers()
        except Exception:
            pass

        # 3. Check if there are pending videos to upload
        up_cmd = [sys.executable, "uploader.py", "--limit", "1", "--visibility", "PUBLIC"]
        up_res = subprocess.run(up_cmd, cwd=up_dir)

        time.sleep(20)

if __name__ == "__main__":
    main()
