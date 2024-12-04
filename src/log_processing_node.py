import json
import logging
import signal
import sqlite3
import threading
from datetime import datetime

import config
from node import Node


class LogProcessingNode(Node):
    def __init__(self, host, port, certfile, keyfile, cafile):
        super().__init__(host, port, certfile, keyfile, cafile)

        self.db_path = config.DB_PATH
        self.init_db()

        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)

    def init_db(self):
        """
        Initializes the database by creating the logs table if it doesn't exist.

        :return: None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    log_message TEXT NOT NULL
                )
            """
            )
            conn.commit()

    def write_log_to_db(self, message):
        """
        Writes a log message to the database.

        :param message: The log message to be written.
        :return: None
        """
        message = json.loads(message)
        timestamp, log_message = message["timestamp"], message["message"]

        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO logs (timestamp, log_message) VALUES (?, ?)",
                (timestamp, log_message),
            )
            conn.commit()

    def process_message(self, message, client_socket):
        """
        Processes and stores a log message received from a client.

        :param message: The log message to be processed.
        :param client_socket: The socket connection to the client.
        :return: None
        """
        self.logger.debug(f"Processing log: {message}")
        try:
            # Assuming the message is a JSON string
            log_data = json.loads(message)
            log_message = json.dumps(log_data)  # Convert back to a string for storage
            self.write_log_to_db(log_message)
            response = "Log processed and stored successfully"
        except json.JSONDecodeError:
            self.logger.debug(f"Invalid JSON format: {message}")
            response = "Error: Invalid log format"
        except Exception as e:
            self.logger.debug(f"Error processing log: {e}")
            response = f"Error: {str(e)}"

        client_socket.send(response.encode())

    def connect_to_node(self):
        return super().connect_to_node(
            host=config.LOG_INGESTION_SERVICE_HOST,
            port=config.LOG_INGESTION_SERVICE_PORT,
        )


def signal_handler(signum, frame):
    """
    Signal handler function to invoke connect_to_node when a signal is received.

    :param signum: The signal number.
    :param frame: The current stack frame.
    :return: None
    """
    log_processing_node.connect_to_node()


if __name__ == "__main__":
    # Start the log processing node
    log_processing_node = LogProcessingNode(
        host=config.LOG_INGESTION_SERVICE_HOST,
        port=config.LOG_PROCESSING_SERVICE_PORT,
        certfile=config.CA_FILE,
        keyfile=config.KEY_FILE,
        cafile=config.CA_FILE,
    )

    # Register the signal handler for SIGUSR1 (or any other desired signal)
    signal.signal(signal.SIGUSR1, signal_handler)

    # Start the log processing node
    threading.Thread(target=log_processing_node.start_server).start()
