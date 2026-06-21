Please act as the Blind Hunter subagent and use the bmad-review-adversarial-general skill to review the following diff:

diff --git a/_bmad-output/implementation-artifacts/3-2-replacement-rule-crud-api.md b/_bmad-output/implementation-artifacts/3-2-replacement-rule-crud-api.md
index 162b2b7..a8df3b5 100644
--- a/_bmad-output/implementation-artifacts/3-2-replacement-rule-crud-api.md
+++ b/_bmad-output/implementation-artifacts/3-2-replacement-rule-crud-api.md
@@ -4,7 +4,7 @@ baseline_commit: 57848c6e377c8a087419ba5f23ff93b6c46e006b
 
 # Story 3.2: Replacement Rule CRUD API
 
-Status: review
+Status: done
 
 ## Story
 
@@ -145,6 +145,11 @@ so that **I can rewrite forwarded text GÇö removing competitor names, swapping l
     - Cascade delete verified (parent delete removes children GÇö integration test)
   - [x] All 182 tests pass (35 new + 147 regression GÇö 0 failures)
 
+### Review Findings
+
+- [x] [Review][Patch] Microsecond timestamp collision in pipeline sorting [forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py:70-81]
+- [x] [Review][Patch] Missing `created_at` and `updated_at` optionality in response schema [forward-bot/src/forward_bot/api/schemas/replacement_rule.py:50-51]
+
 ---
 
 ## Dev Notes
diff --git a/_bmad-output/implementation-artifacts/deferred-work.md b/_bmad-output/implementation-artifacts/deferred-work.md
index 33a2081..27a964b 100644
--- a/_bmad-output/implementation-artifacts/deferred-work.md
+++ b/_bmad-output/implementation-artifacts/deferred-work.md
@@ -40,3 +40,12 @@ The epic spec does not cover what happens when `POST /api/v1/sources` is called
 - Raises `ValueError` for unknown references; `ChannelPrivateError` for private channels; `UsernameNotOccupiedError` for non-existent usernames GÇö all should map to `telegram_resolve_failed` (HTTP 422)
 - Rate limiting: Telegram allows ~30 resolve calls/second; safe for typical operator usage but document in dev notes
 
+## Deferred from: code review of 3-3-atomic-rule-cache-cache-refresher.md (2026-06-18)
+
+- ~~**Sequential O(N) database queries for replacement rules**~~: **RESOLVED** (2026-06-19, Epic 3 Retro)
+  Added `ReplacementRuleRepository.list_all_replacements_for_rules(rule_ids)` GÇö a single `$in` query that fetches all replacement rules for all active rules in one MongoDB round-trip, then groups in-memory. `build_rule_cache` now performs exactly 4 DB queries regardless of rule count (was 4+N). `cache_refresher.py` updated; tests updated in `test_cache_refresher.py`.
+
+## Resolved during: Epic 3 Retrospective (2026-06-19)
+
+- **`_id`/`id` Pydantic v2 serialization-alias pattern documented**: `MongoBaseModel` docstring in `api/schemas/base.py` now contains the definitive two-pattern guide (Pattern A: alias-only subclass; Pattern B: subclass with extra `@field_validator`). Common mistakes listed. Prevents recurrence of the duplicate-validator Pydantic error in Epic 6 schemas.
+
diff --git a/_bmad-output/implementation-artifacts/diff-for-review.diff b/_bmad-output/implementation-artifacts/diff-for-review.diff
index f9d423b..4e367da 100644
Binary files a/_bmad-output/implementation-artifacts/diff-for-review.diff and b/_bmad-output/implementation-artifacts/diff-for-review.diff differ
diff --git a/_bmad-output/implementation-artifacts/prompt-acceptance-auditor.md b/_bmad-output/implementation-artifacts/prompt-acceptance-auditor.md
index e7143a1..c70cacd 100644
--- a/_bmad-output/implementation-artifacts/prompt-acceptance-auditor.md
+++ b/_bmad-output/implementation-artifacts/prompt-acceptance-auditor.md
@@ -1,9 +1,9 @@
 # Acceptance Auditor Review
 
-You are an Acceptance Auditor. Review the diff in `c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\diff-for-review.diff` against the spec in `c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\3-1-forwarding-rule-crud-api.md`.
+You are an Acceptance Auditor. Review the diff in `c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\diff-for-review.diff` against the spec in `c:\Users\hitesh.paliwal\Documents\GitHub\Forward-Bot\_bmad-output\implementation-artifacts\3-2-replacement-rule-crud-api.md`.
 
 Check for:
-1. Violations of acceptance criteria (AC 1 through AC 14).
+1. Violations of acceptance criteria (AC 1 through AC 9).
 2. Deviations from spec intent.
 3. Missing implementation of specified behavior.
 4. Contradictions between spec constraints and actual code.
diff --git a/_bmad-output/implementation-artifacts/sprint-status.yaml b/_bmad-output/implementation-artifacts/sprint-status.yaml
index a1dff1a..a13c58b 100644
--- a/_bmad-output/implementation-artifacts/sprint-status.yaml
+++ b/_bmad-output/implementation-artifacts/sprint-status.yaml
@@ -1,7 +1,7 @@
 # Sprint Status Tracking for Forward Bot
 # =======================================
 # Generated: 2026-06-02
-# Last Updated: 2026-06-18
+# Last Updated: 2026-06-19
 # Project: Forward Bot
 # Project Key: NOKEY
 # Tracking System: file-system
@@ -33,7 +33,7 @@
 # - Dev moves story to 'review', then runs code-review (fresh context, different LLM recommended)
 
 generated: "2026-06-02"
-last_updated: "2026-06-18"
+last_updated: "2026-06-19"
 work_started: "2026-06-02"
 work_completed: "2026-06-09"
 first_story_created: "2026-06-02"
@@ -66,18 +66,18 @@ development_status:
   epic-2-retrospective: done
 
   # ===== EPIC 3: Forwarding Rule Configuration =====
-  epic-3: in-progress
+  epic-3: done
 
   3-1-forwarding-rule-crud-api: done
-  3-2-replacement-rule-crud-api: review
-  3-3-atomic-rule-cache-cache-refresher: backlog
+  3-2-replacement-rule-crud-api: done
+  3-3-atomic-rule-cache-cache-refresher: done
 
-  epic-3-retrospective: optional
+  epic-3-retrospective: done
 
   # ===== EPIC 4: Core Message Forwarding Engine =====
-  epic-4: backlog
+  epic-4: in-progress
 
-  4-1-pipeline-infrastructure-context-protocol-engine-message-mapping: backlog
+  4-1-pipeline-infrastructure-context-protocol-engine-message-mapping: review
   4-2-filter-pipeline-steps-steps-1-5: backlog
   4-3-transform-media-pipeline-steps-steps-6-16: backlog
   4-4-telegram-delivery-reliability: backlog
@@ -113,18 +113,18 @@ summary:
   total_stories: 24
   total_retrospectives: 6
 
-  epics_backlog: 3
+  epics_backlog: 2
   epics_in_progress: 1
-  epics_done: 2
+  epics_done: 3
 
-  stories_backlog: 16
+  stories_backlog: 14
   stories_ready_for_dev: 0
   stories_in_progress: 0
   stories_in_review: 1
-  stories_done: 7
+  stories_done: 9
 
-  retrospectives_optional: 4
-  retrospectives_done: 2
+  retrospectives_optional: 3
+  retrospectives_done: 3
 
 # STORY ORDERING & DEPENDENCIES
 # ==============================
diff --git a/_bmad-output/implementation-artifacts/tests/test-summary.md b/_bmad-output/implementation-artifacts/tests/test-summary.md
index 2c83813..b405724 100644
--- a/_bmad-output/implementation-artifacts/tests/test-summary.md
+++ b/_bmad-output/implementation-artifacts/tests/test-summary.md
@@ -2,9 +2,9 @@
 
 **Framework:** pytest 9.0.3 + pytest-asyncio 1.4.0 (Python 3.13.3)  
 **Test Suites:**
