#!/usr/bin/env python3
"""
Challenge #1: Echo -> This module handles echoing messages between nodes in a distributed system.
"""
import sys
from pathlib import Path
import asyncio
import logging

sys.path.append(str(Path(__file__).parent.parent))

from api import (
    EchoOkPayload,
    EchoPayload,
    InitOkPayload,
    InitPayload,
    Message,
    NodeBase,
    Reply,
    print,
)

logging.basicConfig(level=logging.DEBUG)


class Node(NodeBase):
    """
    Represents a broadcast message in the distributed system
    """

    async def msg_init(self, msg: Message[InitPayload]) -> Reply[InitOkPayload]:
        """
        Initializes the broadcast message.
        """
        return InitOkPayload()

    async def msg_echo(self, msg: Message[EchoPayload]) -> Reply[EchoOkPayload]:
        """
        Echoes the message back to the sender.
        """
        return EchoOkPayload(echo=msg.body.echo)


async def main():
    """
    Main entrypoint for the echo node.
    """
    n = Node()
    await n.run()


if __name__ == "__main__":
    asyncio.run(main())
