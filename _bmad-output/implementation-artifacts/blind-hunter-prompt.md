You are the Blind Hunter. Review the following diff. You receive NO project context — diff only. Follow the bmad-review-adversarial-general skill guidelines.
<diff>
diff --git a/_bmad-output/implementation-artifacts/4-3-transform-media-pipeline-steps-steps-6-16.md b/_bmad-output/implementation-artifacts/4-3-transform-media-pipeline-steps-steps-6-16.md
new file mode 100644
index 0000000..3ed8496
--- /dev/null
+++ b/_bmad-output/implementation-artifacts/4-3-transform-media-pipeline-steps-steps-6-16.md
@@ -0,0 +1,224 @@
+---
+baseline_commit: 343be125cf74a3fef57c093a5518b0c8227b689e
+---
+# Story 4.3: Transform & Media Pipeline Steps (Steps 6ΓÇô16)
+
+Status: review
+
+<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
+
+## Story
+
+As a **Channel Operator**,
+I want forwarded messages to be cleaned and rewritten ΓÇö stripping links/hashtags/mentions, substituting text patterns, auto-replacing source references, and optionally swapping the photo ΓÇö before delivery,
+so that destination channels receive polished, on-brand content without manual editing.
+
+## Acceptance Criteria
+
+1. **Media Decision Step (Step 6):**
+   - **Given** `forward_media="forward"` and the message has a photo.
+   - **When** `MediaDecisionStep.apply()` runs.
+   - **Then** `ctx.media` remains set to the photo and `ctx.caption` is preserved.
+   - **Given** `forward_media="ignore"`.
+   - **When** `MediaDecisionStep.apply()` runs.
+   - **Then** both `ctx.media` and `ctx.caption` are set to `None`.
+   - **Given** `forward_media="caption_only"`.
+   - **When** `MediaDecisionStep.apply()` runs.
+   - **Then** `ctx.media` is set to `None` and the caption text is retained. (If `ctx.text` is empty/None and `ctx.caption` is populated, the caption text is promoted to `ctx.text` so that downstream text-based transforms process it, and `ctx.caption` is set to `None`).
+
+2. **Reply Lookup Step (Step 7):**
+   - **Given** the source message is a Telegram reply (e.g. `ctx.metadata.get("reply_to_msg_id")` is present) and `mapping_repository` is injected.
+   - **When** `ReplyLookupStep.apply()` runs.
+   - **Then** it queries `mapping_repository.get_by_source_message(source_channel_id=ctx.source.telegram_id, source_message_id=reply_to_msg_id, forwarding_rule_id=ctx.rule.id)`.
+   - **And** if a mapping is found, it sets `ctx.reply_target_destination_id = parent_mapping.destination_message_id`.
+   - **And** if no parent mapping is found (filtered or outside retention), it logs a warning `{"event": "reply_parent_not_found", ...}` and leaves `ctx.reply_target_destination_id = None`, continuing the pipeline.
+   - **And** if `mapping_repository` is not configured, it fails open (logs warning and leaves `ctx.reply_target_destination_id = None`).
+
+3. **Source Reference Auto-Replacement Step (Step 8):**
+   - **Given** `auto_replace_source_refs.enabled=true` and a registered source.
+   - **When** `SourceRefReplaceStep.apply()` runs.
+   - **Then** it scans `ctx.text` and `ctx.caption` and case-insensitively replaces references to the source username:
+     - `@<source.telegram_username>`
+     - `t.me/<source.telegram_username>`
+     - `https://t.me/<source.telegram_username>`
+   - **And** replaces them with the destination's reference (defaults to the rule's `destination_channel` username, or `auto_replace_source_refs.replacement` if provided).
+   - **And** if `auto_replace_source_refs.replace_display_name=true`, it case-sensitively replaces `<source.display_name>` in text/caption as well.
+   - **And** this step runs before any generic Replacement Rules.
+
+4. **Text Replacement Rules Step (Step 9):**
+   - **Given** the forwarding rule has active child `ReplacementRules`.
+   - **When** `TextReplacementStep.apply()` runs.
+   - **Then** it applies each active replacement rule to `ctx.text` and `ctx.caption` in ascending order of `created_at`.
+   - **And** if `match_mode="literal"`, case-insensitive substring replacement is performed.
+   - **And** if `match_mode="regex"`, Python regex matching and `re.sub` replacement are performed, supporting capture-group backreferences (e.g. `\1`, `\2`), using pre-compiled patterns from the `RuleCache` snapshot (`CacheHolder.current.compiled_patterns.get(rule.id).replacement_patterns`).
+   - **And** if pre-compiled patterns are missing from cache (e.g., in test environments), it compiles the regex pattern dynamically with case insensitivity (`re.IGNORECASE`), logging a warning on compile error and skipping the invalid pattern.
+
+5. **Link Removal Step (Step 10):**
+   - **Given** `remove_links=true` on the forwarding rule.
+   - **When** `LinkRemovalStep.apply()` runs.
+   - **Then** it strips links from both `ctx.text` and `ctx.caption`.
+   - **And** the stripped patterns include: `http://`, `https://`, `t.me/`, `telegram.me/`, `tg://`, and joinchat link structures (`t.me/joinchat/...` or `t.me/+...`).
+
+6. **Hashtag & Mention Removal Steps (Steps 11 and 12):**
+   - **Given** `remove_hashtags=true` / `remove_mentions=true`.
+   - **When** `HashtagRemovalStep.apply()` and `MentionRemovalStep.apply()` run.
+   - **Then** hashtag tokens (e.g., `#hashtag`) and mention tokens (e.g., `@username`) are stripped from `ctx.text` and `ctx.caption`.
+
+7. **Media Replacement Step (Step 13):**
+   - **Given** `media_replacement.enabled=true` and the message context has a photo (`ctx.media` is present).
+   - **When** `MediaReplacementStep.apply()` runs.
+   - **Then** it resolves the path as `Path(settings.media_replacement_base_dir) / rule.media_replacement.replacement_image_path`.
+   - **And** it enforces path containment to prevent directory traversal: asserts the resolved path is within `settings.media_replacement_base_dir`. If a traversal attempt is detected, it logs a warning `{"event": "media_replacement_path_traversal_attempt", ...}` and falls back to the original source photo.
+   - **And** it checks if the file exists using `asyncio.to_thread(candidate.exists)`. On missing file or read failure, it logs a warning `{"event": "media_replacement_failed", ...}` and falls back to the original source photo.
+   - **And** if the file exists, it assigns the resolved `Path` object to `ctx.media` instead of reading the file into memory as bytes, so that `DeliveryStep` can later pass the path string directly to Telethon, saving significant memory.
+   - **And** based on `replacement_caption_mode`:
+     - `"none"`: sets caption to `None`.
+     - `"use_source"`: keeps the processed caption.
+     - `"use_replacement"`: since there is no custom replacement caption field, sets caption to `None` or leaves it empty.
+
+8. **Whitespace Normalization Step (Step 14):**
+   - **Given** preceding removal transforms have run.
+   - **When** `WhitespaceStep.apply()` runs.
+   - **Then** all multiple consecutive spaces, tabs, or newlines in `ctx.text` and `ctx.caption` are collapsed to single spaces/newlines, and leading/trailing whitespace is stripped.
+
+9. **Attribution Prefix/Suffix Step (Step 15):**
+   - **Given** `attribution.enabled=true`.
+   - **When** `AttributionStep.apply()` runs.
+   - **Then** it formats the template string (replacing `{source_name}` with `ctx.source.display_name` and `{source_username}` with `ctx.source.telegram_username` or display name fallback if username is missing).
+   - **And** if `position="prefix"`, it prepends the formatted attribution.
+   - **And** if `position="suffix"`, it appends the formatted attribution.
+   - **And** attribution target logic strictly follows: `if ctx.media:` apply to `ctx.caption` (initialize to `""` if `None`); `else:` apply to `ctx.text`.
+
+10. **Empty Result Check Step (Step 16):**
+    - **Given** the processed text is empty, caption is empty/None, AND no media is being forwarded.
+    - **When** `EmptyCheckStep.apply()` runs.
+    - **Then** it safely evaluates `if not ctx.text and not ctx.caption and ctx.media is None:` (handling `ctx.media` potentially being a `Path` object) and returns `BlockedOutcome(reason="empty_after_processing")`.
+
+11. **Integration and Exception Isolation:**
+    - **Given** steps 6ΓÇô16 are implemented.
+    - **When** `PipelineEngine` is instantiated.
+    - **Then** all steps are registered in the canonical 18-step sequence, and `ReplyLookupStep` is correctly passed the `mapping_repository`.
+    - **And** unexpected catastrophic exceptions raised inside a step are caught, logged, and return `BlockedOutcome(reason="step_error")` to isolate failures.
+    - **And** expected step-specific fallbacks (like `MediaReplacementStep` falling back to the source photo on read error) MUST take precedence and return the context rather than dropping the message.
+
+## Tasks / Subtasks
+
+- [x] **Infrastructure & Steps Refactoring**
+  - [x] Update `PipelineEngine.__init__` in `src/forward_bot/application/pipeline/engine.py` to accept `mapping_repository: MappingRepository` as an argument and instantiate `ReplyLookupStep(mapping_repository)`.
+  - [x] Update dependency injection in `src/forward_bot/api/dependencies/providers.py` (or where the engine is constructed) to inject `MappingRepository` into the `PipelineEngine` factory.
+  - [x] Implement `MediaDecisionStep` in `src/forward_bot/application/pipeline/steps/media_decision.py`.
+  - [x] Implement `ReplyLookupStep` in `src/forward_bot/application/pipeline/steps/reply_lookup.py` taking `mapping_repository`.
+  - [x] Implement `SourceRefReplaceStep` in `src/forward_bot/application/pipeline/steps/source_ref_replace.py`.
+  - [x] Implement `TextReplacementStep` in `src/forward_bot/application/pipeline/steps/text_replacement.py`.
+  - [x] Implement `LinkRemovalStep` in `src/forward_bot/application/pipeline/steps/link_removal.py`.
+  - [x] Implement `HashtagRemovalStep` in `src/forward_bot/application/pipeline/steps/hashtag_removal.py`.
+  - [x] Implement `MentionRemovalStep` in `src/forward_bot/application/pipeline/steps/mention_removal.py`.
+  - [x] Implement `MediaReplacementStep` in `src/forward_bot/application/pipeline/steps/media_replacement.py`.
+  - [x] Implement `WhitespaceStep` in `src/forward_bot/application/pipeline/steps/whitespace.py`.
+  - [x] Implement `AttributionStep` in `src/forward_bot/application/pipeline/steps/attribution.py`.
+  - [x] Implement `EmptyCheckStep` in `src/forward_bot/application/pipeline/steps/empty_check.py`.
+  - [x] Update `src/forward_bot/application/pipeline/steps/__init__.py` to import and expose these new steps instead of placeholders.
+- [x] **Unit & Integration Testing**
+  - [x] Write unit tests for each step under `tests/application/pipeline/steps/`:
+    - `test_media_decision.py`
+    - `test_reply_lookup.py`
+    - `test_source_ref_replace.py`
+    - `test_text_replacement.py`
+    - `test_link_removal.py`
+    - `test_hashtag_removal.py`
+    - `test_mention_removal.py`
+    - `test_media_replacement.py`
+    - `test_whitespace.py`
+    - `test_attribution.py`
+    - `test_empty_check.py`
+  - [x] Update engine integration tests in `tests/application/pipeline/test_engine.py` to cover steps 6ΓÇô16 end-to-end.
+
+## Dev Notes
+
+- **Dependency Injection Wiring (`PipelineEngine`):**
+  - Ensure `mapping_repository` is injected properly when building the engine:
+    ```python
+    # In providers.py or worker.py setup:
+    engine = PipelineEngine(
+        sampling_repository=sampling_repo,
+        mapping_repository=mapping_repo
+    )
+    ```
+- **Non-blocking File Checks (`MediaReplacementStep`):**
+  - Always use `asyncio.to_thread` when performing file system I/O (e.g. `candidate.exists()`), preventing thread-blocking in the single ASGI worker event loop. Store the `Path` object in `ctx.media` instead of reading the file into memory.
+- **Path Containment/Traversal Guard (`MediaReplacementStep`):**
+  - Ensure the resolved path `candidate_path` is safely enclosed in `settings.media_replacement_base_dir`:
+    ```python
+    base = Path(settings.media_replacement_base_dir).resolve()
+    candidate = (base / rule.media_replacement.replacement_image_path).resolve()
+    if not candidate.is_relative_to(base):
+        # Log warning "media_replacement_path_traversal_attempt"
+        # Fall back to original photo
+    ```
+- **Regular Expressions compilation cache (`TextReplacementStep`):**
+  - Import `CacheHolder` and look up pre-compiled regex pattern objects via the atomic snapshot (`CacheHolder.current.compiled_patterns.get(rule.id)`).
+  - If cache lookup fails or the ID isn't found, gracefully fallback to dynamically compiling patterns using `re.compile(pattern, re.IGNORECASE)`.
+  - Wrap compilation in try/except and fail-safe on error (log warning, skip pattern).
+- **Auto-Replacement Source References (`SourceRefReplaceStep`):**
+  - Match `@<source_username>`, `t.me/<source_username>`, and `https://t.me/<source_username>` case-insensitively, substituting them with the rule's destination channel reference or custom replacement.
+  - If display name auto-replace is enabled, perform case-sensitive replacement of `<source_display_name>`.
+- **Formatting Attribution (`AttributionStep`):**
+  - Safely replace `{source_name}` and `{source_username}` placeholders in the template string using `ctx.source.display_name` and `ctx.source.telegram_username` (use display name if username is not configured).
+
+### Project Structure Notes
+
+- New steps should be placed in separate files under `src/forward_bot/application/pipeline/steps/` rather than keeping them in `placeholders.py`.
+- Update `__init__.py` imports to reference the correct file paths.
+
+### References
+
+- [Functional Requirements FR-7, FR-8, FR-11, FR-13, FR-14, FR-15, FR-31a, FR-39, FR-40, FR-41 in epics.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/epics.md#L40)
+- [Clean Architecture guidelines in architecture.md](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/_bmad-output/planning-artifacts/architecture.md#L621)
+
+## Dev Agent Record
+
+### Agent Model Used
+
+Gemini 3.5 Flash (High)
+
+### Debug Log References
+
+- Task id 0003c108-4c08-4828-b400-dcaa368975ed/task-225: pytest run verification output.
+
+### Completion Notes List
+
+- Implemented 11 pipeline steps (Steps 6-16) under `src/forward_bot/application/pipeline/steps/` and updated `steps/__init__.py`.
+- Refactored `PipelineEngine` to receive and inject `mapping_repository` into `ReplyLookupStep`.
+- Configured FastAPI dependency providers in `providers.py` to wire `MappingRepository` and `PipelineEngine`.
+- Wrote full unit test coverage for the 11 new steps under `tests/application/pipeline/steps/`.
+- Created an end-to-end integration test `test_engine_steps_6_to_16_integration` in `tests/application/pipeline/test_engine.py` verifying full pipeline functionality.
+
+### File List
+
+- `forward-bot/src/forward_bot/application/pipeline/engine.py` (Modified)
+- `forward-bot/src/forward_bot/application/pipeline/steps/__init__.py` (Modified)
+- `forward-bot/src/forward_bot/application/pipeline/steps/placeholders.py` (Modified)
+- `forward-bot/src/forward_bot/api/dependencies/providers.py` (Modified)
+- `forward-bot/src/forward_bot/application/pipeline/steps/media_decision.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/reply_lookup.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/source_ref_replace.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/text_replacement.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/link_removal.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/hashtag_removal.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/mention_removal.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/media_replacement.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/whitespace.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/attribution.py` (New)
+- `forward-bot/src/forward_bot/application/pipeline/steps/empty_check.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_media_decision.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_reply_lookup.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_source_ref_replace.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_text_replacement.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_link_removal.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_hashtag_removal.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_mention_removal.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_media_replacement.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_whitespace.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_attribution.py` (New)
+- `forward-bot/tests/application/pipeline/steps/test_empty_check.py` (New)
+- `forward-bot/tests/application/pipeline/test_engine.py` (Modified)
diff --git a/_bmad-output/implementation-artifacts/sprint-status.yaml b/_bmad-output/implementation-artifacts/sprint-status.yaml
index 419988c..b207cbd 100644
--- a/_bmad-output/implementation-artifacts/sprint-status.yaml
+++ b/_bmad-output/implementation-artifacts/sprint-status.yaml
@@ -79,7 +79,7 @@ development_status:
 
   4-1-pipeline-infrastructure-context-protocol-engine-message-mapping: done
   4-2-filter-pipeline-steps-steps-1-5: done
-  4-3-transform-media-pipeline-steps-steps-6-16: backlog
+  4-3-transform-media-pipeline-steps-steps-6-16: review
   4-4-telegram-delivery-reliability: backlog
   4-5-telegram-worker-end-to-end-message-forwarding: backlog
 
@@ -117,10 +117,10 @@ summary:
   epics_in_progress: 1
   epics_done: 3
 
-  stories_backlog: 13
+  stories_backlog: 12
   stories_ready_for_dev: 0
   stories_in_progress: 0
-  stories_in_review: 0
+  stories_in_review: 1
   stories_done: 11
 
   retrospectives_optional: 3
diff --git a/forward-bot/src/forward_bot/api/dependencies/providers.py b/forward-bot/src/forward_bot/api/dependencies/providers.py
index c95b380..4e1cdfc 100644
--- a/forward-bot/src/forward_bot/api/dependencies/providers.py
+++ b/forward-bot/src/forward_bot/api/dependencies/providers.py
@@ -9,6 +9,8 @@ from forward_bot.infrastructure.mongo.repositories.folder_repository import Fold
 from forward_bot.infrastructure.mongo.repositories.rule_repository import ForwardingRuleRepository
 from forward_bot.infrastructure.mongo.repositories.replacement_repository import ReplacementRuleRepository
 from forward_bot.infrastructure.mongo.repositories.sampling_repository import SamplingRepository
+from forward_bot.infrastructure.mongo.repositories.mapping_repository import MappingRepository
+from forward_bot.application.pipeline.engine import PipelineEngine
 
 
 def get_db() -> AsyncIOMotorDatabase:
@@ -43,6 +45,22 @@ def get_sampling_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> Sampl
     return SamplingRepository(db)
 
 
+def get_mapping_repository(db: AsyncIOMotorDatabase = Depends(get_db)) -> MappingRepository:
+    """Injects the MappingRepository."""
+    return MappingRepository(db)
+
+
+def get_pipeline_engine(
+    mapping_repo: MappingRepository = Depends(get_mapping_repository),
+    sampling_repo: SamplingRepository = Depends(get_sampling_repository),
+) -> PipelineEngine:
+    """Injects the PipelineEngine."""
+    return PipelineEngine(
+        mapping_repository=mapping_repo,
+        sampling_repository=sampling_repo,
+    )
+
+
 def get_telegram_client() -> TelegramClientHolder:
     """Injects the TelegramClientHolder connection client."""
     return telegram_client
diff --git a/forward-bot/src/forward_bot/application/pipeline/engine.py b/forward-bot/src/forward_bot/application/pipeline/engine.py
index 0ebda9e..dff0ea2 100644
--- a/forward-bot/src/forward_bot/application/pipeline/engine.py
+++ b/forward-bot/src/forward_bot/application/pipeline/engine.py
@@ -51,7 +51,7 @@ class PipelineEngine:
                 BlockKeywordStep(),
                 AllowKeywordStep(),
                 MediaDecisionStep(),
-                ReplyLookupStep(),
+                ReplyLookupStep(mapping_repository),
                 SourceRefReplaceStep(),
                 TextReplacementStep(),
                 LinkRemovalStep(),
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py b/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py
index 8a49c3f..088efca 100644
--- a/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py
@@ -4,19 +4,17 @@ from forward_bot.application.pipeline.steps.sampling import SamplingStep
 from forward_bot.application.pipeline.steps.media_type_filter import MediaTypeFilterStep
 from forward_bot.application.pipeline.steps.block_keyword import BlockKeywordStep
 from forward_bot.application.pipeline.steps.allow_keyword import AllowKeywordStep
-from forward_bot.application.pipeline.steps.placeholders import (
-    MediaDecisionStep,
-    ReplyLookupStep,
-    SourceRefReplaceStep,
-    TextReplacementStep,
-    LinkRemovalStep,
-    HashtagRemovalStep,
-    MentionRemovalStep,
-    MediaReplacementStep,
-    WhitespaceStep,
-    AttributionStep,
-    EmptyCheckStep,
-)
+from forward_bot.application.pipeline.steps.media_decision import MediaDecisionStep
+from forward_bot.application.pipeline.steps.reply_lookup import ReplyLookupStep
+from forward_bot.application.pipeline.steps.source_ref_replace import SourceRefReplaceStep
+from forward_bot.application.pipeline.steps.text_replacement import TextReplacementStep
+from forward_bot.application.pipeline.steps.link_removal import LinkRemovalStep
+from forward_bot.application.pipeline.steps.hashtag_removal import HashtagRemovalStep
+from forward_bot.application.pipeline.steps.mention_removal import MentionRemovalStep
+from forward_bot.application.pipeline.steps.media_replacement import MediaReplacementStep
+from forward_bot.application.pipeline.steps.whitespace import WhitespaceStep
+from forward_bot.application.pipeline.steps.attribution import AttributionStep
+from forward_bot.application.pipeline.steps.empty_check import EmptyCheckStep
 from forward_bot.application.pipeline.steps.deliver import DeliverStep
 from forward_bot.application.pipeline.steps.persist_mapping import PersistMappingStep
 
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/attribution.py b/forward-bot/src/forward_bot/application/pipeline/steps/attribution.py
new file mode 100644
index 0000000..cb4a13c
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/attribution.py
@@ -0,0 +1,40 @@
+"""Attribution prefix/suffix step of the forwarding pipeline."""
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+
+
+class AttributionStep:
+    """Formats and prepends/appends source attribution information (FR-14)."""
+    name: str = "AttributionStep"
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        rule = ctx.rule
+        config = getattr(rule, "attribution", None)
+        if not config or not config.enabled:
+            return ctx
+
+        # Determine replacement values
+        source_name = ctx.source.display_name or ""
+        source_username = ctx.source.telegram_username or source_name
+
+        # Format the template
+        template = config.format or "From {source_name}"
+        attr_text = template.replace("{source_name}", source_name).replace("{source_username}", source_username)
+
+        position = config.position or "prefix"
+
+        if ctx.media is not None:
+            # Apply to ctx.caption (initialize to "" if None)
+            caption = ctx.caption or ""
+            if position == "prefix":
+                ctx.caption = f"{attr_text}\n{caption}" if caption else attr_text
+            else:  # suffix
+                ctx.caption = f"{caption}\n{attr_text}" if caption else attr_text
+        else:
+            # Apply to ctx.text
+            text = ctx.text or ""
+            if position == "prefix":
+                ctx.text = f"{attr_text}\n{text}" if text else attr_text
+            else:  # suffix
+                ctx.text = f"{text}\n{attr_text}" if text else attr_text
+
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/empty_check.py b/forward-bot/src/forward_bot/application/pipeline/steps/empty_check.py
new file mode 100644
index 0000000..50d5b0f
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/empty_check.py
@@ -0,0 +1,13 @@
+"""Empty result check step of the forwarding pipeline."""
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+
+
+class EmptyCheckStep:
+    """Verifies that the message is not empty after filtering and transforming (FR-11)."""
+    name: str = "EmptyCheckStep"
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        # Check if text, caption, and media are all empty/None
+        if not ctx.text and not ctx.caption and ctx.media is None:
+            return BlockedOutcome(reason="empty_after_processing")
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/hashtag_removal.py b/forward-bot/src/forward_bot/application/pipeline/steps/hashtag_removal.py
new file mode 100644
index 0000000..d251ff2
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/hashtag_removal.py
@@ -0,0 +1,17 @@
+"""Hashtag removal step of the forwarding pipeline."""
+import re
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+
+
+class HashtagRemovalStep:
+    """Removes hashtags from message text and caption (FR-8)."""
+    name: str = "HashtagRemovalStep"
+    PATTERN = re.compile(r"#\w+")
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        if getattr(ctx.rule, "remove_hashtags", False):
+            if ctx.text:
+                ctx.text = self.PATTERN.sub("", ctx.text)
+            if ctx.caption:
+                ctx.caption = self.PATTERN.sub("", ctx.caption)
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/link_removal.py b/forward-bot/src/forward_bot/application/pipeline/steps/link_removal.py
new file mode 100644
index 0000000..56d830b
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/link_removal.py
@@ -0,0 +1,23 @@
+"""Link removal step of the forwarding pipeline."""
+import re
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+
+
+class LinkRemovalStep:
+    """Removes links from message text and caption (FR-8)."""
+    name: str = "LinkRemovalStep"
+    
+    # Matches URLs starting with http://, https://, tg://, t.me/, telegram.me/
+    # excluding trailing punctuation (like dots/commas) that aren't part of the URL.
+    PATTERN = re.compile(
+        r"(https?://|tg://|t\.me/|telegram\.me/)(?:\S*[^.,?!;:\s])?",
+        re.IGNORECASE
+    )
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        if getattr(ctx.rule, "remove_links", False):
+            if ctx.text:
+                ctx.text = self.PATTERN.sub("", ctx.text)
+            if ctx.caption:
+                ctx.caption = self.PATTERN.sub("", ctx.caption)
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/media_decision.py b/forward-bot/src/forward_bot/application/pipeline/steps/media_decision.py
new file mode 100644
index 0000000..b7bca33
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/media_decision.py
@@ -0,0 +1,25 @@
+"""Media decision step of the forwarding pipeline."""
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+
+
+class MediaDecisionStep:
+    """Evaluates rule-specific media handling configuration (FR-11)."""
+    name: str = "MediaDecisionStep"
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        rule = ctx.rule
+        forward_media = getattr(rule, "forward_media", "forward")
+        if forward_media == "ignore":
+            ctx.media = None
+            ctx.caption = None
+        elif forward_media == "caption_only":
+            if ctx.media is not None:
+                ctx.media = None
+            
+            # Promote caption text to main text if main text is empty and caption is populated
+            if not ctx.text and ctx.caption:
+                ctx.text = ctx.caption
+                ctx.caption = None
+
+        # if forward_media == "forward" (default), do nothing to media and caption
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/media_replacement.py b/forward-bot/src/forward_bot/application/pipeline/steps/media_replacement.py
new file mode 100644
index 0000000..0365757
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/media_replacement.py
@@ -0,0 +1,82 @@
+"""Media replacement step of the forwarding pipeline."""
+import asyncio
+from pathlib import Path
+from forward_bot.config import Settings
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+from forward_bot.infrastructure.logging import logger
+
+
+class MediaReplacementStep:
+    """Replaces forwarded media with a configured static replacement image (FR-15)."""
+    name: str = "MediaReplacementStep"
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        rule = ctx.rule
+        config = getattr(rule, "media_replacement", None)
+        if not config or not config.enabled:
+            return ctx
+
+        # Step only runs if the context actually has media (e.g. photo)
+        if ctx.media is None:
+            return ctx
+
+        replacement_path = config.replacement_image_path
+        if not replacement_path:
+            logger.warning(
+                "media_replacement_failed",
+                rule_id=getattr(rule, "id", None),
+                reason="missing_replacement_image_path"
+            )
+            return ctx
+
+        try:
+            settings = Settings()
+            base_dir = Path(settings.media_replacement_base_dir).resolve()
+            candidate = (base_dir / replacement_path).resolve()
+
+            # Enforce path containment to prevent directory traversal
+            if not candidate.is_relative_to(base_dir):
+                logger.warning(
+                    "media_replacement_path_traversal_attempt",
+                    rule_id=getattr(rule, "id", None),
+                    path=replacement_path,
+                    base_dir=str(base_dir)
+                )
+                # Fall back to original photo
+                return ctx
+
+            # Non-blocking check for file existence
+            exists = await asyncio.to_thread(candidate.exists)
+            if not exists:
+                logger.warning(
+                    "media_replacement_failed",
+                    rule_id=getattr(rule, "id", None),
+                    path=str(candidate),
+                    reason="file_does_not_exist"
+                )
+                # Fall back to original photo
+                return ctx
+
+            # Assign resolved Path object directly to save memory
+            ctx.media = candidate
+
+            # Adjust caption based on replacement_caption_mode
+            caption_mode = config.replacement_caption_mode
+            if caption_mode == "none":
+                ctx.caption = None
+            elif caption_mode == "use_replacement":
+                # Since there is no custom replacement caption field, set to None
+                ctx.caption = None
+            # If "use_source", do nothing (keep processed caption)
+
+        except Exception as e:
+            logger.warning(
+                "media_replacement_failed",
+                rule_id=getattr(rule, "id", None),
+                error=str(e),
+                reason="unexpected_error"
+            )
+            # Fall back to original photo on error
+            return ctx
+
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/mention_removal.py b/forward-bot/src/forward_bot/application/pipeline/steps/mention_removal.py
new file mode 100644
index 0000000..72b3381
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/mention_removal.py
@@ -0,0 +1,17 @@
+"""Mention removal step of the forwarding pipeline."""
+import re
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+
+
+class MentionRemovalStep:
+    """Removes mentions from message text and caption (FR-8)."""
+    name: str = "MentionRemovalStep"
+    PATTERN = re.compile(r"@\w+")
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        if getattr(ctx.rule, "remove_mentions", False):
+            if ctx.text:
+                ctx.text = self.PATTERN.sub("", ctx.text)
+            if ctx.caption:
+                ctx.caption = self.PATTERN.sub("", ctx.caption)
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/placeholders.py b/forward-bot/src/forward_bot/application/pipeline/steps/placeholders.py
index e74027b..c8a20a9 100644
--- a/forward-bot/src/forward_bot/application/pipeline/steps/placeholders.py
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/placeholders.py
@@ -1,114 +1 @@
-"""Placeholder steps for the forwarding pipeline."""
-from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
-
-
-class TimeWindowStep:
-    name: str = "TimeWindowStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class SamplingStep:
-    name: str = "SamplingStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class MediaTypeFilterStep:
-    name: str = "MediaTypeFilterStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class BlockKeywordStep:
-    name: str = "BlockKeywordStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class AllowKeywordStep:
-    name: str = "AllowKeywordStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class MediaDecisionStep:
-    name: str = "MediaDecisionStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class ReplyLookupStep:
-    name: str = "ReplyLookupStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class SourceRefReplaceStep:
-    name: str = "SourceRefReplaceStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class TextReplacementStep:
-    name: str = "TextReplacementStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class LinkRemovalStep:
-    name: str = "LinkRemovalStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class HashtagRemovalStep:
-    name: str = "HashtagRemovalStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class MentionRemovalStep:
-    name: str = "MentionRemovalStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class MediaReplacementStep:
-    name: str = "MediaReplacementStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class WhitespaceStep:
-    name: str = "WhitespaceStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class AttributionStep:
-    name: str = "AttributionStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
-
-
-class EmptyCheckStep:
-    name: str = "EmptyCheckStep"
-
-    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
-        return ctx
+"""Placeholder steps for the forwarding pipeline (all steps now fully implemented)."""
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/reply_lookup.py b/forward-bot/src/forward_bot/application/pipeline/steps/reply_lookup.py
new file mode 100644
index 0000000..4d2aaae
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/reply_lookup.py
@@ -0,0 +1,50 @@
+"""Reply message mapping lookup step of the forwarding pipeline."""
+from typing import Optional
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+from forward_bot.infrastructure.mongo.repositories.mapping_repository import MappingRepository
+from forward_bot.infrastructure.logging import logger
+
+
+class ReplyLookupStep:
+    """Checks if the source message is a reply and looks up parent mapping (FR-31a)."""
+    name: str = "ReplyLookupStep"
+
+    def __init__(self, mapping_repository: Optional[MappingRepository] = None) -> None:
+        self.mapping_repository = mapping_repository
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        reply_to_msg_id = ctx.metadata.get("reply_to_msg_id")
+        if reply_to_msg_id is None:
+            return ctx
+
+        if self.mapping_repository is None:
+            logger.warning(
+                "reply_lookup_failed",
+                reason="mapping_repository_not_configured",
+                correlation_id=ctx.correlation_id,
+            )
+            ctx.reply_target_destination_id = None
+            return ctx
+
+        try:
+            parent_mapping = await self.mapping_repository.get_by_source_message(
+                source_channel_id=ctx.source.telegram_id,
+                source_message_id=reply_to_msg_id,
+                forwarding_rule_id=ctx.rule.id,
+            )
+            if parent_mapping:
+                ctx.reply_target_destination_id = parent_mapping.destination_message_id
+            else:
+                logger.warning(
+                    "reply_parent_not_found",
+                    source_channel_id=ctx.source.telegram_id,
+                    source_message_id=reply_to_msg_id,
+                    forwarding_rule_id=ctx.rule.id,
+                    correlation_id=ctx.correlation_id,
+                )
+                ctx.reply_target_destination_id = None
+        except Exception:
+            # Propagate catastrophic exceptions to be caught by the engine
+            raise
+
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/source_ref_replace.py b/forward-bot/src/forward_bot/application/pipeline/steps/source_ref_replace.py
new file mode 100644
index 0000000..ec08d82
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/source_ref_replace.py
@@ -0,0 +1,65 @@
+"""Source reference auto-replacement step of the forwarding pipeline."""
+import re
+from typing import Optional
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+
+
+class SourceRefReplaceStep:
+    """Case-insensitively replaces source references with destination references (FR-13)."""
+    name: str = "SourceRefReplaceStep"
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        rule = ctx.rule
+        config = getattr(rule, "auto_replace_source_refs", None)
+        if not config or not config.enabled:
+            return ctx
+
+        source_username = ctx.source.telegram_username
+        display_name = ctx.source.display_name
+
+        dest_val = config.replacement or rule.destination_channel
+        dest_val_clean = dest_val.lstrip("@")
+
+        def replace_text(text: Optional[str]) -> Optional[str]:
+            if not text:
+                return text
+
+            # 1. Username-based references (case-insensitive)
+            if source_username:
+                # Escape the username in regex
+                username_escaped = re.escape(source_username)
+                
+                # Replace https://t.me/username
+                text = re.sub(
+                    rf"https://t\.me/{username_escaped}",
+                    f"https://t.me/{dest_val_clean}",
+                    text,
+                    flags=re.IGNORECASE
+                )
+                # Replace t.me/username
+                text = re.sub(
+                    rf"t\.me/{username_escaped}",
+                    f"t.me/{dest_val_clean}",
+                    text,
+                    flags=re.IGNORECASE
+                )
+                # Replace @username
+                text = re.sub(
+                    rf"@{username_escaped}",
+                    f"@{dest_val_clean}",
+                    text,
+                    flags=re.IGNORECASE
+                )
+
+            # 2. Display name-based references (case-sensitive)
+            if config.replace_display_name and display_name:
+                text = text.replace(display_name, dest_val)
+
+            return text
+
+        if ctx.text:
+            ctx.text = replace_text(ctx.text)
+        if ctx.caption:
+            ctx.caption = replace_text(ctx.caption)
+
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/text_replacement.py b/forward-bot/src/forward_bot/application/pipeline/steps/text_replacement.py
new file mode 100644
index 0000000..24aa829
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/text_replacement.py
@@ -0,0 +1,77 @@
+"""Text replacement rules step of the forwarding pipeline."""
+import re
+from datetime import datetime
+
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+from forward_bot.infrastructure.cache.rule_cache import CacheHolder
+from forward_bot.infrastructure.logging import logger
+
+
+class TextReplacementStep:
+    """Applies active child ReplacementRules in order of created_at ASC (FR-7)."""
+    name: str = "TextReplacementStep"
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        rule = ctx.rule
+        cache = CacheHolder.current
+        
+        # Get rules from cache or default to empty list if cache is not initialized
+        replacements = cache.replacements.get(rule.id, []) if cache and cache.replacements else []
+        active_rr = [rr for rr in replacements if rr.is_active]
+        if not active_rr:
+            return ctx
+
+        # Ensure sorted in ascending order of created_at
+        active_rr.sort(key=lambda r: r.created_at or datetime.min)
+
+        for rr in active_rr:
+            if rr.match_mode == "regex":
+                # Find pre-compiled pattern in CacheHolder compiled_patterns
+                pattern = None
+                if cache and cache.compiled_patterns:
+                    compiled = cache.compiled_patterns.get(rule.id)
+                    if compiled and rr.id in compiled.replacement_patterns:
+                        pattern = compiled.replacement_patterns[rr.id]
+
+                if pattern is None:
+                    try:
+                        pattern = re.compile(rr.search_text, re.IGNORECASE)
+                    except Exception as e:
+                        logger.warning(
+                            "regex_compile_error",
+                            rule_id=rule.id,
+                            replacement_rule_id=rr.id,
+                            pattern=rr.search_text,
+                            error=str(e),
+                            message="Failed to compile replacement regex. Skipping."
+                        )
+                        continue
+
+                # Apply re.sub supporting capture-group backreferences (e.g. \1, \2)
+                if ctx.text:
+                    ctx.text = pattern.sub(rr.replacement_text, ctx.text)
+                if ctx.caption:
+                    ctx.caption = pattern.sub(rr.replacement_text, ctx.caption)
+
+            else:
+                # match_mode == "literal" (case-insensitive substring replacement)
+                try:
+                    pattern = re.compile(re.escape(rr.search_text), re.IGNORECASE)
+                except Exception as e:
+                    logger.warning(
+                        "literal_compile_error",
+                        rule_id=rule.id,
+                        replacement_rule_id=rr.id,
+                        pattern=rr.search_text,
+                        error=str(e),
+                        message="Failed to compile literal replacement pattern. Skipping."
+                    )
+                    continue
+
+                # Using lambda treats replacement_text literally, preventing backslash backref parsing
+                if ctx.text:
+                    ctx.text = pattern.sub(lambda m: rr.replacement_text, ctx.text)
+                if ctx.caption:
+                    ctx.caption = pattern.sub(lambda m: rr.replacement_text, ctx.caption)
+
+        return ctx
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/whitespace.py b/forward-bot/src/forward_bot/application/pipeline/steps/whitespace.py
new file mode 100644
index 0000000..4d78b6e
--- /dev/null
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/whitespace.py
@@ -0,0 +1,27 @@
+"""Whitespace normalization step of the forwarding pipeline."""
+import re
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+
+
+class WhitespaceStep:
+    """Collapses consecutive spaces, tabs, and newlines (FR-14)."""
+    name: str = "WhitespaceStep"
+
+    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
+        def clean_whitespace(text: str | None) -> str | None:
+            if not text:
+                return text
+            # Collapse multiple consecutive spaces and tabs to a single space
+            text = re.sub(r"[ \t]+", " ", text)
+            # Remove horizontal spaces surrounding newlines
+            text = re.sub(r" ?\n ?", "\n", text)
+            # Collapse multiple consecutive newlines to a single newline
+            text = re.sub(r"\n+", "\n", text)
+            return text.strip()
+
+        if ctx.text:
+            ctx.text = clean_whitespace(ctx.text)
+        if ctx.caption:
+            ctx.caption = clean_whitespace(ctx.caption)
+
+        return ctx
diff --git a/forward-bot/tests/application/pipeline/steps/test_attribution.py b/forward-bot/tests/application/pipeline/steps/test_attribution.py
new file mode 100644
index 0000000..1f18292
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_attribution.py
@@ -0,0 +1,95 @@
+"""Unit tests for AttributionStep."""
+import pytest
+from unittest.mock import MagicMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule, AttributionConfig
+from forward_bot.domain.entities.source import Source
+from forward_bot.application.pipeline.steps.attribution import AttributionStep
+
+
+def make_context(
+    enabled: bool,
+    position: str,
+    fmt: str,
+    source_name: str,
+    source_username: str | None,
+    media,
+    text: str,
+    caption: str | None = None
+) -> PipelineContext:
+    config = AttributionConfig(
+        enabled=enabled,
+        position=position,
+        format=fmt
+    )
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan",
+        attribution=config
+    )
+    source = MagicMock(spec=Source)
+    source.display_name = source_name
+    source.telegram_username = source_username
+    return PipelineContext(
+        text=text,
+        caption=caption,
+        media=media,
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_attribution_disabled() -> None:
+    step = AttributionStep()
+    ctx = make_context(False, "suffix", "From {source_name}", "MySource", "src_user", None, "Hello")
+    res = await step.apply(ctx)
+    assert res.text == "Hello"
+
+
+@pytest.mark.asyncio
+async def test_attribution_prefix_no_media() -> None:
+    step = AttributionStep()
+    ctx = make_context(True, "prefix", "From {source_name} (@{source_username})", "MySource", "src_user", None, "Hello")
+    res = await step.apply(ctx)
+    assert res.text == "From MySource (@src_user)\nHello"
+
+
+@pytest.mark.asyncio
+async def test_attribution_suffix_no_media() -> None:
+    step = AttributionStep()
+    ctx = make_context(True, "suffix", "From {source_name}", "MySource", "src_user", None, "Hello")
+    res = await step.apply(ctx)
+    assert res.text == "Hello\nFrom MySource"
+
+
+@pytest.mark.asyncio
+async def test_attribution_username_fallback() -> None:
+    # If username is None, fall back to display name in {source_username}
+    step = AttributionStep()
+    ctx = make_context(True, "prefix", "Author: {source_username}", "MySource", None, None, "Hello")
+    res = await step.apply(ctx)
+    assert res.text == "Author: MySource\nHello"
+
+
+@pytest.mark.asyncio
+async def test_attribution_with_media_prefix() -> None:
+    step = AttributionStep()
+    ctx = make_context(True, "prefix", "Credits: {source_name}", "MySource", "src_user", "photo_obj", "Hello", caption="My Caption")
+    res = await step.apply(ctx)
+    # Applies to caption, text is untouched
+    assert res.text == "Hello"
+    assert res.caption == "Credits: MySource\nMy Caption"
+
+
+@pytest.mark.asyncio
+async def test_attribution_with_media_empty_caption() -> None:
+    step = AttributionStep()
+    ctx = make_context(True, "suffix", "Credits: {source_name}", "MySource", "src_user", "photo_obj", "Hello", caption=None)
+    res = await step.apply(ctx)
+    assert res.text == "Hello"
+    assert res.caption == "Credits: MySource"
diff --git a/forward-bot/tests/application/pipeline/steps/test_empty_check.py b/forward-bot/tests/application/pipeline/steps/test_empty_check.py
new file mode 100644
index 0000000..c5ce259
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_empty_check.py
@@ -0,0 +1,59 @@
+"""Unit tests for EmptyCheckStep."""
+import pytest
+from unittest.mock import MagicMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
+from forward_bot.domain.entities.source import Source
+from forward_bot.application.pipeline.steps.empty_check import EmptyCheckStep
+
+
+def make_context(text: str, caption: str | None, media) -> PipelineContext:
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan"
+    )
+    source = MagicMock(spec=Source)
+    return PipelineContext(
+        text=text,
+        caption=caption,
+        media=media,
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_empty_check_all_empty() -> None:
+    step = EmptyCheckStep()
+    ctx = make_context("", None, None)
+    res = await step.apply(ctx)
+    assert isinstance(res, BlockedOutcome)
+    assert res.reason == "empty_after_processing"
+
+
+@pytest.mark.asyncio
+async def test_empty_check_has_text() -> None:
+    step = EmptyCheckStep()
+    ctx = make_context("Hello", None, None)
+    res = await step.apply(ctx)
+    assert isinstance(res, PipelineContext)
+
+
+@pytest.mark.asyncio
+async def test_empty_check_has_caption() -> None:
+    step = EmptyCheckStep()
+    ctx = make_context("", "My Caption", None)
+    res = await step.apply(ctx)
+    assert isinstance(res, PipelineContext)
+
+
+@pytest.mark.asyncio
+async def test_empty_check_has_media() -> None:
+    step = EmptyCheckStep()
+    ctx = make_context("", None, "photo_object")
+    res = await step.apply(ctx)
+    assert isinstance(res, PipelineContext)
diff --git a/forward-bot/tests/application/pipeline/steps/test_hashtag_removal.py b/forward-bot/tests/application/pipeline/steps/test_hashtag_removal.py
new file mode 100644
index 0000000..d82691f
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_hashtag_removal.py
@@ -0,0 +1,44 @@
+"""Unit tests for HashtagRemovalStep."""
+import pytest
+from unittest.mock import MagicMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
+from forward_bot.domain.entities.source import Source
+from forward_bot.application.pipeline.steps.hashtag_removal import HashtagRemovalStep
+
+
+def make_context(remove_hashtags: bool, text: str, caption: str | None = None) -> PipelineContext:
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan",
+        remove_hashtags=remove_hashtags
+    )
+    source = MagicMock(spec=Source)
+    return PipelineContext(
+        text=text,
+        caption=caption,
+        media="photo",
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_hashtag_removal_disabled() -> None:
+    step = HashtagRemovalStep()
+    ctx = make_context(False, "Check #news and #sports")
+    res = await step.apply(ctx)
+    assert res.text == "Check #news and #sports"
+
+
+@pytest.mark.asyncio
+async def test_hashtag_removal_enabled() -> None:
+    step = HashtagRemovalStep()
+    ctx = make_context(True, "Check #news and #sports", "Important #info")
+    res = await step.apply(ctx)
+    assert res.text == "Check  and "
+    assert res.caption == "Important "
diff --git a/forward-bot/tests/application/pipeline/steps/test_link_removal.py b/forward-bot/tests/application/pipeline/steps/test_link_removal.py
new file mode 100644
index 0000000..ad29168
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_link_removal.py
@@ -0,0 +1,50 @@
+"""Unit tests for LinkRemovalStep."""
+import pytest
+from unittest.mock import MagicMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
+from forward_bot.domain.entities.source import Source
+from forward_bot.application.pipeline.steps.link_removal import LinkRemovalStep
+
+
+def make_context(remove_links: bool, text: str, caption: str | None = None) -> PipelineContext:
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan",
+        remove_links=remove_links
+    )
+    source = MagicMock(spec=Source)
+    return PipelineContext(
+        text=text,
+        caption=caption,
+        media="photo",
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_link_removal_disabled() -> None:
+    step = LinkRemovalStep()
+    ctx = make_context(False, "Check https://t.me/mychan")
+    res = await step.apply(ctx)
+    assert res.text == "Check https://t.me/mychan"
+
+
+@pytest.mark.asyncio
+async def test_link_removal_enabled() -> None:
+    step = LinkRemovalStep()
+    ctx = make_context(
+        remove_links=True,
+        text="Visit http://example.com/abc or https://google.com. Join t.me/joinchat/12345.",
+        caption="Telegram tg://resolve?domain=xyz or telegram.me/mychan"
+    )
+    res = await step.apply(ctx)
+    # The links are stripped, trailing spaces collapsed/stripped in the next steps,
+    # but here they are just replaced by "".
+    assert res.text == "Visit  or . Join ."
+    assert res.caption == "Telegram  or "
diff --git a/forward-bot/tests/application/pipeline/steps/test_media_decision.py b/forward-bot/tests/application/pipeline/steps/test_media_decision.py
new file mode 100644
index 0000000..06ab4ad
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_media_decision.py
@@ -0,0 +1,67 @@
+"""Unit tests for MediaDecisionStep."""
+import pytest
+from unittest.mock import MagicMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
+from forward_bot.domain.entities.source import Source
+from forward_bot.application.pipeline.steps.media_decision import MediaDecisionStep
+
+
+def make_context(forward_media: str, media, text: str, caption: str | None) -> PipelineContext:
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan",
+        forward_media=forward_media
+    )
+    source = MagicMock(spec=Source)
+    return PipelineContext(
+        text=text,
+        caption=caption,
+        media=media,
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_media_decision_forward() -> None:
+    step = MediaDecisionStep()
+    ctx = make_context("forward", "photo_object", "Hello", "Caption Text")
+    res = await step.apply(ctx)
+    assert res.media == "photo_object"
+    assert res.caption == "Caption Text"
+
+
+@pytest.mark.asyncio
+async def test_media_decision_ignore() -> None:
+    step = MediaDecisionStep()
+    ctx = make_context("ignore", "photo_object", "Hello", "Caption Text")
+    res = await step.apply(ctx)
+    assert res.media is None
+    assert res.caption is None
+
+
+@pytest.mark.asyncio
+async def test_media_decision_caption_only_with_text() -> None:
+    step = MediaDecisionStep()
+    # If text is present, caption is retained as caption
+    ctx = make_context("caption_only", "photo_object", "Hello", "Caption Text")
+    res = await step.apply(ctx)
+    assert res.media is None
+    assert res.caption == "Caption Text"
+    assert res.text == "Hello"
+
+
+@pytest.mark.asyncio
+async def test_media_decision_caption_only_no_text() -> None:
+    step = MediaDecisionStep()
+    # If text is empty/None, caption is promoted to text
+    ctx = make_context("caption_only", "photo_object", "", "Caption Text")
+    res = await step.apply(ctx)
+    assert res.media is None
+    assert res.caption is None
+    assert res.text == "Caption Text"
diff --git a/forward-bot/tests/application/pipeline/steps/test_media_replacement.py b/forward-bot/tests/application/pipeline/steps/test_media_replacement.py
new file mode 100644
index 0000000..0e79dee
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_media_replacement.py
@@ -0,0 +1,145 @@
+"""Unit tests for MediaReplacementStep."""
+import pytest
+from unittest.mock import MagicMock, patch
+from pathlib import Path
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule, MediaReplacementConfig
+from forward_bot.domain.entities.source import Source
+from forward_bot.application.pipeline.steps.media_replacement import MediaReplacementStep
+
+
+def make_context(
+    enabled: bool,
+    path: str | None,
+    mode: str,
+    media="original_photo",
+    caption="Original Caption"
+) -> PipelineContext:
+    config = MediaReplacementConfig(
+        enabled=enabled,
+        replacement_image_path=path,
+        replacement_caption_mode=mode
+    )
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan",
+        media_replacement=config
+    )
+    rule.id = "rule_1"
+    source = MagicMock(spec=Source)
+    return PipelineContext(
+        text="Hello",
+        caption=caption,
+        media=media,
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_media_replacement_disabled() -> None:
+    step = MediaReplacementStep()
+    ctx = make_context(False, "image.png", "use_source")
+    res = await step.apply(ctx)
+    assert res.media == "original_photo"
+
+
+@pytest.mark.asyncio
+async def test_media_replacement_no_media_in_ctx() -> None:
+    step = MediaReplacementStep()
+    ctx = make_context(True, "image.png", "use_source", media=None)
+    res = await step.apply(ctx)
+    assert res.media is None
+
+
+@pytest.mark.asyncio
+async def test_media_replacement_missing_image_path() -> None:
+    step = MediaReplacementStep()
+    ctx = make_context(True, None, "use_source")
+    res = await step.apply(ctx)
+    assert res.media == "original_photo"
+
+
+@pytest.mark.asyncio
+async def test_media_replacement_success(tmp_path) -> None:
+    base_dir = tmp_path / "replacement-images"
+    base_dir.mkdir()
+    repl_file = base_dir / "logo.png"
+    repl_file.write_text("dummy image")
+
+    step = MediaReplacementStep()
+    ctx = make_context(True, "logo.png", "use_source")
+
+    mock_settings = MagicMock()
+    mock_settings.media_replacement_base_dir = str(base_dir)
+
+    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
+        res = await step.apply(ctx)
+
+    assert isinstance(res.media, Path)
+    assert res.media.resolve() == repl_file.resolve()
+    assert res.caption == "Original Caption"
+
+
+@pytest.mark.asyncio
+async def test_media_replacement_caption_modes(tmp_path) -> None:
+    base_dir = tmp_path / "replacement-images"
+    base_dir.mkdir()
+    repl_file = base_dir / "logo.png"
+    repl_file.write_text("dummy image")
+
+    mock_settings = MagicMock()
+    mock_settings.media_replacement_base_dir = str(base_dir)
+
+    # 1. Mode: none -> caption set to None
+    step = MediaReplacementStep()
+    ctx1 = make_context(True, "logo.png", "none", caption="Original Caption")
+    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
+        res1 = await step.apply(ctx1)
+    assert res1.caption is None
+
+    # 2. Mode: use_replacement -> caption set to None
+    ctx2 = make_context(True, "logo.png", "use_replacement", caption="Original Caption")
+    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
+        res2 = await step.apply(ctx2)
+    assert res2.caption is None
+
+
+@pytest.mark.asyncio
+async def test_media_replacement_path_traversal(tmp_path) -> None:
+    base_dir = tmp_path / "replacement-images"
+    base_dir.mkdir()
+
+    step = MediaReplacementStep()
+    ctx = make_context(True, "../traversal.png", "use_source")
+
+    mock_settings = MagicMock()
+    mock_settings.media_replacement_base_dir = str(base_dir)
+
+    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
+        res = await step.apply(ctx)
+
+    # Should fall back to the original photo
+    assert res.media == "original_photo"
+
+
+@pytest.mark.asyncio
+async def test_media_replacement_file_not_found(tmp_path) -> None:
+    base_dir = tmp_path / "replacement-images"
+    base_dir.mkdir()
+
+    step = MediaReplacementStep()
+    ctx = make_context(True, "nonexistent.png", "use_source")
+
+    mock_settings = MagicMock()
+    mock_settings.media_replacement_base_dir = str(base_dir)
+
+    with patch("forward_bot.application.pipeline.steps.media_replacement.Settings", return_value=mock_settings):
+        res = await step.apply(ctx)
+
+    # Should fall back to the original photo
+    assert res.media == "original_photo"
diff --git a/forward-bot/tests/application/pipeline/steps/test_mention_removal.py b/forward-bot/tests/application/pipeline/steps/test_mention_removal.py
new file mode 100644
index 0000000..5f13425
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_mention_removal.py
@@ -0,0 +1,44 @@
+"""Unit tests for MentionRemovalStep."""
+import pytest
+from unittest.mock import MagicMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
+from forward_bot.domain.entities.source import Source
+from forward_bot.application.pipeline.steps.mention_removal import MentionRemovalStep
+
+
+def make_context(remove_mentions: bool, text: str, caption: str | None = None) -> PipelineContext:
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan",
+        remove_mentions=remove_mentions
+    )
+    source = MagicMock(spec=Source)
+    return PipelineContext(
+        text=text,
+        caption=caption,
+        media="photo",
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_mention_removal_disabled() -> None:
+    step = MentionRemovalStep()
+    ctx = make_context(False, "Check @user and @admin")
+    res = await step.apply(ctx)
+    assert res.text == "Check @user and @admin"
+
+
+@pytest.mark.asyncio
+async def test_mention_removal_enabled() -> None:
+    step = MentionRemovalStep()
+    ctx = make_context(True, "Check @user and @admin", "Important @info")
+    res = await step.apply(ctx)
+    assert res.text == "Check  and "
+    assert res.caption == "Important "
diff --git a/forward-bot/tests/application/pipeline/steps/test_reply_lookup.py b/forward-bot/tests/application/pipeline/steps/test_reply_lookup.py
new file mode 100644
index 0000000..be9867a
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_reply_lookup.py
@@ -0,0 +1,84 @@
+"""Unit tests for ReplyLookupStep."""
+import pytest
+from unittest.mock import MagicMock, AsyncMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
+from forward_bot.domain.entities.source import Source
+from forward_bot.domain.entities.message_mapping import MessageMapping
+from forward_bot.application.pipeline.steps.reply_lookup import ReplyLookupStep
+
+
+def make_context(reply_to_msg_id: int | None) -> PipelineContext:
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan"
+    )
+    rule.id = "rule_1"
+    source = MagicMock(spec=Source)
+    source.telegram_id = 98765
+    metadata = {}
+    if reply_to_msg_id is not None:
+        metadata["reply_to_msg_id"] = reply_to_msg_id
+    return PipelineContext(
+        text="Hello",
+        caption=None,
+        media=None,
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata=metadata
+    )
+
+
+@pytest.mark.asyncio
+async def test_reply_lookup_no_reply_id() -> None:
+    step = ReplyLookupStep(MagicMock())
+    ctx = make_context(None)
+    res = await step.apply(ctx)
+    assert res.reply_target_destination_id is None
+
+
+@pytest.mark.asyncio
+async def test_reply_lookup_no_repo() -> None:
+    step = ReplyLookupStep(None)
+    ctx = make_context(123)
+    res = await step.apply(ctx)
+    assert res.reply_target_destination_id is None
+
+
+@pytest.mark.asyncio
+async def test_reply_lookup_parent_found() -> None:
+    mock_repo = MagicMock()
+    mock_mapping = MagicMock(spec=MessageMapping)
+    mock_mapping.destination_message_id = 45678
+    mock_repo.get_by_source_message = AsyncMock(return_value=mock_mapping)
+
+    step = ReplyLookupStep(mock_repo)
+    ctx = make_context(123)
+    res = await step.apply(ctx)
+
+    assert res.reply_target_destination_id == 45678
+    mock_repo.get_by_source_message.assert_called_once_with(
+        source_channel_id=98765,
+        source_message_id=123,
+        forwarding_rule_id="rule_1"
+    )
+
+
+@pytest.mark.asyncio
+async def test_reply_lookup_parent_not_found() -> None:
+    mock_repo = MagicMock()
+    mock_repo.get_by_source_message = AsyncMock(return_value=None)
+
+    step = ReplyLookupStep(mock_repo)
+    ctx = make_context(123)
+    res = await step.apply(ctx)
+
+    assert res.reply_target_destination_id is None
+    mock_repo.get_by_source_message.assert_called_once_with(
+        source_channel_id=98765,
+        source_message_id=123,
+        forwarding_rule_id="rule_1"
+    )
diff --git a/forward-bot/tests/application/pipeline/steps/test_source_ref_replace.py b/forward-bot/tests/application/pipeline/steps/test_source_ref_replace.py
new file mode 100644
index 0000000..9a8e4f1
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_source_ref_replace.py
@@ -0,0 +1,99 @@
+"""Unit tests for SourceRefReplaceStep."""
+import pytest
+from unittest.mock import MagicMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule, AutoReplaceSourceRefsConfig
+from forward_bot.domain.entities.source import Source
+from forward_bot.application.pipeline.steps.source_ref_replace import SourceRefReplaceStep
+
+
+def make_context(
+    enabled: bool,
+    replacement: str | None,
+    replace_display_name: bool,
+    source_username: str | None,
+    display_name: str,
+    text: str,
+    caption: str | None = None
+) -> PipelineContext:
+    config = AutoReplaceSourceRefsConfig(
+        enabled=enabled,
+        replacement=replacement,
+        replace_display_name=replace_display_name
+    )
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan",
+        auto_replace_source_refs=config
+    )
+    source = MagicMock(spec=Source)
+    source.telegram_username = source_username
+    source.display_name = display_name
+    return PipelineContext(
+        text=text,
+        caption=caption,
+        media="photo",
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_source_ref_replace_disabled() -> None:
+    step = SourceRefReplaceStep()
+    ctx = make_context(False, None, False, "src_user", "MySource", "Post @src_user")
+    res = await step.apply(ctx)
+    assert res.text == "Post @src_user"
+
+
+@pytest.mark.asyncio
+async def test_source_ref_replace_username_default() -> None:
+    step = SourceRefReplaceStep()
+    ctx = make_context(
+        enabled=True,
+        replacement=None,
+        replace_display_name=False,
+        source_username="src_user",
+        display_name="MySource",
+        text="Visit https://t.me/src_user or check t.me/Src_User or mention @src_user",
+        caption="From @SRC_USER"
+    )
+    res = await step.apply(ctx)
+    assert res.text == "Visit https://t.me/dest_chan or check t.me/dest_chan or mention @dest_chan"
+    assert res.caption == "From @dest_chan"
+
+
+@pytest.mark.asyncio
+async def test_source_ref_replace_username_custom() -> None:
+    step = SourceRefReplaceStep()
+    ctx = make_context(
+        enabled=True,
+        replacement="@custom_repl",
+        replace_display_name=False,
+        source_username="src_user",
+        display_name="MySource",
+        text="Check @src_user",
+    )
+    res = await step.apply(ctx)
+    assert res.text == "Check @custom_repl"
+
+
+@pytest.mark.asyncio
+async def test_source_ref_replace_display_name() -> None:
+    step = SourceRefReplaceStep()
+    # Case-sensitive replace display_name.
+    # Note: Text contains "MySource" (exact match) and "mysource" (lower, should not replace display name).
+    ctx = make_context(
+        enabled=True,
+        replacement="@custom_repl",
+        replace_display_name=True,
+        source_username=None,
+        display_name="MySource",
+        text="From MySource (not mysource)",
+    )
+    res = await step.apply(ctx)
+    assert res.text == "From @custom_repl (not mysource)"
diff --git a/forward-bot/tests/application/pipeline/steps/test_text_replacement.py b/forward-bot/tests/application/pipeline/steps/test_text_replacement.py
new file mode 100644
index 0000000..42a6925
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_text_replacement.py
@@ -0,0 +1,121 @@
+"""Unit tests for TextReplacementStep."""
+import pytest
+import re
+from datetime import datetime
+from unittest.mock import MagicMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
+from forward_bot.domain.entities.replacement_rule import ReplacementRule
+from forward_bot.domain.entities.source import Source
+from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder, CompiledPatterns
+from forward_bot.application.pipeline.steps.text_replacement import TextReplacementStep
+
+
+def make_context(text: str, caption: str | None = None) -> PipelineContext:
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan"
+    )
+    rule.id = "rule_1"
+    source = MagicMock(spec=Source)
+    return PipelineContext(
+        text=text,
+        caption=caption,
+        media=None,
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_text_replacement_no_replacements() -> None:
+    CacheHolder.current = RuleCache()  # Empty cache
+    step = TextReplacementStep()
+    ctx = make_context("Hello World")
+    res = await step.apply(ctx)
+    assert res.text == "Hello World"
+
+
+@pytest.mark.asyncio
+async def test_text_replacement_literal_and_regex_ordered() -> None:
+    # Set up some rules:
+    # Rule 1: Literal, replace "apple" with "banana", created at T1
+    # Rule 2: Regex, replace "ba(na){2}" with "cherry", created at T2
+    # Rule 3: Inactive, replace "cherry" with "nothing", created at T3
+    r1 = ReplacementRule(
+        forwarding_rule_id="rule_1",
+        search_text="apple",
+        replacement_text="banana",
+        match_mode="literal",
+        is_active=True,
+        id="r1",
+        created_at=datetime(2026, 6, 1, 12, 0)
+    )
+    r2 = ReplacementRule(
+        forwarding_rule_id="rule_1",
+        search_text=r"ba(na){2}",
+        replacement_text="cherry",
+        match_mode="regex",
+        is_active=True,
+        id="r2",
+        created_at=datetime(2026, 6, 1, 13, 0)
+    )
+    r3 = ReplacementRule(
+        forwarding_rule_id="rule_1",
+        search_text="cherry",
+        replacement_text="nothing",
+        match_mode="literal",
+        is_active=False,
+        id="r3",
+        created_at=datetime(2026, 6, 1, 14, 0)
+    )
+
+    # Compile regex pattern for Rule 2 in CompiledPatterns
+    compiled_patterns = CompiledPatterns(
+        replacement_patterns={"r2": re.compile(r"ba(na){2}", re.IGNORECASE)}
+    )
+
+    # Populate cache
+    cache = RuleCache(
+        replacements={"rule_1": [r2, r3, r1]},  # Out of order to test sorting
+        compiled_patterns={"rule_1": compiled_patterns}
+    )
+    CacheHolder.current = cache
+
+    step = TextReplacementStep()
+    
+    # "Apple" (literal, case-insensitive) becomes "banana" (first rule applied)
+    # Then "banana" matches "ba(na){2}" (regex) and becomes "cherry"
+    # Rule 3 is inactive, so "cherry" remains "cherry"
+    ctx = make_context("I love Apple pie.")
+    res = await step.apply(ctx)
+    assert res.text == "I love cherry pie."
+
+
+@pytest.mark.asyncio
+async def test_text_replacement_regex_dynamic_fallback() -> None:
+    # If compiled pattern is missing from CompiledPatterns, dynamically compile it.
+    r1 = ReplacementRule(
+        forwarding_rule_id="rule_1",
+        search_text=r"\d+",
+        replacement_text="NUM",
+        match_mode="regex",
+        is_active=True,
+        id="r1",
+        created_at=datetime(2026, 6, 1, 12, 0)
+    )
+    
+    cache = RuleCache(
+        replacements={"rule_1": [r1]},
+        compiled_patterns={}  # Missing compiled patterns
+    )
+    CacheHolder.current = cache
+
+    step = TextReplacementStep()
+    ctx = make_context("Code 123 and 456")
+    res = await step.apply(ctx)
+    assert res.text == "Code NUM and NUM"
diff --git a/forward-bot/tests/application/pipeline/steps/test_whitespace.py b/forward-bot/tests/application/pipeline/steps/test_whitespace.py
new file mode 100644
index 0000000..e9e07ec
--- /dev/null
+++ b/forward-bot/tests/application/pipeline/steps/test_whitespace.py
@@ -0,0 +1,38 @@
+"""Unit tests for WhitespaceStep."""
+import pytest
+from unittest.mock import MagicMock
+from forward_bot.domain.entities.pipeline_context import PipelineContext
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
+from forward_bot.domain.entities.source import Source
+from forward_bot.application.pipeline.steps.whitespace import WhitespaceStep
+
+
+def make_context(text: str, caption: str | None = None) -> PipelineContext:
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan"
+    )
+    source = MagicMock(spec=Source)
+    return PipelineContext(
+        text=text,
+        caption=caption,
+        media=None,
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="corr-123",
+        rule=rule,
+        source=source,
+        metadata={}
+    )
+
+
+@pytest.mark.asyncio
+async def test_whitespace_normalization() -> None:
+    step = WhitespaceStep()
+    ctx = make_context(
+        text="   Hello    World!  \n\n\n  Next   Line.   ",
+        caption="\tCaption\t\tWith\tTabs\n\nAnd   Newlines\t"
+    )
+    res = await step.apply(ctx)
+    assert res.text == "Hello World!\nNext Line."
+    assert res.caption == "Caption With Tabs\nAnd Newlines"
diff --git a/forward-bot/tests/application/pipeline/test_engine.py b/forward-bot/tests/application/pipeline/test_engine.py
index 89cb4fb..35c7a57 100644
--- a/forward-bot/tests/application/pipeline/test_engine.py
+++ b/forward-bot/tests/application/pipeline/test_engine.py
@@ -126,3 +126,79 @@ async def test_engine_default_steps_execution(mock_context) -> None:
     assert result.metadata["destination_channel_id"] == 99999
     # Check that PersistMappingStep called mock_repo.add_mapping
     mock_repo.add_mapping.assert_called_once()
