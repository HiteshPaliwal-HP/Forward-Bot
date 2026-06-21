"""Placeholder steps for the forwarding pipeline."""
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class TimeWindowStep:
    name: str = "TimeWindowStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class SamplingStep:
    name: str = "SamplingStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class MediaTypeFilterStep:
    name: str = "MediaTypeFilterStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class BlockKeywordStep:
    name: str = "BlockKeywordStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class AllowKeywordStep:
    name: str = "AllowKeywordStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class MediaDecisionStep:
    name: str = "MediaDecisionStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class ReplyLookupStep:
    name: str = "ReplyLookupStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class SourceRefReplaceStep:
    name: str = "SourceRefReplaceStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class TextReplacementStep:
    name: str = "TextReplacementStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class LinkRemovalStep:
    name: str = "LinkRemovalStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class HashtagRemovalStep:
    name: str = "HashtagRemovalStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class MentionRemovalStep:
    name: str = "MentionRemovalStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class MediaReplacementStep:
    name: str = "MediaReplacementStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class WhitespaceStep:
    name: str = "WhitespaceStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class AttributionStep:
    name: str = "AttributionStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx


class EmptyCheckStep:
    name: str = "EmptyCheckStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        return ctx
