from typing import Tuple
from abc import ABCMeta, abstractmethod

AddressType = Tuple[str, int]


class Socket(metaclass=ABCMeta):
    @abstractmethod
    async def recv(self, num: int) -> bytes:
        raise NotImplementedError()

    @abstractmethod
    async def send(self, data: bytes) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError()

    @property
    @abstractmethod
    def closed(self) -> bool:
        """
        return True if socket is closed.
        """
        raise NotImplementedError()
