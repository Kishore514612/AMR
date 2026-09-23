"""
Integration tests for P2P Mesh Networking, Discovery, and Relevance-Based Communication
"""
import pytest
import asyncio
from edgefleet.simulation.warehouse import WarehouseMap
from edgefleet.amr.robot import AMRRobot
from edgefleet.network.protocol import P2PMessage, MessageType

@pytest.mark.asyncio
async def test_two_robot_p2p_tcp_message_exchange():
    wh = WarehouseMap.create_default()
    r1 = AMRRobot("R1", initial_pos=(2, 2), warehouse=wh, port=9301)
    r2 = AMRRobot("R2", initial_pos=(2, 9), warehouse=wh, port=9302)

    await r1.start()
    await r2.start()

    # Mutual discovery
    r1.discovery_table.register_peer("R2", r2.host, r2.port, pos=(2, 9))
    r2.discovery_table.register_peer("R1", r1.host, r1.port, pos=(2, 2))

    # Send direct message R1 -> R2
    test_msg = P2PMessage(
        message_type=MessageType.STATE_UPDATE,
        sender_id="R1",
        payload={"battery": 95.0, "position": [2, 2]}
    )
    success = await r1.p2p_node.send_direct("R2", test_msg)
    assert success is True

    # Allow asyncio loop to process incoming buffer
    await asyncio.sleep(0.1)

    assert "R1" in r2.peer_poses
    assert r2.peer_poses["R1"] == (2, 2)
    assert r2.peer_batteries.get("R1") == 95.0

    await r1.stop()
    await r2.stop()

@pytest.mark.asyncio
async def test_relevance_based_communication_filter():
    wh = WarehouseMap.create_default()
    # R1 at (2, 2), R2 at (5, 2) [Distance = 3 <= 8 Comm Radius] -> RELEVANT
    # R3 at (28, 17) [Distance = 30 > 8 Comm Radius] -> DISTANT / FILTERED OUT
    r1 = AMRRobot("R1", initial_pos=(2, 2), warehouse=wh, port=9303, comm_radius=8.0)
    r2 = AMRRobot("R2", initial_pos=(5, 2), warehouse=wh, port=9304, comm_radius=8.0)
    r3 = AMRRobot("R3", initial_pos=(28, 17), warehouse=wh, port=9305, comm_radius=8.0)

    await r1.start()
    await r2.start()
    await r3.start()

    r1.discovery_table.register_peer("R2", r2.host, r2.port, pos=(5, 2))
    r1.discovery_table.register_peer("R3", r3.host, r3.port, pos=(28, 17))

    # Relevance check
    assert r1.discovery_table.is_relevant_neighbor("R2", my_pos=(2, 2)) is True
    assert r1.discovery_table.is_relevant_neighbor("R3", my_pos=(2, 2)) is False

    # Broadcast to relevant neighbors
    msg = P2PMessage(
        message_type=MessageType.INTENT_UPDATE,
        sender_id="R1",
        payload={"position": [2, 2]}
    )
    sent_count = await r1.p2p_node.broadcast_to_relevant(msg, my_pos=(2, 2))
    assert sent_count == 1  # Delivered to R2 only, R3 spared from O(N^2) traffic!

    await r1.stop()
    await r2.stop()
    await r3.stop()
