import asyncio
from dataclasses import dataclass, asdict
import logging
from enum import Enum
from inspect import get_annotations, getmembers, ismethod
import json
import sys
import traceback
from typing import Any, Generic, TypeAlias, TypeVar, get_args

from api.errors import (
    CrashError,
    MaelstormError,
    MaelstormErrorCode,
    NotSupportedError,
    TimeoutError_,
)

_og_print = print

PayloadBodyFieldPrimitive: TypeAlias = int | float | str | bool | None
PayloadBodyField = (
    PayloadBodyFieldPrimitive
    | list[PayloadBodyFieldPrimitive]
    | dict[str, PayloadBodyFieldPrimitive]
)


def print(*args, **kwargs):
    _og_print(*args, **kwargs, file=sys.stderr)


async def setup_stdio():
    # alex_noname CC BY-SA 4.0 https://stackoverflow.com/a/64317899
    # - Cosmetic changes were made to code layout and variable naming
    loop = asyncio.get_running_loop()

    stdin = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(stdin)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    w_transport, w_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    stdout = asyncio.StreamWriter(w_transport, w_protocol, stdin, loop)
    return stdin, stdout


class PayloadType(Enum):
    INIT = "init"
    INIT_OK = "init_ok"
    ERROR = "error"
    ECHO = "echo"
    ECHO_OK = "echo_ok"
    GENERATE = "generate"
    GENERATE_OK = "generate_ok"
    TOPOLOGY = "topology"
    TOPOLOGY_OK = "topology_ok"
    BROADCAST = "broadcast"
    BROADCAST_OK = "broadcast_ok"
    READ = "read"
    READ_OK = "read_ok"
    CUSTOM_SYNC = "custom_sync"
    CUSTOM_SYNC_OK = "custom_sync_ok"


@dataclass(kw_only=True)
class Payload:
    type: PayloadType
    msg_id: int | None = None
    in_reply_to: int | None = None


@dataclass(kw_only=True)
class InitPayload(Payload):
    type: PayloadType = PayloadType.INIT
    node_id: str
    node_ids: list[str]


@dataclass(kw_only=True)
class InitOkPayload(Payload):
    type: PayloadType = PayloadType.INIT_OK


@dataclass(kw_only=True)
class ErrorPayload(Payload):
    type: PayloadType = PayloadType.ERROR
    code: int
    text: str | None = None


PayloadT = TypeVar("PayloadT", bound=Payload)


@dataclass(frozen=True, kw_only=True)
class Message(Generic[PayloadT]):
    id: int | None = None
    src: str
    dest: str
    body: PayloadT


Reply: TypeAlias = PayloadT | None

# Workload: echo


@dataclass(kw_only=True)
class EchoPayload(Payload):
    type: PayloadType = PayloadType.ECHO
    echo: PayloadBodyField


@dataclass(kw_only=True)
class EchoOkPayload(Payload):
    type: PayloadType = PayloadType.ECHO_OK
    echo: PayloadBodyField


# Workload: unique-IDs


@dataclass(kw_only=True)
class GeneratePayload(Payload):
    type: PayloadType = PayloadType.GENERATE


@dataclass(kw_only=True)
class GenerateOkPayload(Payload):
    type: PayloadType = PayloadType.GENERATE_OK
    id: PayloadBodyField


# Workload: broadcast


@dataclass(kw_only=True)
class TopologyPayload(Payload):
    type: PayloadType = PayloadType.TOPOLOGY
    topology: dict[str, list[str]]


@dataclass(kw_only=True)
class TopologyOkPayload(Payload):
    type: PayloadType = PayloadType.TOPOLOGY_OK


@dataclass(kw_only=True)
class BroadcastPayload(Payload):
    type: PayloadType = PayloadType.BROADCAST
    message: PayloadBodyField


@dataclass(kw_only=True)
class BroadcastOkPayload(Payload):
    type: PayloadType = PayloadType.BROADCAST_OK


@dataclass(kw_only=True)
class ReadPayload(Payload):
    type: PayloadType = PayloadType.READ


@dataclass(kw_only=True)
class ReadOkPayload(Payload):
    type: PayloadType = PayloadType.READ_OK
    messages: list[PayloadBodyField]

@dataclass(kw_only=True)
class SyncPayload(Payload):
    type: PayloadType = PayloadType.CUSTOM_SYNC
    my_length: int


@dataclass(kw_only=True)
class SyncOkPayload(Payload):
    type: PayloadType = PayloadType.CUSTOM_SYNC_OK
    my_messages: list[int] | None = None


# Node base


