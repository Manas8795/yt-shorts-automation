from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class JobState(Enum):
    CREATED = "CREATED"
    BROWSER_READY = "BROWSER_READY"
    FLOW_READY = "FLOW_READY"
    PROMPT_SUBMITTED = "PROMPT_SUBMITTED"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    DOWNLOADED = "DOWNLOADED"
    
    # Terminal / Recovery States
    AUTH_REQUIRED = "AUTH_REQUIRED"
    GENERATION_FAILED = "GENERATION_FAILED"
    TIMEOUT = "TIMEOUT"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"


@dataclass
class GenerationJob:
    job_id: str
    prompt: str
    state: JobState = JobState.CREATED
    project_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    output_video_path: Optional[str] = None
    error_message: Optional[str] = None

    def transition_to(self, new_state: JobState, error_message: Optional[str] = None) -> None:
        """Transitions the job state and updates timestamp."""
        self.state = new_state
        self.updated_at = datetime.now()
        if error_message:
            self.error_message = error_message

    def set_project_url(self, url: str) -> None:
        """Saves the project URL for instant resume/re-check capabilities."""
        self.project_url = url
        self.updated_at = datetime.now()
