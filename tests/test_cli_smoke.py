import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "chat_small.json"


def run_cli(*args):
    cmd = [sys.executable, str(ROOT / "main.py"), str(FIXTURE), "--skip-plots", "--log-level", "ERROR", *args]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def test_cli_quick_profile_smoke():
    result = run_cli("--profile", "quick")
    assert result.returncode == 0, result.stderr


def test_cli_modules_override_profile():
    result = run_cli("--profile", "quick", "--modules", "nlp", "anomaly")
    assert result.returncode == 0, result.stderr


def test_cli_report_format_html():
    result = run_cli("--report-format", "html")
    assert result.returncode == 0, result.stderr
