"""Exit codes of chapter9/hermes-self-evolution/run_acceptance_review.py.

`hermes chat -q` echoes the query, and acceptance_review.md quotes both
`VERDICT: ACCEPT` and `VERDICT: REJECT`, so every transcript contains both
strings before the reviewer says anything. The gate must read the reviewer's
own final line-anchored verdict, as finalize_evidence.py already does.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

EXPERIMENT = Path(__file__).resolve().parent.parent / "chapter9" / "hermes-self-evolution"
if str(EXPERIMENT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT))

import run_acceptance_review

RAW_V1 = EXPERIMENT / "validation" / "exp9-8-hermes-gpt56luna-20260802-v1" / "raw"
RAW_V2 = EXPERIMENT / "validation" / "exp9-8-hermes-gpt56luna-autonomous-20260802-v2" / "raw"
PROMPT = (EXPERIMENT / "acceptance_review.md").read_text(encoding="utf-8")


def run_gate(monkeypatch, tmp_path, transcript, returncode=0):
    """Run main() with Hermes replaced by a canned transcript."""
    shutil.copy(EXPERIMENT / "acceptance_review.md", tmp_path / "acceptance_review.md")
    monkeypatch.setattr(run_acceptance_review, "ROOT", tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr(sys, "argv", ["run_acceptance_review.py", "--run-id", "t"])

    def fake_run(cmd, **kwargs):
        if cmd[0] == "git":
            return subprocess.CompletedProcess(cmd, 0, stdout=b"")
        return subprocess.CompletedProcess(cmd, returncode, stdout=transcript)

    monkeypatch.setattr(run_acceptance_review.subprocess, "run", fake_run)
    return run_acceptance_review.main()


@pytest.mark.parametrize(
    "transcript",
    [RAW_V1 / "hermes-acceptance-review-6.txt", RAW_V2 / "hermes-acceptance-review-4.txt"],
    ids=["v1-round6", "v2-round4"],
)
def test_retained_accepting_review_returns_zero(monkeypatch, tmp_path, capsys, transcript):
    text = transcript.read_text(encoding="utf-8")
    assert run_gate(monkeypatch, tmp_path, text) == 0


@pytest.mark.parametrize(
    "transcript",
    [RAW_V1 / f"hermes-acceptance-review-{n}.txt" for n in range(1, 6)]
    + [RAW_V2 / f"hermes-acceptance-review-{n}.txt" for n in range(1, 4)],
    ids=lambda p: f"{p.parent.parent.name[-2:]}-{p.stem[-1]}",
)
def test_retained_rejecting_review_returns_three(monkeypatch, tmp_path, capsys, transcript):
    text = transcript.read_text(encoding="utf-8")
    assert run_gate(monkeypatch, tmp_path, text) == 3


def test_echoed_prompt_without_reviewer_verdict_is_invalid(monkeypatch, tmp_path, capsys):
    text = f"Query: {PROMPT}\nI ran out of time before deciding.\n"
    assert run_gate(monkeypatch, tmp_path, text) == 4


def test_last_verdict_line_wins(monkeypatch, tmp_path, capsys):
    text = f"Query: {PROMPT}\nVERDICT: ACCEPT\nOn reflection, no.\nVERDICT: REJECT\n"
    assert run_gate(monkeypatch, tmp_path, text) == 3


def test_hermes_failure_exit_code_is_passed_through(monkeypatch, tmp_path, capsys):
    text = f"Query: {PROMPT}\nVERDICT: ACCEPT\n"
    assert run_gate(monkeypatch, tmp_path, text, returncode=1) == 1


def make_dirty_checkout(root):
    """A candidate checkout that already carries the uncommitted patch under review."""
    source = root / "worktree" / "hermes-agent"
    source.mkdir(parents=True)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    (source / "agent.py").write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "add", "agent.py"], cwd=source, check=True)
    subprocess.run([*git, "commit", "-q", "-m", "init"], cwd=source, check=True)
    (source / "agent.py").write_text("candidate patch\n", encoding="utf-8")
    (source / "notes.md").write_text("candidate notes\n", encoding="utf-8")
    return source


@pytest.mark.parametrize("edited", [None, "agent.py", "notes.md"], ids=["none", "tracked", "untracked"])
def test_reviewer_rewriting_an_already_dirty_file_is_caught(monkeypatch, tmp_path, capsys, edited):
    source = make_dirty_checkout(tmp_path)
    shutil.copy(EXPERIMENT / "acceptance_review.md", tmp_path / "acceptance_review.md")
    monkeypatch.setattr(run_acceptance_review, "ROOT", tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr(sys, "argv", ["run_acceptance_review.py", "--run-id", "t"])
    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if cmd[0] == "git":
            return real_run(cmd, **kwargs)
        if edited:
            (source / edited).write_text("reviewer rewrote the candidate\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout=f"Query: {PROMPT}\nVERDICT: ACCEPT\n")

    monkeypatch.setattr(run_acceptance_review.subprocess, "run", fake_run)
    if edited is None:
        assert run_acceptance_review.main() == 0
        return
    with pytest.raises(RuntimeError, match="modified the candidate checkout"):
        run_acceptance_review.main()
