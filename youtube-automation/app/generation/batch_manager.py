import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.utils.logger import get_logger
from app.generation.prompt_generator import PromptGenerator
from app.storage.excel_tracker import ExcelTracker

logger = get_logger("batch_manager")


class BatchManager:
    """
    Manages the 100-vehicle database, extracts the daily 10-vehicle batch,
    and coordinates AI prompt generation via ChatGPT framework.
    """
    def __init__(
        self,
        vehicles_file: str = "data/vehicles.json",
        prompt_generator: Optional[PromptGenerator] = None,
        excel_file: str = "data/vehicles_tracker.xlsx"
    ):
        if not os.path.isabs(vehicles_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            vehicles_file = os.path.join(base_dir, vehicles_file)

        self.vehicles_file = vehicles_file
        self.prompt_generator = prompt_generator or PromptGenerator()
        self.excel_tracker = ExcelTracker(excel_path=excel_file)
        self.vehicles = self._load_vehicles()

    def _load_vehicles(self) -> List[Dict[str, Any]]:
        """Loads vehicle records from JSON database."""
        if os.path.exists(self.vehicles_file):
            with open(self.vehicles_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_vehicles(self) -> None:
        """Persists updated vehicle statuses to JSON database and syncs Excel tracker."""
        os.makedirs(os.path.dirname(self.vehicles_file), exist_ok=True)
        with open(self.vehicles_file, "w", encoding="utf-8") as f:
            json.dump(self.vehicles, f, indent=2)
        try:
            self.excel_tracker.sync_from_vehicles_list(self.vehicles)
        except Exception as e:
            logger.warning(f"Could not auto-update Excel tracker: {e}")

        # Synchronize parent master tracker on every generation iteration
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            import sys
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
            from sync_master_tracker import update_master_tracker
            update_master_tracker(root_dir)
            if "100 popular cars" in self.vehicles_file:
                from sync_100_cars_tracker import update_100_cars_tracker
                update_100_cars_tracker(root_dir)
            if "popular_cars_usa_canada" in self.vehicles_file:
                from sync_usa_cars_tracker import update_usa_cars_tracker
                update_usa_cars_tracker(root_dir)
        except Exception as e:
            logger.debug(f"Master tracker sync bypassed: {e}")


    def get_next_batch(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves the next N uncompleted (PENDING) vehicles.
        """
        pending = [v for v in self.vehicles if v.get("status", "PENDING") == "PENDING"]
        batch = pending[:count]
        logger.info(f"Retrieved next batch of {len(batch)} vehicles (Total pending remaining: {len(pending) - len(batch)})")
        return batch

    def generate_prompt_for_vehicle(self, vehicle: Dict[str, Any]) -> str:
        """
        Generates the customized ASMR prompt for a specific vehicle using ChatGPT framework.
        """
        prompt = self.prompt_generator.generate_prompt_for_vehicle(
            vehicle_name=vehicle["vehicle_name"],
            vehicle_type=vehicle.get("type", "motorcycle"),
            color_scheme=vehicle.get("color_scheme", "Classic Black with Silver"),
            scale=vehicle.get("scale", "1:12")
        )
        return prompt

    def mark_completed(self, vehicle_id: int, output_video_path: str) -> None:
        """Marks a vehicle as completed and saves timestamp and output path."""
        for v in self.vehicles:
            if v["id"] == vehicle_id:
                v["status"] = "COMPLETED"
                v["completed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                v["output_video_path"] = output_video_path
                break
        self._save_vehicles()
        logger.info(f"Vehicle #{vehicle_id} marked as COMPLETED.")

    def mark_failed(self, vehicle_id: int, error_message: str) -> None:
        """Marks a vehicle as failed with error details."""
        for v in self.vehicles:
            if v["id"] == vehicle_id:
                v["status"] = "FAILED"
                v["error_message"] = error_message
                break
        self._save_vehicles()
        logger.warning(f"Vehicle #{vehicle_id} marked as FAILED.")
