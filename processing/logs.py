import os
import logging
from datetime import datetime
import pytz
from collections import deque


class PrependFileHandler(logging.Handler):
    """
    A custom logging handler to prepend logs to a file. Ensures new log entries appear
    at the beginning of the log file.
    """
    def __init__(self, filename, encoding="utf-8"):
        super().__init__()
        self.filename = filename
        self.encoding = encoding

    def emit(self, record):
        """
        Overrides the emit method to prepend the log entry to the file.
        """
        try:
            log_entry = self.format(record)  # Format the log record
            try:
                with open(self.filename, "r", encoding=self.encoding) as f:
                    existing_content = f.read()  # Read existing file content
            except FileNotFoundError:
                existing_content = ""  # If the file doesn't exist, start fresh

            with open(self.filename, "w", encoding=self.encoding) as f:
                f.write(log_entry + "\n" + existing_content)  # Prepend the log entry
        except Exception:
            self.handleError(record)  # Handle any errors during the logging process


class LimitedConsoleHandler(logging.StreamHandler):
    """
    A custom logging handler to limit console logs to a fixed number of entries.
    """
    def __init__(self, max_logs=15):
        super().__init__()
        self.max_logs = max_logs
        self.log_cache = deque(maxlen=max_logs)  # Fixed-length deque for recent logs

    def emit(self, record):
        """
        Overrides the emit method to maintain limited log history in the console.
        Clears the console before printing the most recent logs if new logs are added.
        """
        try:
            log_entry = self.format(record)  # Format the log record
            if not self.log_cache or self.log_cache[-1] != log_entry:
                self.log_cache.append(log_entry)  # Add the new log to the deque

                # Clear the console and display only the last max_logs entries
                print("\033[H\033[J", end="")  # Clear console (ANSI escape code)
                for log in self.log_cache:
                    print(log)  # Print each log from the deque
        except Exception:
            self.handleError(record)  # Handle any errors during the logging process


def configure_logging():
    """
    Configures logging to:
    - Prepend logs to daily and monthly log files.
    - Limit console output to the most recent 15 log entries.
    - Ensure log folders and files are created if they do not exist.
    """
    # Set timezone for log timestamps
    tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(tz)

    # Define log folder paths
    monthly_log_folder = os.path.join("logs", "monthly")
    daily_log_folder = os.path.join("logs", "daily")

    # Ensure log directories exist
    os.makedirs(monthly_log_folder, exist_ok=True)
    os.makedirs(daily_log_folder, exist_ok=True)

    # Define log file paths
    monthly_log_file = os.path.join(
        monthly_log_folder,
        f"{current_time.strftime('%Y_%B')}_log.txt"  # Format: Year_Month_log.txt
    )
    daily_log_file = os.path.join(
        daily_log_folder,
        f"{current_time.strftime('%Y_%B_%d')}_log.txt"  # Format: Year_Month_Day_log.txt
    )

    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Set logging level to INFO

    # Define the log message format
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # PrependFileHandler for daily logs
    daily_handler = PrependFileHandler(daily_log_file)
    daily_handler.setFormatter(formatter)

    # PrependFileHandler for monthly logs
    monthly_handler = PrependFileHandler(monthly_log_file)
    monthly_handler.setFormatter(formatter)

    # LimitedConsoleHandler for clean console output
    console_handler = LimitedConsoleHandler(max_logs=15)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

    # Add handlers to the root logger
    logger.addHandler(daily_handler)
    logger.addHandler(monthly_handler)
    logger.addHandler(console_handler)

    # Log a message indicating successful configuration
    logging.info("Logging configured successfully.")


def initialize_logging():
    """
    Initialize logging for the application.
    """
    try:
        configure_logging()
    except Exception as e:
        print(f"Error initializing logging: {e}")


# Call the initialize_logging function to apply the configuration
initialize_logging()
