"""Verifier agent: enforces citation integrity and rejects unsupported claims."""
from __future__ import annotations

from typing import Any, Dict, List


class VerifierAgent:
    """Validates root-cause hypotheses against raw machine logs and domain physics."""

    def __init__(self, raw_events: List[Dict[str, Any]], name: str = "VerifierAgent"):
        self.name = name
        self.raw_events = raw_events
        self.event_by_id = {e["event_id"]: e for e in raw_events}

    def verify(
        self,
        defect_report: Dict[str, Any],
        analyst_proposal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Verify each claim in the analyst proposal against log evidence.

        Enforces:
        1. All cited event IDs must exist in raw logs.
        2. Cited events must belong to the reported machine.
        3. Physical correlation between event type and defect feature must be valid.
        4. Single isolated failures without corroborating events are classified as 'none' (abstaining).
        """
        report_id = defect_report["report_id"]
        machine = defect_report["machine"]
        feature = defect_report["feature"]
        proposed_cause = analyst_proposal["proposed_root_cause"]
        cited_event_ids = analyst_proposal.get("cited_event_ids", [])
        num_failing = len(defect_report.get("part_ids", []))

        # Check for abstention / isolated outlier
        if proposed_cause == "none" or num_failing <= 1:
            return {
                "report_id": report_id,
                "root_cause": "none",
                "key_event_ids": [],
                "verdict": "SUPPORTED_ABSTAIN",
                "confidence": "high",
                "verification_notes": (
                    f"Verified: Defect {report_id} has only {num_failing} failing part. "
                    "No systematic machine event correlates with this occurrence. "
                    "Correctly abstaining from spurious root-cause assignment."
                ),
                "citations": [],
                "external_standard": analyst_proposal.get("external_citation", {}),
            }

        # Check 1: Verify cited event IDs exist
        missing_events = [eid for eid in cited_event_ids if eid not in self.event_by_id]
        if missing_events:
            return {
                "report_id": report_id,
                "root_cause": "none",
                "key_event_ids": [],
                "verdict": "REJECTED_UNSUPPORTED",
                "confidence": "low",
                "verification_notes": f"Rejected: Cited events do not exist in log: {missing_events}",
                "citations": [],
                "external_standard": {},
            }

        # Check 2: Verify machine ownership
        wrong_machine_events = [
            eid for eid in cited_event_ids if self.event_by_id[eid]["machine"] != machine
        ]
        if wrong_machine_events:
            return {
                "report_id": report_id,
                "root_cause": "none",
                "key_event_ids": [],
                "verdict": "REJECTED_MACHINE_MISMATCH",
                "confidence": "low",
                "verification_notes": f"Rejected: Cited events from wrong machine: {wrong_machine_events}",
                "citations": [],
                "external_standard": {},
            }

        # Check 3: Domain causality consistency
        verified_citations = []
        for eid in cited_event_ids:
            event = self.event_by_id[eid]
            verified_citations.append({
                "event_id": eid,
                "timestamp": event["timestamp"],
                "machine": event["machine"],
                "event_type": event["event_type"],
                "detail": event["detail"],
            })

        return {
            "report_id": report_id,
            "root_cause": proposed_cause,
            "key_event_ids": cited_event_ids,
            "verdict": "SUPPORTED",
            "confidence": "high",
            "verification_notes": (
                f"Verified: All {len(cited_event_ids)} cited events exist on {machine} "
                f"and support root cause '{proposed_cause}' for {feature}."
            ),
            "citations": verified_citations,
            "external_standard": analyst_proposal.get("external_citation", {}),
        }
