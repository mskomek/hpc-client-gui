"""Own and close the client threads used by mock SSH integration servers."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable

import paramiko


class ClientHandlerRegistry:
    def __init__(self, stop_event: threading.Event) -> None:
        self._stop = stop_event
        self._lock = threading.RLock()
        self._threads: set[threading.Thread] = set()
        self._sockets: set[socket.socket] = set()
        self._transports: set[paramiko.Transport] = set()

    def start(self, client_sock: socket.socket, handler: Callable[[socket.socket], None]) -> None:
        worker = threading.Thread(
            target=self._run_handler, args=(client_sock, handler), daemon=True
        )
        with self._lock:
            self._threads.add(worker)
            self._sockets.add(client_sock)
        try:
            worker.start()
        except BaseException:
            with self._lock:
                self._threads.discard(worker)
                self._sockets.discard(client_sock)
            client_sock.close()
            raise

    def _run_handler(
        self,
        client_sock: socket.socket,
        handler: Callable[[socket.socket], None],
    ) -> None:
        try:
            handler(client_sock)
        finally:
            with self._lock:
                self._threads.discard(threading.current_thread())
                self._sockets.discard(client_sock)

    def add_transport(self, transport: paramiko.Transport) -> None:
        with self._lock:
            self._transports.add(transport)

    def remove_transport(self, transport: paramiko.Transport) -> None:
        with self._lock:
            self._transports.discard(transport)

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._threads)

    def close(self, listener_thread: threading.Thread | None) -> None:
        with self._lock:
            transports = tuple(self._transports)
            client_sockets = tuple(self._sockets)
            client_threads = tuple(self._threads)
        for transport in transports:
            try:
                transport.close()
            except Exception:
                pass
        for client_sock in client_sockets:
            try:
                client_sock.close()
            except OSError:
                pass
        deadline = time.monotonic() + 3.0
        threads = ([listener_thread] if listener_thread is not None else []) + list(client_threads)
        for worker in threads:
            if worker is threading.current_thread():
                continue
            try:
                worker.join(timeout=max(0.0, deadline - time.monotonic()))
            except Exception:
                pass
