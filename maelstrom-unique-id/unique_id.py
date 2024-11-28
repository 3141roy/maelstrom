#!/usr/bin/env python3
"""
Challenge #2: Unique ID Generation -> 
"""
import sys
from pathlib import Path
import asyncio
import uuid
import logging

sys.path.append(str(Path(__file__).parent.parent))

from api import (
    GenerateOkPayload,
    GeneratePayload,
    InitOkPayload,
    InitPayload,
    Message,
    NodeBase,
    Reply,
)

logging.basicConfig(level=logging.DEBUG)


class UniqueIDNode(NodeBase):
    """
    Represents a unique ID generation node in the distributed system.
    """

    def __init__(self):
        """
        Initializes the unique ID generation node.
        """
        super().__init__()
        self.unique_ids = set()

    async def msg_init(self, msg: Message[InitPayload]) -> Reply[InitOkPayload]:
        """
        Initializes the unique ID generation node.
        """
        return InitOkPayload()

    async def msg_generate(
        self, msg: Message[GeneratePayload]
    ) -> Reply[GenerateOkPayload]:
        """
        Generates a unique ID.
        """
        while True:
            identity = uuid.uuid4().hex
            if identity not in self.unique_ids:
                self.unique_ids.add(identity)
                return GenerateOkPayload(id=identity)
            logging.debug("Collision detected for UUID: %s, retrying...", identity)


async def main():
    """
    The main function to run the unique ID generation node.
    """
    node_instance = UniqueIDNode()
    await node_instance.run()


if __name__ == "__main__":
    asyncio.run(main())
