"""Domain exceptions for Forward Bot."""

class DomainException(Exception):
    """Base class for all domain-specific exceptions."""
    pass


class TelegramUnavailableException(DomainException):
    """Raised when the Telegram client is not connected but is required."""
    pass


class SourceAlreadyExistsException(DomainException):
    """Raised when registering a source that already exists in the database."""
    def __init__(self, telegram_id: int):
        self.telegram_id = telegram_id
        super().__init__(f"Source with Telegram ID {telegram_id} already exists.")


class SourceUsernameAlreadyExistsException(DomainException):
    """Raised when registering or updating a source to a username that already exists."""
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Source with username {username} already exists.")



class TelegramResolveFailedException(DomainException):
    """Raised when Telegram fails to resolve a reference (username or ID)."""
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"Failed to resolve Telegram reference: {details}")


class SourceNotFoundException(DomainException):
    """Raised when a requested source is not found in the database."""
    def __init__(self, source_id: str):
        self.source_id = source_id
        super().__init__(f"Source {source_id} not found.")


class SourceInUseException(DomainException):
    """Raised when attempting to delete a source referenced by forwarding rules."""
    def __init__(self, source_id: str, rule_count: int):
        self.source_id = source_id
        self.rule_count = rule_count
        super().__init__(f"Source {source_id} is referenced by {rule_count} rules.")


class FolderNotFoundException(DomainException):
    """Raised when a folder ID referenced by a source does not exist."""
    def __init__(self, folder_id: str):
        self.folder_id = folder_id
        super().__init__(f"Folder with ID {folder_id} does not exist.")


class FolderNameInUseException(DomainException):
    """Raised when creating or updating a folder with a name that is already in use."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Folder name in use: {name}.")


class FolderReferenceNotFoundException(DomainException):
    """Raised when a referenced folder is missing."""
    def __init__(self, folder_id: str):
        self.folder_id = folder_id
        super().__init__(f"Folder with ID {folder_id} does not exist.")


# ---------------------------------------------------------------------------
# Forwarding Rule exceptions (Story 3.1)
# ---------------------------------------------------------------------------

class RuleNotFoundException(DomainException):
    """Raised when a requested forwarding rule is not found."""
    def __init__(self, rule_id: str):
        self.rule_id = rule_id
        super().__init__(f"Rule {rule_id} not found.")


class RuleSourceNotFoundException(DomainException):
    """Raised by rule use cases when source_id is not found (returns HTTP 422, not 404).

    Distinct from SourceNotFoundException which maps to 404.
    Used by CreateRule and UpdateRule when the referenced source does not exist.
    """
    def __init__(self, source_id: str):
        self.source_id = source_id
        super().__init__(f"Source {source_id} not found.")


class RuleInvalidRegexException(DomainException):
    """Raised when a keyword pattern is not a valid Python regex."""
    def __init__(self, pattern: str, reason: str):
        self.pattern = pattern
        self.reason = reason
        super().__init__(f"Invalid regex /{pattern}/: {reason}.")


class RuleSelfReferentialException(DomainException):
    """Raised when source and destination refer to the same Telegram entity."""
    def __init__(self):
        super().__init__("Cannot create rule: source equals destination.")


class RuleInvalidTimezoneException(DomainException):
    """Raised when time_window.timezone is not a valid IANA timezone."""
    def __init__(self, timezone: str):
        self.timezone = timezone
        super().__init__(f"Invalid timezone: {timezone}.")


class RuleMediaReplacementPathRequiredException(DomainException):
    """Raised when media_replacement.enabled=True but replacement_image_path is null."""
    def __init__(self):
        super().__init__("media_replacement.replacement_image_path is required when enabled=true.")


# ---------------------------------------------------------------------------
# Replacement Rule exceptions (Story 3.2)
# ---------------------------------------------------------------------------

class ReplacementRuleNotFoundException(DomainException):
    """Raised when a requested replacement rule is not found."""
    def __init__(self, replacement_id: str):
        self.replacement_id = replacement_id
        super().__init__(f"Replacement rule {replacement_id} not found.")

