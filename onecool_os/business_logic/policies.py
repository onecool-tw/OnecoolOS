"""Business logic policy configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onecool_os.business_logic.validation import parse_optional_dict
from onecool_os.business_logic.validation import require_text


@dataclass(frozen=True)
class BasePolicy:
    """Rule configuration for calculators and evaluators."""

    policy_name: str
    policy_version: str
    rules: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate policy identity and rule configuration."""

        object.__setattr__(
            self,
            "policy_name",
            require_text(self.policy_name, "policy_name"),
        )
        object.__setattr__(
            self,
            "policy_version",
            require_text(self.policy_version, "policy_version"),
        )
        object.__setattr__(
            self,
            "rules",
            parse_optional_dict(self.rules, "rules"),
        )
