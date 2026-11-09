"""Unit and integration tests for Agentic Quality Engineer."""
import pytest
from pipeline.data_loader import (
    load_defect_reports,
    load_events,
    load_ground_truth,
    load_measurements,
    get_part_slot,
)
from pipeline.exa_retriever import ExaRetriever
from pipeline.event_matcher import EventMatcher
from agents.analyst import AnalystAgent
from agents.verifier import VerifierAgent
from pipeline.runner import run_pipeline, evaluate_accuracy


def test_data_loader():
    measurements = load_measurements()
    events = load_events()
    reports = load_defect_reports()
    truth = load_ground_truth()

    assert len(measurements) > 0
    assert len(events) == 9
    assert len(reports) == 4
    assert len(truth) == 4
    assert get_part_slot("P-2-024") == 24


def test_exa_retriever_offline_cache():
    retriever = ExaRetriever(live=False)
    res = retriever.retrieve_for_defect("bore_diameter", "tool_wear", "bore undersize")

    assert res["source"] == "offline_cache"
    assert res["cost_cents"] == 0.0
    assert len(res["results"]) > 0
    assert "ISO 3685" in res["results"][0]["standard_reference"]


def test_end_to_end_pipeline_ground_truth():
    """Verify that all 4 planted scenarios match ground truth with zero external cost."""
    results = run_pipeline(live_exa=False, verbose=False)
    assert len(results) == 4
    assert evaluate_accuracy(results, verbose=False) is True


def test_verifier_rejects_hallucinated_event():
    """Ensure verifier rejects analyst claims citing non-existent event IDs."""
    events = load_events()
    verifier = VerifierAgent(raw_events=events)

    fake_report = {
        "report_id": "R99",
        "machine": "CNC-1",
        "feature": "flatness",
        "part_ids": ["P-1-001", "P-1-002"],
    }
    fake_proposal = {
        "proposed_root_cause": "thermal",
        "cited_event_ids": ["E999"],  # Does not exist
    }

    verified = verifier.verify(fake_report, fake_proposal)
    assert verified["verdict"] == "REJECTED_UNSUPPORTED"
    assert verified["root_cause"] == "none"
    assert verified["key_event_ids"] == []


def test_verifier_abstains_on_isolated_outlier():
    """Ensure verifier abstains when part count is isolated (R4 scenario)."""
    events = load_events()
    verifier = VerifierAgent(raw_events=events)

    r4_report = {
        "report_id": "R4",
        "machine": "CNC-1",
        "feature": "bore_diameter",
        "part_ids": ["P-1-008"],
    }
    r4_proposal = {
        "proposed_root_cause": "none",
        "cited_event_ids": [],
    }

    verified = verifier.verify(r4_report, r4_proposal)
    assert verified["verdict"] == "SUPPORTED_ABSTAIN"
    assert verified["root_cause"] == "none"
    assert verified["key_event_ids"] == []
