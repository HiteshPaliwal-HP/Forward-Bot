# Deferred Work

This file tracks technical debt and deferred items from code reviews and implementations.

## Deferred from: code review of 1-1-initialize-project-scaffold-directory-structure (2026-06-06)

- **Default MongoDB URI Warn/Error in Production**: Add a check that prevents running with localhost MongoDB URI when in a production environment (to be addressed in Story 1.2 during database setup).
- **UI Enabled Flag verification for static files directory**: When `ui_enabled` settings is true, check if the UI's static build folder exists on start (to be addressed in Story 1.3 during web server shell setup).
- **Logging Ring-Buffer Size Default Configuration**: Evaluate logging ring buffer size constraints for high-traffic environments to prevent early log eviction (to be addressed in Story 5.2 during structured logging implementation).

## Deferred from: code review of 1-2-configure-application-settings-database-client (2026-06-06)

- **SecretRedactor risk of over-scrubbing**: If `API_KEY` or `SECRET_KEY` are very short, `SecretRedactor` might redact safe data in logs. Pre-existing risk but deferred since keys are typically long hashes.

## Deferred from: code review of 1-4-telegram-authentication-session-management (2026-06-08)

- **Session file path detection logic is duplicated**: The logic that appends `.session` if the path doesn't already end with it is copy-pasted in both `TelegramClientHolder.connect()` and `main_auth()`. Refactor into a shared helper function when touching this area again.
- **`/health/telegram` returns HTTP 200 when Telegram is disconnected**: The health endpoint always returns 200 regardless of Telegram status. For proper readiness/liveness probes, it should return 503 when disconnected. Address in the observability epic (Story 5.x).
- **`TelegramClientHolder.connect()` doesn't guard against reconnect when already connected**: If called twice concurrently, the lock protects against overlap, but sequential calls after a successful connect would re-initialize the client. Add a short-circuit guard (`if self.status == "connected": return`) when retry/reconnect logic is introduced in Epic 4.
