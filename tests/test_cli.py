import os

from course_enhancer import cli


def test_nonexistent_file_errors_cleanly(tmp_path, capsys):
    missing = str(tmp_path / "does-not-exist.md")
    exit_code = cli.main([missing])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "not found" in captured.err
    # must not have silently produced output from the path string as content
    assert not os.path.isdir(os.path.join("output", "untitled-course"))


def test_valid_file_runs_successfully(tmp_path, capsys):
    source = os.path.join(os.path.dirname(__file__), "..", "examples", "sample_course.md")
    exit_code = cli.main([source, "--out", str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Output written to" in captured.out
