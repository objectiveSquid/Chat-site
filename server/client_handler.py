from .client_stuff import ServerSideClient
from shared.config import SERVER_CONFIG
from .db_handler import DBWrapper

import threading
import socket
import sys


class Server(threading.Thread):
    def __init__(self) -> None:
        super().__init__(name="ChatServer")
        self.__create_and_bind_socket(
            SERVER_CONFIG["connection"]["listen_address"],
            SERVER_CONFIG["connection"]["listen_port"],
        )

        self.__running = False
        self.__clients: list[ServerSideClient] = []
        self.__db_wrapper = DBWrapper()
        self.__db_wrapper.ensure_tables()

    def run(self) -> None:
        self.__running = True

        while self.__running:
            try:
                new_client_sock = self.__sock.accept()[0]
            except OSError:
                self.stop()
                break

            new_client_sock.setblocking(False)
            new_client = ServerSideClient(new_client_sock, self)
            new_client.start()
            self.__clients.append(new_client)

    def stop(self) -> None:
        self.__running = False

    def __create_and_bind_socket(self, address: str, port: int) -> None:
        self.__sock = socket.socket()
        if sys.platform != "win32":
            self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__sock.bind((address, port))
        self.__sock.listen(2)
        self.__sock.setblocking(True)

    @property
    def clients(self) -> list[ServerSideClient]:
        return self.__clients

    @property
    def db_wrapper(self) -> DBWrapper:
        return self.__db_wrapper
