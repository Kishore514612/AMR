"""
Unit tests for P2P Protocol, Serialization, and Sequence Numbers
"""
import pytest
import time
from edgefleet.network.protocol import P2PMessage, MessageType

def test_p2p_message_serialization():
    msg = P2PMessage(
        message_type=MessageType.STATE_UPDATE,
        sender_id="R1",
        recipient_id="R2",
        payload={"position": [10.5, 4.2], "battery": 92.5},
        sequence_number=15,
        timestamp=100.0
    )

    json_str = msg.to_json()
    assert isinstance(json_str, str)

    parsed = P2PMessage.from_json(json_str)
    assert parsed.message_type == MessageType.STATE_UPDATE
    assert parsed.sender_id == "R1"
    assert parsed.recipient_id == "R2"
    assert parsed.payload["position"] == [10.5, 4.2]
    assert parsed.sequence_number == 15
    assert parsed.timestamp == 100.0

def test_stale_message_rejection():
    old_msg = P2PMessage(
        message_type=MessageType.HEARTBEAT,
        sender_id="R1",
        timestamp=time.time() - 10.0
    )
    assert old_msg.is_stale(max_age_seconds=5.0) is True

    fresh_msg = P2PMessage(
        message_type=MessageType.HEARTBEAT,
        sender_id="R1",
        timestamp=time.time()
    )
    assert fresh_msg.is_stale(max_age_seconds=5.0) is False

def test_all_message_types_enum():
    types = [
        MessageType.DISCOVERY,
        MessageType.DISCOVERY_ACK,
        MessageType.ADDRESS_UPDATE,
        MessageType.HEARTBEAT,
        MessageType.STATE_UPDATE,
        MessageType.INTENT_UPDATE,
        MessageType.PATH_UPDATE,
        MessageType.CONFLICT_REQUEST,
        MessageType.CONFLICT_RESPONSE,
        MessageType.RESERVATION_REQUEST,
        MessageType.RESERVATION_GRANTED,
        MessageType.YIELD,
        MessageType.PROCEED,
        MessageType.RESERVATION_RELEASE,
        MessageType.REROUTE,
        MessageType.DEADLOCK_ALERT,
    ]
    for m in types:
        msg = P2PMessage(message_type=m, sender_id="R1")
        assert msg.message_type == m
