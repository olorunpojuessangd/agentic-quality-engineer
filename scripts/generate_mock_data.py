"""Generate a small synthetic CMM inspection dataset with planted root causes.

Outputs (deterministic, seed=42):
  data/mock_logs/measurements.csv   - one row per measured feature per part
  data/mock_logs/events.csv         - machine events (tool changes, alarms, maintenance)
  data/mock_logs/defect_reports.json- defect reports the pipeline must explain
  data/eval/ground_truth.json       - the planted answers (the pipeline must NEVER read this)

Planted scenarios:
  R1  CNC-2 bore diameter drifts undersize from tool wear; fixed by a tool change.
  R2  CNC-1 flatness fails right after a coolant temperature alarm (thermal).
  R3  CNC-1 hole position shifts after fixture maintenance (fixture misaligned).
  R4  One isolated CNC-1 bore failure with no supporting event (correct answer: no confident cause).
Distractors: a calibration on CNC-2 and shift changes on both machines, which affect nothing.
"""
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "data" / "mock_logs"
EVAL = ROOT / "data" / "eval"
rng = random.Random(42)

START = datetime(2026, 10, 1, 6, 0)
N_PARTS = 40
INTERVAL = timedelta(minutes=10)

# feature: (nominal, lower_tol, upper_tol) in mm
FEATURES = {
    "bore_diameter": (25.000, -0.015, 0.015),
    "flatness": (0.000, 0.0, 0.020),
    "hole_position": (0.000, 0.0, 0.050),
}

def ts(i):
    return (START + i * INTERVAL).strftime("%Y-%m-%dT%H:%M")

# --- events (index = part slot when the event happened) ---
event_specs = [
    (0,  "CNC-2", "tool_change",          "Boring bar T12 replaced"),
    (0,  "CNC-1", "tool_change",          "Boring bar T12 replaced"),
    (10, "CNC-2", "calibration",          "Spindle probe calibration completed"),
    (15, "CNC-1", "coolant_temp_alarm",   "Coolant temperature 31.4C exceeds 28.0C limit"),
    (20, "CNC-1", "coolant_temp_cleared", "Coolant temperature back to 24.9C"),
    (20, "CNC-1", "shift_change",         "Shift B start"),
    (20, "CNC-2", "shift_change",         "Shift B start"),
    (28, "CNC-1", "fixture_maintenance",  "Fixture F3 removed for cleaning and reinstalled"),
    (30, "CNC-2", "tool_change",          "Boring bar T12 replaced"),
]
events = []
for n, (i, machine, etype, detail) in enumerate(event_specs, start=1):
    events.append({"event_id": f"E{n:03d}", "slot": i, "timestamp": ts(i),
                   "machine": machine, "event_type": etype, "detail": detail})
ev = {(e["machine"], e["event_type"], e["slot"]): e["event_id"] for e in events}

def measure(machine, i, feature):
    """Return a measured value, applying any planted effect."""
    if feature == "bore_diameter":
        value = 25.000 + rng.gauss(0, 0.002)
        if machine == "CNC-2":
            since_change = i if i < 30 else i - 30
            value -= 0.0007 * since_change          # R1: tool wear drift
        if machine == "CNC-1" and i == 8:
            value = 25.0172                          # R4: isolated outlier
        return value
    if feature == "flatness":
        value = abs(rng.gauss(0.008, 0.002))
        if machine == "CNC-1" and 15 <= i < 20:
            value = 0.026 + rng.uniform(0, 0.006)    # R2: thermal
        return value
    if feature == "hole_position":
        value = abs(rng.gauss(0.015, 0.006))
        if machine == "CNC-1" and i >= 28:
            value = 0.060 + rng.uniform(0, 0.010)    # R3: fixture shift
        return value

# --- measurements ---
rows, m = [], 0
for i in range(N_PARTS):
    for machine in ("CNC-1", "CNC-2"):
        part_id = f"P-{machine[-1]}-{i:03d}"
        for feature, (nom, lo, hi) in FEATURES.items():
            m += 1
            val = round(measure(machine, i, feature), 4)
            ok = (nom + lo) <= val <= (nom + hi)
            rows.append({"measurement_id": f"M{m:04d}", "timestamp": ts(i), "machine": machine,
                         "part_id": part_id, "feature": feature, "nominal": nom,
                         "lower_tol": lo, "upper_tol": hi, "measured": val,
                         "result": "PASS" if ok else "FAIL"})

def fails(machine, feature, lo=0, hi=N_PARTS):
    return [r["part_id"] for r in rows if r["machine"] == machine and r["feature"] == feature
            and r["result"] == "FAIL" and lo <= int(r["part_id"][-3:]) < hi]

reports = [
    {"report_id": "R1", "machine": "CNC-2", "feature": "bore_diameter",
     "description": "Bore diameter undersize on several CNC-2 parts.", "part_ids": fails("CNC-2", "bore_diameter")},
    {"report_id": "R2", "machine": "CNC-1", "feature": "flatness",
     "description": "Flatness out of tolerance on a run of CNC-1 parts.", "part_ids": fails("CNC-1", "flatness")},
    {"report_id": "R3", "machine": "CNC-1", "feature": "hole_position",
     "description": "Hole position failures on recent CNC-1 parts.", "part_ids": fails("CNC-1", "hole_position")},
    {"report_id": "R4", "machine": "CNC-1", "feature": "bore_diameter",
     "description": "Single oversize bore on CNC-1.", "part_ids": fails("CNC-1", "bore_diameter")},
]
truth = [
    {"report_id": "R1", "root_cause": "tool_wear", "key_event_ids": [ev[("CNC-2", "tool_change", 0)], ev[("CNC-2", "tool_change", 30)]]},
    {"report_id": "R2", "root_cause": "thermal", "key_event_ids": [ev[("CNC-1", "coolant_temp_alarm", 15)], ev[("CNC-1", "coolant_temp_cleared", 20)]]},
    {"report_id": "R3", "root_cause": "fixture_misalignment", "key_event_ids": [ev[("CNC-1", "fixture_maintenance", 28)]]},
    {"report_id": "R4", "root_cause": "none", "key_event_ids": []},
]

# --- write ---
LOGS.mkdir(parents=True, exist_ok=True)
EVAL.mkdir(parents=True, exist_ok=True)
with open(LOGS / "measurements.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(rows)
with open(LOGS / "events.csv", "w", newline="") as f:
    fields = ["event_id", "timestamp", "machine", "event_type", "detail"]
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n"); w.writeheader(); w.writerows(events)
(LOGS / "defect_reports.json").write_text(json.dumps(reports, indent=2) + "\n")
(EVAL / "ground_truth.json").write_text(json.dumps(truth, indent=2) + "\n")

print(f"{len(rows)} measurements, {len(events)} events, {len(reports)} defect reports")
for r in reports:
    print(f"  {r['report_id']}: {len(r['part_ids'])} failing parts -> {r['part_ids']}")
unexplained = [r for r in rows if r["result"] == "FAIL"
               and not any(r["part_id"] in rep["part_ids"] and r["feature"] == rep["feature"] for rep in reports)]
print(f"failures not covered by any report: {len(unexplained)}")
