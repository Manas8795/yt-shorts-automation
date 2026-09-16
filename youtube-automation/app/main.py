import os
import sys
import json
import yaml
from datetime import datetime
from typing import Dict, Any, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.utils.logger import setup_logger, get_logger
from app.browser.browser_manager import BrowserManager
from app.browser.flow_client import FlowClient
from app.generation.generation_job import GenerationJob, JobState
from app.storage.file_manager import FileManager
from app.generation.batch_manager import BatchManager


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Loads and validates configuration from YAML file."""
    if not os.path.isabs(config_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, config_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt(prompt_path: str = "prompts/test_prompt.txt") -> str:
    """Loads the test prompt text."""
    if not os.path.isabs(prompt_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(base_dir, prompt_path)

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_existing_job(job_dir: str) -> Optional[Dict[str, Any]]:
    """Checks if a status.json exists for an in-progress job."""
    status_file = os.path.join(job_dir, "status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_job_status(job_dir: str, job: GenerationJob, extra_info: Dict[str, Any] = None) -> str:
    """Saves job execution status to status.json in the job output directory."""
    status_file = os.path.join(job_dir, "status.json")
    data = {
        "job_id": job.job_id,
        "state": job.state.value,
        "project_url": job.project_url,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "output_video_path": job.output_video_path,
        "error_message": job.error_message,
        "extra": extra_info or {}
    }
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return status_file


def run_pipeline() -> int:
    """
    Executes the Hybrid Pipeline (Seamless Live Wait + Resume / Re-Check Fallback):
    1. Checks if an in-progress job exists with saved project_url (to resume without spending credits).
    2. Otherwise, creates a fresh project, saves project_url immediately, and submits generation.
    3. Seamlessly monitors rendering in real-time.
    4. Downloads and validates the video output as soon as it's ready.
    """
    config = load_config()
    log_dir = config.get("storage", {}).get("log_directory", "./logs")
    setup_logger(log_dir=log_dir)
    logger = get_logger("main")
    
    logger.info("===============================================================")
    logger.info(" Starting YouTube Shorts Automation — Hybrid Video Pipeline")
    logger.info("===============================================================")
    
    vehicles_file = config.get("batch", {}).get("vehicles_file", "data/vehicles.json")
    for arg in sys.argv[1:]:
        if arg in ["--100-cars", "--100cars"]:
            vehicles_file = "100 popular cars/vehicles.json"
        elif arg.startswith("--vehicles="):
            vehicles_file = arg.split("=", 1)[1]

    batch_mgr = BatchManager(vehicles_file=vehicles_file)
    pending_vehicles = batch_mgr.get_next_batch(count=1)

    # Auto-switch to 100 popular cars if default database is fully completed
    if not pending_vehicles and "100 popular cars" not in vehicles_file:
        alt_path = "100 popular cars/vehicles.json"
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if os.path.exists(os.path.join(base_dir, alt_path)):
            alt_mgr = BatchManager(vehicles_file=alt_path)
            alt_pending = alt_mgr.get_next_batch(count=1)
            if alt_pending:
                logger.info(f"Original database ({vehicles_file}) is fully completed (50/50).")
                logger.info(f"Automatically switching to 100 Popular Cars ({alt_path})!")
                batch_mgr = alt_mgr
                pending_vehicles = alt_pending
                vehicles_file = alt_path

    if not pending_vehicles:
        logger.info("All vehicles in the database have already been completed! No pending jobs.")
        return 0

    vehicle = pending_vehicles[0]
    v_id = vehicle["id"]
    v_name = vehicle["vehicle_name"]
    safe_name = v_name.replace(" ", "_").replace("/", "-")
    source_excel = vehicle.get("source_excel", "100_popular_cars_in_India" if "100 popular cars" in str(vehicles_file) else "master_vehicles_tracker")
    job_id = f"{source_excel}_{v_id:02d}_{safe_name}"

    logger.info(f"Processing Next Uncompleted Vehicle #{v_id}: {v_name} ({vehicle.get('color_scheme', '')})")
    prompt_text = batch_mgr.generate_prompt_for_vehicle(vehicle)

    job = GenerationJob(job_id=job_id, prompt=prompt_text)
    file_manager = FileManager(base_output_dir=config.get("storage", {}).get("output_directory", "./output"))
    job_dir = file_manager.prepare_job_directory(job.job_id)
    file_manager.save_prompt(job_dir, prompt_text)

    if "--dry-run" in sys.argv:
        print(f"\n[DRY RUN MODE] Next Vehicle in Queue:")
        print(f"  ID: #{v_id} - {v_name}")
        print(f"  Color Scheme: {vehicle.get('color_scheme')}")
        print(f"  Prompt ({len(prompt_text)} chars):\n  {prompt_text[:300]}...\n")
        return 0
    
    # Check if this job was already dispatched with a saved project_url
    existing_status = load_existing_job(job_dir)
    resuming = False
    if existing_status and existing_status.get("project_url") and existing_status.get("state") in ["GENERATING", "PROMPT_SUBMITTED"]:
        job.set_project_url(existing_status["project_url"])
        job.transition_to(JobState.GENERATING)
        resuming = True
        logger.info(f"Detected in-progress job with saved Project URL: {job.project_url}")
        logger.info("Resuming existing project without spending additional credits.")

    # Browser Setup
    browser_cfg = config.get("browser", {})
    gen_cfg = config.get("generation", {})
    debug_dir = config.get("storage", {}).get("debug_directory", "./debug")

    browser_mgr = BrowserManager(
        profile_directory=browser_cfg.get("profile_directory", "./browser_profile"),
        headless=browser_cfg.get("headless", False),
        slow_mo_ms=browser_cfg.get("slow_mo_ms", 0),
        viewport_width=browser_cfg.get("viewport_width", 1280),
        viewport_height=browser_cfg.get("viewport_height", 900),
        default_timeout_ms=browser_cfg.get("default_timeout_ms", 30000),
        debug_directory=debug_dir
    )

    try:
        page = browser_mgr.launch()
        job.transition_to(JobState.BROWSER_READY)
        logger.info(f"Browser launched. Job state: {job.state.value}")

        flow_url = config.get("flow", {}).get("url", "https://flow.google.com/")
        flow_client = FlowClient(page=page, flow_url=flow_url)
        flow_client.open()

        if not flow_client.wait_for_authentication(timeout_seconds=600):
            job.transition_to(JobState.AUTH_REQUIRED, "Authentication session expired or not found.")
            save_job_status(job_dir, job)
            return 1

        aspect_ratio = gen_cfg.get("aspect_ratio", "9:16")
        videos_per_job = gen_cfg.get("videos_per_job", 1)
        model = gen_cfg.get("model", "Omni")
        resolution = gen_cfg.get("resolution", "720p")
        duration = gen_cfg.get("duration", "8s")

        if resuming and job.project_url:
            # Re-check mode: Navigate directly to the saved project canvas
            flow_client.resume_project(job.project_url)
        else:
            # New job mode: Open new project canvas
            project_url = flow_client.navigate_to_create()
            job.set_project_url(project_url)
            save_job_status(job_dir, job)

            # Configure 9:16 aspect ratio & x1 count & 720p resolution & 8s duration
            flow_client.configure_generation(aspect_ratio=aspect_ratio, count=videos_per_job, model=model, resolution=resolution, duration=duration)

            # Enter Prompt & Submit
            flow_client.enter_prompt(prompt_text)
            flow_client.submit_generation()
            job.transition_to(JobState.PROMPT_SUBMITTED)
            save_job_status(job_dir, job)

        # Seamless Live Wait (Option A)
        job.transition_to(JobState.GENERATING)
        save_job_status(job_dir, job)
        
        timeout_seconds = gen_cfg.get("timeout_seconds", 900)
        poll_interval = gen_cfg.get("poll_interval_seconds", 5)
        min_wait_seconds = gen_cfg.get("min_render_wait_seconds", 150)

        is_completed = flow_client.wait_for_generation(
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval,
            min_wait_seconds=min_wait_seconds
        )
        
        if not is_completed:
            # Fail-safe: Keep project URL saved so it can be re-checked later without re-spending credits
            logger.warning(f"Live wait window elapsed. Project URL '{job.project_url}' saved for auto re-check.")
            save_job_status(job_dir, job, extra_info={"note": "Waiting for cloud rendering completion. Re-check scheduled."})
            return 0

        job.transition_to(JobState.COMPLETED)
        logger.info("Video rendering completed. Downloading asset...")

        # Download Video (720p Original size)
        video_path = flow_client.download_video(job_dir, resolution=resolution)
        job.output_video_path = video_path

        # Verify File on Disk
        is_valid, size_bytes = file_manager.verify_video_file(video_path)
        if not is_valid:
            raise FileNotFoundError(f"Downloaded video file missing or empty at: {video_path}")

        size_mb = size_bytes / (1024 * 1024)
        job.transition_to(JobState.DOWNLOADED)
        save_job_status(job_dir, job, extra_info={"file_size_mb": round(size_mb, 2)})

        # Update Master Database
        batch_mgr.mark_completed(vehicle_id=v_id, output_video_path=video_path)

        # Save audit screenshot
        screenshot_path = os.path.join(job_dir, "screenshot.png")
        page.screenshot(path=screenshot_path)

        logger.info("===============================================================")
        logger.info(" ✓ JOB COMPLETED SUCCESSFULLY!")
        logger.info(f" Output Video: {video_path} ({round(size_mb, 2)} MB)")
        logger.info(f" Project URL: {job.project_url}")
        logger.info("===============================================================")

        return 0

    except PlaywrightTimeoutError as e:
        logger.error(f"Playwright operation timed out: {e}")
        browser_mgr.capture_debug_screenshot("timeout_error")
        job.transition_to(JobState.TIMEOUT, str(e))
        save_job_status(job_dir, job)
        return 1

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        browser_mgr.capture_debug_screenshot("pipeline_error")
        job.transition_to(JobState.GENERATION_FAILED, str(e))
        save_job_status(job_dir, job)
        return 1

    finally:
        browser_mgr.close()


if __name__ == "__main__":
    sys.exit(run_pipeline())
