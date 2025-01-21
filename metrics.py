from dataclasses import dataclass
from typing import Dict
import time

@dataclass
class Metrics:
    form_fill_duration: float
    success_rate: float
    field_match_rate: float
    error_count: int
    field_stats: Dict[str, Dict[str, int]]