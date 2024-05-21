from .packets import (
    PACKET_CLASS_TO_TYPE,
    PACKET_TYPE_TO_CLASS,
    PacketType,
    Packet,
)
from .config import SHARED_CONFIG

import socket


class PacketSocket:
    def __init__(self, sock: socket.socket) -> None:
        self.__sock = sock

    def recv(self) -> Packet:
        packet_id = int.from_bytes(
            self.__sock.recv(SHARED_CONFIG["packets"]["packet_id_bytes"])
        )
        packet_type = PacketType(
            int.from_bytes(
                self.__sock.recv(SHARED_CONFIG["packets"]["packet_type_bytes"])
            )
        )
        packet_data_length = int.from_bytes(
            self.__sock.recv(SHARED_CONFIG["packets"]["packet_data_length_bytes"])
        )
        packet_data = self.__sock.recv(packet_data_length)

        packet = PACKET_TYPE_TO_CLASS[packet_type](packet_id)
        packet.init_packet_from_data(packet_data)
        return packet

    def send(self, packet: Packet) -> None:
        self.__sock.sendall(packet.compile())

    @property
    def raw_socket(self) -> socket.socket:
        return self.__sock
