
import argparse
import sys
from pathlib import Path

from src.pipeline import run_pipeline, write_results


def main() -> int:
    parser = argparse.ArgumentParser(description="Screen and rank resumes for a Python + AI SDE internship.")
    parser.add_argument("--input", required=True, type=Path, help="folder containing resume PDFs")
    parser.add_argument("--output", type=Path, default=Path("output/results.json"))
    parser.add_argument("--no-github", action="store_true", help="skip GitHub enrichment")
    parser.add_argument("--no-llm", action="store_true", help="skip the optional LLM review")
    args = parser.parse_args()

    try:
        results = run_pipeline(args.input, use_github=not args.no_github, use_llm=not args.no_llm)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    write_results(results, args.output)

    s = results["batch_summary"]
    print(f"Resumes: {s['total_resumes']} | parsed: {s['successfully_parsed']} | eligible: {s['eligible']} | "
          f"rejected: {s['rejected']} | failed: {s['failed_or_unreadable']} | duplicates: {s['duplicates_skipped']}")
    for c in results["ranked_candidates"]:
        print(f"  #{c['rank']:<3} {c['total_score']:>3}  {c['candidate_name']}  ({c['file_name']})")
    print(f"Results written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())