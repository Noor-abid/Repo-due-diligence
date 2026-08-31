"""
Dependency Agent
----------------
Checks the project's actual dependencies for known vulnerabilities and
staleness — signals that don't show up anywhere in a README but directly
affect maintenance cost and risk for a buyer.

Node: uses `npm audit --json` (real vulnerability DB).
Python: compares pinned versions in requirements.txt/pyproject.toml
against the latest version on PyPI to flag staleness (a lightweight,
dependency-free proxy for "is this actively maintained upstream").
"""
import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.common import run_cmd, save_trajectory, clone_repo


def _latest_pypi_version(pkg: str) -> str | None:
    try:
        resp = requests.get(f"https://pypi.org/pypi/{pkg}/json", timeout=10)
        if resp.status_code == 200:
            return resp.json()["info"]["version"]
    except requests.RequestException:
        pass
    return None


def analyze(repo_url: str, repo_name: str) -> dict:
    path = clone_repo(repo_url, repo_name)
    trajectory = []
    findings = {"repo_name": repo_name, "ecosystem": None,
                "vulnerabilities": None, "stale_packages": []}

    if (path / "package.json").exists():
        findings["ecosystem"] = "npm"
        install = run_cmd(["npm", "install", "--silent", "--no-audit=false"], path, timeout=180)
        trajectory.append({"step": "npm_install", "returncode": install["returncode"]})
        audit = run_cmd(["npm", "audit", "--json"], path, timeout=120)
        trajectory.append({"step": "npm_audit", "returncode": audit["returncode"]})
        try:
            audit_data = json.loads(audit["stdout"])
            meta = audit_data.get("metadata", {}).get("vulnerabilities", {})
            findings["vulnerabilities"] = meta
        except (json.JSONDecodeError, KeyError):
            findings["vulnerabilities"] = {"parse_error": True}

    elif (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        findings["ecosystem"] = "pip"
        req_text = ""
        source_file = None
        if (path / "requirements.txt").exists():
            req_text = (path / "requirements.txt").read_text(errors="ignore")
            source_file = "requirements.txt"
        elif (path / "pyproject.toml").exists():
            req_text = (path / "pyproject.toml").read_text(errors="ignore")
            source_file = "pyproject.toml"
        # Matches both "pkg==1.2.3" (requirements.txt) and "pkg>=1.2.3" /
        # "pkg (==1.2.3)" style pins that show up in pyproject.toml dependency lists.
        pinned = re.findall(
            r"([A-Za-z0-9_\-\.]+)\s*(?:==|>=)\s*([A-Za-z0-9_\-\.]+)", req_text
        )
        trajectory.append({"step": "parse_dependency_manifest", "source_file": source_file,
                            "pinned_count": len(pinned)})
        stale = []
        for pkg, version in pinned[:25]:  # cap to keep runtime reasonable
            latest = _latest_pypi_version(pkg)
            if latest and latest != version:
                stale.append({"package": pkg, "pinned": version, "latest": latest})
        trajectory.append({"step": "check_pypi_staleness", "stale_found": len(stale)})
        findings["stale_packages"] = stale
    else:
        findings["ecosystem"] = "unknown"
        trajectory.append({"step": "no_dependency_manifest_found"})

    save_trajectory("dependency_agent", repo_name, trajectory)
    return findings


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python dependency_agent.py <repo_url> <repo_name>")
        sys.exit(1)
    print(json.dumps(analyze(sys.argv[1], sys.argv[2]), indent=2))
