from .items import Relation, Message
from .config import SHARED_CONFIG
from .misc import UniqueValueEnum

import random
import abc


class PacketType(UniqueValueEnum):
    client_authenticate = 100
    client_get_relations = 101
    client_get_messages = 102
    client_add_friend = 103
    client_remove_friend = 104
    client_send_message = 105

    quit = 200
    invalid_packet_type = 201

    server_authenticate = 300
    server_get_relations = 301
    server_get_messages = 302
    server_add_friend = 303
    server_remove_friend = 304
    server_send_message = 305


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


class EmptyPacket(Packet, abc.ABC):
    def init_packet_from_params(self) -> None:
        pass

    def init_packet_from_data(self, data: bytes) -> None:
        pass

    def compile_data(self) -> bytes:
        return b""


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

    class GetRelations(EmptyPacket):
        @property
        def type(self) -> PacketType:
            return PacketType.client_get_relations

    class GetMessages(Packet):
        def init_packet_from_params(self, secondary_user: str, after: int) -> None:
            self.__secondary_user = secondary_user
            self.__after = after

        def init_packet_from_data(self, data: bytes) -> None:
            while len(data) > 8:
                secondary_user_length = int.from_bytes(data[:2])
                data = data[2:]
                self.__secondary_user = data[:secondary_user_length].decode()
                data = data[secondary_user_length:]

            self.__after = int.from_bytes(data)

        def compile_data(self) -> bytes:
            output = bytearray()

            output += len(self.__secondary_user.encode()).to_bytes(2)
            output += self.__secondary_user.encode()
            output += self.__after.to_bytes(8)

            return output

        @property
        def type(self) -> PacketType:
            return PacketType.client_get_messages

        @property
        def secondary_user(self) -> str:
            return self.__secondary_user

        @property
        def after(self) -> int:
            return self.__after

    class AddFriend(Packet):
        def init_packet_from_params(self, username: str) -> None:
            self.__username = username

        def init_packet_from_data(self, data: bytes) -> None:
            self.__username = data.decode()

        def compile_data(self) -> bytes:
            return self.__username.encode()

        @property
        def type(self) -> PacketType:
            return PacketType.client_add_friend

        @property
        def username(self) -> str:
            return self.__username

    class RemoveFriend(Packet):
        def init_packet_from_params(self, username: str) -> None:
            self.__username = username

        def init_packet_from_data(self, data: bytes) -> None:
            self.__username = data.decode()

        def compile_data(self) -> bytes:
            return self.__username.encode()

        @property
        def type(self) -> PacketType:
            return PacketType.client_remove_friend

        @property
        def username(self) -> str:
            return self.__username

    class SendMessage(Packet):

        def init_packet_from_params(self, receiver: str, content: str) -> None:
            self.__receiver = receiver
            self.__content = content

        def init_packet_from_data(self, data: bytes) -> None:
            receiver_length = int.from_bytes(data[:2])
            data = data[2:]
            self.__receiver = data[:receiver_length].decode()
            data = data[receiver_length:]

            self.__content = data.decode()

        def compile_data(self) -> bytes:
            output_bytes = bytearray()

            output_bytes += len(self.__receiver.encode()).to_bytes(2)
            output_bytes += self.__receiver.encode()
            output_bytes += self.__content.encode()

            return output_bytes

        @property
        def type(self) -> PacketType:
            return PacketType.client_send_message

        @property
        def receiver(self) -> str:
            return self.__receiver

        @property
        def content(self) -> str:
            return self.__content


