from .config import SHARED_CONFIG
from .misc import UniqueValueEnum

import random
import abc


class PacketType(UniqueValueEnum):
    client_authenticate = 100

    quit = 200
    invalid_packet_type = 201

    server_authenticate = 300


class Packet(abc.ABC):
    def __init__(self, id: int | None = None) -> None:
        if isinstance(id, int):
            self.__id = id
        else:
            self.__id = int.from_bytes(
                random.randbytes(SHARED_CONFIG["packets"]["packet_id_bytes"])
            )

    def compile(self) -> bytes:
        return (
            self.__id.to_bytes(SHARED_CONFIG["packets"]["packet_id_bytes"])
            + self.type.value.to_bytes(SHARED_CONFIG["packets"]["packet_type_bytes"])
            + self.data_length.to_bytes(
                SHARED_CONFIG["packets"]["packet_data_length_bytes"]
            )
            + self.compile_data()
        )

    @property
    def id(self) -> int:
        return self.__id

    @property
    def data_length(self) -> int:
        return len(self.compile_data())

    @abc.abstractmethod
    def init_packet_from_params(self) -> None: ...

    @abc.abstractmethod
    def init_packet_from_data(self, data: bytes) -> None: ...

    @abc.abstractmethod
    def compile_data(self) -> bytes: ...

    @property
    @abc.abstractmethod
    def type(self) -> PacketType: ...


# Client Packets
class ClientPackets:

    class Authenticate(Packet):
        def init_packet_from_params(self, token: str) -> None:
            self.__token = token

        def init_packet_from_data(self, data: bytes) -> None:
            self.__token = data.decode()

        def compile_data(self) -> bytes:
            return self.__token.encode()

        @property
        def token(self) -> str:
            return self.__token

        @property
        def type(self) -> PacketType:
            return PacketType.client_authenticate


# Shared packets
class SharedPackets:

    class Quit(Packet):
        def init_packet_from_params(self) -> None:
            pass

        def compile_data(self) -> bytes:
            return b""

        def init_packet_from_data(self, data: bytes) -> None:
            pass

        @property
        def type(self) -> PacketType:
            return PacketType.quit

    class InvalidPacketType(Packet):
        def init_packet_from_params(self, expected_types: list[PacketType]) -> None:
            self.__expected_types = expected_types

        def init_packet_from_data(self, data: bytes) -> None:
            i = 0
            while i < len(data):
                packet_type = PacketType(
                    int.from_bytes(
                        data[i:][: SHARED_CONFIG["packets"]["packet_type_bytes"]]
                    )
                )
                self.__expected_types.append(packet_type)
                i += SHARED_CONFIG["packets"]["packet_type_bytes"]

        def compile_data(self) -> bytes:
            output_bytes = bytearray()
            for expected_type in self.__expected_types:
                output_bytes += expected_type.value.to_bytes(
                    SHARED_CONFIG["packets"]["packet_type_bytes"]
                )
            return output_bytes

        @property
        def type(self) -> PacketType:
            return PacketType.invalid_packet_type


# Server Packets
class ServerPackets:

    class Authenticate(Packet):
        def init_packet_from_params(self, success: bool, username: str | None) -> None:
            self.__success = success
            self.__username = username

        def init_packet_from_data(self, data: bytes) -> None:
            self.__success = bool(data[0])
            self.__username = data[1:].decode()

        def compile_data(self) -> bytes:
            output_data = bytearray()

            if self.__success:
                output_data += b"\xFF"
            else:
                output_data += b"\x00"
            if self.__username != None:
                output_data += self.__username.encode()

            return output_data

        @property
        def success(self) -> bool:
            return self.__success

        @property
        def username(self) -> str | None:
            return self.__username

        @property
        def type(self) -> PacketType:
            return PacketType.server_authenticate


PACKET_TYPE_TO_CLASS: dict[PacketType, type[Packet]] = {
    # Client packets
    PacketType.client_authenticate: ClientPackets.Authenticate,
    # Shared packets
    PacketType.quit: SharedPackets.Quit,
    PacketType.invalid_packet_type: SharedPackets.InvalidPacketType,
    # Server packets
    PacketType.server_authenticate: ServerPackets.Authenticate,
}

PACKET_CLASS_TO_TYPE = {
    packet_class: packet_type
    for packet_type, packet_class in PACKET_TYPE_TO_CLASS.items()
}
