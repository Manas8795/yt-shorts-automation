import os
from datetime import datetime
from typing import Tuple


class FileManager:
    def __init__(self, base_output_dir: str = "./output"):
        self.base_output_dir = os.path.abspath(base_output_dir)

    def prepare_job_directory(self, job_id: str) -> str:
        """
        Creates and returns output/<job_id> directory directly without date subfolders.
        Folder format: <car_number>_<car_name>_<excel_name>
        """
        job_dir = os.path.join(self.base_output_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        return job_dir

    def save_prompt(self, job_dir: str, prompt: str) -> str:
        """Saves prompt text into the job directory."""
        prompt_path = os.path.join(job_dir, "prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt.strip() + "\n")
        return prompt_path

    def verify_video_file(self, video_path: str, min_size_bytes: int = 500 * 1024) -> Tuple[bool, int]:
        """
        Verifies that the video file exists and has valid video size (default > 500KB).
        Returns (is_valid, size_bytes).
        """
        if os.path.isfile(video_path):
            size = os.path.getsize(video_path)
            return size >= min_size_bytes, size
        return False, 0

