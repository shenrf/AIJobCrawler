"""Verify iter2 subcommands are wired into main.py via --help."""
import subprocess
import sys
from pathlib import Path


MAIN = str(Path(__file__).resolve().parents[1] / "main.py")


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, MAIN] + args,
        capture_output=True,
        text=True,
        cwd=str(Path(MAIN).parent),
    )


def test_top_level_help_lists_iter2():
    r = _run(["--help"])
    assert r.returncode == 0
    for sub in ["discover", "enrich", "track", "discover-all"]:
        assert sub in r.stdout


def test_discover_help():
    r = _run(["discover", "--help"])
    assert r.returncode == 0
    assert "--max-queries-per-lab" in r.stdout
    assert "--min-talent" in r.stdout


def test_enrich_help():
    r = _run(["enrich", "--help"])
    assert r.returncode == 0


def test_track_help():
    r = _run(["track", "--help"])
    assert r.returncode == 0


def test_discover_all_help():
    r = _run(["discover-all", "--help"])
    assert r.returncode == 0
    assert "--max-queries-per-lab" in r.stdout
