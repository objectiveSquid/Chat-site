from __future__ import annotations
from typing import TYPE_CHECKING

from shared.packets import (
    ServerPackets,
    SharedPackets,
    ClientPackets,
    PacketType,
    Packet,
)
from shared.packet_socket import PacketSocket
from server.db_handler import DBWrapper
from shared.config import SERVER_CONFIG

if TYPE_CHECKING:
    from .client_handler import Server

import threading
import logging
import socket
import time


class ServerSideClient(threading.Thread):
    def __init__(self, sock: socket.socket, server_thread: Server) -> None:
        super().__init__(
            name=f"ChatServerSideClient (Address: {sock.getpeername()[0]})"
        )
        self.__logger = logging.getLogger(
            f"Client {sock.getpeername()[0]}:{sock.getpeername()[1]}"
        )

        self.__packet_sock = PacketSocket(sock)
        self.__pending_packets = []
        self.__server_thread = server_thread
        self.__authenticated = False
        self.__username = None

        self.__running = False
        self.__send_quit = False

    def run(self) -> None:
        self.__running = True
        self.__db_wrapper = DBWrapper()

        # authenticate
        start_time = time.time()
        self.__logger.debug("Waiting for authentication packet")
        while self.__running:
            if (
                time.time()
                > start_time + SERVER_CONFIG["connection"]["authentication_timeout"]
            ):
                self.__logger.info("Authentication timeout reached")
                self.stop(send_quit=False)
                break

            try:
                time.sleep(0.1)
                auth_packet: ClientPackets.Authenticate = self.__packet_sock.recv()  # type: ignore
                if auth_packet.type != PacketType.client_authenticate:
                    self.__logger.error("Client sent invalid first packet")
                    error_packet = SharedPackets.InvalidPacketType(auth_packet.id)
                    error_packet.init_packet_from_params(
                        [PacketType.client_authenticate]
                    )
                    self.__packet_sock.send(error_packet)
                    self.stop(send_quit=False)
                    break

                self.__authenticated, self.__username = self.__db_wrapper.check_token(
                    auth_packet.token
                )

                response_packet = ServerPackets.Authenticate(auth_packet.id)
                response_packet.init_packet_from_params(
                    self.__authenticated,
                    self.__username if isinstance(self.__username, str) else "",
                )
                self.__packet_sock.send(response_packet)

                if not self.__authenticated:
                    self.__logger.info("Client sent invalid token")
                    self.stop(send_quit=False)
                    break
                self.__logger.info("Successfully authenticated")
                break
            except BlockingIOError:
                continue
            except OSError:
                self.stop(send_quit=False)
                break

        # main loop
        while self.__running:
            try:
                packet = self.__packet_sock.recv()
                response_packet = self.__handle_packet(packet)
                if response_packet == None:
                    continue
                self.__packet_sock.send(response_packet)
            except BlockingIOError:
                time.sleep(0.1)
                continue
            except OSError:
                self.stop(send_quit=False)
                return

        self.__logger.info("Quitting")
        # quit
        if not self.__send_quit:
            return
        try:
            self.__packet_sock.send(SharedPackets.Quit())
        except OSError:
            return

    def __handle_packet(self, input_packet: Packet) -> Packet | None:
        match input_packet.type:
            case PacketType.quit:
                self.__server_thread.clients.remove(self)
                self.__packet_sock.raising_socket.close()
                self.stop(send_quit=False)
                return None
            case PacketType.client_get_relations:
                relations = self.__db_wrapper.get_all_relations(self.__username)  # type: ignore
                relations_packet = ServerPackets.GetRelations(input_packet.id)
                relations_packet.init_packet_from_params(relations)
                return relations_packet
            case PacketType.client_get_messages:
                messages = self.__db_wrapper.get_messages(self.__username, input_packet.secondary_user, round(time.time() - input_packet.after))  # type: ignore
                messages_packet = ServerPackets.GetMessages(input_packet.id)
                messages_packet.init_packet_from_params(messages)
                return messages_packet
            case PacketType.client_add_friend:
                add_friend_success = self.__db_wrapper.add_friend(
                    self.__username, input_packet.username  # type: ignore
                )
                add_friend_response_packet = ServerPackets.AddFriend(input_packet.id)
                add_friend_response_packet.init_packet_from_params(add_friend_success)
                return add_friend_response_packet
            case PacketType.client_remove_friend:
                self.__db_wrapper.remove_friend(
                    self.__username, input_packet.username  # type: ignore
                )
                return ServerPackets.RemoveFriend(input_packet.id)
            case _:
                error_packet = SharedPackets.InvalidPacketType(input_packet.id)
                error_packet.init_packet_from_params(
                    [
                        PacketType.quit,
                        PacketType.client_get_relations,
                        PacketType.client_get_messages,
                        PacketType.client_add_friend,
                        PacketType.client_remove_friend,
                    ]
                )
                return error_packet

    def stop(self, send_quit: bool = True) -> None:
        self.__send_quit = send_quit
        self.__running = False

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
    def packet_socket(self) -> PacketSocket:
        return self.__packet_sock

    @property
    def authenticated(self) -> bool:
        return self.__authenticated
