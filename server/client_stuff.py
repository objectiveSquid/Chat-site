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

        self.__running = False
        self.__send_quit = False

    def run(self) -> None:
        self.__running = True

        # authenticate
        start_time = time.time()
        while self.__running:
            if (
                time.time()
                < start_time
                + SERVER_CONFIG["connection"]["wait_for_authentication_timeout_secs"]
            ):
                self.stop(send_quit=False)
                return

            try:
                self.__logger.debug("Waiting for authentication packet")
                auth_packet: ClientPackets.Authenticate = self.__packet_sock.recv()  # type: ignore
                if auth_packet.type != PacketType.client_authenticate:
                    self.__logger.error("Client sent invalid first packet")
                    self.__logger.debug("Responding with invalid packet type")
                    error_packet = SharedPackets.InvalidPacketType(auth_packet.id)
                    error_packet.init_packet_from_params(
                        [PacketType.client_authenticate]
                    )
                    self.__packet_sock.send(error_packet)
                    self.__logger.debug("Sent invalid packet type")
                    self.__running = False
                    return

                self.__logger.debug("Recieved authentication packet")
                self.__authenticated, username = (
                    self.__server_thread.db_wrapper.check_token(auth_packet.token)
                )

                response_packet = ServerPackets.Authenticate(auth_packet.id)
                response_packet.init_packet_from_params(self.__authenticated, username)
                self.__logger.debug(
                    "Sending authentication response packet (authenticated: %s)",
                    response_packet.success,
                )
                self.__packet_sock.send(response_packet)
                self.__logger.debug("Sent authentication response packet")
            except BlockingIOError:
                continue
            except OSError:
                self.stop(send_quit=False)
                return

        # main loop
        while self.__running:
            try:
                packet = self.__packet_sock.recv()
                self.__logger.debug("Recieved %s packet", packet.type.name)
                self.__handle_packet(packet)
            except BlockingIOError:
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

    def __handle_packet(self, input_packet: Packet) -> None:
        match input_packet.type:
            case PacketType.quit:
                self.__server_thread.clients.remove(self)
                self.__packet_sock.raw_socket.close()
                self.stop(send_quit=False)
            case _:
                error_packet = SharedPackets.InvalidPacketType(input_packet.id)
                error_packet.init_packet_from_params([PacketType.quit])
                self.__packet_sock.send(error_packet)

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
                continue

    @property
    def packet_socket(self) -> PacketSocket:
        return self.__packet_sock

    @property
    def authenticated(self) -> bool:
        return self.__authenticated
