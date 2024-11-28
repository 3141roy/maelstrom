from enum import Enum


class MaelstormErrorCode(int, Enum):
    timeout = 0
    node_not_found = 1

    not_supported = 10
    temporarily_unavailable = 11
    malformed_request = 12
    crash = 13
    abort = 14

    key_does_not_exist = 20
    key_already_exists = 21
    precondition_failed = 22

    txn_conflict = 30

    @property
    def definite(self):
        return self.value in [
            self.node_not_found,
            #
            self.not_supported,
            self.temporarily_unavailable,
            self.malformed_request,
            self.abort,
            #
            self.key_does_not_exist,
            self.key_already_exists,
            self.precondition_failed,
            #
            self.txn_conflict,
        ]


class MaelstormError(RuntimeError):
    def __init__(self, code: MaelstormErrorCode, msg: str = ""):
        super().__init__(f"{code.name}: {msg}" if msg != "" else code.name)
        self.code = code
        self.msg = msg


class TimeoutError_(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.timeout, msg)


class NodeNotFoundError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.node_not_found, msg)


class NotSupportedError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.not_supported, msg)


class TemporarilyUnavailableError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.temporarily_unavailable, msg)


class MalformedRequestError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.malformed_request, msg)


class CrashError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.crash, msg)


class AbortError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.abort, msg)


class KeyDoesNotExistError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.key_does_not_exist, msg)


class KeyAlreadyExistsError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.key_already_exists, msg)


class PreconditionFailedError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.precondition_failed, msg)


class TxnConflictError(MaelstormError):
    def __init__(self, msg: str = ""):
        super().__init__(MaelstormErrorCode.txn_conflict, msg)
