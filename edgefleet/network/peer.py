"""
Asyncio TCP P2P Networking Node & Message Dispatcher
"""
import asyncio
import logging
from typing import Callable, Coroutine, Dict, List, Optional, Tuple
import time
from edgefleet.network.protocol import P2PMessage, MessageType
from edgefleet.network.discovery import DiscoveryTable, PeerEntry
from edgefleet.config import STALE_MESSAGE_THRESHOLD

logger = logging.getLogger(__name__)

class P2PNode:
    """
    Decentralized TCP Node for each AMR.
    """
    def __init__(
        self,
        robot_id: str,
        host: str,
        port: int,
        discovery_table: DiscoveryTable,
        message_handler: Optional[Callable[[P2PMessage], Coroutine]] = None
    ):
        self.robot_id = robot_id
        self.host = host
        self.port = port
        self.discovery_table = discovery_table
        self.message_handler = message_handler

        self._server: Optional[asyncio.Server] = None
        self._seq_counter = 0
        self._running = False
        self._processed_messages: Dict[str, float] = {}  # msg_key -> timestamp
        self.sent_messages_log: List[dict] = []
        self.received_messages_log: List[dict] = []

    def get_next_seq_no(self) -> int:
        self._seq_counter += 1
        return self._seq_counter

    async def start(self) -> None:
        """Starts TCP listening server."""
        self._running = True
        self._server = await asyncio.start_server(
            self._handle_client_connection,
            self.host,
            self.port,
            reuse_address=True
        )
        logger.info(f"[{self.robot_id}] P2P TCP Server listening on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Stops TCP listening server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info(f"[{self.robot_id}] P2P TCP Server stopped.")

    async def _handle_client_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handles incoming TCP stream from a peer."""
        try:
            while self._running:
                line = await reader.readline()
                if not line:
                    break
                decoded_line = line.decode('utf-8').strip()
                if not decoded_line:
                    continue

                try:
                    msg = P2PMessage.from_json(decoded_line)
                    await self._process_incoming_message(msg)
                except Exception as e:
                    logger.warning(f"[{self.robot_id}] Failed to parse incoming P2P message: {e}")
        except Exception as e:
            logger.debug(f"[{self.robot_id}] Connection error with client: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _process_incoming_message(self, msg: P2PMessage) -> None:
        """Filters stale/duplicate messages and forwards to handler."""
        # 1. Stale message rejection
        if msg.is_stale(max_age_seconds=STALE_MESSAGE_THRESHOLD):
            logger.debug(f"[{self.robot_id}] Dropping stale message {msg.message_type} from {msg.sender_id}")
            return

        # 2. Duplicate detection key: (sender_id, seq_no, msg_type)
        msg_key = f"{msg.sender_id}_{msg.sequence_number}_{msg.message_type.value}"
        now = time.time()
        if msg_key in self._processed_messages:
            return
        self._processed_messages[msg_key] = now

        # Prune old processed keys
        if len(self._processed_messages) > 1000:
            cutoff = now - 10.0
            self._processed_messages = {k: v for k, v in self._processed_messages.items() if v > cutoff}

        # 3. Update discovery table last_seen and pose if present in payload
        pos = None
        if "position" in msg.payload and isinstance(msg.payload["position"], (list, tuple)):
            pos = tuple(msg.payload["position"])
        self.discovery_table.update_heartbeat(msg.sender_id, pos=pos, seq_no=msg.sequence_number)

        # Log for dashboard telemetry
        self.received_messages_log.append({
            "type": msg.message_type.value,
            "sender": msg.sender_id,
            "recipient": msg.recipient_id or self.robot_id,
            "seq": msg.sequence_number,
            "timestamp": msg.timestamp,
            "payload": msg.payload
        })
        if len(self.received_messages_log) > 200:
            self.received_messages_log.pop(0)

        # 4. Dispatch to handler
        if self.message_handler:
            await self.message_handler(msg)

    async def send_direct(self, recipient_id: str, msg: P2PMessage) -> bool:
        """Sends a message directly to a specific peer over TCP."""
        peer = self.discovery_table.get_peer(recipient_id)
        if not peer or not peer.is_alive():
            return False

        msg.sequence_number = self.get_next_seq_no()
        msg.recipient_id = recipient_id
        payload_str = msg.to_json() + "\n"

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(peer.host, peer.port),
                timeout=1.0
            )
            writer.write(payload_str.encode('utf-8'))
            await writer.drain()
            writer.close()
            await writer.wait_closed()

            self.sent_messages_log.append({
                "type": msg.message_type.value,
                "sender": self.robot_id,
                "recipient": recipient_id,
                "seq": msg.sequence_number,
                "timestamp": msg.timestamp,
                "payload": msg.payload
            })
            if len(self.sent_messages_log) > 200:
                self.sent_messages_log.pop(0)

            return True
        except Exception as e:
            logger.debug(f"[{self.robot_id}] Failed sending to peer {recipient_id} ({peer.host}:{peer.port}): {e}")
            return False

    async def broadcast_to_relevant(
        self,
        msg: P2PMessage,
        my_pos: Tuple[float, float],
        my_bbox: Optional[Tuple[float, float, float, float]] = None
    ) -> int:
        """
        Scalability Filter: Broadcasts message only to peers within communication radius
        or overlapping bounding boxes.
        """
        success_count = 0
        active_peers = self.discovery_table.get_active_peers()

        for peer in active_peers:
            if peer.robot_id == self.robot_id:
                continue

            # Check relevance
            if self.discovery_table.is_relevant_neighbor(peer.robot_id, my_pos, my_bbox):
                success = await self.send_direct(peer.robot_id, msg)
                if success:
                    success_count += 1

        return success_count

    async def broadcast_to_all(self, msg: P2PMessage) -> int:
        """Broadcasts to all known active peers (used for DISCOVERY and HEARTBEAT)."""
        success_count = 0
        active_peers = self.discovery_table.get_active_peers()
        for peer in active_peers:
            if peer.robot_id == self.robot_id:
                continue
            if await self.send_direct(peer.robot_id, msg):
                success_count += 1
        return success_count
