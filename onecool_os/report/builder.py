"""Base report builder contract."""

from __future__ import annotations

from typing import Any

from onecool_os.report.validation import ReportError


class BaseReportBuilder:
    """Base interface for structured report builders."""

    builder_name = "base_report"

    def build(self, source: Any):
        """Build a structured report."""

        raise ReportError(f"{self.builder_name} does not implement build().")