+
+
+@pytest.mark.asyncio
+async def test_engine_steps_6_to_16_integration() -> None:
+    from datetime import datetime
+    from forward_bot.domain.entities.forwarding_rule import AutoReplaceSourceRefsConfig, AttributionConfig
+    from forward_bot.domain.entities.replacement_rule import ReplacementRule
+    from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder
+
+    rule = ForwardingRule(
+        source_id="65c52c6f1f2e3d4a5b6c7d81",
+        destination_channel="dest_chan",
+        remove_links=True,
+        remove_hashtags=True,
+        remove_mentions=True,
+        forward_media="caption_only",
+        auto_replace_source_refs=AutoReplaceSourceRefsConfig(
+            enabled=True,
+            replace_display_name=True
+        ),
+        attribution=AttributionConfig(
+            enabled=True,
+            position="suffix",
+            format="From {source_name}"
+        )
+    )
+    rule.id = "rule_1"
+
+    source = MagicMock(spec=Source)
+    source.telegram_id = 12345
+    source.telegram_username = "src_user"
+    source.display_name = "MySource"
+
+    rr = ReplacementRule(
+        forwarding_rule_id="rule_1",
+        search_text="awesome",
+        replacement_text="incredible",
+        match_mode="literal",
+        is_active=True,
+        id="rr1",
+        created_at=datetime(2026, 6, 1, 12, 0)
+    )
+
+    CacheHolder.current = RuleCache(
+        replacements={"rule_1": [rr]},
+        compiled_patterns={}
+    )
+
+    mock_mapping_repo = MagicMock()
+    mock_mapping_repo.get_by_source_message = AsyncMock(return_value=None)
+    mock_mapping_repo.add_mapping = AsyncMock()
+
+    engine = PipelineEngine(mapping_repository=mock_mapping_repo)
+
+    media = MagicMock()
+    media.type_name = "photo"
+
+    ctx = PipelineContext(
+        text="",
+        caption="Visit http://t.me/src_user. #hash @mention. This is awesome by MySource.",
+        media=media,
+        attribution_decided=False,
+        reply_target_destination_id=None,
+        correlation_id="xyz12345",
+        rule=rule,
+        source=source,
+        metadata={"source_message_id": 123456}
+    )
+
+    result = await engine.execute(ctx)
+    assert isinstance(result, PipelineContext)
+    assert "incredible" in result.text
+    assert "dest_chan" in result.text
+    assert "From MySource" in result.text
+    assert result.media is None
+    assert result.caption is None

</diff>
