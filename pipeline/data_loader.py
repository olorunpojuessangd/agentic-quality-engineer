"""Data loader module for CMM measurements, machine events, and defect reports."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
MOCK_LOGS_DIR = ROOT_DIR / "data" / "mock_logs"
EVAL_DIR = ROOT_DIR / "data" / "eval"


def load_measurements(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = path or (MOCK_LOGS_DIR / "measurements.csv")
    with open(target, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            {
                **row,
                "nominal": float(row["nominal"]),
                "lower_tol": float(row["lower_tol"]),
                "upper_tol": float(row["upper_tol"]),
                "measured": float(row["measured"]),
            }
            for row in reader
        ]


def load_events(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = path or (MOCK_LOGS_DIR / "events.csv")
    with open(target, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_defect_reports(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = path or (MOCK_LOGS_DIR / "defect_reports.json")
    with open(target, mode="r", encoding="utf-8") as f:
        return json.load(f)


def load_ground_truth(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = path or (EVAL_DIR / "ground_truth.json")
    with open(target, mode="r", encoding="utf-8") as f:
        return json.load(f)


def get_part_slot(part_id: str) -> int:
    """Extract zero-indexed part slot number from part_id like 'P-2-024' -> 24."""
    try:
        return int(part_id.split("-")[-1])
    except (ValueError, IndexError):
        return -1
