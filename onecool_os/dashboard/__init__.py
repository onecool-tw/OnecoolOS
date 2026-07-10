"""Dashboard foundation."""

from onecool_os.dashboard.analytics_view import DashboardAnalyticsSection
from onecool_os.dashboard.analytics_view import DashboardAnalyticsView
from onecool_os.dashboard.builder import DashboardBuilder
from onecool_os.dashboard.collectibles import CollectibleDashboard
from onecool_os.dashboard.collectibles import CollectibleDashboardBuilder
from onecool_os.dashboard.collectibles import CollectibleDashboardSection
from onecool_os.dashboard.collectibles import collection_health_lines
from onecool_os.dashboard.collectibles import collection_health_section
from onecool_os.dashboard.models import DashboardSection
from onecool_os.dashboard.models import DashboardView
from onecool_os.dashboard.performance import PerformanceDashboard
from onecool_os.dashboard.performance import PerformanceDashboardBuilder
from onecool_os.dashboard.validation import DashboardError

__all__ = [
    "DashboardAnalyticsSection",
    "DashboardAnalyticsView",
    "CollectibleDashboard",
    "CollectibleDashboardBuilder",
    "CollectibleDashboardSection",
    "collection_health_lines",
    "collection_health_section",
    "DashboardBuilder",
    "DashboardError",
    "DashboardSection",
    "DashboardView",
    "PerformanceDashboard",
    "PerformanceDashboardBuilder",
]
