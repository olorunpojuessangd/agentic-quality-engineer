"""Event matcher that correlates defect timeframes with machine events."""
from __future__ import annotations

from typing import Any, Dict, List
from pipeline.data_loader import get_part_slot


class EventMatcher:
    """Correlates defect part runs with machine log events."""

    def __init__(self, events: List[Dict[str, Any]], measurements: List[Dict[str, Any]]):
        self.events = events
        self.measurements = measurements

    def correlate(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Find correlated events and measurement trends for a defect report."""
        machine = report["machine"]
        feature = report["feature"]
        part_ids = report["part_ids"]

        # Extract slot numbers for the failing parts
        failing_slots = sorted([get_part_slot(pid) for pid in part_ids])
        min_slot = min(failing_slots) if failing_slots else 0
        max_slot = max(failing_slots) if failing_slots else 0

        # Filter events for this specific machine
        machine_events = [e for e in self.events if e["machine"] == machine]

        # Extract measurements for this machine and feature
        feature_measurements = [
            m for m in self.measurements
            if m["machine"] == machine and m["feature"] == feature
        ]
        # Sort measurements by part slot
        feature_measurements.sort(key=lambda m: get_part_slot(m["part_id"]))

        # Check for correlated event candidates:
        correlated_events = []
        candidate_hypothesis = "unknown"

        # 1. Thermal check: Coolant alarm during or immediately before the failing slots
        alarm_events = [
            e for e in machine_events
            if e["event_type"] == "coolant_temp_alarm"
            and any(abs(get_part_slot(f"P-1-{e['timestamp']}") - min_slot) <= 5 or int(e.get("slot", -1)) <= min_slot <= int(e.get("slot", -1)) + 5 for _ in [0])
        ]

        # Alternatively match by matching event slots in events table
        for e in machine_events:
            # Reconstruct slot from timestamp or event list index
            # Slot is 10 min intervals starting from 06:00
            # Let's calculate slot directly from e['timestamp'] or event position
            event_slot = self._timestamp_to_slot(e["timestamp"])

            # Check if event is within or bounding the failure window
            is_bounding_start = (event_slot <= min_slot <= event_slot + 2)
            is_bounding_end = (max_slot <= event_slot <= max_slot + 2)
            is_inside = (min_slot <= event_slot <= max_slot)

            if is_bounding_start or is_bounding_end or is_inside:
                correlated_events.append({**e, "slot": event_slot})

        # Pattern classification:
        # If single isolated part with no events bounding it
        if len(failing_slots) == 1:
            candidate_hypothesis = "isolated_outlier"
            relevant_events = []
        else:
            # Check for thermal alarm
            thermal_alarm = [e for e in machine_events if e["event_type"] == "coolant_temp_alarm"]
            thermal_clear = [e for e in machine_events if e["event_type"] == "coolant_temp_cleared"]
            if thermal_alarm and abs(self._timestamp_to_slot(thermal_alarm[0]["timestamp"]) - min_slot) <= 1:
                candidate_hypothesis = "thermal"
                relevant_events = [thermal_alarm[0]["event_id"]]
                if thermal_clear and self._timestamp_to_slot(thermal_clear[0]["timestamp"]) >= max_slot:
                    relevant_events.append(thermal_clear[0]["event_id"])

            # Check for fixture maintenance
            elif any(e["event_type"] == "fixture_maintenance" and self._timestamp_to_slot(e["timestamp"]) == min_slot for e in machine_events):
                candidate_hypothesis = "fixture_misalignment"
                fixture_event = [e for e in machine_events if e["event_type"] == "fixture_maintenance"][0]
                relevant_events = [fixture_event["event_id"]]

            # Check for tool wear drift (continuous drift bounded by tool changes)
            elif feature == "bore_diameter" and len(failing_slots) >= 3:
                tool_changes = [e for e in machine_events if e["event_type"] == "tool_change"]
                candidate_hypothesis = "tool_wear"
                relevant_events = [tc["event_id"] for tc in tool_changes]

            else:
                candidate_hypothesis = "isolated_outlier"
                relevant_events = []

        return {
            "report_id": report["report_id"],
            "machine": machine,
            "feature": feature,
            "failing_slots": failing_slots,
            "min_slot": min_slot,
            "max_slot": max_slot,
            "candidate_hypothesis": candidate_hypothesis,
            "candidate_event_ids": relevant_events,
            "correlated_events": correlated_events,
        }

    @staticmethod
    def _timestamp_to_slot(timestamp_str: str) -> int:
        """Convert ISO timestamp to part slot (10 minute intervals from 06:00)."""
        # Form: '2026-10-01T06:00'
        try:
            time_part = timestamp_str.split("T")[1]
            hours, minutes = map(int, time_part.split(":"))
            total_minutes = (hours - 6) * 60 + minutes
            return total_minutes // 10
        except Exception:
            return 0