# Shared packets
class SharedPackets:

    class Quit(EmptyPacket):
        @property
        def type(self) -> PacketType:
            return PacketType.quit

    class InvalidPacketType(Packet):
        def init_packet_from_params(self, expected_types: list[PacketType]) -> None:
            self.__expected_types = expected_types

        def init_packet_from_data(self, data: bytes) -> None:
            self.__expected_types = []
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

    class GetRelations(Packet):
        def init_packet_from_params(self, relations: list[Relation]) -> None:
            self.__relations = relations

        def init_packet_from_data(self, data: bytes) -> None:
            self.__relations = []

            while len(data) > 0:
                first_username_length = int.from_bytes(data[:2])
                data = data[2:]
                first_username = data[:first_username_length].decode()
                data = data[first_username_length:]

                secondary_username_length = int.from_bytes(data[:2])
                data = data[2:]
                secondary_username = data[:secondary_username_length].decode()
                data = data[secondary_username_length:]

                first_is_friend = bool(data[0])
                data = data[1:]

                secondary_is_friend = bool(data[0])
                data = data[1:]

                secondary_is_blocked = bool(data[0])
                data = data[1:]

                self.__relations.append(
                    Relation(
                        first_username,
                        secondary_username,
                        first_is_friend,
                        secondary_is_friend,
                        secondary_is_blocked,
                    )
                )

        def compile_data(self) -> bytes:
            output = bytearray()

            for relation in self.__relations:
                output += len(relation.first_username.encode()).to_bytes(2)
                output += relation.first_username.encode()
                output += len(relation.secondary_username.encode()).to_bytes(2)
                output += relation.secondary_username.encode()
                output += b"\xFF" if relation.first_is_friend else b"\x00"
                output += b"\xFF" if relation.secondary_is_friend else b"\x00"
                output += b"\xFF" if relation.secondary_is_blocked else b"\x00"

            return output

        @property
        def type(self) -> PacketType:
            return PacketType.server_get_relations

        @property
        def relations(self) -> list[Relation]:
            return self.__relations

    class GetMessages(Packet):
        def init_packet_from_params(self, messages: list[Message]) -> None:
            self.__messages = messages

        def init_packet_from_data(self, data: bytes) -> None:
            self.__messages = []

            while len(data) > 0:
                sender_length = int.from_bytes(data[:2])
                data = data[2:]
                sender = data[:sender_length].decode()
                data = data[sender_length:]

                receiver_length = int.from_bytes(data[:2])
                data = data[2:]
                receiver = data[:receiver_length].decode()
                data = data[receiver_length:]

                time_sent = int.from_bytes(data[:8])
                data = data[8:]

                content_length = int.from_bytes(data[:8])
                data = data[8:]
                content = data[:content_length].decode()
                data = data[content_length:]

                self.__messages.append(Message(sender, receiver, time_sent, content))

        def compile_data(self) -> bytes:
            output = bytearray()

            for message in self.__messages:
                output += len(message.sender.encode()).to_bytes(2)
                output += message.sender.encode()
                output += len(message.receiver.encode()).to_bytes(2)
                output += message.receiver.encode()
                output += message.time_sent.to_bytes(8)
                output += len(message.content.encode()).to_bytes(8)
                output += message.content.encode()

            return output

        @property
        def type(self) -> PacketType:
            return PacketType.server_get_messages

        @property
        def messages(self) -> list[Message]:
            return self.__messages

    class AddFriend(Packet):
        def init_packet_from_params(self, success: bool) -> None:
            self.__success = success

        def init_packet_from_data(self, data: bytes) -> None:
            self.__success = bool(int.from_bytes(data))

        def compile_data(self) -> bytes:
            return b"\xFF" if self.__success else b"\x00"

        @property
        def type(self) -> PacketType:
            return PacketType.server_add_friend

        @property
        def success(self) -> bool:
            return self.__success

    class RemoveFriend(EmptyPacket):
        @property
        def type(self) -> PacketType:
            return PacketType.server_remove_friend

    class SendMessage(EmptyPacket):
        @property
        def type(self) -> PacketType:
            return PacketType.server_send_message


PACKET_TYPE_TO_CLASS: dict[PacketType, type[Packet]] = {
    # Client packets
    PacketType.client_authenticate: ClientPackets.Authenticate,
    PacketType.client_get_relations: ClientPackets.GetRelations,
    PacketType.client_get_messages: ClientPackets.GetMessages,
    PacketType.client_add_friend: ClientPackets.AddFriend,
    PacketType.client_remove_friend: ClientPackets.RemoveFriend,
    PacketType.client_send_message: ClientPackets.SendMessage,
    # Shared packets
    PacketType.quit: SharedPackets.Quit,
    PacketType.invalid_packet_type: SharedPackets.InvalidPacketType,
    # Server packets
    PacketType.server_authenticate: ServerPackets.Authenticate,
    PacketType.server_get_relations: ServerPackets.GetRelations,
    PacketType.server_get_messages: ServerPackets.GetMessages,
    PacketType.server_add_friend: ServerPackets.AddFriend,
    PacketType.server_remove_friend: ServerPackets.RemoveFriend,
    PacketType.server_send_message: ServerPackets.SendMessage,
}

PACKET_CLASS_TO_TYPE = {
    packet_class: packet_type
    for packet_type, packet_class in PACKET_TYPE_TO_CLASS.items()
}
