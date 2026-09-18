"""
100 Popular Cars Batch Video Generator
--------------------------------------
Automates batch video generation for the 100 Popular Cars in India using Google Flow.

Features:
- Reads database: youtube-automation/100 popular cars/vehicles.json
- Generates tailored ASMR prompts via PromptGenerator
- Submits jobs to Google Flow (9:16, Omni model, 720p)
- Downloads, verifies video integrity, and logs completion
- Real-time synchronization to d:/Temp/yt automation/100_popular_cars_tracker.xlsx

Usage:
  python run_100_cars_batch.py --limit 5
  python run_100_cars_batch.py --start-id 1 --limit 10
  python run_100_cars_batch.py --dry-run
"""

import os
import sys
import time
import argparse

# Ensure parent directory (youtube-automation) and workspace root are in path
current_dir = os.path.dirname(os.path.abspath(__file__))
yt_automation_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(yt_automation_dir)

if yt_automation_dir not in sys.path:
    sys.path.insert(0, yt_automation_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.batch_runner import load_config
from app.generation.batch_manager import BatchManager
from app.utils.logger import setup_logger, get_logger
from app.storage.file_manager import FileManager
from app.browser.browser_manager import BrowserManager
from app.browser.flow_client import FlowClient
from app.generation.generation_job import GenerationJob, JobState

try:
    from sync_100_cars_tracker import update_100_cars_tracker
except ImportError:
    update_100_cars_tracker = None


def main():
    parser = argparse.ArgumentParser(description="100 Popular Cars Batch Generator")
    parser.add_argument("--limit", type=int, default=10, help="Number of cars to generate in this run (default: 10).")
    parser.add_argument("--start-id", type=int, default=None, help="Start from car ID >= start-id.")
    parser.add_argument("--car", type=str, default=None, help="Filter specific car name or ID.")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompt generation without launching browser.")
    args = parser.parse_args()

    config = load_config(os.path.join(yt_automation_dir, "config", "config.yaml"))
    log_dir = os.path.join(yt_automation_dir, config.get("storage", {}).get("log_directory", "./logs"))
    setup_logger(log_dir=log_dir)
    logger = get_logger("100_cars_batch")

    vehicles_json = os.path.join(current_dir, "vehicles.json")
    batch_mgr = BatchManager(vehicles_file=vehicles_json)

    # Filter pending vehicles
    all_vehicles = batch_mgr.vehicles
    pending = [v for v in all_vehicles if v.get("status") in ["PENDING", None, "FAILED"]]

    if args.start_id:
        pending = [v for v in pending if v.get("id", 0) >= args.start_id]

    if args.car:
        q = args.car.lower()
        pending = [v for v in pending if str(v.get("id")) == q or q in v.get("vehicle_name", "").lower()]

    if not pending:
        logger.info("[*] No pending cars found matching criteria. Everything is completed!")
        print("\n[*] No pending cars to generate. All selected vehicles are completed!")
        return 0

    batch = pending[:args.limit]

    print("=" * 65)
    print("100 POPULAR CARS — BATCH GENERATION")
    print(f"Total Pending in Database: {len(pending)}")
    print(f"Target Batch Size: {len(batch)}")
    print(f"Master Tracker: {os.path.join(root_dir, '100_popular_cars_tracker.xlsx')}")
    print("=" * 65)

    if args.dry_run:
        print("\n=== DRY RUN MODE: PREVIEWING PROMPTS ===")
        for idx, v in enumerate(batch, 1):
            prompt = batch_mgr.generate_prompt_for_vehicle(v)
            print(f"\n[{idx}/{len(batch)}] Car: {v['vehicle_name']} (ID: {v['id']})")
            print(f"Color: {v.get('color_scheme')}")
            print(f"Prompt Length: {len(prompt)} characters")
            print(f"Prompt Snippet: {prompt[:180]}...")
        return 0

    # Ensure output directories
    base_output = os.path.join(yt_automation_dir, "output")
    file_mgr = FileManager(base_output_dir=base_output)
    browser_cfg = config.get("browser", {})
    gen_cfg = config.get("generation", {})
    flow_url = config.get("flow", {}).get("url", "https://flow.google.com/")

    successful_count = 0

    # Launch browser with persistent profile
    profile_dir = os.path.join(yt_automation_dir, browser_cfg.get("profile_directory", "./browser_profile"))
    browser_mgr = BrowserManager(
        profile_directory=profile_dir,
        headless=browser_cfg.get("headless", False),
        slow_mo_ms=browser_cfg.get("slow_mo_ms", 0),
        viewport_width=browser_cfg.get("viewport_width", 1280),
        viewport_height=browser_cfg.get("viewport_height", 900),
        debug_directory=os.path.join(yt_automation_dir, "debug")
    )

    try:
        page = browser_mgr.launch()
        flow_client = FlowClient(page=page, flow_url=flow_url)
        flow_client.open()

        if not flow_client.wait_for_authentication(timeout_seconds=600):
            logger.error("Authentication required. Halting batch.")
            print("[-] Google Flow authentication timed out. Run switch_account.bat to log in.")
            return 1

        for idx, vehicle in enumerate(batch, start=1):
            v_id = vehicle["id"]
            v_name = vehicle["vehicle_name"]
            safe_name = v_name.replace(" ", "_").replace("/", "-")
            source_excel = vehicle.get("source_excel", "100_popular_cars_in_India")
            job_id = f"{source_excel}_{v_id:02d}_{safe_name}"

            print("\n" + "=" * 65)
            print(f" [Job {idx}/{len(batch)}] Generating Car #{v_id}: {v_name}")
            print(f" Appearance: {vehicle.get('color_scheme')}")
            print("=" * 65)

            # 1. Generate customized ASMR unboxing prompt
            prompt = batch_mgr.generate_prompt_for_vehicle(vehicle)

            # 2. Prepare job directory
            job_dir = file_mgr.prepare_job_directory(job_id)
            file_mgr.save_prompt(job_dir, prompt)
            job = GenerationJob(job_id=job_id, prompt=prompt)

            try:
                # Ensure healthy page before starting job
                try:
                    if browser_mgr.page is None or browser_mgr.page.is_closed():
                        logger.info("Automation page is closed or not ready. Launching tab...")
                        flow_client.page = browser_mgr.launch()
                    else:
                        flow_client.page.bring_to_front()
                except Exception:
                    flow_client.page = browser_mgr.launch()

                # Open fresh project canvas
                project_url = flow_client.navigate_to_create()
                job.set_project_url(project_url)

                # Configure generation settings
                flow_client.configure_generation(
                    aspect_ratio=gen_cfg.get("aspect_ratio", "9:16"),
                    count=gen_cfg.get("videos_per_job", 1),
                    model=gen_cfg.get("model", "Omni"),
                    resolution=gen_cfg.get("resolution", "720p")
                )

                # Enter prompt & submit
                flow_client.enter_prompt(prompt)
                flow_client.submit_generation()
                job.transition_to(JobState.GENERATING)

                # Wait for video rendering
                is_done = flow_client.wait_for_generation(
                    timeout_seconds=gen_cfg.get("timeout_seconds", 900),
                    poll_interval_seconds=gen_cfg.get("poll_interval_seconds", 5),
                    min_wait_seconds=gen_cfg.get("min_render_wait_seconds", 150)
                )

                if not is_done:
                    logger.warning(f"Generation for {v_name} timed out.")
                    batch_mgr.mark_failed(v_id, "Generation timed out")
                    continue

                # Download video (720p)
                video_path = flow_client.download_video(job_dir, resolution=gen_cfg.get("resolution", "720p"))
                is_valid, size = file_mgr.verify_video_file(video_path)

                if is_valid:
                    size_mb = round(size / (1024 * 1024), 2)
                    batch_mgr.mark_completed(v_id, video_path)
                    successful_count += 1
                    print(f"[+] Successfully generated & downloaded: {video_path} ({size_mb} MB)")
                else:
                    batch_mgr.mark_failed(v_id, "Download validation failed")
                    print(f"[-] Video validation failed for {v_name}")

            except Exception as e:
                logger.error(f"Error processing {v_name}: {e}", exc_info=True)
                print(f"[-] Error generating {v_name}: {e}")
                batch_mgr.mark_failed(v_id, str(e))

            # Synchronize 100 Popular Cars Excel Tracker live
            if update_100_cars_tracker:
                try:
                    update_100_cars_tracker(root_dir)
                except Exception as ex:
                    logger.debug(f"Tracker update note: {ex}")

            # Polite pause between jobs
            time.sleep(10)

    finally:
        browser_mgr.close()

    print("\n" + "=" * 65)
    print(f"BATCH FINISHED: {successful_count}/{len(batch)} Cars Generated Successfully.")
    print(f"Tracker: {os.path.join(root_dir, '100_popular_cars_tracker.xlsx')}")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    main()
