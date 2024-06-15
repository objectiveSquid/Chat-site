from shared.packets import ServerPackets, SharedPackets, ClientPackets, Packet
from shared.packet_socket import PacketSocket
from shared.items import Relation, Message
from shared.config import CLIENT_CONFIG

import dataclasses
import threading
import logging
import random
import socket
import time
import abc


def generate_random_event_id() -> int:
    return int.from_bytes(random.randbytes(CLIENT_CONFIG["events"]["event_id_bytes"]))


@dataclasses.dataclass(frozen=True)
class Event(abc.ABC):
    id: int


class InputEvents:
    class GetRelations(Event): ...

    @dataclasses.dataclass(frozen=True)
    class GetMessages(Event):
        sender: str
        after: int

    @dataclasses.dataclass(frozen=True)
    class AddFriend(Event):
        username: str

    @dataclasses.dataclass(frozen=True)
    class RemoveFriend(Event):
        username: str

    @dataclasses.dataclass(frozen=True)
    class SendMessage(Event):
        receiver: str
        content: str


class OutputEvents:
    @dataclasses.dataclass(frozen=True)
    class GetRelations(Event):
        relations: list[Relation]

    @dataclasses.dataclass(frozen=True)
    class GetMessages(Event):
        messages: list[Message]

    @dataclasses.dataclass(frozen=True)
    class AddFriend(Event):
        success: bool

    class RemoveFriend(Event): ...

    class SendMessage(Event): ...


class Connection(threading.Thread):
    def __init__(self, token: str) -> None:
        super().__init__(name="ChatConnection")
        self.__logger = logging.getLogger("Connection")

        self.__sock = socket.socket()
        self.__sock.connect(
            (
                CLIENT_CONFIG["connection"]["connect_address"],
                CLIENT_CONFIG["connection"]["connect_port"],
            )
        )
        self.__sock.setblocking(False)
        self.__packet_sock = PacketSocket(self.__sock)
        self.__token = token

        self.__pending_packets = []
        self.__authenticated = False
        self.__username = None

        self.__running = False
        self.__send_quit = False

        self.__output_events = []
        self.__input_events = []

    def run(self) -> None:
        self.__running = True

        # authenticate
        while self.__running:
            try:
                auth_packet = ClientPackets.Authenticate()
                auth_packet.init_packet_from_params(self.__token)
                response_packet: ServerPackets.Authenticate = self.send_and_wait_for_response(auth_packet)  # type: ignore
                self.__logger.debug(
                    "Received authentication response (username: %s, length: %s)",
                    response_packet.username,
                    response_packet.data_length,
                )
                self.__authenticated = response_packet.success

                if not self.__authenticated:
                    self.__logger.critical(
                        "Incorrect token supplied (token: %s)",
                        CLIENT_CONFIG["user"]["token"],
                    )
                    self.stop(send_quit=False)
                    break
                self.__username = response_packet.username
                self.__logger.info(
                    "Successfully authenticated (username: %s)",
                    response_packet.username,
                )
                break
            except OSError:
                self.__running = False

        # main loop
        while self.__running:
            time.sleep(0.1)
            for input_event in self.__input_events:
                threading.Thread(self.__handle_input_event(input_event)).start()
                self.__input_events.remove(input_event)

        # quit
        if not self.__send_quit:
            return

        try:
            self.__packet_sock.send(SharedPackets.Quit())
        except OSError:
            return

    def stop(self, send_quit: bool = True) -> None:
        self.__send_quit = send_quit
        self.__running = False

    def __handle_input_event(self, input_event: Event) -> None:
        match type(input_event):
            case InputEvents.GetRelations:
                response = self.send_and_wait_for_response(ClientPackets.GetRelations())
                self.__output_events.append(OutputEvents.GetRelations(input_event.id, response.relations))  # type: ignore
            case InputEvents.GetMessages:
                get_messages_packet = ClientPackets.GetMessages()
                get_messages_packet.init_packet_from_params(input_event.sender, input_event.after)  # type: ignore
                response = self.send_and_wait_for_response(get_messages_packet)
                self.__output_events.append(OutputEvents.GetMessages(input_event.id, response.messages))  # type: ignore
            case InputEvents.AddFriend:
                add_friend_packet = ClientPackets.AddFriend()
                add_friend_packet.init_packet_from_params(input_event.username)  # type: ignore
                response = self.send_and_wait_for_response(add_friend_packet)
                self.__output_events.append(OutputEvents.AddFriend(input_event.id, response.success))  # type: ignore
            case InputEvents.RemoveFriend:
                remove_friend_packet = ClientPackets.RemoveFriend()
                remove_friend_packet.init_packet_from_params(input_event.username)  # type: ignore
                self.send_and_wait_for_response(remove_friend_packet)
                self.__output_events.append(OutputEvents.RemoveFriend(input_event.id))
            case InputEvents.SendMessage:
                send_message_packet = ClientPackets.SendMessage()
                send_message_packet.init_packet_from_params(input_event.receiver, input_event.content)  # type: ignore
                self.send_and_wait_for_response(send_message_packet)
                self.__output_events.append(OutputEvents.SendMessage(input_event.id))

    def send_and_wait_for_response(self, send_packet: Packet) -> Packet:
        self.__packet_sock.send(send_packet)

        while True:
            for received_packet in self.__pending_packets:
                if received_packet.id == send_packet.id:
                    self.__pending_packets.remove(received_packet)
                    return received_packet
            try:
                self.__pending_packets.append(self.__packet_sock.recv())
            except BlockingIOError:
                time.sleep(0.1)
                continue

    @property
    def authenticated(self) -> bool:
        return self.__authenticated

    @property
    def username(self) -> str | None:
        return self.__username

    def add_input_event(self, event: Event) -> None:
        self.__input_events.append(event)

    def add_input_event_and_wait_for_response(self, input_event: Event) -> Event:
        self.add_input_event(input_event)

        while True:
            for output_event in self.__output_events:
                if output_event.id == input_event.id:
                    self.__output_events.remove(output_event)
                    return output_event
            time.sleep(0.1)
