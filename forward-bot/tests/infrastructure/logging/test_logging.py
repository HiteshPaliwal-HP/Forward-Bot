from forward_bot.infrastructure.logging import SecretRedactor

def test_secret_redactor_ignores_short_keys():
    """Verify that SecretRedactor only redacts secrets that are at least 6 characters long."""
    # Length < 6 should be ignored, length >= 6 should be loaded
    redactor = SecretRedactor(api_key="12345", secret_key="1234567")
    assert "12345" not in redactor.secrets
    assert "1234567" in redactor.secrets
    
    data = {
        "msg": "API KEY is 12345 and secret is 1234567"
    }
    redacted = redactor.redact(data)
    # "12345" is not redacted (short key ignored to prevent over-scrubbing)
    # "1234567" is redacted correctly
    assert redacted["msg"] == "API KEY is 12345 and secret is [REDACTED]"
