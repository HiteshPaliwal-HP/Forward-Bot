from datetime import datetime, timezone
from forward_bot.domain.entities.message_mapping import MessageMapping


def test_message_mapping_instantiation() -> None:
    now = datetime.now(timezone.utc)
    mapping = MessageMapping(
        forwarding_rule_id="507f1f77bcf86cd799439011",
        source_channel_id=11111,
        source_message_id=22222,
        destination_channel_id=33333,
        destination_message_id=44444,
        forwarded_at=now,
    )
    assert mapping.forwarding_rule_id == "507f1f77bcf86cd799439011"
    assert mapping.source_channel_id == 11111
    assert mapping.source_message_id == 22222
    assert mapping.destination_channel_id == 33333
    assert mapping.destination_message_id == 44444
    assert mapping.forwarded_at == now
    assert mapping.id is None
