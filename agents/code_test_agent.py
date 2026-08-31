"""
Code & Test Agent
------------------
Tool-using agent step. Actually executes commands against the repo instead
of guessing from text: detects the project type, tries to install deps,
runs the test suite, and reports real pass/fail evidence.

This is the "give the agent better tools" capability from the brief —
ground truth from execution beats guessing from a README every time.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.common import run_cmd, save_trajectory, clone_repo


def detect_project_type(path: Path) -> str:
    if (path / "package.json").exists():
        return "node"
    if (path / "pyproject.toml").exists() or (path / "requirements.txt").exists():
        return "python"
    if (path / "Cargo.toml").exists():
        return "rust"
    if (path / "go.mod").exists():
        return "go"
    return "unknown"


def analyze(repo_url: str, repo_name: str) -> dict:
    path = clone_repo(repo_url, repo_name)
    trajectory = []
    ptype = detect_project_type(path)
    trajectory.append({"step": "detect_project_type", "result": ptype})

    findings = {"project_type": ptype, "build": None, "tests": None, "has_ci": False}

    ci_paths = [".github/workflows", ".gitlab-ci.yml", ".circleci/config.yml"]
    findings["has_ci"] = any((path / p).exists() for p in ci_paths)
    trajectory.append({"step": "check_ci", "result": findings["has_ci"]})

    if ptype == "python":
        install = run_cmd(
            ["pip", "install", "-e", ".", "--break-system-packages", "-q"], path, timeout=180
        )
        trajectory.append({"step": "pip_install", "result": install})
        # Ensure a test runner exists even if the repo's own env doesn't ship one —
        # otherwise "no module named pytest" gets misread as "tests fail".
        ensure_pytest = run_cmd(
            ["pip", "install", "pytest", "--break-system-packages", "-q"], path, timeout=60
        )
        trajectory.append({"step": "ensure_pytest_available", "result": ensure_pytest})
        test = run_cmd(["python", "-m", "pytest", "--tb=short", "-q"], path, timeout=180)
        trajectory.append({"step": "run_pytest", "result": test})
        findings["tests"] = {
            "ran": not test["timed_out"] and test["returncode"] is not None,
            "passed": test["returncode"] == 0,
            "summary": test["stdout"][-800:] or test["stderr"][-800:],
        }

    elif ptype == "node":
        install = run_cmd(["npm", "install", "--silent"], path, timeout=180)
        trajectory.append({"step": "npm_install", "result": install})
        test = run_cmd(["npm", "test", "--silent"], path, timeout=180)
        trajectory.append({"step": "npm_test", "result": test})
        findings["tests"] = {
            "ran": not test["timed_out"] and test["returncode"] is not None,
            "passed": test["returncode"] == 0,
            "summary": test["stdout"][-800:] or test["stderr"][-800:],
        }
    else:
        findings["tests"] = {"ran": False, "passed": None,
                              "summary": f"No automated test runner wired up for project type '{ptype}'."}
        trajectory.append({"step": "skip_tests", "reason": f"unsupported project type: {ptype}"})

    save_trajectory("code_test_agent", repo_name, trajectory)
    findings["repo_name"] = repo_name
    return findings


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python code_test_agent.py <repo_url> <repo_name>")
        sys.exit(1)
    print(json.dumps(analyze(sys.argv[1], sys.argv[2]), indent=2))
