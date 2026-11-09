"""Pipeline runner: executes the autonomous quality engineer RAG pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from pipeline.data_loader import (
    load_defect_reports,
    load_events,
    load_ground_truth,
    load_measurements,
)
from pipeline.event_matcher import EventMatcher
from pipeline.exa_retriever import ExaRetriever
from agents.analyst import AnalystAgent
from agents.verifier import VerifierAgent

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "data" / "reports"


def run_pipeline(live_exa: bool = False, verbose: bool = True) -> List[Dict[str, Any]]:
    """Run the agentic root-cause analysis pipeline across all defect reports."""
    # 1. Load data
    measurements = load_measurements()
    events = load_events()
    defect_reports = load_defect_reports()

    # 2. Initialize components
    retriever = ExaRetriever(live=live_exa)
    matcher = EventMatcher(events=events, measurements=measurements)
    analyst = AnalystAgent()
    verifier = VerifierAgent(raw_events=events)

    results = []

    if verbose:
        retrieval_mode = "LIVE EXA API" if live_exa else "OFFLINE CACHE (Zero Cost)"
        print("=" * 72)
        print(" AGENTIC QUALITY ENGINEER - ROOT CAUSE RETRIEVAL PIPELINE")
        print(f" Retrieval Engine: Exa ({retrieval_mode})")
        print("=" * 72)

    for report in defect_reports:
        report_id = report["report_id"]

        # Step A: Event & measurement correlation
        correlation = matcher.correlate(report)

        # Step B: Exa external domain retrieval
        exa_retrieval = retriever.retrieve_for_defect(
            feature=report["feature"],
            hypothesis_key=correlation["candidate_hypothesis"],
            defect_description=report["description"],
        )

        # Step C: Analyst Agent synthesis
        analyst_proposal = analyst.analyze(
            defect_report=report,
            correlation=correlation,
            exa_retrieval=exa_retrieval,
        )

        # Step D: Verifier Agent validation loop
        verified_report = verifier.verify(
            defect_report=report,
            analyst_proposal=analyst_proposal,
        )

        verified_report["machine"] = report["machine"]
        verified_report["feature"] = report["feature"]
        verified_report["retrieval_source"] = exa_retrieval.get("source")
        results.append(verified_report)

        if verbose:
            print(f"\n[Defect {report_id}] {report['machine']} - {report['feature']}")
            print(f"  Description    : {report['description']}")
            print(f"  Failing parts  : {len(report['part_ids'])}")
            print(f"  Analyst Propose: {analyst_proposal['proposed_root_cause']}")
            print(f"  Verifier Call  : {verified_report['verdict']} -> {verified_report['root_cause']}")
            print(f"  Cited Events   : {verified_report['key_event_ids']}")
            ext_std = verified_report.get("external_standard", {})
            if ext_std.get("standard"):
                print(f"  Exa Reference  : {ext_std.get('standard')}")
                print(f"  Exa Source URL : {ext_std.get('url')}")
            print(f"  Notes          : {verified_report['verification_notes']}")

    # Save output reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = REPORTS_DIR / "latest_pipeline_run.json"
    out_file.write_text(json.dumps(results, indent=2) + "\n")

    return results


def evaluate_accuracy(results: List[Dict[str, Any]], verbose: bool = True) -> bool:
    """Evaluate pipeline predictions against planted ground truth."""
    ground_truth = load_ground_truth()
    truth_map = {item["report_id"]: item for item in ground_truth}

    correct_causes = 0
    correct_events = 0
    total = len(ground_truth)

    if verbose:
        print("\n" + "=" * 72)
        print(" EVALUATION BENCHMARK vs GROUND TRUTH")
        print("=" * 72)

    all_passed = True
    for res in results:
        rid = res["report_id"]
        truth = truth_map.get(rid, {})

        cause_match = (res["root_cause"] == truth.get("root_cause"))
        events_match = (sorted(res["key_event_ids"]) == sorted(truth.get("key_event_ids", [])))

        if cause_match:
            correct_causes += 1
        if events_match:
            correct_events += 1

        if not (cause_match and events_match):
            all_passed = False

        status = "PASSED" if (cause_match and events_match) else "FAILED"
        if verbose:
            print(f"[{status}] Report {rid}:")
            print(f"   Root Cause: predicted='{res['root_cause']}' | truth='{truth.get('root_cause')}'")
            print(f"   Events    : predicted={res['key_event_ids']} | truth={truth.get('key_event_ids')}")

    if verbose:
        print("-" * 72)
        print(f" Root Cause Accuracy : {correct_causes}/{total} ({correct_causes/total*100:.1f}%)")
        print(f" Event Citation Acc  : {correct_events}/{total} ({correct_events/total*100:.1f}%)")
        print("=" * 72)

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Run Agentic Quality Engineer Pipeline")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live Exa API retrieval (requires EXA_API_KEY). Default is offline cache ($0).",
    )
    args = parser.parse_args()

    results = run_pipeline(live_exa=args.live, verbose=True)
    all_passed = evaluate_accuracy(results, verbose=True)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
