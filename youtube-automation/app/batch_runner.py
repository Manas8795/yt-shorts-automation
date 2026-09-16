import os
import sys
import yaml
import time
from datetime import datetime
from typing import Dict, Any

from app.utils.logger import setup_logger, get_logger
from app.generation.batch_manager import BatchManager
from app.generation.generation_job import GenerationJob, JobState
from app.storage.file_manager import FileManager
from app.browser.browser_manager import BrowserManager
from app.browser.flow_client import FlowClient


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Loads configuration file."""
    if not os.path.isabs(config_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_daily_batch(limit: int = 10) -> int:
    """
    Executes the daily 10-video batch automation:
    1. Loads the next 10 uncompleted vehicles from data/vehicles.json.
    2. For each vehicle: generates customized prompt via ASMR framework.
    3. Runs isolated Google Flow generation (1 prompt -> 1 video).
    4. Downloads and validates each video in its own output directory.
    5. Updates database with COMPLETED status and video paths.
    """
    config = load_config()
    log_dir = config.get("storage", {}).get("log_directory", "./logs")
    setup_logger(log_dir=log_dir)
    logger = get_logger("batch_runner")

    logger.info("==================================================================")
    logger.info(f" Starting Daily Batch Video Generation (Target: {limit} Videos)")
    logger.info("==================================================================")

    vehicles_file = config.get("batch", {}).get("vehicles_file", "data/vehicles.json")
    for arg in sys.argv[1:]:
        if arg in ["--100-cars", "--100cars"]:
            vehicles_file = "100 popular cars/vehicles.json"
        elif arg.startswith("--vehicles="):
            vehicles_file = arg.split("=", 1)[1]

    batch_mgr = BatchManager(vehicles_file=vehicles_file)
    batch = batch_mgr.get_next_batch(count=limit)

    # Auto-switch to 100 popular cars if default database is fully completed
    if not batch and "100 popular cars" not in vehicles_file:
        alt_path = "100 popular cars/vehicles.json"
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if os.path.exists(os.path.join(base_dir, alt_path)):
            alt_mgr = BatchManager(vehicles_file=alt_path)
            alt_batch = alt_mgr.get_next_batch(count=limit)
            if alt_batch:
                logger.info(f"Original database ({vehicles_file}) is fully completed (50/50).")
                logger.info(f"Automatically switching to 100 Popular Cars ({alt_path})!")
                batch_mgr = alt_mgr
                batch = alt_batch
                vehicles_file = alt_path

    if not batch:
        logger.info("All vehicles in the database have already been completed! No pending jobs.")
        return 0

    logger.info(f"Loaded {len(batch)} vehicles for today's batch execution.")

    # Storage & Settings
    file_mgr = FileManager(base_output_dir=config.get("storage", {}).get("output_directory", "./output"))
    browser_cfg = config.get("browser", {})
    gen_cfg = config.get("generation", {})
    flow_url = config.get("flow", {}).get("url", "https://flow.google.com/")

    successful_count = 0

    # Initialize Single Persistent Browser Session for the Entire Batch
    browser_mgr = BrowserManager(
        profile_directory=browser_cfg.get("profile_directory", "./browser_profile"),
        headless=browser_cfg.get("headless", False),
        slow_mo_ms=browser_cfg.get("slow_mo_ms", 0),
        viewport_width=browser_cfg.get("viewport_width", 1280),
        viewport_height=browser_cfg.get("viewport_height", 900),
        debug_directory=config.get("storage", {}).get("debug_directory", "./debug")
    )

    try:
        page = browser_mgr.launch()
        flow_client = FlowClient(page=page, flow_url=flow_url)
        flow_client.open()

        if not flow_client.wait_for_authentication(timeout_seconds=600):
            logger.error("Authentication required. Halting batch.")
            return 1

        for idx, vehicle in enumerate(batch, start=1):
            v_id = vehicle["id"]
            v_name = vehicle["vehicle_name"]
            safe_name = v_name.replace(" ", "_").replace("/", "-")
            source_excel = vehicle.get("source_excel", "100_popular_cars_in_India" if "100 popular cars" in str(vehicles_file) else "master_vehicles_tracker")
            job_id = f"{source_excel}_{v_id:02d}_{safe_name}"

            logger.info("\n" + "=" * 65)
            logger.info(f" [Job {idx}/{len(batch)}] Processing Vehicle #{v_id}: {v_name}")
            logger.info("=" * 65)

            # 1. Generate prompt for this specific vehicle
            prompt = batch_mgr.generate_prompt_for_vehicle(vehicle)
            
            # 2. Prepare job directory
            job_dir = file_mgr.prepare_job_directory(job_id)
            file_mgr.save_prompt(job_dir, prompt)

            job = GenerationJob(job_id=job_id, prompt=prompt)

            try:
                # Open fresh project canvas
                project_url = flow_client.navigate_to_create()
                job.set_project_url(project_url)

                # Configure settings (9:16, x1, Omni model, 720p)
                aspect_ratio = gen_cfg.get("aspect_ratio", "9:16")
                videos_per_job = gen_cfg.get("videos_per_job", 1)
                model = gen_cfg.get("model", "Omni")
                resolution = gen_cfg.get("resolution", "720p")
                flow_client.configure_generation(
                    aspect_ratio=aspect_ratio,
                    count=videos_per_job,
                    model=model,
                    resolution=resolution
                )

                # Enter prompt & submit
                flow_client.enter_prompt(prompt)
                flow_client.submit_generation()
                job.transition_to(JobState.GENERATING)

                # Wait for video rendering (150s render wait, up to 15 min timeout)
                is_done = flow_client.wait_for_generation(
                    timeout_seconds=gen_cfg.get("timeout_seconds", 900),
                    poll_interval_seconds=gen_cfg.get("poll_interval_seconds", 5),
                    min_wait_seconds=gen_cfg.get("min_render_wait_seconds", 150)
                )

                if not is_done:
                    logger.warning(f"Generation for {v_name} exceeded live window. Saved for resume.")
                    batch_mgr.mark_failed(v_id, "Generation timed out")
                    continue

                # Download video (720p Original size)
                video_path = flow_client.download_video(job_dir, resolution=resolution)
                is_valid, size = file_mgr.verify_video_file(video_path)
                
                if is_valid:
                    size_mb = round(size / (1024 * 1024), 2)
                    batch_mgr.mark_completed(v_id, video_path)
                    successful_count += 1
                    logger.info(f"✓ Video for {v_name} saved: {video_path} ({size_mb} MB)")
                else:
                    batch_mgr.mark_failed(v_id, "Download validation failed")

            except Exception as e:
                logger.error(f"Error processing {v_name}: {e}", exc_info=True)
                batch_mgr.mark_failed(v_id, str(e))

            # Polite pause between jobs (10 seconds)
            time.sleep(10)

    finally:
        browser_mgr.close()

    logger.info("==================================================================")
    logger.info(f" Batch Finished: {successful_count}/{len(batch)} Videos Successfully Generated.")
    logger.info("==================================================================")
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Google Flow ASMR Video Generator")
    parser.add_argument("--count", "-c", type=int, default=10, help="Number of videos to generate (default: 10)")
    parser.add_argument("--single", "-s", action="store_true", help="Generate just 1 single video")
    args = parser.parse_args()

    limit = 1 if args.single else args.count
    sys.exit(run_daily_batch(limit=limit))
