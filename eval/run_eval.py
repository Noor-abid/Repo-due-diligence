"""
Evaluation harness.

Runs the baseline AND the full agent pipeline on the same set of repos
(defined in repos.json), then compares each method's ranking against
your human ranking using Spearman rank correlation.

Usage:
    export GEMINI_API_KEY=your-key-here
    python eval/run_eval.py

Outputs:
    reports/<repo_name>_baseline.json
    reports/<repo_name>_agent.json
    reports/eval_summary.json   <- final metric table for the writeup
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baseline.baseline import run_baseline
from agents.code_test_agent import analyze as run_code_test_agent
from agents.history_agent import analyze as run_history_agent
from agents.dependency_agent import analyze as run_dependency_agent
from agents.synthesis_agent import synthesize

REPORTS_DIR = ROOT / "reports"


def spearman(rank_a: list[float], rank_b: list[float]) -> float:
    """Plain-Python Spearman rank correlation (no scipy dependency)."""
    n = len(rank_a)
    if n < 2:
        return float("nan")

    def to_ranks(values):
        sorted_idx = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        for rank, idx in enumerate(sorted_idx, start=1):
            ranks[idx] = rank
        return ranks

    ra, rb = to_ranks(rank_a), to_ranks(rank_b)
    d_sq_sum = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1 - (6 * d_sq_sum) / (n * (n**2 - 1))


def run_agent_pipeline(repo_url: str, repo_name: str) -> dict:
    code_findings = run_code_test_agent(repo_url, repo_name)
    history_findings = run_history_agent(repo_url, repo_name)
    dependency_findings = run_dependency_agent(repo_url, repo_name)
    report = synthesize(repo_name, code_findings, history_findings, dependency_findings)
    return report


def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    repos_config = json.loads((ROOT / "eval" / "repos.json").read_text())
    repos = repos_config["repos"]

    if any(r["human_rank"] is None for r in repos):
        print("WARNING: some repos have human_rank=null. Fill these in eval/repos.json "
              "(see eval/rubric.md) before trusting the correlation numbers below.\n")

    baseline_results, agent_results = [], []

    for repo in repos:
        name, url = repo["repo_name"], repo["repo_url"]
        print(f"\n=== {name} ===")

        print("  running baseline...")
        t0 = time.time()
        b = run_baseline(url, name)
        b["runtime_sec"] = round(time.time() - t0, 1)
        (REPORTS_DIR / f"{name}_baseline.json").write_text(json.dumps(b, indent=2))
        baseline_results.append(b)

        print("  running agent pipeline...")
        t0 = time.time()
        a = run_agent_pipeline(url, name)
        a["runtime_sec"] = round(time.time() - t0, 1)
        (REPORTS_DIR / f"{name}_agent.json").write_text(json.dumps(a, indent=2))
        agent_results.append(a)

        time.sleep(5)  # brief pause between repos to stay under per-minute rate limits

    human_ranks = [r["human_rank"] for r in repos]
    baseline_scores = [-b["quality_score"] for b in baseline_results]  # negate: higher score = better rank
    agent_scores = [-a["quality_score"] for a in agent_results]

    summary = {
        "n_repos": len(repos),
        "baseline_spearman_vs_human": None,
        "agent_spearman_vs_human": None,
        "baseline_avg_runtime_sec": round(sum(b["runtime_sec"] for b in baseline_results) / len(baseline_results), 1),
        "agent_avg_runtime_sec": round(sum(a["runtime_sec"] for a in agent_results) / len(agent_results), 1),
        "per_repo": [
            {
                "repo_name": r["repo_name"],
                "human_rank": r["human_rank"],
                "is_trap": r.get("is_trap", False),
                "baseline_score": b["quality_score"],
                "agent_score": a["quality_score"],
                "agent_verification_passed": a.get("verification_passed"),
            }
            for r, b, a in zip(repos, baseline_results, agent_results)
        ],
    }

    if all(h is not None for h in human_ranks):
        summary["baseline_spearman_vs_human"] = round(spearman(human_ranks, baseline_scores), 3)
        summary["agent_spearman_vs_human"] = round(spearman(human_ranks, agent_scores), 3)

    (REPORTS_DIR / "eval_summary.json").write_text(json.dumps(summary, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"\nFull results written to {REPORTS_DIR}/")


if __name__ == "__main__":
    main()
