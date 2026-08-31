"""
Baseline solution: exactly what an unaided buyer would do today —
skim the README and top-level file listing, then ask one direct
question with no tools, no test runs, no history, no dependency check.

This intentionally represents "the manual process people use today"
(a quick eyeball review) so we can measure how much the full agent
pipeline actually improves on it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.common import call_claude_json, clone_repo

SYSTEM = """You are assessing a code repository for a potential buyer.
You only have the README and a top-level file listing. Respond with a
JSON object only:
{
  "quality_score": <1-10 integer>,
  "reasoning": "<2-4 sentences>",
  "recommendation": "<buy / renegotiate / walk away>"
}
No text outside the JSON."""


def run_baseline(repo_url: str, repo_name: str) -> dict:
    path = clone_repo(repo_url, repo_name)
    readme_text = ""
    for candidate in ["README.md", "README.rst", "README.txt", "readme.md"]:
        f = path / candidate
        if f.exists():
            readme_text = f.read_text(errors="ignore")[:6000]
            break

    top_level = sorted(p.name for p in path.iterdir() if not p.name.startswith(".git"))

    user_prompt = f"""Repository: {repo_name}

Top-level files/folders:
{top_level}

README contents:
{readme_text if readme_text else "(no README found)"}

Rate this repository's quality for an acquiring buyer."""

    result = call_claude_json(SYSTEM, user_prompt)
    result["repo_name"] = repo_name
    result["method"] = "baseline_single_prompt"
    return result


if __name__ == "__main__":
    import json
    if len(sys.argv) != 3:
        print("Usage: python baseline.py <repo_url> <repo_name>")
        sys.exit(1)
    out = run_baseline(sys.argv[1], sys.argv[2])
    print(json.dumps(out, indent=2))
