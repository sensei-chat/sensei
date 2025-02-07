import logging
import sys
import colorama


# Initialize colorama
colorama.init(autoreset=True)

# Define color codes
RESET = colorama.Style.RESET_ALL
BLACK = colorama.Fore.BLACK
RED = colorama.Fore.RED
GREEN = colorama.Fore.GREEN
YELLOW = colorama.Fore.YELLOW
BLUE = colorama.Fore.BLUE
MAGENTA = colorama.Fore.MAGENTA
CYAN = colorama.Fore.CYAN
WHITE = colorama.Fore.WHITE


class ColoredFormatter(logging.Formatter):
    # Mapping of log levels to colors
    LEVEL_COLORS = {
        logging.DEBUG: CYAN,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: MAGENTA,
    }

    def format(self, record):
        # Get the color for the current log level
        level_color = self.LEVEL_COLORS.get(record.levelno, WHITE)

        # Apply the color to the level name and message
        record.levelname = f"{level_color}{record.levelname}{RESET}"
        record.msg = f"{level_color}{record.msg}{RESET}"

        # Format the message
        return super().format(record)


def create_logger(verbose, name=None):
    if name:
        my_logger = logging.getLogger(name)
    else:
        my_logger = logging.getLogger()

    if verbose:
        my_logger.setLevel(logging.DEBUG)
    else:
        my_logger.setLevel(logging.CRITICAL)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    log_format = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(log_format)

    my_logger.addHandler(console_handler)

    return my_logger