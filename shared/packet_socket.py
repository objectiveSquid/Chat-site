from .packets import (
    PACKET_TYPE_TO_CLASS,
    PacketType,
    Packet,
)
from .config import SHARED_CONFIG

import logging
import socket
import os


class RaisingSocket(socket.socket):
    def recv(self, bufsize: int, flags: int = 0) -> bytes:
        data = super().recv(bufsize, flags)
        if len(data) == 0 and bufsize > 0:
            raise ConnectionResetError("Connection reset by peer")

        return data

    @classmethod
    def from_existing_socket(cls, sock: socket.socket):
        instance = cls(sock.family, sock.type, sock.proto)

        instance.setblocking(sock.getblocking())
        os.dup2(sock.fileno(), instance.fileno())

        return instance


class PacketSocket:
    def __init__(self, sock: socket.socket) -> None:
        self.__raising_sock = RaisingSocket.from_existing_socket(sock)
        self.__logger = logging.getLogger(
            f"PacketSocket ({sock.getpeername()[0]}:{sock.getpeername()[1]})"
        )

    def recv(self) -> Packet:
        packet_id = int.from_bytes(
            self.__raising_sock.recv(SHARED_CONFIG["packets"]["packet_id_bytes"])
        )
        packet_type = PacketType(
            int.from_bytes(
                self.__raising_sock.recv(SHARED_CONFIG["packets"]["packet_type_bytes"])
            )
        )
        packet_data_length = int.from_bytes(
            self.__raising_sock.recv(
                SHARED_CONFIG["packets"]["packet_data_length_bytes"]
            )
        )
        packet_data = self.__raising_sock.recv(packet_data_length)

        packet = PACKET_TYPE_TO_CLASS[packet_type](packet_id)
        packet.init_packet_from_data(packet_data)
        self.__logger.debug(
            "Received packet (type: %s, id: %s, data_length: %s bytes)",
            packet.type.name,
            packet.id,
            packet.data_length,
        )
        return packet

    def send(self, packet: Packet) -> None:
        self.__logger.debug(
            "Sending packet (type: %s, id: %s, data_length: %s bytes)",
            packet.type.name,
            packet.id,
            packet.data_length,
        )
        self.__raising_sock.sendall(packet.compile())

    @property
    def raising_socket(self) -> socket.socket:
        return self.__raising_sock
