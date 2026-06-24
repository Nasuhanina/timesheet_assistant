"""Run pip-audit and auto-fix vulnerabilities when possible."""
import subprocess
import sys
import json


def run_pip_audit():
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "--format", "json", "--requirement", "requirements.txt"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("pip-audit: No vulnerabilities found.")
        return True

    try:
        data = json.loads(result.stdout)
        vulns = data.get("vulnerabilities", [])
    except (json.JSONDecodeError, KeyError):
        print("pip-audit output could not be parsed.")
        return False

    if not vulns:
        print("pip-audit: No vulnerabilities found.")
        return True

    print(f"pip-audit: {len(vulns)} vulnerabilities found. Attempting fixes...")
    for v in vulns:
        pkg = v["package"]
        name = pkg["name"]
        installed = pkg.get("version", "")
        vuln_id = v.get("id", "unknown")
        fix_versions = v.get("fix_versions", [])
        print(f"  {vuln_id}: {name}=={installed} -> fix available: {fix_versions}")
        if fix_versions:
            target = f"{name}>={fix_versions[-1]}"
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", target],
                capture_output=True, text=True
            )
    return False


if __name__ == "__main__":
    ok = run_pip_audit()
    if not ok:
        print("pip-audit: Re-checking after fixes...")
        run_pip_audit()
    sys.exit(0)
