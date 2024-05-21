from shared.packets import ServerPackets, SharedPackets, ClientPackets, Packet
from shared.packet_socket import PacketSocket
from shared.config import CLIENT_CONFIG

import logging
import socket


class Connection:
    def __init__(self, token: str) -> None:
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

        self.__running = False
        self.__send_quit = False

    def run(self) -> None:
        self.__running = True

        # authenticate
        while self.__running:
            try:
                auth_packet = ClientPackets.Authenticate()
                auth_packet.init_packet_from_params(self.__token)
                self.__logger.debug(
                    "Sending authentication packet (length: %s, id: %s)",
                    auth_packet.data_length,
                    auth_packet.id,
                )
                response_packet: ServerPackets.Authenticate = self.send_and_wait_for_response(auth_packet)  # type: ignore
                self.__logger.debug(
                    "Recieved authentication response (username: %s, length: %s)",
                    response_packet.username,
                    response_packet.data_length,
                )
                self.__authenticated = response_packet.success

                if not self.__authenticated:
                    self.__logger.critical(
                        "Incorrect token supplied (token: %s)",
                        CLIENT_CONFIG["user"]["token"],
                    )
                    self.stop()
                    break
                self.__logger.info("Successfully authenticated")
            except OSError:
                self.__running = False

        # main loop
        while self.__running:
            ...  # TODO: Implement main loop

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
    def authenticated(self) -> bool:
        return self.__authenticated
