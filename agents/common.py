"""Shared utilities used by all agents: repo cloning, LLM calls, JSON parsing.

Uses Google's Gemini API (via its OpenAI-compatible endpoint) so the project
can run entirely on Google AI Studio's free, no-credit-card tier. Function
names are kept as call_claude / call_claude_json for compatibility with the
rest of the codebase, even though they now call Gemini under the hood.
"""
import os
import json
import subprocess
import shutil
import time
from pathlib import Path

from openai import OpenAI

GEMINI_MODEL = "gemini-3.5-flash-lite"  # Flash-Lite tier: much higher free daily quota than flagship Flash
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def get_client() -> OpenAI:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set GEMINI_API_KEY in your environment before running any agent."
        )
    return OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)


def call_claude(system: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Single-turn call to Gemini. Returns the raw text response.
    Automatically waits and retries once if a rate limit (429) is hit."""
    client = get_client()
    try:
        resp = client.chat.completions.create(
            model=GEMINI_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        # Rate limit (429) — wait and retry once. Free tier daily/per-minute
        # caps are tight, so a short wait usually clears a transient limit.
        if "429" in str(e) or "RateLimitError" in type(e).__name__:
            print(f"  [rate limit hit, waiting 20s before retry...]")
            time.sleep(20)
            resp = client.chat.completions.create(
                model=GEMINI_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content or ""
        raise


def call_claude_json(system: str, user_prompt: str, max_tokens: int = 2000) -> dict:
    """Call Gemini and force-parse the reply as JSON. Strips code fences if present.
    Retries once with a higher token budget if the response looks truncated."""
    raw = call_claude(system, user_prompt, max_tokens=max_tokens)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        # Likely truncated mid-response — retry once with a larger budget.
        retry_tokens = max_tokens * 2
        raw = call_claude(system, user_prompt, max_tokens=retry_tokens)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Could not parse JSON from model output after retry:\n{raw}") from e


def clone_repo(repo_url: str, repo_name: str, shallow: bool = True) -> Path:
    """Clone (or refresh a cached clone of) a repo into data/<repo_name>. Returns path.
    If a clone already exists, it's refreshed with a fetch + hard reset rather than
    reused as-is — this avoids serving stale or partially-cloned data from an earlier
    interrupted run."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / repo_name
    if dest.exists():
        # Refresh instead of trusting a possibly-stale or partial prior clone.
        fetch = subprocess.run(
            ["git", "fetch", "--depth", "200", "origin"], cwd=dest,
            capture_output=True, text=True, timeout=120,
        )
        if fetch.returncode == 0:
            subprocess.run(
                ["git", "reset", "--hard", "origin/HEAD"], cwd=dest,
                capture_output=True, text=True, timeout=60,
            )
            return dest
        # Fetch failed (e.g. corrupted partial clone) — wipe and re-clone fresh.
        shutil.rmtree(dest, ignore_errors=True)
    cmd = ["git", "clone"]
    if shallow:
        cmd += ["--depth", "200"]  # enough history for bus-factor analysis, still fast
    cmd += [repo_url, str(dest)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed for {repo_url}:\n{result.stderr}")
    return dest


def run_cmd(cmd: list[str], cwd: Path, timeout: int = 180, max_output_chars: int = 4000) -> dict:
    """Run a shell command, capturing pass/fail + output. Never raises on failure.

    max_output_chars caps stdout/stderr length. For tail-heavy output (test
    logs, where errors appear near the end) the default keeps the END of the
    output. Pass max_output_chars=None to keep full output uncapped — needed
    for commands like `git log` where the START of the output (most recent
    entries) is what matters and truncating from the end silently discards
    recent history instead of old history.
    """
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        stdout = result.stdout
        stderr = result.stderr
        if max_output_chars is not None:
            stdout = stdout[-max_output_chars:]
            stderr = stderr[-max_output_chars:]
        return {
            "cmd": " ".join(cmd),
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {"cmd": " ".join(cmd), "returncode": None, "stdout": "", "stderr": "",
                 "timed_out": True}
    except FileNotFoundError:
        return {"cmd": " ".join(cmd), "returncode": None, "stdout": "",
                 "stderr": "command not found", "timed_out": False}


def save_trajectory(agent_name: str, repo_name: str, trajectory: list[dict]):
    """Save a step-by-step trajectory log for the required 'Agent trajectories' deliverable."""
    traj_dir = Path(__file__).resolve().parent.parent / "trajectories"
    traj_dir.mkdir(parents=True, exist_ok=True)
    path = traj_dir / f"{repo_name}__{agent_name}.json"
    with open(path, "w") as f:
        json.dump(trajectory, f, indent=2)
    return path
