#!/usr/bin/env python3
"""
This module handles broadcasting messages between nodes in a distributed system.
"""
import random
import sys
from pathlib import Path
from typing import Any
import asyncio

sys.path.append(str(Path(__file__).parent.parent))

from api.errors import TimeoutError_
from api import (
    BroadcastOkPayload,
    BroadcastPayload,
    InitOkPayload,
    InitPayload,
    Message,
    NodeBase,
    ReadOkPayload,
    ReadPayload,
    Reply,
    TopologyOkPayload,
    TopologyPayload,
    SyncPayload,
    SyncOkPayload,
    print,
)


class Node(NodeBase):
    """
    Represents a broadcast message in the distributed system.
    """

    neighbors: list[str]
    census: list[str]

    def __init__(self):
        """
        Initializes the broadcast message.
        """
        super().__init__()
        self.messages: set[Any] = set()
        self.census = []
        self.health_check_interval = 10
        asyncio.create_task(self.update_census_periodically())
        asyncio.create_task(self.periodic_sync())

    async def msg_init(self, msg: Message[InitPayload]) -> Reply[InitOkPayload]:
        """
        Initializes the broadcast message.
        Args:
            msg (Message[InitPayload]): The initialization message.
        Returns:
            Reply[InitOkPayload]: The initialization OK payload.
        """
        num_nodes = len(msg.body.node_ids)
        self.census = self.select_census_nodes(msg.body.node_ids, num_nodes)
        return InitOkPayload()

    def select_census_nodes(self, node_ids: list[str], num_nodes: int) -> list[str]:
        """
        Rndomly shuffle and select n/2+1 nodes from the list of node IDs to act as census nodes.
        Args:
            node_ids (list[str]): The list of node IDs.
            num_nodes (int): The number of nodes.
        Returns:
            list[str]: The selected census nodes.
        """
        nodes = [x for x in node_ids if x != self.node_id]
        random.shuffle(nodes)
        census_size = num_nodes // 2 + 1
        return nodes[:census_size]

    async def msg_topology(
        self, msg: Message[TopologyPayload]
    ) -> Reply[TopologyOkPayload]:
        """
        Sets the neighbors of the node based on the topology.
        """
        self.neighbors = msg.body.topology[self.node_id]
        return TopologyOkPayload()

    async def msg_broadcast(
        self, msg: Message[BroadcastPayload]
    ) -> Reply[BroadcastOkPayload]:
        """
        Broadcasting of messages to other nodes in the distributed system
        """
        if msg.body.message not in self.messages:
            self.messages.add(msg.body.message)
            await self.propagate_message(msg.body)
        return BroadcastOkPayload()

    async def propagate_message(self, payload: BroadcastPayload):
        """
        Sending the broadcast message to the node's neighbors and census nodes.
        """
        tasks = [self.send(x, payload) for x in self.census]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def msg_custom_sync(self, msg: Message[SyncPayload]) -> Reply[SyncOkPayload]:
        """
        Responds to incoming sync requests from other nodes.
        """
        if msg.body.my_length >= len(self.messages):
            return SyncOkPayload()
        return SyncOkPayload(my_messages=list(self.messages))

    async def sync_with(self, node_id: str):
        """
        Used to initiate syncronisation with another node
        """
        try:
            data = await self.communicate(
                SyncOkPayload,
                node_id,
                SyncPayload(my_length=len(self.messages)),
                timeout=1,
            )
        except TimeoutError_:
            return
        if data.my_messages:
            self.messages |= set(data.my_messages)

    async def msg_read(self, msg: Message[ReadPayload]) -> Reply[ReadOkPayload]:
        """
        Reads the messages from the nodes in the census.
        """
        await asyncio.gather(*(self.sync_with(x) for x in self.census))
        return ReadOkPayload(messages=list(self.messages))

    async def update_census_periodically(self):
        """
        Asynchronously calls the function to updte a node's census periodically.
        """
        while True:
            await asyncio.sleep(self.health_check_interval) # sleep for a tine period before updating censud
            await self.update_census()

    async def update_census(self):
        """
        Updates the census of a node based on the health of the nodes in the current census.
        """
        healthy_nodes = []
        for node in self.census:
            if await self.check_node_health(node):
                healthy_nodes.append(node)
        if len(healthy_nodes) < len(self.census):
            new_nodes = self.select_census_nodes(self.neighbors, len(self.neighbors))
            self.census = (
                healthy_nodes
                + [node for node in new_nodes if node not in healthy_nodes][
                    : len(self.census) - len(healthy_nodes)
                ]
            )
        print(f"Updated census: {self.census}")

    async def check_node_health(self, node_id: str) -> bool:
        """
        Checks the health of a node
        """
        try:
            await self.communicate(
                SyncOkPayload, node_id, SyncPayload(my_length=0), timeout=1
            )
            return True
        except TimeoutError_:
            return False

    async def periodic_sync(self):
        """
        Asynchronously calls the function to sync with the nodes in the census periodically.
        """
        while True:
            await asyncio.sleep(self.health_check_interval)
            await asyncio.gather(*(self.sync_with(x) for x in self.census))


async def main():
    """
    Entrypoint.
    """
    n = Node()
    await n.run()


asyncio.run(main())
