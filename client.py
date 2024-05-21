from shared.logger import configure_logger
from client.connection import Connection
from shared.config import CLIENT_CONFIG

import logging


configure_logger(logging.DEBUG)


def main() -> None:
    conn = Connection(CLIENT_CONFIG["user"]["token"])
    conn.start()
    conn.stop()


if __name__ == "__main__":
    main()
