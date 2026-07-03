"""Dashboard foundation."""

from onecool_os.dashboard.builder import DashboardBuilder
from onecool_os.dashboard.models import DashboardSection
from onecool_os.dashboard.models import DashboardView
from onecool_os.dashboard.validation import DashboardError

__all__ = [
    "DashboardBuilder",
    "DashboardError",
    "DashboardSection",
    "DashboardView",
]
