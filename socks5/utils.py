import asyncio
import warnings
import logging
from asyncio import Task, Future
from socket import AF_INET, AF_INET6, inet_pton
from typing import Optional, Set

from websockets.legacy.client import (
    WebSocketClientProtocol,
    connect as websockets_connect,
)

from .values import Atyp
from .types import Socket, AddressType


def judge_atyp(host: str) -> int:
    """
    return the host's ATYP.
    """
    try:
        inet_pton(AF_INET, host)
        return Atyp.IPV4
    except OSError:
        pass

    try:
        inet_pton(AF_INET6, host)
        return Atyp.IPV6
    except OSError:
        pass

    return Atyp.DOMAIN


def onlyfirst(*coros, loop=None) -> Future:
    """
    Execute multiple coroutines concurrently, returning only the results of the first execution.

    When one is completed, the execution of other coroutines will be canceled.
    """
    loop = loop or asyncio.get_running_loop()
    tasks: Set[Task] = set()
    result, _future = loop.create_future(), None

    def _done_callback(fut: Future) -> None:
        nonlocal result, _future

        if result.cancelled():
            return  # nothing to do on onlyfirst cancelled

        if _future is None:
            _future = fut  # record first completed future

        cancel_all_task()

        if not result.done():
            if _future.exception() is None:
                result.set_result(_future.result())
            else:
                result.set_exception(_future.exception())

    def cancel_all_task() -> None:
        for task in tasks:
            task.remove_done_callback(_done_callback)

        for task in filter(lambda task: not task.done(), tasks):
            task.cancel()

    for coro in coros:
        task: Task = loop.create_task(coro)
        task.add_done_callback(_done_callback)
        tasks.add(task)

    result.add_done_callback(lambda fut: cancel_all_task())

    return result


class TCPSocket(Socket):
    """
    wrapper asyncio.StreamReader, asyncio.StreamWriter
    """

    state_log = logging.getLogger("Socket.state")
    message_log = logging.getLogger("Socket.message")

    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self.r = reader
        self.w = writer
        self.__address = writer.get_extra_info("peername")
        self.state_log.debug(f"Opened {self}")

    def __del__(self) -> None:
        if not self.closed:
            warnings.warn(f"{self} not closed.")

    def __repr__(self) -> str:
        return (
            "["
            + str(self.w.get_extra_info("sockname"))
            + ", "
            + str(self.w.get_extra_info("peername"))
            + "]"
        )

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def address(self) -> AddressType:
        """
        return remote address.
        """
        return self.__address

    async def recv(self, num: int) -> bytes:
        data = await self.r.read(num)
        self.message_log.debug(f"<<< {data}")
        return data

    async def send(self, data: bytes) -> int:
        self.w.write(data)
        await self.w.drain()
        self.message_log.debug(f">>> {data}")
        return len(data)

    @property
    def closed(self) -> bool:
        return self.w.is_closing()

    async def close(self) -> None:
        self.w.close()
        self.state_log.debug(f"Closed {self}")

        try:
            await self.w.wait_closed()
        except ConnectionError:
            pass  # in closing, sending the remaining data may cause a network error


class WebSocket(Socket):
    connection: Optional[WebSocketClientProtocol] = None
    stopped = False

    def __init__(self, host: str, port: int, ws_proxy: str) -> None:
        self.ws = websockets_connect(f"{ws_proxy}?host={host}&port={port}")
        self.reader = asyncio.StreamReader()

        self.recv_task = asyncio.create_task(self._recv_worker())
        self.start_signal = asyncio.Event()

    async def _recv_worker(self) -> None:
        try:
            async with self.ws as connection:
                self.connection = connection
                self.start_signal.set()
                while not self.stopped:
                    data = await connection.recv()
                    if isinstance(data, str):
                        data = data.encode()
                    self.reader.feed_data(data)
        except Exception as e:
            self.reader.set_exception(e)

        self.reader.feed_eof()
        self.connection = None

    async def recv(self, num: int) -> bytes:
        return await self.reader.read(num)

    async def send(self, data: bytes) -> int:
        if self.connection is None:
            await self.start_signal.wait()

        assert self.connection is not None, "WebSocket connection is None"
        await self.connection.send(data)
        return len(data)

    @property
    def closed(self) -> bool:
        return self.stopped

    async def close(self) -> None:
        self.stopped = True
        if self.connection is not None:
            await self.connection.close()
        await self.recv_task
