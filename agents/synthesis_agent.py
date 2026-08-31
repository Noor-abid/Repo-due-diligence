"""
Synthesis Agent
---------------
Takes the raw findings from Code&Test, History, and Dependency agents and
writes a buyer-facing due-diligence report. Includes a verification pass:
a second Claude call checks the draft report only makes claims that are
backed by the actual findings dict, catching hallucinated specifics before
the report reaches the user (the "verification" capability from the brief).

Also produces a single quality_score (1-10) and ranking rationale so this
plugs directly into the same evaluation used for the baseline.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.common import call_claude, call_claude_json, save_trajectory

REPORT_SYSTEM = """You are a senior technical due-diligence analyst writing a
report for a non-technical buyer deciding whether to acquire a codebase.
You are given structured findings from three specialist agents (test
execution, git history mining, dependency audit). Write ONLY from these
findings — do not invent details not present in the data.
Keep the "summary" field to 3-5 sentences and each item in "key_risks" and "requires_human_review" to one concise sentence. 
Do not exceed these limits — the output must be complete, valid JSON.

Output a JSON object with exactly these fields:
{
  "quality_score": <1-10 integer>,
  "recommendation": "<buy / renegotiate / walk away>",
  "summary": "<3-5 sentence plain-English summary for a non-technical buyer>",
  "key_risks": ["<risk 1>", "<risk 2>", ...],
  "requires_human_review": ["<specific item a qualified engineer should verify before signing>", ...]
}
No text outside the JSON."""

VERIFY_SYSTEM = """You are a fact-checker. You will be given a JSON report
and the raw findings it was based on. Check whether every specific claim
in the report (numbers, pass/fail statements, risk counts) is actually
supported by the raw findings. Respond with JSON only:
{
  "all_claims_supported": <true/false>,
  "unsupported_claims": ["<claim text>", ...],
  "notes": "<brief explanation>"
}"""


def synthesize(repo_name: str, code_findings: dict, history_findings: dict,
                dependency_findings: dict) -> dict:
    trajectory = []
    combined = {
        "code_and_tests": code_findings,
        "git_history": history_findings,
        "dependencies": dependency_findings,
    }
    trajectory.append({"step": "combine_findings", "input": combined})

    user_prompt = f"Repository: {repo_name}\n\nFindings:\n{json.dumps(combined, indent=2)}"
    report = call_claude_json(REPORT_SYSTEM, user_prompt, max_tokens=3000)
    trajectory.append({"step": "generate_draft_report", "result": report})

    # Verification pass: catch unsupported/hallucinated claims before returning
    verify_prompt = (
        f"Raw findings:\n{json.dumps(combined, indent=2)}\n\n"
        f"Report to check:\n{json.dumps(report, indent=2)}"
    )
    verification = call_claude_json(VERIFY_SYSTEM, verify_prompt, max_tokens=1500)
    trajectory.append({"step": "verify_report", "result": verification})

    if not verification.get("all_claims_supported", True):
        # Regenerate once, explicitly telling the model what it got wrong
        fix_prompt = (
            user_prompt
            + f"\n\nYour previous draft made unsupported claims: "
              f"{verification.get('unsupported_claims')}. "
              f"Rewrite the report using ONLY what the findings actually support."
        )
        report = call_claude_json(REPORT_SYSTEM, fix_prompt, max_tokens=3000)
        trajectory.append({"step": "regenerate_after_verification_failure", "result": report})

    report["repo_name"] = repo_name
    report["method"] = "agent_pipeline"
    report["verification_passed"] = verification.get("all_claims_supported", None)

    save_trajectory("synthesis_agent", repo_name, trajectory)
    return report


if __name__ == "__main__":
    print("This agent is meant to be called from eval/run_eval.py after the "
          "other three agents produce findings. See run_eval.py for usage.")
