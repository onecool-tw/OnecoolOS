"""Base Radar Engine builder contract."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from onecool_os.radar.models import RadarSnapshot
from onecool_os.radar.validation import RadarError


class BaseRadarBuilder:
    """Base interface for radar snapshot builders."""

    builder_name = "base_radar"

    def build(
        self,
        previous_intelligence: Any,
        current_intelligence: Any,
        *,
        reference_datetime: datetime,
    ) -> RadarSnapshot:
        """Build a radar snapshot."""

        raise RadarError(f"{self.builder_name} does not implement build().")