class NodeBase:
    handler_timeout: float = 5
    stdin: asyncio.StreamReader
    stdout: asyncio.StreamWriter
    running: bool
    node_id: str
    node_idx: int
    node_ids: list[str]
    last_msg_id: int = 0
    receives_waiting: dict[int, tuple[asyncio.Event, Any]] = {}

    async def run(self):
        print("Setting up I/O")
        self.stdin, self.stdout = await setup_stdio()
        running = True
        methods = {
            name[len("msg_") :]: f
            for name, f in getmembers(
                self, lambda x: ismethod(x) and x.__name__.startswith("msg_")
            )
        }

        async def process_line(line: bytes):
            try:
                data: Any
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"failed to decode message: {line}") from e

                try:
                    try:
                        body = data["body"]
                        del data["body"]
                        type_ = PayloadType(body["type"])
                        logging.debug(f"Processing message type: {type_}, body: {body}")

                        if type_ == PayloadType.INIT:
                            self.node_id = body["node_id"]
                            self.node_ids = body["node_ids"]
                            self.node_idx = self.node_ids.index(self.node_id)
                        elif type_ == PayloadType.ERROR:
                            print(
                                f"!!! Error ({body['code']})"
                                + (
                                    f": {body['text']}"
                                    if body["text"] is not None
                                    else ""
                                )
                            )
                        in_reply_to = body.get("in_reply_to")
                        rec = (
                            self.receives_waiting.get(in_reply_to)
                            if in_reply_to is not None
                            else None
                        )
                        if rec is not None:
                            self.receives_waiting[in_reply_to] = (rec[0], body)
                            rec[0].set()
                            return
                        handler = methods.get(type_.value)
                        if handler is None:
                            raise NotSupportedError(f"unknown message type: {type_}")
                        payload_cls = get_args(get_annotations(handler)["msg"])[0]
                        try:
                            reply: Reply[Payload] = await asyncio.wait_for(
                                handler(Message(**data, body=payload_cls(**body))),
                                self.handler_timeout,
                            )
                        except TimeoutError as e:
                            raise TimeoutError_(f"handler timed out: {type_}") from e
                        except Exception as e:
                            raise CrashError(f"handler crashed: {type_}") from e
                        if reply is not None:
                            reply.in_reply_to = body["msg_id"]
                            await self.send(data["src"], reply)
                    except Exception as e:
                        raise CrashError() from e
                except MaelstormError as err:
                    print(f"!!! Internal error ({err.code.name}):", err.msg)
                    print(traceback.format_exc())
                    await self.error(data["dest"], err.code, err.msg)
            except Exception:
                print(traceback.format_exc())

        print("Starting main loop")
        while running:
            try:
                line = await self.stdin.readline()
                logging.debug(f"Received line: {line}")
                asyncio.create_task(process_line(line))
            except Exception:
                print(traceback.format_exc())
                continue

    async def send(self, dest: str, body: Payload, *, msg_id: int | None = None):
        if not dest[0] == "c" and dest not in self.node_ids:
            raise ValueError("unknown destination:", dest)
        if msg_id is None:
            msg_id = self.last_msg_id
            self.last_msg_id += 1
        data = {
            "src": self.node_id,
            "dest": dest,
            "body": {
                k: (v.value if isinstance(v, Enum) else v)
                for k, v in asdict(body).items()
                if v is not None
            },
        }
        data["body"]["msg_id"] = msg_id
        x = json.dumps(data) + "\n"
        self.stdout.write(x.encode())
        await self.stdout.drain()

    async def communicate(
        self,
        res_cls: type[PayloadT],
        dest: str,
        body: Payload,
        *,
        timeout: float | None = None,
    ) -> PayloadT:
        msg_id = self.last_msg_id
        self.last_msg_id += 1

        ev = asyncio.Event()
        self.receives_waiting[msg_id] = (ev, None)

        await self.send(dest, body, msg_id=msg_id)
        try:
            await asyncio.wait_for(self.receives_waiting[msg_id][0].wait(), timeout)
        except TimeoutError as e:
            raise TimeoutError_(f"reply timed out: {msg_id} ") from e

        res_body = self.receives_waiting[msg_id][1]
        del self.receives_waiting[msg_id]
        return res_cls(**res_body)

    async def error(self, dest: str, code: MaelstormErrorCode, text: str | None = None):
        await self.send(dest, ErrorPayload(code=code.value, text=text))

    async def msg_init(self, msg: Message[InitPayload]) -> Reply[InitOkPayload]:
        logging.debug(f"Handled init message: {msg}")
        return InitOkPayload()

    async def msg_error(self, msg: Message[ErrorPayload]) -> None:
        logging.debug(f"Handled error message: {msg}")

    async def msg_echo(self, msg: Message[EchoPayload]) -> Reply[EchoOkPayload]:
        raise NotSupportedError()

    async def msg_echo_ok(self, msg: Message[EchoOkPayload]) -> None:
        raise NotSupportedError()

    async def msg_generate(
        self, msg: Message[GeneratePayload]
    ) -> Reply[GenerateOkPayload]:
        raise NotSupportedError()

    async def msg_generate_ok(self, msg: Message[GenerateOkPayload]) -> None:
        raise NotSupportedError()

    async def msg_topology(
        self, msg: Message[TopologyPayload]
    ) -> Reply[TopologyOkPayload]:
        raise NotSupportedError()

    async def msg_topology_ok(self, msg: Message[TopologyOkPayload]) -> None:
        raise NotSupportedError()

    async def msg_broadcast(
        self, msg: Message[BroadcastPayload]
    ) -> Reply[BroadcastOkPayload]:
        raise NotSupportedError()

    async def msg_broadcast_ok(self, msg: Message[BroadcastOkPayload]) -> None:
        raise NotSupportedError()

    async def msg_read(self, msg: Message[ReadPayload]) -> Reply[ReadOkPayload]:
        raise NotSupportedError()

    async def msg_read_ok(self, msg: Message[ReadOkPayload]) -> None:
        raise NotSupportedError()
