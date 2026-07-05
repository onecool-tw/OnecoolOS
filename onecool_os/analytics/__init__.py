"""Analytics Engine foundation."""

from onecool_os.analytics.enums import MetricType
from onecool_os.analytics.enums import RiskLevel
from onecool_os.analytics.loader import AnalyticsImportResult
from onecool_os.analytics.loader import AnalyticsLoader
from onecool_os.analytics.loader import AnalyticsLoaderError
from onecool_os.analytics.models import AnalyticsSnapshot
from onecool_os.analytics.timeline import TimelineAnalyticsBuilder
from onecool_os.analytics.timeline import TimelineSnapshot
from onecool_os.analytics.timeline import TrendDirection
from onecool_os.analytics.timeline import TrendStrength
from onecool_os.analytics.validation import AnalyticsError

__all__ = [
    "AnalyticsError",
    "AnalyticsImportResult",
    "AnalyticsLoader",
    "AnalyticsLoaderError",
    "AnalyticsSnapshot",
    "MetricType",
    "RiskLevel",
    "TimelineAnalyticsBuilder",
    "TimelineSnapshot",
    "TrendDirection",
    "TrendStrength",
]
