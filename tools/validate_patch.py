import argparse
import compileall
from pathlib import Path
import subprocess
import sys
import json

parser = argparse.ArgumentParser()
parser.add_argument("--repo", required=True)
args = parser.parse_args()

repo = Path(args.repo).resolve()

result = {
    "compile_success": False,
    "smoke_success": False,
    "errors": []
}

try:
    result["compile_success"] = compileall.compile_dir(repo, quiet=1)
except Exception as e:
    result["errors"].append(str(e))

try:
    proc = subprocess.run(
        [
            sys.executable,
            str(repo / "run_batch.py"),
            str(repo / "jobs" / "sample_jobs.json")
        ],
        cwd=repo,
        capture_output=True,
        text=True
    )
    result["smoke_success"] = proc.returncode == 0
    if proc.returncode != 0:
        result["errors"].append(proc.stderr)
except Exception as e:
    result["errors"].append(str(e))

print(json.dumps(result, indent=2))