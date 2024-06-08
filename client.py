from client import Connection, flask_app, WebGUI
from shared.logger import configure_logger
from shared.config import CLIENT_CONFIG

import flask.cli as flask_cli
import threading
import logging
import time


configure_logger(logging.DEBUG)


def main() -> None:
    conn = Connection(CLIENT_CONFIG["user"]["token"])
    web_gui = WebGUI(conn)
    flask_web_gui_runnner = threading.Thread(
        target=flask_app.run,
        name="WebGUI",
        args=[CLIENT_CONFIG["gui"]["host_address"], CLIENT_CONFIG["gui"]["host_port"]],
    )

    # hide flask output
    flask_cli.show_server_banner = lambda *args, **kwargs: None
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    main_logger = logging.getLogger("Client")

    main_logger.info(
        "Starting connection to %s:%s",
        CLIENT_CONFIG["connection"]["connect_address"],
        CLIENT_CONFIG["connection"]["connect_port"],
    )
    conn.start()
    max_authentication_time = (
        time.time() + CLIENT_CONFIG["connection"]["authentication_timeout"]
    )
    while conn.authenticated == None:
        if time.time() > max_authentication_time:
            main_logger.critical("Authentication timeout reached")
            time.sleep(0.1)
            break

    main_logger.info(
        "Starting WebGUI on %s:%s",
        CLIENT_CONFIG["gui"]["host_address"],
        CLIENT_CONFIG["gui"]["host_port"],
    )
    flask_web_gui_runnner.start()

    conn.join()
    flask_web_gui_runnner.join()
    main_logger.info("Quitting")


if __name__ == "__main__":
    main()
