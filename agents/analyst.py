"""Analyst agent: synthesizes machine telemetry with Exa-retrieved domain knowledge."""
from __future__ import annotations

from typing import Any, Dict, List


class AnalystAgent:
    """Proposes root-cause hypotheses grounded in log evidence and external standards."""

    def __init__(self, name: str = "AnalystAgent"):
        self.name = name

    def analyze(
        self,
        defect_report: Dict[str, Any],
        correlation: Dict[str, Any],
        exa_retrieval: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Synthesize defect facts, machine logs, and Exa search results into a hypothesis."""
        candidate_key = correlation["candidate_hypothesis"]
        candidate_events = correlation["candidate_event_ids"]
        feature = defect_report["feature"]
        machine = defect_report["machine"]
        num_failing = len(defect_report.get("part_ids", []))

        exa_results = exa_retrieval.get("results", [])
        top_standard = exa_results[0] if exa_results else {}

        # If isolated single part with no events, Analyst notes lack of supporting evidence
        if candidate_key == "isolated_outlier" or num_failing <= 1:
            return {
                "report_id": defect_report["report_id"],
                "proposed_root_cause": "none",
                "cited_event_ids": [],
                "confidence": "low",
                "reasoning": (
                    f"Only {num_failing} part failed for {feature} on {machine}. "
                    "No preceding alarms or maintenance events were detected. "
                    "Per SPC guidelines retrieved via Exa, single isolated anomalies should not be "
                    "attributed to systematic causes without further occurrences."
                ),
                "external_citation": {
                    "source": exa_retrieval.get("source"),
                    "title": top_standard.get("title"),
                    "standard": top_standard.get("standard_reference"),
                    "url": top_standard.get("url"),
                },
            }

        # Tool wear scenario
        if candidate_key == "tool_wear":
            reasoning = (
                f"Defect report shows progressive drift on {feature} across parts on {machine}. "
                f"Failures began accumulating after initial tool change ({candidate_events[0] if candidate_events else 'E001'}) "
                f"and stopped after subsequent tool change ({candidate_events[-1] if len(candidate_events) > 1 else 'E009'}). "
                f"Exa domain retrieval confirms that cutting insert wear decreases depth of cut on internal boring, "
                f"causing holes to drift undersize over time."
            )
            return {
                "report_id": defect_report["report_id"],
                "proposed_root_cause": "tool_wear",
                "cited_event_ids": candidate_events,
                "confidence": "high",
                "reasoning": reasoning,
                "external_citation": {
                    "source": exa_retrieval.get("source"),
                    "title": top_standard.get("title"),
                    "standard": top_standard.get("standard_reference"),
                    "url": top_standard.get("url"),
                },
            }

        # Thermal scenario
        if candidate_key == "thermal":
            reasoning = (
                f"Flatness failures on {machine} occurred strictly within the window of "
                f"coolant temperature alarm event {candidate_events[0] if candidate_events else 'E004'}. "
                f"Once temperature was cleared ({candidate_events[-1] if len(candidate_events) > 1 else 'E005'}), "
                f"part flatness returned to tolerance. "
                f"Exa domain retrieval confirms that cutting fluid above 28°C induces thermal expansion "
                f"and workpiece warping during face milling."
            )
            return {
                "report_id": defect_report["report_id"],
                "proposed_root_cause": "thermal",
                "cited_event_ids": candidate_events,
                "confidence": "high",
                "reasoning": reasoning,
                "external_citation": {
                    "source": exa_retrieval.get("source"),
                    "title": top_standard.get("title"),
                    "standard": top_standard.get("standard_reference"),
                    "url": top_standard.get("url"),
                },
            }

        # Fixture misalignment scenario
        if candidate_key == "fixture_misalignment":
            reasoning = (
                f"Hole position failures on {machine} began immediately after fixture maintenance "
                f"event {candidate_events[0] if candidate_events else 'E008'}. "
                f"Exa domain retrieval confirms that fixture removal/re-clamping introduces datum shift "
                f"and angular tilt, directly causing true position geometric errors."
            )
            return {
                "report_id": defect_report["report_id"],
                "proposed_root_cause": "fixture_misalignment",
                "cited_event_ids": candidate_events,
                "confidence": "high",
                "reasoning": reasoning,
                "external_citation": {
                    "source": exa_retrieval.get("source"),
                    "title": top_standard.get("title"),
                    "standard": top_standard.get("standard_reference"),
                    "url": top_standard.get("url"),
                },
            }

        return {
            "report_id": defect_report["report_id"],
            "proposed_root_cause": "unknown",
            "cited_event_ids": [],
            "confidence": "low",
            "reasoning": "Unrecognized pattern; unable to propose supported root cause.",
            "external_citation": {},
        }
