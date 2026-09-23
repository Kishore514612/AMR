"""
P2P Network Protocol & Message Schema
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import json
import time

class MessageType(str, Enum):
    DISCOVERY = "DISCOVERY"
    DISCOVERY_ACK = "DISCOVERY_ACK"
    ADDRESS_UPDATE = "ADDRESS_UPDATE"
    HEARTBEAT = "HEARTBEAT"
    STATE_UPDATE = "STATE_UPDATE"
    INTENT_UPDATE = "INTENT_UPDATE"
    PATH_UPDATE = "PATH_UPDATE"
    CONFLICT_REQUEST = "CONFLICT_REQUEST"
    CONFLICT_RESPONSE = "CONFLICT_RESPONSE"
    RESERVATION_REQUEST = "RESERVATION_REQUEST"
    RESERVATION_GRANTED = "RESERVATION_GRANTED"
    YIELD = "YIELD"
    PROCEED = "PROCEED"
    RESERVATION_RELEASE = "RESERVATION_RELEASE"
    REROUTE = "REROUTE"
    DEADLOCK_ALERT = "DEADLOCK_ALERT"

@dataclass
class P2PMessage:
    message_type: MessageType
    sender_id: str
    recipient_id: Optional[str] = None  # None indicates broadcast to relevant peers
    payload: Dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if isinstance(self.message_type, str):
            self.message_type = MessageType(self.message_type)

    def is_stale(self, max_age_seconds: float = 5.0, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        return (now - self.timestamp) > max_age_seconds

    def to_json(self) -> str:
        return json.dumps({
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "payload": self.payload,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp
        })

    @classmethod
    def from_json(cls, json_str: str) -> "P2PMessage":
        data = json.loads(json_str)
        return cls(
            message_type=MessageType(data["message_type"]),
            sender_id=data["sender_id"],
            recipient_id=data.get("recipient_id"),
            payload=data.get("payload", {}),
            sequence_number=data.get("sequence_number", 0),
            timestamp=data.get("timestamp", 0.0)
        )
