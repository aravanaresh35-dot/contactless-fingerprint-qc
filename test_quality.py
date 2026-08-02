"""
test_quality.py
================

Batch evaluation script for the contactless fingerprint QC pipeline.

Runs ``quality_gate`` against every image in ``test_dataset/<category>/``,
compares the pipeline's pass/fail decision against the expected category
label implied by the folder name, and writes a summary report to
``test_results.csv``.

Usage
-----
    python test_quality.py
    python test_quality.py --dataset-dir test_dataset --output test_results.csv
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import time

import pandas as pd

from quality_assessment import quality_gate

# Categories where the expected outcome is a PASS vs a REJECT, used purely
# for the human-readable accuracy summary printed at the end of the run.
EXPECTED_PASS = {"good": True, "blurry": False, "dark": False, "glare": False}


def run_batch_tests(dataset_dir: str = "test_dataset", output_csv: str = "test_results.csv") -> pd.DataFrame:
    """
    Evaluate every image under ``dataset_dir`` and write results to CSV.

    Parameters
    ----------
    dataset_dir : str
        Root directory containing one sub-folder per condition category.
    output_csv : str
        Destination path for the CSV summary report.

    Returns
    -------
    pd.DataFrame
        The full results table (also written to disk).
    """
    image_paths = sorted(
        glob.glob(os.path.join(dataset_dir, "*", "*.jpg"))
        + glob.glob(os.path.join(dataset_dir, "*", "*.jpeg"))
        + glob.glob(os.path.join(dataset_dir, "*", "*.png"))
    )

    if not image_paths:
        print(
            f"No images found under '{dataset_dir}/'. "
            "Run 'python generate_dummy_dataset.py' first, or add real "
            "smartphone captures to the category sub-folders."
        )
        sys.exit(1)

    records = []
    for path in image_paths:
        folder_category = os.path.basename(os.path.dirname(path))
        filename = os.path.basename(path)

        start = time.perf_counter()
        try:
            res = quality_gate(path)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            error = ""
        except ValueError as exc:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            print(f"[WARN] Failed to process '{path}': {exc}")
            records.append(
                {
                    "File": filename,
                    "Expected Category": folder_category,
                    "Passed": False,
                    "Composite Score": 0.0,
                    "Blur Score": None,
                    "Brightness": None,
                    "Glare Fraction": None,
                    "ROI Fraction": None,
                    "Ridge Score": None,
                    "Latency (ms)": elapsed_ms,
                    "Guidance": f"ERROR: {exc}",
                }
            )
            continue

        expected_pass = EXPECTED_PASS.get(folder_category)
        correctly_classified = (
            (res["passed"] == expected_pass) if expected_pass is not None else None
        )

        records.append(
            {
                "File": filename,
                "Expected Category": folder_category,
                "Passed": res["passed"],
                "Expected Pass": expected_pass,
                "Correctly Classified": correctly_classified,
                "Composite Score": res["composite_score"],
                "Blur Score": res["blur"]["blur_score"],
                "Brightness": res["brightness"]["brightness"],
                "Glare Fraction": res["glare"]["glare_fraction"],
                "ROI Fraction": res["roi"]["roi_fraction"],
                "Ridge Score": res["ridge"]["ridge_score"],
                "Latency (ms)": elapsed_ms,
                "Guidance": res["guidance"],
            }
        )

    df = pd.DataFrame(records)

    print("\n================ QUALITY CONTROL BATCH EVALUATION ================\n")
    print(df.to_string(index=False))

    if "Correctly Classified" in df.columns:
        valid = df["Correctly Classified"].dropna()
        if len(valid):
            accuracy = 100.0 * valid.sum() / len(valid)
            print(f"\nClassification accuracy vs. expected category label: {accuracy:.1f}%")

    if "Latency (ms)" in df.columns:
        avg_latency = df["Latency (ms)"].mean()
        print(f"Average pipeline latency: {avg_latency:.2f} ms (budget: 300 ms)")

    df.to_csv(output_csv, index=False)
    print(f"\nResults written to '{output_csv}'.")
    return df


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch-test the fingerprint QC pipeline.")
    parser.add_argument(
        "--dataset-dir", default="test_dataset", help="Root directory of test images."
    )
    parser.add_argument(
        "--output", default="test_results.csv", help="Path to write the CSV report."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_batch_tests(dataset_dir=args.dataset_dir, output_csv=args.output)
