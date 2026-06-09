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
