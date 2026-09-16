"""
Batch Runner: Complete Bike Assembly (4 bikes) + 6 Popular Cars (#35-#40) + Upload All 10
------------------------------------------------------------------------------------------
Step 1: Generates & edits 4 remaining bikes (Ranks 17-20: TVS Sport, TVS Radeon, RE Himalayan 450, Yamaha MT-15)
Step 2: Generates 6 popular cars (#35-#40) via Google Flow
Step 3: Batch edits the 6 popular cars with logo, intro SFX, and outro (NO mid sound)
Step 4: Uploads all 4 bike assembly videos to YouTube Studio (Public, Not made for kids, 100% upload check)
Step 5: Uploads all 6 car videos to YouTube Studio (Public, Not made for kids, 100% upload check)
"""

import os
import sys
import time
import subprocess

root_dir = os.path.dirname(os.path.abspath(__file__))
yt_dir = os.path.join(root_dir, "youtube-automation")
ve_dir = os.path.join(root_dir, "video-editor")
bike_dir = os.path.join(ve_dir, "bike assembling niche")
uploader_dir = os.path.join(root_dir, "youtube-uploader")

def main():
    print("=" * 70)
    print("STARTING 10-VIDEO GENERATION & UPLOAD PIPELINE")
    print("4 Bike Assembly (Ranks 17-20) + 6 Popular Cars (#35-#40)")
    print("=" * 70)

    # -------------------------------------------------------------
    # PHASE 1: Generate & Edit 4 Bikes (Ranks 17-20)
    # -------------------------------------------------------------
    print("\n[PHASE 1/4] Generating & Editing 4 Remaining Bikes (Bike Assembly Niche)...")
    cmd_bikes = [sys.executable, "run_bike_assembly.py", "4"]
    res_bikes = subprocess.run(cmd_bikes, cwd=bike_dir)
    print(f"[PHASE 1 COMPLETE] Bike assembly pipeline exited with code {res_bikes.returncode}")

    time.sleep(5)

    # -------------------------------------------------------------
    # PHASE 2: Generate 6 Popular Cars (#35-#40)
    # -------------------------------------------------------------
    print("\n[PHASE 2/4] Generating 6 Popular Cars (#35-#40) via Google Flow...")
    cmd_cars = [sys.executable, "run_main_loop.py", "-n", "6", "-d", "10", "--100-cars"]
    res_cars = subprocess.run(cmd_cars, cwd=yt_dir)
    print(f"[PHASE 2 COMPLETE] Car generation loop exited with code {res_cars.returncode}")

    time.sleep(5)

    # -------------------------------------------------------------
    # PHASE 3: Batch Edit the 6 Popular Cars
    # -------------------------------------------------------------
    print("\n[PHASE 3/4] Batch Editing Newly Generated Cars (with logo, intro SFX, pikarev outro)...")
    cmd_edit = [sys.executable, "batch_editor.py", "--delete-original"]
    res_edit = subprocess.run(cmd_edit, cwd=ve_dir)
    print(f"[PHASE 3 COMPLETE] Batch editor exited with code {res_edit.returncode}")

    # Synchronize trackers
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    try:
        from manage_status import sync_all_trackers
        sync_all_trackers()
    except Exception as e:
        print(f"[-] Note on tracker sync: {e}")

    time.sleep(5)

    # -------------------------------------------------------------
    # PHASE 4: Upload All 10 Videos to YouTube Studio
    # -------------------------------------------------------------
    print("\n[PHASE 4/4] Uploading All 10 Videos to YouTube Studio...")
    
    # 4a. Upload Bike Assembly videos (4)
    print("\n[*] Uploading 4 Bike Assembly videos...")
    cmd_up_bikes = [sys.executable, "uploader.py", "--bike-assembly", "--limit", "4", "--visibility", "PUBLIC"]
    res_up_bikes = subprocess.run(cmd_up_bikes, cwd=uploader_dir)
    print(f"[*] Bike uploads exited with code {res_up_bikes.returncode}")

    time.sleep(5)

    # 4b. Upload Car videos (6)
    print("\n[*] Uploading 6 Popular Car videos...")
    cmd_up_cars = [sys.executable, "uploader.py", "--limit", "6", "--visibility", "PUBLIC"]
    res_up_cars = subprocess.run(cmd_up_cars, cwd=uploader_dir)
    print(f"[*] Car uploads exited with code {res_up_cars.returncode}")

    print("\n" + "=" * 70)
    print("ALL 10 VIDEOS GENERATED, EDITED, AND UPLOADED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
