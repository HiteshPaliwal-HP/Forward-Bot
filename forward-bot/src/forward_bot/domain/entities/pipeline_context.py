"""Pipeline context and blocked outcome domain models."""
import copy
from dataclasses import dataclass, field
from typing import Any, Optional

from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source

BLOCK_REASONS = {
    "outside_time_window",
    "sampled_out",
    "media_type_filtered",
    "blocked_keyword",
    "no_allow_keyword_matched",
    "empty_after_processing",
    "unsupported_media_type",
    "step_error",
}


@dataclass
class BlockedOutcome:
    """Represents a message being blocked or filtered out of the pipeline."""
    reason: str
    matched_keyword: Optional[str] = None
    details: Optional[str] = None

    def __post_init__(self) -> None:
        if self.reason not in BLOCK_REASONS:
            raise ValueError(f"Invalid block reason: {self.reason}")


@dataclass
class PipelineContext:
    """Carries the state of a message as it flows through the forwarding pipeline."""
    text: str
    caption: Optional[str]
    media: Optional[Any]
    attribution_decided: bool
    reply_target_destination_id: Optional[int]
    correlation_id: str
    rule: ForwardingRule
    source: Source
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Create a copy-on-write snapshot of ForwardingRule and Source
        self.rule = copy.deepcopy(self.rule)
        self.source = copy.deepcopy(self.source)