-- E2E Tests: [`tests/e2e/test_epic1_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic1_e2e.py), [`tests/e2e/test_epic2_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic2_e2e.py)
-- API Tests: [`tests/api/test_folders.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_folders.py), [`tests/api/test_sources.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_sources.py), [`tests/api/test_health.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_health.py)
-- Repository & Client Tests: [`tests/infrastructure/mongo/`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/mongo/)
+- E2E Tests: [`tests/e2e/test_epic1_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic1_e2e.py), [`tests/e2e/test_epic2_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic2_e2e.py), [`tests/e2e/test_epic3_e2e.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/e2e/test_epic3_e2e.py)
+- API Tests: [`tests/api/test_rules.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_rules.py), [`tests/api/test_replacement_rules.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_replacement_rules.py), [`tests/api/test_folders.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_folders.py), [`tests/api/test_sources.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_sources.py), [`tests/api/test_health.py`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/api/test_health.py)
+- Repository & Client Tests: [`tests/infrastructure/mongo/`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/mongo/), [`tests/infrastructure/cache/`](file:///c:/Users/hitesh.paliwal/Documents/GitHub/Forward-Bot/forward-bot/tests/infrastructure/cache/)
 
 ---
 
@@ -71,38 +71,108 @@
 
 ---
 
+### Epic 3 GÇö Forwarding Rule Configuration
+
+#### E2E Workflow Test (`test_epic3_e2e_workflow`)
+Single comprehensive test exercising the full HTTP GåÆ use-case GåÆ MockDatabase cycle:
+
+**Story 3.1 GÇö Forwarding Rule CRUD:**
+- Auth gate enforcement (401 without API key).
+- Create rule returns 201 with all 14 default fields verified.
+- Duplicate `(source_id, destination_channel)` pairs permitted (no uniqueness constraint).
+- Non-existent `source_id` GåÆ 422 `source_not_found`.
+- Self-referential rule by username GåÆ 422 `self_referential_rule`.
+- Self-referential rule by Telegram ID string GåÆ 422 `self_referential_rule`.
+- Invalid regex in `block_keywords` GåÆ 422 `invalid_regex`.
+- Invalid regex in `allow_keywords` GåÆ 422 `invalid_regex`.
+- Cross-midnight time window (`end_time < start_time`) accepted GåÆ 201.
+- Invalid IANA timezone GåÆ 422 `invalid_timezone`.
+- `media_replacement.enabled=true` + `null` path GåÆ 422 `media_replacement_path_required`.
+- Get single rule 200 / not-found 404 `rule_not_found`.
+- Enable rule GåÆ 200 `{ok: true}`; `is_active` becomes `true`.
+- Disable rule GåÆ 200 `{ok: true}`; enable/disable on non-existent GåÆ 404.
+- List rules with pagination (total, page, page_size).
+- Filter by `source_id`, `is_active`, `destination_channel`.
+- `page_size` capped at 200.
+- PUT update with all validation rules (invalid source, invalid regex, invalid timezone, not-found).
+- DELETE returns 204; cascade to replacement_rules; delete non-existent GåÆ 404.
+
+**Story 3.2 GÇö Replacement Rule CRUD:**
+- POST to non-existent parent rule GåÆ 404 `rule_not_found`.
+- Create replacement rule GåÆ 201 with all fields including `is_active=true` default.
+- Invalid regex in `search_text` GåÆ 422 `invalid_regex`.
+- List returns ordered by `created_at` ASC (pipeline order).
+- List for non-existent parent GåÆ 404 `rule_not_found`.
+- PUT update refreshes fields; invalid regex GåÆ 422; not-found GåÆ 404 `replacement_rule_not_found`.
+- DELETE GåÆ 204; verify removal from listing; delete non-existent GåÆ 404.
+- Auth gate for replacement-rules endpoints (401 without API key).
+- Cascade delete: deleting parent rule removes all child replacement rules.
+
+#### Story 3.3 GÇö Atomic Rule Cache & Cache Refresher
+
+##### RuleCache Unit Tests (`tests/e2e/test_epic3_e2e.py` + `tests/infrastructure/cache/test_rule_cache.py`)
+- `test_rule_cache_is_frozen`: Mutation of frozen RuleCache raises `AttributeError`/`TypeError`.
+- `test_rule_cache_empty_defaults`: `RuleCache()` with no args is version=0, all fields empty.
+- `test_cache_holder_starts_with_empty_cache`: `CacheHolder.current` is empty at startup.
+- `test_cache_holder_atomic_swap`: Assigning `CacheHolder.current` atomically replaces the snapshot.
+- `test_compiled_patterns_empty_defaults`: `CompiledPatterns` defaults to empty lists/dict.
+- `test_compiled_patterns_with_real_patterns`: `re.Pattern` objects stored and retrievable.
+
+##### Cache Refresher Tests (`tests/e2e/test_epic3_e2e.py` + `tests/infrastructure/cache/test_cache_refresher.py`)
+- `test_build_rule_cache_happy_path`: Fetches all 4 collections, builds valid `RuleCache` with correct version.
+- `test_build_rule_cache_compiles_regex_patterns`: Block/allow/replacement regex patterns are pre-compiled into `CompiledPatterns`.
+- `test_build_rule_cache_skips_invalid_regex`: Invalid regex skipped GÇö `block_patterns` empty; refresh completes; version is set.
+- `test_cache_refresher_retains_snapshot_on_mongodb_failure`: MongoDB failure GåÆ `CacheHolder.current` retains last valid snapshot (version unchanged).
+
+#### API Integration Tests
+
+##### Rules Router (`tests/api/test_rules.py`)
+All 14 ACs from Story 3.1 covered with 25 tests including: happy path create with defaults, duplicate pair permitted, source not found (422), self-referential (username + telegram_id), invalid regex (block + allow), cross-midnight time window, invalid timezone, media_replacement path required, enable/disable (success + not-found), list (pagination + 4 filters), get (200 + 404), PUT (success + validations + not-found), DELETE cascade (204 + 404), auth gate.
+
+##### Replacement Rules Router (`tests/api/test_replacement_rules.py`)
+All 8 ACs from Story 3.2 covered with 10 tests including: happy path create, invalid regex rejection (POST + PUT), parent rule not found (POST + GET), list ordered ASC, update refreshes `updated_at`, delete 204, auth gate, cascade delete.
+
+---
+
 ## Suite Summary & Coverage
 
 | Test Suite | Total Passed | Description |
 |------------|--------------|-------------|
 | `test_epic1_e2e.py` | 52 | E2E foundation client tests |
-| `test_epic2_e2e.py` | 1 | E2E complete workflow test |
+| `test_epic2_e2e.py` | 1 | E2E complete Epic 2 workflow |
+| `test_epic3_e2e.py` | 11 | E2E Epic 3 workflow + cache unit/integration |
+| `test_rules.py` | 25 | Forwarding Rules HTTP API integration tests |
+| `test_replacement_rules.py` | 10 | Replacement Rules HTTP API integration tests |
 | `test_folders.py` | 10 | Folders HTTP API integration tests |
 | `test_sources.py` | 19 | Sources HTTP API integration tests |
 | `test_health.py` | 5 | Health endpoints unit tests |
 | `test_client.py` | 2 | MongoClientHolder unit tests |
-| `test_folder_repository.py` | 2 | Folder repository database mapper tests |
+| `test_folder_repository.py` | 6 | Folder repository + `list_folders` tests |
 | `test_source_repository.py` | 3 | Source repository database mapper tests |
+| `test_rule_repository.py` | 8 | Rule repository (cascade delete, filters, join) |
+| `test_replacement_repository.py` | 14 | Replacement repository mapper + edge cases |
+| `test_rule_cache.py` | 10 | RuleCache / CacheHolder / CompiledPatterns |
+| `test_cache_refresher.py` | 11 | build_rule_cache + run_cache_refresher |
 | `test_telegram_client.py` | 5 | Telegram connection unit tests |
 | `test_config.py` | 7 | Settings validation unit tests |
 
-**Total passing tests in project: 106**  
-**Execution duration: ~3.07 seconds**  
-**Warnings: 2 (FastAPI standard deprecation warning)**  
+**Total passing tests in project: 230**  
+**Execution duration: ~12.27 seconds**  
+**Warnings: 4 (FastAPI standard deprecation warning GÇö `HTTP_422_UNPROCESSABLE_ENTITY`)**
 
 ---
 
 ## Test Run Results
 
 ```
-======================= 106 passed, 2 warnings in 3.07s =======================
+====================== 230 passed, 4 warnings in 12.27s =======================
 ```
 
-All E2E and API integration tests pass with 100% success rate.
+All E2E, API integration, repository, and unit tests pass with 100% success rate.
 
 ---
 
 ## Next Steps
 
-- Integrate Epic 3 (Forwarding Rule Configuration) CRUD endpoints and verify cached rule operations.
-- Implement UI components for folder CRUD modals and source listings matching the new endpoint specs.
+- Integrate Epic 4 (Core Message Forwarding Engine) pipeline steps GÇö the `RuleCache` and `CacheHolder` from Story 3.3 are ready.
+- E2E test for Epic 4 will exercise the full pipeline dispatch cycle (filter + transform + delivery).
diff --git a/_bmad_review_diff.txt b/_bmad_review_diff.txt
index f781803..1202cb5 100644
Binary files a/_bmad_review_diff.txt and b/_bmad_review_diff.txt differ
diff --git a/forward-bot/src/forward_bot/api/schemas/base.py b/forward-bot/src/forward_bot/api/schemas/base.py
index e4c39b9..a27bd67 100644
--- a/forward-bot/src/forward_bot/api/schemas/base.py
+++ b/forward-bot/src/forward_bot/api/schemas/base.py
@@ -15,9 +15,61 @@ SAMPLING_COUNTERS = "sampling_counters"
 
 class MongoBaseModel(BaseModel):
     """Base model for MongoDB documents returned by the API.
-    
-    Converts MongoDB _id to string id, serializes ObjectIds,
-    and formats datetimes as ISO 8601 UTC strings with Z suffix.
+
+    Converts MongoDB ``_id`` to a string ``id`` field, coerces BSON ObjectIds,
+    and serializes datetimes as ISO 8601 UTC strings with a ``Z`` suffix.
+
+    GöÇGöÇ _id / id contract GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
+    MongoDB stores the primary key as ``_id`` (BSON ObjectId).  The API must
+    expose it as ``"id"`` (plain string) in JSON responses.  This base class
+    handles the mapping via ``Field(alias="_id")``.
+
+    SUBCLASS RULES GÇö read before creating a new response schema:
+
+    Pattern A GÇö no extra field_validator needed on the subclass
+    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+    Use when the subclass does NOT need to validate any other field
+    (e.g. ReplacementRuleResponse, SourceFolderResponse)::
+
+        class MyResponse(MongoBaseModel):
+            # Redeclare only the aliases GÇö never re-add a @field_validator("id").
+            id: str = Field(validation_alias="_id", serialization_alias="id")
+            other_field: str
+
+        @classmethod
+        def from_entity(cls, e) -> "MyResponse":
+            # Always pass "_id" (not "id") as the key to model_validate.
+            return cls.model_validate({"_id": e.id, "other_field": e.x})
+
+    Pattern B GÇö subclass also needs a field_validator on another BSON field
+    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+    Use when another field is stored as ObjectId in MongoDB (e.g. source_id
+    in ForwardingRuleResponse)::
+
+        class MyResponse(MongoBaseModel):
+            id: str = Field(validation_alias="_id", serialization_alias="id")
+            foreign_id: str  # stored as ObjectId in Mongo
+
+            @field_validator("foreign_id", mode="before")
+            @classmethod
+            def coerce_foreign_id(cls, v: Any) -> str:
+                return str(v)
+
+            @classmethod
+            def from_entity(cls, e) -> "MyResponse":
+                return cls.model_validate({"_id": e.id, "foreign_id": e.foreign_id})
+
+    Common mistakes to avoid
+    ~~~~~~~~~~~~~~~~~~~~~~~~
+    - Do NOT add ``@field_validator("id")`` in a subclass GÇö MongoBaseModel
+      already has ``coerce_object_id``.  Pydantic v2 raises a duplicate-validator
+      error at import time.
+    - Do NOT pass ``"id": e.id`` to ``model_validate`` GÇö always use ``"_id"``
+      so the alias chain resolves correctly.
+    - Do NOT use ``Field(alias="_id")`` alone and expect ``"id"`` in the JSON
+      output GÇö you also need ``serialization_alias="id"`` on the subclass field,
+      because ``alias`` controls parsing only.
+    GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
     """
     model_config = ConfigDict(
         populate_by_name=True,
@@ -29,7 +81,7 @@ class MongoBaseModel(BaseModel):
     @field_validator("id", mode="before")
     @classmethod
     def coerce_object_id(cls, v: Any) -> str:
-        """Coerce ObjectId to string."""
+        """Coerce BSON ObjectId to hex string. Safe to call on a plain string."""
         if isinstance(v, ObjectId):
             return str(v)
         return str(v)
diff --git a/forward-bot/src/forward_bot/api/schemas/replacement_rule.py b/forward-bot/src/forward_bot/api/schemas/replacement_rule.py
index af0aea1..49b8420 100644
--- a/forward-bot/src/forward_bot/api/schemas/replacement_rule.py
+++ b/forward-bot/src/forward_bot/api/schemas/replacement_rule.py
@@ -1,6 +1,6 @@
 """Pydantic schemas for Replacement Rule API request/response models."""
 from datetime import datetime
-from typing import Literal
+from typing import Literal, Optional
 
 from pydantic import BaseModel, Field
 
@@ -47,12 +47,11 @@ class ReplacementRuleResponse(MongoBaseModel):
     replacement_text: str
     match_mode: str
     is_active: bool
-    created_at: datetime   # serialized as ISO 8601 UTC string by MongoBaseModel.serialize_dt
-    updated_at: datetime
-    # GÜán+Å created_at and updated_at are non-Optional here. The domain entity uses
-    # Optional[datetime] for flexibility, but use cases MUST always set both to
-    # datetime.now(timezone.utc) before persisting. A None value here will cause
-    # a Pydantic validation error at response serialization time.
+    created_at: Optional[datetime] = None   # serialized as ISO 8601 UTC string by MongoBaseModel.serialize_dt
+    updated_at: Optional[datetime] = None
+    # GÜán+Å created_at and updated_at are Optional[datetime] here to match the domain entity's
+    # representation and allow flexibility in tests. In production, these should
+    # be populated with datetime.now(timezone.utc) before persisting.
 
     @classmethod
     def from_entity(cls, r) -> "ReplacementRuleResponse":
diff --git a/forward-bot/src/forward_bot/app.py b/forward-bot/src/forward_bot/app.py
index db75f33..9037640 100644
--- a/forward-bot/src/forward_bot/app.py
+++ b/forward-bot/src/forward_bot/app.py
@@ -54,6 +54,16 @@ async def default_lifespan(app: FastAPI):
                 await mongo_client.db[REPLACEMENT_RULES].create_index(
                     [("forwarding_rule_id", 1), ("is_active", 1), ("created_at", 1)], background=True
                 )
+                # Message mapping compound index (pre-created for Epic 4 Story 4.1)
+                from forward_bot.api.schemas.base import MESSAGE_MAPPINGS
+                await mongo_client.db[MESSAGE_MAPPINGS].create_index(
+                    [
+                        ("forwarding_rule_id", 1),
+                        ("source_channel_id", 1),
+                        ("source_message_id", 1),
+                    ],
+                    background=True
+                )
                 logger.info("mongodb_indexes_created", message="MongoDB indexes verified/created successfully")
             except Exception as e:
                 logger.error("mongodb_index_creation_failed", error=str(e), message="Failed to create MongoDB indexes")
@@ -73,7 +83,7 @@ async def default_lifespan(app: FastAPI):
         raise e
 
     # Start background task stubs
-    cache_task = asyncio.create_task(run_cache_refresher())
+    cache_task = asyncio.create_task(run_cache_refresher(settings, mongo_client.db))
     sweeper_task = asyncio.create_task(run_mapping_sweeper())
     worker_task = asyncio.create_task(run_telegram_worker())
 
diff --git a/forward-bot/src/forward_bot/application/pipeline/__init__.py b/forward-bot/src/forward_bot/application/pipeline/__init__.py
index e69de29..e344cb8 100644
--- a/forward-bot/src/forward_bot/application/pipeline/__init__.py
+++ b/forward-bot/src/forward_bot/application/pipeline/__init__.py
@@ -0,0 +1,8 @@
+"""Pipeline application package."""
+from forward_bot.application.pipeline.protocol import PipelineStep
+from forward_bot.application.pipeline.engine import PipelineEngine
+
+__all__ = [
+    "PipelineStep",
+    "PipelineEngine",
+]
diff --git a/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py b/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py
index e69de29..8521025 100644
--- a/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py
+++ b/forward-bot/src/forward_bot/application/pipeline/steps/__init__.py
@@ -0,0 +1,42 @@
+"""Pipeline steps application package."""
+from forward_bot.application.pipeline.steps.placeholders import (
+    TimeWindowStep,
+    SamplingStep,
+    MediaTypeFilterStep,
+    BlockKeywordStep,
+    AllowKeywordStep,
+    MediaDecisionStep,
+    ReplyLookupStep,
+    SourceRefReplaceStep,
+    TextReplacementStep,
+    LinkRemovalStep,
+    HashtagRemovalStep,
+    MentionRemovalStep,
+    MediaReplacementStep,
+    WhitespaceStep,
+    AttributionStep,
+    EmptyCheckStep,
+)
+from forward_bot.application.pipeline.steps.deliver import DeliverStep
+from forward_bot.application.pipeline.steps.persist_mapping import PersistMappingStep
+
+__all__ = [
+    "TimeWindowStep",
+    "SamplingStep",
+    "MediaTypeFilterStep",
+    "BlockKeywordStep",
+    "AllowKeywordStep",
+    "MediaDecisionStep",
+    "ReplyLookupStep",
+    "SourceRefReplaceStep",
+    "TextReplacementStep",
+    "LinkRemovalStep",
+    "HashtagRemovalStep",
+    "MentionRemovalStep",
+    "MediaReplacementStep",
+    "WhitespaceStep",
+    "AttributionStep",
+    "EmptyCheckStep",
+    "DeliverStep",
+    "PersistMappingStep",
+]
diff --git a/forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py b/forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py
new file mode 100644
index 0000000..191397c
--- /dev/null
+++ b/forward-bot/src/forward_bot/infrastructure/cache/cache_refresher.py
@@ -0,0 +1,232 @@
+"""Background cache refresher for the forwarding rule pipeline.
+
+Provides two public coroutines:
+
+  - ``build_rule_cache(db, version)``  GÇö fetches all four MongoDB collections,
+    compiles regex patterns, and returns a frozen ``RuleCache`` snapshot.
+  - ``run_cache_refresher(settings, db)`` GÇö long-running background loop that
+    calls ``build_rule_cache`` every ``HOT_RELOAD_INTERVAL`` seconds and
+    atomically replaces ``CacheHolder.current``.
+
+Design decisions
+----------------
+* **Sleep-first pattern**: the refresher sleeps *before* the first build so
+  that the MongoDB connection pool and all startup tasks are fully established
+  before the initial fetch.  The pipeline starts with the empty
+  ``RuleCache()`` (version=0) until the first refresh completes GÇö Epic 4
+  workers tolerate an empty ``rules`` list at startup.
+* **Atomic swap**: ``CacheHolder.current = new_cache`` is a single Python
+  reference assignment, which is atomic under the CPython GIL and the asyncio
+  event loop.  No locking primitives are needed.
+* **Retain last snapshot on failure**: if MongoDB is temporarily unreachable
+  the ``WARNING`` is logged and ``CacheHolder.current`` is left unchanged so
+  the pipeline continues with the last known-good snapshot.
+* **Invalid regex GÇö skip and log**: a ``re.error`` during pattern compilation
+  logs an ``ERROR`` for the offending rule/pattern and skips that pattern.
+  The rest of the refresh completes normally (AC-3).
+* **O(1) DB queries**: the refresh performs exactly 4 MongoDB round-trips
+  (sources, folders, rules, all-replacements-in-one-``$in``-query),
+  regardless of rule count. Previously replacement rules were fetched in an
+  O(N) per-rule loop GÇö this is fixed as of the Epic 3 retrospective.
+"""
+import asyncio
+import re
+from datetime import datetime, timezone
+
+from forward_bot.infrastructure.logging import logger
+from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder, CompiledPatterns
+from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository
+from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository
+from forward_bot.infrastructure.mongo.repositories.rule_repository import ForwardingRuleRepository
+from forward_bot.infrastructure.mongo.repositories.replacement_repository import ReplacementRuleRepository
+
+
+async def build_rule_cache(db, version: int) -> RuleCache:
+    """Fetch all four collections from MongoDB and build an atomic RuleCache snapshot.
+
+    Steps
+    -----
+    1. Fetch all Sources GåÆ ``dict[id, Source]``
+    2. Fetch all Folders GåÆ ``dict[id, SourceFolder]``
+    3. Fetch **active** ForwardingRules GåÆ ``list[ForwardingRule]``
+    4. Fetch ALL ReplacementRules for all active rules in one ``$in`` query GåÆ
+       ``dict[rule_id, list[ReplacementRule]]``  (O(1) DB round-trips)
+    5. Compile regex patterns for each rule
+       (``block_keywords``, ``allow_keywords``, replacement ``search_text``)
+    6. Return a frozen ``RuleCache`` with the supplied ``version`` number.
+
+    Args:
+        db:      Motor ``AsyncIOMotorDatabase`` instance.
+        version: Version number to stamp on the returned cache snapshot.
+
+    Returns:
+        A frozen ``RuleCache`` snapshot ready to be atomically assigned to
+        ``CacheHolder.current``.
+
+    Raises:
+        Any exception raised by MongoDB (network failures, etc.) GÇö callers
+        should catch these and retain the last valid snapshot.
+    """
+    source_repo = SourceRepository(db)
+    folder_repo = FolderRepository(db)
+    rule_repo = ForwardingRuleRepository(db)
+    replacement_repo = ReplacementRuleRepository(db)
+
+    # 1. Fetch all sources (not just active) GÇö page_size=10000 effectively fetches all
+    #    (NFR-Scale target is 100 active sources, so this is well above the expected ceiling)
+    all_sources_list, _ = await source_repo.list_sources(page_size=10000)
+    sources = {s.id: s for s in all_sources_list if s.id}
+
+    # 2. Fetch all folders
+    all_folders = await folder_repo.list_folders()
+    folders = {f.id: f for f in all_folders if f.id}
+
+    # 3. Fetch only active forwarding rules
+    #    source_repo=None is fine here because we are not filtering by folder_id
+    active_rules, _ = await rule_repo.list_rules(
+        source_repo=None,
+        is_active=True,
+        page_size=10000,
+    )
+
+    # 4. Fetch ALL replacement rules for all active rules in ONE MongoDB query.
+    #    ``list_all_replacements_for_rules`` uses a ``$in`` filter, reducing DB
+    #    round-trips from O(N) per-rule to a fixed O(1) regardless of rule count.
+    #    All replacement rules are loaded (not filtered by is_active) so that the
+    #    pipeline TextReplacementStep can skip is_active=False at runtime GÇö
+    #    consistent with FR-7 and the Epic 4 design notes.
+    rule_ids = [r.id for r in active_rules if r.id]
+    replacements: dict[str, list] = await replacement_repo.list_all_replacements_for_rules(rule_ids)
+
+    # 5. Compile regex patterns for each active rule.
+    #    Invalid patterns are logged as ERROR and skipped (no-op) for the
+    #    lifetime of this snapshot GÇö the refresh continues normally (AC-3).
+    compiled_patterns: dict[str, CompiledPatterns] = {}
+    for rule in active_rules:
+        if not rule.id:
+            continue
+
+        patterns = CompiledPatterns()
+
+        if rule.keyword_match_mode == "regex":
+            # Compile block_keywords
+            for kw in rule.block_keywords:
+                try:
+                    patterns.block_patterns.append(re.compile(kw, re.IGNORECASE))
+                except re.error as e:
+                    logger.error(
+                        "cache_pattern_compile_failed",
+                        rule_id=rule.id,
+                        pattern=kw,
+                        field="block_keywords",
+                        error=str(e),
+                    )
+                    # Skip this pattern GÇö no-op for this snapshot's lifetime
+
+            # Compile allow_keywords
+            for kw in rule.allow_keywords:
+                try:
+                    patterns.allow_patterns.append(re.compile(kw, re.IGNORECASE))
+                except re.error as e:
+                    logger.error(
+                        "cache_pattern_compile_failed",
+                        rule_id=rule.id,
+                        pattern=kw,
+                        field="allow_keywords",
+                        error=str(e),
+                    )
+                    # Skip this pattern GÇö no-op for this snapshot's lifetime
+
+        # Compile replacement rule search_text patterns (regex mode only)
+        for rr in replacements.get(rule.id, []):
+            if rr.match_mode == "regex" and rr.id:
+                try:
+                    patterns.replacement_patterns[rr.id] = re.compile(
+                        rr.search_text, re.IGNORECASE
+                    )
+                except re.error as e:
+                    logger.error(
+                        "cache_pattern_compile_failed",
+                        rule_id=rule.id,
+                        replacement_rule_id=rr.id,
+                        pattern=rr.search_text,
+                        field="replacement_search_text",
+                        error=str(e),
+                    )
+                    # Skip this pattern GÇö no-op for this snapshot's lifetime
+
+        compiled_patterns[rule.id] = patterns
+
+    return RuleCache(
+        sources=sources,
+        folders=folders,
+        rules=active_rules,
+        replacements=replacements,
+        compiled_patterns=compiled_patterns,
+        version=version,
+        refreshed_at=datetime.now(timezone.utc),
+    )
+
+
+async def run_cache_refresher(settings, db) -> None:
+    """Background coroutine: refreshes ``RuleCache`` every ``HOT_RELOAD_INTERVAL`` seconds.
+
+    Behaviour
+    ---------
+    * **Sleep-first**: waits one interval before the first build so that the
+      rest of the application (MongoDB pool, Telegram client) has time to
+      initialise.  The pipeline starts with the empty ``RuleCache()``
+      (version=0, ``rules=[]``) until the first refresh completes.
+    * **On success**: atomically replaces ``CacheHolder.current``; logs INFO
+      with version, rule_count, source_count, folder_count.
+    * **On failure**: logs WARNING with ``last_successful_refresh`` ISO
+      timestamp; retains the current ``CacheHolder.current`` (last known-good
+      snapshot); continues the loop on the next interval (AC-5).
+    * **Graceful shutdown**: re-raises ``asyncio.CancelledError`` after logging
+      so that the task can be awaited cleanly by the lifespan handler.
+
+    The ``version`` counter starts at 1 on the first successful build
+    (``CacheHolder`` starts at version=0, the empty initial cache).
+
+    Args:
+        settings: Application ``Settings`` instance with ``hot_reload_interval``.
+        db:       Motor ``AsyncIOMotorDatabase`` instance.
+    """
+    version = 1
+    last_successful_refresh: datetime | None = None
+    logger.info("cache_refresher_started", hot_reload_interval=settings.hot_reload_interval)
+
+    while True:
+        try:
+            # Sleep first GÇö ensures MongoDB is ready before the initial fetch
+            await asyncio.sleep(settings.hot_reload_interval)
+
+            new_cache = await build_rule_cache(db, version)
+            CacheHolder.current = new_cache          # GåÉ atomic under asyncio event loop
+            last_successful_refresh = new_cache.refreshed_at
+            version += 1
+
+            logger.info(
+                "cache_refreshed",
+                version=new_cache.version,
+                rule_count=len(new_cache.rules),
+                source_count=len(new_cache.sources),
+                folder_count=len(new_cache.folders),
+            )
+
+        except asyncio.CancelledError:
+            logger.info("cache_refresher_stopped")
+            raise
+
+        except Exception as e:
+            logger.warning(
+                "cache_refresh_failed",
+                error=str(e),
+                last_successful_refresh=(
+                    last_successful_refresh.strftime("%Y-%m-%dT%H:%M:%SZ")
+                    if last_successful_refresh
+                    else None
+                ),
+            )
+            # Retain CacheHolder.current (last valid snapshot) GÇö do NOT clear it.
+            # The loop continues on the next interval (AC-5).
diff --git a/forward-bot/src/forward_bot/infrastructure/cache/rule_cache.py b/forward-bot/src/forward_bot/infrastructure/cache/rule_cache.py
new file mode 100644
index 0000000..1946c4b
--- /dev/null
+++ b/forward-bot/src/forward_bot/infrastructure/cache/rule_cache.py
@@ -0,0 +1,87 @@
+"""Atomic cache snapshot types for the forwarding rule pipeline.
+
+This module defines the three types consumed by Epic 4 pipeline steps:
+
+  - CompiledPatterns  GÇö pre-compiled re.Pattern objects for a single ForwardingRule.
+  - RuleCache         GÇö frozen, immutable snapshot of all four MongoDB collections.
+  - CacheHolder       GÇö mutable singleton whose `.current` attribute is atomically
+                        replaced by the cache refresher on each interval.
+
+Assignment of ``CacheHolder.current`` is a single Python reference swap, which is
+atomic under both the CPython GIL and the asyncio event loop's single-threaded
+execution model.  No locking primitives are required.
+"""
+import re
+from dataclasses import dataclass, field
+from datetime import datetime
+from typing import Optional
+
+
+@dataclass
+class CompiledPatterns:
+    """Pre-compiled regex patterns for a single ForwardingRule.
+
+    Keyed structures allow O(1) lookup by field name during pipeline execution.
+    ``block_patterns`` and ``allow_patterns`` are lists of compiled ``re.Pattern``
+    objects (one per keyword that uses regex mode).
+    ``replacement_patterns`` maps each ``replacement_rule.id`` GåÆ
+    compiled ``re.Pattern`` for its ``search_text``.
+    """
+
+    block_patterns: list[re.Pattern] = field(default_factory=list)
+    allow_patterns: list[re.Pattern] = field(default_factory=list)
+    replacement_patterns: dict[str, re.Pattern] = field(default_factory=dict)
+    # Key: replacement_rule.id (str) GåÆ compiled re.Pattern for search_text
+
+
+@dataclass(frozen=True)
+class RuleCache:
+    """Atomic, immutable snapshot of all four MongoDB collections.
+
+    Built once per ``HOT_RELOAD_INTERVAL`` by the cache refresher and atomically
+    assigned to ``CacheHolder.current``.  Pipeline steps read this snapshot for
+    the full lifecycle of a single message dispatch GÇö no torn reads possible.
+
+    Fields:
+        sources:           All sources keyed by their id (hex string).
+        folders:           All folders keyed by their id (hex string).
+        rules:             Active-only ForwardingRules (``is_active=True``),
+                           fetched with ``page_size=10000`` (all active rules).
+        replacements:      All replacement rules per parent rule_id.
+                           Key: ``forwarding_rule_id`` (str) GåÆ
+                           ``list[ReplacementRule]`` (``created_at`` ASC order).
+        compiled_patterns: Pre-compiled regex patterns per rule_id.
+                           Key: ``rule_id`` (str) GåÆ ``CompiledPatterns``.
+        version:           Monotonically increasing integer.  Starts at 0
+                           (initial empty cache), increments by 1 on each
+                           successful build.  Useful for debugging staleness.
+        refreshed_at:      UTC datetime of the last successful cache build.
+                           ``None`` for the initial empty cache (version=0).
+    """
+
+    sources: dict = field(default_factory=dict)           # dict[str, Source]
+    folders: dict = field(default_factory=dict)           # dict[str, SourceFolder]
+    rules: list = field(default_factory=list)             # list[ForwardingRule] (active only)
+    replacements: dict = field(default_factory=dict)      # dict[str, list[ReplacementRule]]
+    compiled_patterns: dict = field(default_factory=dict)  # dict[str, CompiledPatterns]
+    version: int = 0
+    refreshed_at: Optional[datetime] = None
+
+
+class CacheHolder:
+    """Singleton holder for the current ``RuleCache`` snapshot.
+
+    ``CacheHolder.current`` is the only write path for the cache refresher.
+    All reads come from pipeline steps (Epic 4) which consume a local reference
+    to the snapshot at the start of each dispatch.
+
+    Usage::
+
+        # Read in pipeline steps (capture once per dispatch):
+        snapshot = CacheHolder.current
+
+        # Write in cache_refresher only (atomic reference swap):
+        CacheHolder.current = new_cache
+    """
+
+    current: RuleCache = RuleCache()  # Start with empty cache (version=0)
diff --git a/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py b/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py
index a0cf0ac..ee17c10 100644
--- a/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py
+++ b/forward-bot/src/forward_bot/infrastructure/mongo/repositories/folder_repository.py
@@ -76,6 +76,15 @@ class FolderRepository(BaseRepository):
             )
         return deleted
 
+    async def list_folders(self) -> list[SourceFolder]:
+        """Fetch all SourceFolders from the database mapped to domain entities.
+
+        Returns all folders in the collection with no filtering or pagination.
+        Used by the cache refresher (Story 3.3) to populate ``RuleCache.folders``.
+        """
+        docs = await self.find({})
+        return [self._to_entity(doc) for doc in docs]
+
     async def list_folders_with_source_count(self, name_filter: str | None = None) -> list[dict[str, Any]]:
         """List folders with their source counts using a single aggregate query."""
         pipeline: list[dict[str, Any]] = []
diff --git a/forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py b/forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py
index 4fa7eb3..3c78408 100644
--- a/forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py
+++ b/forward-bot/src/forward_bot/infrastructure/mongo/repositories/replacement_repository.py
@@ -67,6 +67,42 @@ class ReplacementRuleRepository(BaseRepository):
         """Delete a replacement rule by ObjectId. Returns True if deleted."""
         return await self.delete(id)
 
+    async def list_all_replacements_for_rules(
+        self, rule_ids: list[str]
+    ) -> dict[str, list[ReplacementRule]]:
+        """Fetch ALL replacement rules for a set of forwarding rule IDs in ONE query.
+
+        Uses a ``$in`` filter to fetch all matching documents in a single MongoDB
+        round-trip, then groups results in-memory by ``forwarding_rule_id``.
+        Within each group the order is ``created_at ASC, _id ASC`` (pipeline order, FR-7).
+
+        This is the O(1) replacement for the O(N) per-rule sequential loop previously
+        used in ``build_rule_cache``. At NFR-Scale (100 active rules) this reduces cache
+        refresh DB round-trips from 101 to 4 (sources, folders, rules, replacements).
+
+        Args:
+            rule_ids: List of forwarding rule ID hex strings whose replacement rules to fetch.
+
+        Returns:
+            ``dict[forwarding_rule_id, list[ReplacementRule]]`` GÇö every requested rule_id
+            appears as a key; missing ones map to ``[]``.
+        """
+        if not rule_ids:
+            return {}
+
+        cursor = (
+            self.collection.find({"forwarding_rule_id": {"$in": rule_ids}})
+            .sort([("created_at", 1), ("_id", 1)])  # pipeline application order (FR-7)
+        )
+        docs = await cursor.to_list(length=None)
+
+        # Group in-memory; pre-seed all requested IDs so callers get [] for rules with no replacements
+        grouped: dict[str, list[ReplacementRule]] = {rid: [] for rid in rule_ids}
+        for doc in docs:
+            entity = self._to_entity(doc)
+            grouped.setdefault(entity.forwarding_rule_id, []).append(entity)
+        return grouped
+
     async def list_replacements_for_rule(self, rule_id: str) -> list[ReplacementRule]:
         """List all replacement rules for a parent forwarding rule, ordered by created_at ASC.
 
@@ -75,7 +111,7 @@ class ReplacementRuleRepository(BaseRepository):
         """
         cursor = (
             self.collection.find({"forwarding_rule_id": rule_id})
-            .sort("created_at", 1)  # ASC GÇö pipeline application order (FR-7)
+            .sort([("created_at", 1), ("_id", 1)])  # ASC with secondary _id sort to prevent collision
         )
         docs = await cursor.to_list(length=None)
         return [self._to_entity(doc) for doc in docs]
diff --git a/forward-bot/src/forward_bot/tasks.py b/forward-bot/src/forward_bot/tasks.py
index 2a37c2b..2287b33 100644
--- a/forward-bot/src/forward_bot/tasks.py
+++ b/forward-bot/src/forward_bot/tasks.py
@@ -2,14 +2,32 @@
 import asyncio
 from forward_bot.infrastructure.logging import logger
 
-async def run_cache_refresher() -> None:
-    """Stub for cache refresher task."""
-    logger.info("cache_refresher_started", status="stub")
-    try:
-        await asyncio.sleep(float('inf'))
-    except asyncio.CancelledError:
-        logger.info("cache_refresher_stopped")
-        raise
+async def run_cache_refresher(settings=None, db=None) -> None:
+    """Real cache refresher GÇö delegates to infrastructure/cache/cache_refresher.py.
+
+    When called without arguments (legacy / test scenarios) the function falls
+    back to an infinite sleep so that task cancellation still works cleanly GÇö
+    preserving backward compatibility with existing E2E tests from Story 1.3.
+
+    Args:
+        settings: Application ``Settings`` instance with ``hot_reload_interval``.
+                  When ``None`` the function sleeps indefinitely (stub mode).
+        db:       Motor ``AsyncIOMotorDatabase`` instance.
+                  When ``None`` the function sleeps indefinitely (stub mode).
+    """
+    if settings is None or db is None:
+        # Stub mode: sleep until cancelled (preserves cancellation semantics)
+        logger.info("cache_refresher_started", status="stub-no-settings")
+        try:
+            await asyncio.sleep(float("inf"))
+        except asyncio.CancelledError:
+            logger.info("cache_refresher_stopped")
+            raise
+        return
+
+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher as _run
+    await _run(settings, db)
+
 
 async def run_mapping_sweeper() -> None:
     """Stub for mapping sweeper task."""
diff --git a/forward-bot/tests/infrastructure/cache/__init__.py b/forward-bot/tests/infrastructure/cache/__init__.py
new file mode 100644
index 0000000..d0d1445
--- /dev/null
+++ b/forward-bot/tests/infrastructure/cache/__init__.py
@@ -0,0 +1 @@
+# tests/infrastructure/cache/__init__.py
diff --git a/forward-bot/tests/infrastructure/cache/test_cache_refresher.py b/forward-bot/tests/infrastructure/cache/test_cache_refresher.py
new file mode 100644
index 0000000..c0ab3fe
--- /dev/null
+++ b/forward-bot/tests/infrastructure/cache/test_cache_refresher.py
@@ -0,0 +1,583 @@
+import asyncio
+import contextlib
+from datetime import datetime, timezone
+from unittest.mock import AsyncMock, MagicMock, patch
+
+import pytest
+
+from forward_bot.domain.entities.forwarding_rule import ForwardingRule
+from forward_bot.domain.entities.replacement_rule import ReplacementRule
+from forward_bot.domain.entities.source import Source
+from forward_bot.domain.entities.source_folder import SourceFolder
+from forward_bot.infrastructure.cache.rule_cache import CacheHolder, CompiledPatterns, RuleCache
+
+
+# ---------------------------------------------------------------------------
+# Helper factories
+# ---------------------------------------------------------------------------
+
+
+def _now() -> datetime:
+    return datetime.now(timezone.utc)
+
+
+def make_source(id_: str = "src1") -> Source:
+    return Source(
+        id=id_,
+        telegram_id=1001,
+        telegram_username="test_chan",
+        display_name="Test Chan",
+        type="channel",
+        folder_id=None,
+        created_at=_now(),
+        updated_at=_now(),
+    )
+
+
+def make_folder(id_: str = "fol1") -> SourceFolder:
+    return SourceFolder(id=id_, name="Test Folder", created_at=_now(), updated_at=_now())
+
+
+def make_rule(
+    id_: str = "rule1",
+    match_mode: str = "literal",
+    block: list[str] | None = None,
+    allow: list[str] | None = None,
+    active: bool = True,
+) -> ForwardingRule:
+    return ForwardingRule(
+        id=id_,
+        source_id="src1",
+        destination_channel="@dest",
+        is_active=active,
+        keyword_match_mode=match_mode,
+        block_keywords=block or [],
+        allow_keywords=allow or [],
+    )
+
+
+def make_replacement(
+    id_: str = "rr1",
+    search: str = "old",
+    mode: str = "literal",
+    rule_id: str = "rule1",
+) -> ReplacementRule:
+    return ReplacementRule(
+        id=id_,
+        forwarding_rule_id=rule_id,
+        search_text=search,
+        replacement_text="new",
+        match_mode=mode,
+        is_active=True,
+        created_at=_now(),
+        updated_at=_now(),
+    )
+
+
+def _make_mock_repos(
+    sources=None,
+    folders=None,
+    rules=None,
+    replacements=None,
+):
+    """Return a dict of pre-configured mock repositories.
+
+    ``replacements`` should be a ``dict[rule_id, list[ReplacementRule]]``.
+    The mock wires up ``list_all_replacements_for_rules`` (the O(1) batch method
+    used by ``build_rule_cache``) to return the dict keyed by the requested IDs.
+    The per-rule ``list_replacements_for_rule`` is NOT called by the cache refresher.
+    """
+    mock_source_repo = MagicMock()
+    mock_source_repo.list_sources = AsyncMock(
+        return_value=(sources or [], len(sources) if sources else 0)
+    )
+
+    mock_folder_repo = MagicMock()
+    mock_folder_repo.list_folders = AsyncMock(return_value=folders or [])
+
+    mock_rule_repo = MagicMock()
+    mock_rule_repo.list_rules = AsyncMock(
+        return_value=(rules or [], len(rules) if rules else 0)
+    )
+
+    mock_replacement_repo = MagicMock()
+    _replacements = replacements or {}
+
+    async def batch_list(rule_ids):
+        """Simulate list_all_replacements_for_rules: pre-seed every requested id."""
+        return {rid: _replacements.get(rid, []) for rid in rule_ids}
+
+    mock_replacement_repo.list_all_replacements_for_rules = batch_list
+
+    return mock_source_repo, mock_folder_repo, mock_rule_repo, mock_replacement_repo
+
+
+@contextlib.contextmanager
+def _patch_repos(source_repo, folder_repo, rule_repo, replacement_repo):
+    """Context manager that patches all four repository classes simultaneously."""
+    with (
+        patch(
+            "forward_bot.infrastructure.cache.cache_refresher.SourceRepository",
+            return_value=source_repo,
+        ),
+        patch(
+            "forward_bot.infrastructure.cache.cache_refresher.FolderRepository",
+            return_value=folder_repo,
+        ),
+        patch(
+            "forward_bot.infrastructure.cache.cache_refresher.ForwardingRuleRepository",
+            return_value=rule_repo,
+        ),
+        patch(
+            "forward_bot.infrastructure.cache.cache_refresher.ReplacementRuleRepository",
+            return_value=replacement_repo,
+        ),
+    ):
+        yield
+
+
+
+# ---------------------------------------------------------------------------
+# build_rule_cache GÇö happy path
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_happy_path():
+    """build_rule_cache fetches 4 collections and builds a valid RuleCache snapshot."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    source = make_source()
+    folder = make_folder()
+    rule = make_rule()
+    replacement = make_replacement()
+
+    sr, fr, rr, rep = _make_mock_repos(
+        sources=[source],
+        folders=[folder],
+        rules=[rule],
+        replacements={"rule1": [replacement]},
+    )
+
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    assert isinstance(cache, RuleCache)
+    assert cache.version == 1
+    assert "src1" in cache.sources
+    assert "fol1" in cache.folders
+    assert len(cache.rules) == 1
+    assert "rule1" in cache.replacements
+    assert len(cache.replacements["rule1"]) == 1
+    assert cache.refreshed_at is not None
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_version_stamped_correctly():
+    """build_rule_cache stamps the provided version number into the snapshot."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    sr, fr, rr, rep = _make_mock_repos()
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=7)
+
+    assert cache.version == 7
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_refreshed_at_is_utc():
+    """build_rule_cache sets refreshed_at to UTC datetime."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    sr, fr, rr, rep = _make_mock_repos()
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    assert cache.refreshed_at is not None
+    assert cache.refreshed_at.tzinfo is not None  # timezone-aware
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_empty_db():
+    """build_rule_cache with empty collections returns an empty but valid snapshot."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    sr, fr, rr, rep = _make_mock_repos()
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    assert cache.sources == {}
+    assert cache.folders == {}
+    assert cache.rules == []
+    assert cache.replacements == {}
+    assert cache.compiled_patterns == {}
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_multiple_sources_and_rules():
+    """build_rule_cache correctly indexes multiple sources and rules."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    sources = [make_source(id_=f"src{i}") for i in range(3)]
+    rules = [make_rule(id_=f"rule{i}") for i in range(2)]
+
+    sr, fr, rr, rep = _make_mock_repos(sources=sources, rules=rules)
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    assert len(cache.sources) == 3
+    assert len(cache.rules) == 2
+    assert all(f"src{i}" in cache.sources for i in range(3))
+
+
+# ---------------------------------------------------------------------------
+# build_rule_cache GÇö regex pattern compilation (AC-2)
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_compiles_block_and_allow_regex():
+    """Regex block_keywords and allow_keywords are compiled into CompiledPatterns (AC-2)."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    rule = make_rule(match_mode="regex", block=["pump.*"], allow=["BTC|ETH"])
+
+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    assert "rule1" in cache.compiled_patterns
+    cp = cache.compiled_patterns["rule1"]
+    assert len(cp.block_patterns) == 1
+    assert cp.block_patterns[0].pattern == "pump.*"
+    assert len(cp.allow_patterns) == 1
+    assert cp.allow_patterns[0].pattern == "BTC|ETH"
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_compiles_replacement_regex():
+    """Regex replacement search_text is compiled into CompiledPatterns.replacement_patterns."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    rule = make_rule(match_mode="literal")  # keyword mode doesn't matter for replacement regex
+    replacement = make_replacement(search="old.+new", mode="regex")
+
+    sr, fr, rr, rep = _make_mock_repos(
+        rules=[rule],
+        replacements={"rule1": [replacement]},
+    )
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    assert "rule1" in cache.compiled_patterns
+    cp = cache.compiled_patterns["rule1"]
+    assert "rr1" in cp.replacement_patterns
+    assert cp.replacement_patterns["rr1"].pattern == "old.+new"
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_literal_keywords_not_compiled():
+    """Literal-mode keywords do NOT populate block_patterns or allow_patterns."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    rule = make_rule(match_mode="literal", block=["pump"], allow=["btc"])
+
+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    cp = cache.compiled_patterns["rule1"]
+    # Literal mode GÇö no compiled patterns for block/allow
+    assert cp.block_patterns == []
+    assert cp.allow_patterns == []
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_literal_replacement_not_compiled():
+    """Literal-mode replacement rules do NOT populate replacement_patterns."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    rule = make_rule()
+    replacement = make_replacement(search="old", mode="literal")
+
+    sr, fr, rr, rep = _make_mock_repos(
+        rules=[rule],
+        replacements={"rule1": [replacement]},
+    )
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    cp = cache.compiled_patterns["rule1"]
+    assert cp.replacement_patterns == {}
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_patterns_compiled_with_ignorecase():
+    """Compiled patterns use re.IGNORECASE flag (FR-36, FR-8 compliance)."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+    import re
+
+    rule = make_rule(match_mode="regex", block=["TestPATTERN"])
+
+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    cp = cache.compiled_patterns["rule1"]
+    assert cp.block_patterns[0].flags & re.IGNORECASE
+
+
+# ---------------------------------------------------------------------------
+# build_rule_cache GÇö invalid regex skip and log (AC-3)
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_skips_invalid_block_regex(caplog):
+    """Invalid block_keywords regex is skipped and logged as ERROR GÇö refresh completes (AC-3)."""
+    import logging
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    rule = make_rule(match_mode="regex", block=["[invalid("])  # invalid regex
+
+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
+    with _patch_repos(sr, fr, rr, rep):
+        with caplog.at_level(logging.ERROR):
+            cache = await build_rule_cache(MagicMock(), version=1)
+
+    # Refresh completes GÇö version stamped correctly
+    assert cache.version == 1
+    # Invalid pattern skipped GÇö CompiledPatterns exists but block_patterns is empty
+    assert "rule1" in cache.compiled_patterns
+    assert cache.compiled_patterns["rule1"].block_patterns == []
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_skips_invalid_allow_regex():
+    """Invalid allow_keywords regex is skipped GÇö other valid patterns still compile."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    rule = make_rule(match_mode="regex", block=["pump.*"], allow=["[bad("])
+
+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    cp = cache.compiled_patterns["rule1"]
+    # Valid block pattern compiled; invalid allow pattern skipped
+    assert len(cp.block_patterns) == 1
+    assert cp.allow_patterns == []
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_skips_invalid_replacement_regex():
+    """Invalid replacement search_text regex is skipped GÇö refresh completes (AC-3)."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    rule = make_rule()
+    bad_replacement = make_replacement(search="[invalid(", mode="regex")
+
+    sr, fr, rr, rep = _make_mock_repos(
+        rules=[rule],
+        replacements={"rule1": [bad_replacement]},
+    )
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    # Refresh completes; invalid replacement pattern absent from compiled_patterns
+    assert cache.version == 1
+    assert cache.compiled_patterns["rule1"].replacement_patterns == {}
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_valid_patterns_survive_invalid_one():
+    """When one of multiple patterns is invalid, valid patterns still compile."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    rule = make_rule(match_mode="regex", block=["pump.*", "[invalid(", "dump.*"])
+
+    sr, fr, rr, rep = _make_mock_repos(rules=[rule])
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    cp = cache.compiled_patterns["rule1"]
+    # 2 valid patterns compiled; 1 invalid skipped
+    assert len(cp.block_patterns) == 2
+    compiled_texts = {p.pattern for p in cp.block_patterns}
+    assert "pump.*" in compiled_texts
+    assert "dump.*" in compiled_texts
+
+
+@pytest.mark.asyncio
+async def test_build_rule_cache_invalid_regex_other_rules_unaffected():
+    """An invalid pattern in one rule does not affect compilation of other rules."""
+    from forward_bot.infrastructure.cache.cache_refresher import build_rule_cache
+
+    rule_bad = make_rule(id_="rule_bad", match_mode="regex", block=["[invalid("])
+    rule_good = make_rule(id_="rule_good", match_mode="regex", block=["pump.*"])
+
+    sr, fr, rr, rep = _make_mock_repos(rules=[rule_bad, rule_good])
+    with _patch_repos(sr, fr, rr, rep):
+        cache = await build_rule_cache(MagicMock(), version=1)
+
+    # Bad rule: empty block_patterns
+    assert cache.compiled_patterns["rule_bad"].block_patterns == []
+    # Good rule: compiled correctly
+    assert len(cache.compiled_patterns["rule_good"].block_patterns) == 1
+
+
+# ---------------------------------------------------------------------------
+# run_cache_refresher GÇö MongoDB failure retains last snapshot (AC-5)
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.asyncio
+async def test_run_cache_refresher_retains_snapshot_on_mongodb_failure():
+    """On MongoDB error, CacheHolder.current retains the last valid snapshot (AC-5)."""
+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
+
+    initial_cache = RuleCache(version=99)
+    saved = CacheHolder.current
+    CacheHolder.current = initial_cache
+
+    mock_settings = MagicMock()
+    mock_settings.hot_reload_interval = 0.01  # very short for test speed
+
+    async def mock_build(db, version):
+        raise Exception("MongoDB connection lost")
+
+    with patch(
+        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
+        side_effect=mock_build,
+    ):
+        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
+        await asyncio.sleep(0.05)  # Let it fail at least once
+        task.cancel()
+        try:
+            await task
+        except asyncio.CancelledError:
+            pass
+
+    # Snapshot retained GÇö not reset to empty
+    assert CacheHolder.current.version == 99
+    CacheHolder.current = saved
+
+
+@pytest.mark.asyncio
+async def test_run_cache_refresher_continues_after_failure():
+    """After a MongoDB failure the refresher continues on the next interval (AC-5)."""
+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
+
+    saved = CacheHolder.current
+    CacheHolder.current = RuleCache(version=0)
+
+    call_count = 0
+
+    async def mock_build(db, version):
+        nonlocal call_count
+        call_count += 1
+        raise Exception("transient error")
+
+    mock_settings = MagicMock()
+    mock_settings.hot_reload_interval = 0.01
+
+    with patch(
+        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
+        side_effect=mock_build,
+    ):
+        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
+        await asyncio.sleep(0.08)
+        task.cancel()
+        try:
+            await task
+        except asyncio.CancelledError:
+            pass
+
+    # Refresher looped multiple times despite repeated failures
+    assert call_count >= 2
+    CacheHolder.current = saved
+
+
+@pytest.mark.asyncio
+async def test_run_cache_refresher_version_increments_on_success():
+    """Version counter increments by 1 on each successful cache build."""
+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
+
+    saved = CacheHolder.current
+    version_log: list[int] = []
+
+    async def mock_build(db, version):
+        version_log.append(version)
+        return RuleCache(version=version, refreshed_at=datetime.now(timezone.utc))
+
+    mock_settings = MagicMock()
+    mock_settings.hot_reload_interval = 0.01
+
+    with patch(
+        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
+        side_effect=mock_build,
+    ):
+        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
+        await asyncio.sleep(0.08)
+        task.cancel()
+        try:
+            await task
+        except asyncio.CancelledError:
+            pass
+
+    # Versions should be sequential starting at 1
+    assert version_log[0] == 1
+    for i in range(1, len(version_log)):
+        assert version_log[i] == version_log[i - 1] + 1
+
+    CacheHolder.current = saved
+
+
+@pytest.mark.asyncio
+async def test_run_cache_refresher_swaps_cache_on_success():
+    """run_cache_refresher atomically replaces CacheHolder.current on a successful build."""
+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
+
+    saved = CacheHolder.current
+    CacheHolder.current = RuleCache(version=0)
+
+    built_cache = RuleCache(version=1, refreshed_at=datetime.now(timezone.utc))
+
+    async def mock_build(db, version):
+        return built_cache
+
+    mock_settings = MagicMock()
+    mock_settings.hot_reload_interval = 0.01
+
+    with patch(
+        "forward_bot.infrastructure.cache.cache_refresher.build_rule_cache",
+        side_effect=mock_build,
+    ):
+        task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
+        await asyncio.sleep(0.05)
+        task.cancel()
+        try:
+            await task
+        except asyncio.CancelledError:
+            pass
+
+    # CacheHolder.current was replaced
+    assert CacheHolder.current.refreshed_at is not None
+
+    CacheHolder.current = saved
+
+
+@pytest.mark.asyncio
+async def test_run_cache_refresher_cancelled_error_propagates():
+    """run_cache_refresher re-raises CancelledError for clean shutdown."""
+    from forward_bot.infrastructure.cache.cache_refresher import run_cache_refresher
+
+    mock_settings = MagicMock()
+    mock_settings.hot_reload_interval = 10.0  # long sleep
+
+    task = asyncio.create_task(run_cache_refresher(mock_settings, MagicMock()))
+    await asyncio.sleep(0.01)
+    task.cancel()
+
+    with pytest.raises(asyncio.CancelledError):
+        await task
diff --git a/forward-bot/tests/infrastructure/cache/test_rule_cache.py b/forward-bot/tests/infrastructure/cache/test_rule_cache.py
new file mode 100644
index 0000000..b17ae53
--- /dev/null
+++ b/forward-bot/tests/infrastructure/cache/test_rule_cache.py
@@ -0,0 +1,143 @@
+"""Unit tests for RuleCache, CacheHolder, and CompiledPatterns.
+
+Tests the construction, frozen behaviour, and atomic swap semantics of the
+cache types defined in ``infrastructure/cache/rule_cache.py``.
+"""
+import re
+from datetime import datetime, timezone
+
+import pytest
+
+from forward_bot.infrastructure.cache.rule_cache import CacheHolder, CompiledPatterns, RuleCache
+
+
+# ---------------------------------------------------------------------------
+# RuleCache GÇö construction and frozen semantics
+# ---------------------------------------------------------------------------
+
+
+def test_rule_cache_defaults():
+    """RuleCache() with no args produces a valid empty snapshot (version=0)."""
+    cache = RuleCache()
+    assert cache.sources == {}
+    assert cache.folders == {}
+    assert cache.rules == []
+    assert cache.replacements == {}
+    assert cache.compiled_patterns == {}
+    assert cache.version == 0
+    assert cache.refreshed_at is None
+
+
+def test_rule_cache_with_version():
+    """RuleCache stores the supplied version number."""
+    cache = RuleCache(version=5)
+    assert cache.version == 5
+
+
+def test_rule_cache_with_refreshed_at():
+    """RuleCache stores a non-None refreshed_at when explicitly supplied."""
+    ts = datetime.now(timezone.utc)
+    cache = RuleCache(version=1, refreshed_at=ts)
+    assert cache.refreshed_at == ts
+
+
+def test_rule_cache_frozen():
+    """RuleCache is a frozen dataclass GÇö attributes cannot be mutated after creation."""
+    cache = RuleCache(version=1)
+    with pytest.raises((AttributeError, TypeError)):
+        cache.version = 2  # type: ignore[misc]
+
+
+def test_rule_cache_frozen_sources():
+    """RuleCache.sources dict is NOT replaced after creation (frozen reference)."""
+    cache = RuleCache(version=1, sources={"s1": object()})
+    with pytest.raises((AttributeError, TypeError)):
+        cache.sources = {}  # type: ignore[misc]
+
+
+# ---------------------------------------------------------------------------
+# CacheHolder GÇö singleton and atomic swap
+# ---------------------------------------------------------------------------
+
+
+def test_cache_holder_starts_with_empty_cache():
+    """CacheHolder.current starts as an empty RuleCache (version=0).
+
+    Note: CacheHolder is module-level state GÇö we reset it before asserting to
+    ensure isolation from other tests that mutate it.
+    """
+    CacheHolder.current = RuleCache()
+    assert CacheHolder.current.version == 0
+    assert CacheHolder.current.rules == []
+    assert CacheHolder.current.refreshed_at is None
+
+
+def test_cache_holder_atomic_swap():
+    """Assigning CacheHolder.current replaces the snapshot reference atomically."""
+    original = CacheHolder.current
+    new_cache = RuleCache(version=42)
+    CacheHolder.current = new_cache
+    assert CacheHolder.current.version == 42
+    # Restore to keep other tests clean
+    CacheHolder.current = original
+
+
+def test_cache_holder_multiple_swaps():
+    """Multiple successive swaps always expose the latest cache."""
+    saved = CacheHolder.current
+    for v in range(1, 6):
+        CacheHolder.current = RuleCache(version=v)
+        assert CacheHolder.current.version == v
+    CacheHolder.current = saved
+
+
+def test_cache_holder_local_snapshot_not_affected_by_swap():
+    """A local reference to the old snapshot is not changed by a later swap."""
+    saved = CacheHolder.current
+    snapshot_before = CacheHolder.current      # capture reference
+    CacheHolder.current = RuleCache(version=99)
+    # The local variable still points to the old snapshot
+    assert snapshot_before is not CacheHolder.current
+    CacheHolder.current = saved
+
+
+# ---------------------------------------------------------------------------
+# CompiledPatterns
+# ---------------------------------------------------------------------------
+
+
+def test_compiled_patterns_defaults():
+    """CompiledPatterns has correct empty defaults."""
+    p = CompiledPatterns()
+    assert p.block_patterns == []
+    assert p.allow_patterns == []
+    assert p.replacement_patterns == {}
+
+
+def test_compiled_patterns_with_real_patterns():
+    """CompiledPatterns stores compiled re.Pattern objects correctly."""
+    block = [re.compile("pump", re.IGNORECASE)]
+    allow = [re.compile("btc", re.IGNORECASE)]
+    repl = {"rr-id-1": re.compile("old", re.IGNORECASE)}
+    p = CompiledPatterns(block_patterns=block, allow_patterns=allow, replacement_patterns=repl)
+    assert len(p.block_patterns) == 1
+    assert p.block_patterns[0].pattern == "pump"
+    assert len(p.allow_patterns) == 1
+    assert p.allow_patterns[0].pattern == "btc"
+    assert "rr-id-1" in p.replacement_patterns
+    assert p.replacement_patterns["rr-id-1"].pattern == "old"
+
+
+def test_compiled_patterns_multiple_block_patterns():
+    """CompiledPatterns can hold multiple block and allow patterns."""
+    block = [re.compile(p, re.IGNORECASE) for p in ["pump.*", "dump.*", "scam"]]
+    p = CompiledPatterns(block_patterns=block)
+    assert len(p.block_patterns) == 3
+    assert {pat.pattern for pat in p.block_patterns} == {"pump.*", "dump.*", "scam"}
+
+
+def test_compiled_patterns_ignorecase_flag():
+    """CompiledPatterns correctly stores patterns compiled with IGNORECASE."""
+    pattern = re.compile("TestPattern", re.IGNORECASE)
+    p = CompiledPatterns(block_patterns=[pattern])
+    assert p.block_patterns[0].flags & re.IGNORECASE
diff --git a/forward-bot/tests/infrastructure/mongo/test_folder_repository.py b/forward-bot/tests/infrastructure/mongo/test_folder_repository.py
index 79edbdb..79f9d68 100644
--- a/forward-bot/tests/infrastructure/mongo/test_folder_repository.py
+++ b/forward-bot/tests/infrastructure/mongo/test_folder_repository.py
@@ -146,3 +146,97 @@ async def test_list_folders_with_source_count():
     results_filtered = await repo.list_folders_with_source_count("crypto")
     pipeline_filtered = mock_collection.aggregate.call_args[0][0]
     assert any("$match" in step for step in pipeline_filtered)
+
+
+# ---------------------------------------------------------------------------
+# list_folders GÇö Story 3.3 addition
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.asyncio
+async def test_list_folders_returns_all_folders():
+    """list_folders() fetches all SourceFolders with no filtering (Story 3.3)."""
+    mock_db = MagicMock()
+    mock_collection = AsyncMock()
+    mock_db.__getitem__.return_value = mock_collection
+
+    now = datetime.now(timezone.utc)
+    mock_docs = [
+        {"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"), "name": "Folder A",
+         "created_at": now, "updated_at": now},
+        {"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8f"), "name": "Folder B",
+         "created_at": now, "updated_at": now},
+    ]
+
+    mock_cursor = MagicMock()
+    mock_cursor.to_list = AsyncMock(return_value=mock_docs)
+    mock_collection.find = MagicMock(return_value=mock_cursor)
+
+    repo = FolderRepository(mock_db)
+    folders = await repo.list_folders()
+
+    assert len(folders) == 2
+    assert all(isinstance(f, SourceFolder) for f in folders)
+    names = {f.name for f in folders}
+    assert names == {"Folder A", "Folder B"}
+
+
+@pytest.mark.asyncio
+async def test_list_folders_called_with_empty_filter():
+    """list_folders() queries the collection with an empty filter ({})."""
+    mock_db = MagicMock()
+    mock_collection = AsyncMock()
+    mock_db.__getitem__.return_value = mock_collection
+
+    mock_cursor = MagicMock()
+    mock_cursor.to_list = AsyncMock(return_value=[])
+    mock_collection.find = MagicMock(return_value=mock_cursor)
+
+    repo = FolderRepository(mock_db)
+    await repo.list_folders()
+
+    mock_collection.find.assert_called_once_with({})
+
+
+@pytest.mark.asyncio
+async def test_list_folders_empty_collection():
+    """list_folders() returns an empty list when the collection is empty."""
+    mock_db = MagicMock()
+    mock_collection = AsyncMock()
+    mock_db.__getitem__.return_value = mock_collection
+
+    mock_cursor = MagicMock()
+    mock_cursor.to_list = AsyncMock(return_value=[])
+    mock_collection.find = MagicMock(return_value=mock_cursor)
+
+    repo = FolderRepository(mock_db)
+    folders = await repo.list_folders()
+
+    assert folders == []
+
+
+@pytest.mark.asyncio
+async def test_list_folders_maps_to_domain_entity():
+    """list_folders() correctly maps MongoDB documents to SourceFolder entities."""
+    mock_db = MagicMock()
+    mock_collection = AsyncMock()
+    mock_db.__getitem__.return_value = mock_collection
+
+    oid = ObjectId("65c52c6f1f2e3d4a5b6c7d8e")
+    now = datetime.now(timezone.utc)
+    mock_doc = {"_id": oid, "name": "My Folder", "created_at": now, "updated_at": now}
+
+    mock_cursor = MagicMock()
+    mock_cursor.to_list = AsyncMock(return_value=[mock_doc])
+    mock_collection.find = MagicMock(return_value=mock_cursor)
+
+    repo = FolderRepository(mock_db)
+    folders = await repo.list_folders()
+
+    assert len(folders) == 1
+    folder = folders[0]
+    assert folder.id == str(oid)
+    assert folder.name == "My Folder"
+    assert folder.created_at == now
+    assert folder.updated_at == now
+
diff --git a/forward-bot/tests/infrastructure/mongo/test_replacement_repository.py b/forward-bot/tests/infrastructure/mongo/test_replacement_repository.py
index 9474b9c..f9cd099 100644
--- a/forward-bot/tests/infrastructure/mongo/test_replacement_repository.py
+++ b/forward-bot/tests/infrastructure/mongo/test_replacement_repository.py
@@ -303,7 +303,7 @@ async def test_list_replacements_for_rule_returns_ordered_entities():
 
     # Verify query uses string comparison (not ObjectId)
     mock_collection.find.assert_called_once_with({"forwarding_rule_id": PARENT_OID})
-    mock_cursor.sort.assert_called_once_with("created_at", 1)   # ASC GÇö pipeline order
+    mock_cursor.sort.assert_called_once_with([("created_at", 1), ("_id", 1)])   # ASC with secondary sort
 
 
 @pytest.mark.asyncio

