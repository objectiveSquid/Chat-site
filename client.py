from shared.logger import configure_logger
from shared.config import CLIENT_CONFIG
from client import Connection

import logging


configure_logger(logging.DEBUG)


def main() -> None:
    conn = Connection(CLIENT_CONFIG["user"]["token"])
    conn.start()
    conn.stop()


if __name__ == "__main__":
    main()
