"""Tests for the reporter module."""

from __future__ import annotations

import io
import json

from aap_config_validate.models import Issue, Severity
from aap_config_validate.reporter import report_json, report_text


def _make_issues():
    return [
        Issue(severity=Severity.ERROR, path="var[0]", message="missing field"),
        Issue(
            severity=Severity.WARNING,
            path="var[1]",
            message="typo",
            suggestion='did you mean "x"?',
        ),
        Issue(severity=Severity.INFO, path="var[2].key", message="skipped Jinja"),
    ]


class TestReportText:
    def test_output_contains_messages(self):
        buf = io.StringIO()
        report_text(_make_issues(), color=False, file=buf)
        output = buf.getvalue()
        assert "ERROR" in output
        assert "WARNING" in output
        assert "INFO" in output
        assert "missing field" in output
        assert "1 error" in output

    def test_no_issues(self):
        buf = io.StringIO()
        report_text([], color=False, file=buf)
        assert "No issues found" in buf.getvalue()


class TestReportJson:
    def test_valid_json(self):
        buf = io.StringIO()
        report_json(_make_issues(), file=buf)
        data = json.loads(buf.getvalue())
        assert data["summary"]["errors"] == 1
        assert data["summary"]["warnings"] == 1
        assert data["summary"]["info"] == 1
        assert len(data["issues"]) == 3

    def test_empty(self):
        buf = io.StringIO()
        report_json([], file=buf)
        data = json.loads(buf.getvalue())
        assert data["summary"]["errors"] == 0
