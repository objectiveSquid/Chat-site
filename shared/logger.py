import colorama
import logging


class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: colorama.Fore.BLUE + colorama.Style.BRIGHT,
        logging.INFO: colorama.Fore.GREEN + colorama.Style.BRIGHT,
        logging.WARNING: colorama.Fore.YELLOW + colorama.Style.BRIGHT,
        logging.ERROR: colorama.Fore.RED + colorama.Style.BRIGHT,
        logging.CRITICAL: colorama.Fore.RED
        + colorama.Style.BRIGHT
        + colorama.Back.WHITE,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, "")
        formatted_message = super().format(record)
        return log_color + formatted_message + colorama.Style.RESET_ALL


def configure_logger(level: int) -> None:
    colorama.init(autoreset=True)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(
        "%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    logging.basicConfig(level=level, handlers=[console_handler])
