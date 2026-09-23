"""
Heartbeat & Peer Liveness Monitor
"""
import asyncio
import logging
from typing import Optional, Tuple
import time
from edgefleet.network.protocol import P2PMessage, MessageType
from edgefleet.network.peer import P2PNode
from edgefleet.config import HEARTBEAT_INTERVAL

logger = logging.getLogger(__name__)

class HeartbeatManager:
    """
    Manages periodic heartbeat emission and peer status monitoring.
    """
    def __init__(
        self,
        p2p_node: P2PNode,
        get_current_pos_callback,
        get_status_callback,
        interval: float = HEARTBEAT_INTERVAL
    ):
        self.p2p_node = p2p_node
        self.get_current_pos = get_current_pos_callback
        self.get_status = get_status_callback
        self.interval = interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_heartbeat_loop())

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run_heartbeat_loop(self) -> None:
        while self._running:
            try:
                pos = self.get_current_pos()
                status = self.get_status()

                msg = P2PMessage(
                    message_type=MessageType.HEARTBEAT,
                    sender_id=self.p2p_node.robot_id,
                    payload={
                        "position": list(pos) if pos else None,
                        "status": status,
                        "timestamp": time.time()
                    }
                )
                await self.p2p_node.broadcast_to_all(msg)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Heartbeat loop exception: {e}")

            await asyncio.sleep(self.interval)
