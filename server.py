from shared.logger import configure_logger
from server import Server

import logging


configure_logger(logging.DEBUG)


def main() -> None:
    server = Server()
    server.run()


if __name__ == "__main__":
    main()
