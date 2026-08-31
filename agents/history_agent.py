"""
History Agent
-------------
Mines git history directly (not just what the README claims) to surface
risk signals a buyer cares about: bus factor, commit recency/frequency,
and any red-flag commit messages (reverts, hotfixes, "temporary" hacks
that stuck around). This is the "memory / longitudinal context" piece —
judging quality requires looking across the whole history, not a snapshot.
"""
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.common import run_cmd, save_trajectory, clone_repo

RED_FLAG_TERMS = ["revert", "hotfix", "temporary", "hack", "workaround", "fixme", "todo: remove"]


def analyze(repo_url: str, repo_name: str) -> dict:
    path = clone_repo(repo_url, repo_name)
    trajectory = []

    log = run_cmd(
        ["git", "log", "--pretty=format:%H|%an|%ad|%s", "--date=iso-strict"], path
    )
    trajectory.append({"step": "git_log", "returncode": log["returncode"]})

    # Direct cross-check: ask git for the tip commit's date on its own, independent
    # of parsing the full log below. Using this as the authoritative "last commit"
    # figure avoids bugs from parsing/max()-ing potentially malformed timestamps
    # elsewhere in history (some repos, e.g. psf/requests, have known bad timezone
    # data on older commits — see their own README's fetch.fsck.badTimezone note).
    tip_result = run_cmd(["git", "log", "-1", "--format=%cI"], path)
    tip_date_str = tip_result["stdout"].strip()
    trajectory.append({"step": "git_tip_commit_date_check", "raw_value": tip_date_str})

    lines = [l for l in log["stdout"].splitlines() if l.strip()]
    authors = Counter()
    dates = []
    red_flags = []

    for line in lines:
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        _, author, date_str, subject = parts
        authors[author] += 1
        try:
            dates.append(datetime.fromisoformat(date_str.strip()))
        except ValueError:
            pass
        if any(term in subject.lower() for term in RED_FLAG_TERMS):
            red_flags.append(subject.strip())

    total_commits = sum(authors.values())
    top_author_share = (authors.most_common(1)[0][1] / total_commits) if total_commits else 0
    bus_factor = sum(
        1 for _, count in authors.most_common()
        if count / total_commits >= 0.1
    ) if total_commits else 0

    last_commit_days_ago = None
    if dates:
        latest = max(dates)
        now = datetime.now(tz=latest.tzinfo) if latest.tzinfo else datetime.now()
        last_commit_days_ago = (now - latest).days

    # Use the direct git tip-commit date as authoritative if it parses and
    # disagrees meaningfully with the max()-over-full-log figure above —
    # protects against malformed timestamps elsewhere in history skewing the result.
    tip_days_ago = None
    if tip_date_str:
        try:
            tip_date = datetime.fromisoformat(tip_date_str)
            now = datetime.now(tz=tip_date.tzinfo) if tip_date.tzinfo else datetime.now()
            tip_days_ago = (now - tip_date).days
        except ValueError:
            pass
    if tip_days_ago is not None:
        if last_commit_days_ago is None or abs(tip_days_ago - last_commit_days_ago) > 2:
            trajectory.append({
                "step": "date_discrepancy_detected",
                "max_over_log": last_commit_days_ago,
                "direct_tip_check": tip_days_ago,
                "resolution": "using direct tip check as authoritative",
            })
        last_commit_days_ago = tip_days_ago

    trajectory.append({
        "step": "compute_stats",
        "total_commits": total_commits,
        "unique_authors": len(authors),
        "top_author_share": round(top_author_share, 2),
        "red_flag_count": len(red_flags),
    })

    findings = {
        "repo_name": repo_name,
        "total_commits": total_commits,
        "unique_authors": len(authors),
        "top_author_commit_share": round(top_author_share, 2),
        "bus_factor_estimate": bus_factor or (1 if total_commits else 0),
        "last_commit_days_ago": last_commit_days_ago,
        "red_flag_commits_sample": red_flags[:10],
        "red_flag_count": len(red_flags),
    }

    save_trajectory("history_agent", repo_name, trajectory)
    return findings


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python history_agent.py <repo_url> <repo_name>")
        sys.exit(1)
    print(json.dumps(analyze(sys.argv[1], sys.argv[2]), indent=2))
