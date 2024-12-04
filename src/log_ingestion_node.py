import json
import logging
import os
import threading
import time
from datetime import datetime

import config
from node import Node


class LogIngestionNode(Node):
    def __init__(self, host, port, certfile, keyfile, cafile):
        super().__init__(host, port, certfile, keyfile, cafile)

        self.log_file_path = config.LOG_FILE_PATH
        self.last_read_position = 0

        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch_logs(self):
        """
        Continuously monitors a log file for new entries.

        This method:

        1. Checks if the log file exists.
        2. Reads new log lines since the last check.
        3. Formats each log as a JSON object with timestamp and message.
        4. Broadcasts the JSON-formatted logs to connected clients.

        :return: None
        :raises:
            Exception: Any errors reading or processing logs.
        """
        while True:
            try:
                # Check if the file exists
                if not os.path.exists(self.log_file_path):
                    self.logger.debug(f"Log file not found: {self.log_file_path}")
                    time.sleep(5)  # Wait for 5 seconds before trying again
                    continue

                # Open the file and seek to the last read position
                with open(self.log_file_path, "r") as log_file:
                    log_file.seek(self.last_read_position)

                    # Read new lines
                    new_logs = log_file.readlines()

                    # Update the last read position
                    self.last_read_position = log_file.tell()

                for log in new_logs:
                    # Skip empty lines
                    if not log.strip():
                        continue

                    # Create a dictionary with log information
                    log_dict = {
                        "timestamp": datetime.now().isoformat(),
                        "message": log.strip(),
                    }

                    # Convert the dictionary to a JSON string
                    json_log = json.dumps(log_dict)

                    # Send the JSON-formatted log
                    self.send_message(json_log)

                # Wait for a short period before checking for new logs
                time.sleep(1)  # Adjust this value to change the polling frequency

            except Exception as e:
                self.logger.debug(f"Error reading logs: {e}")
                time.sleep(5)  # Wait for 5 seconds before trying again

    def process_message(self, message, client_socket):
        pass

    def start_server(self):
        # Start the log reading thread
        self.log_thread = threading.Thread(target=self.fetch_logs)
        self.log_thread.daemon = (
            True  # Set as daemon so it exits when the main thread exits
        )
        self.log_thread.start()

        # Call the parent class's start_server method
        super().start_server()


if __name__ == "__main__":
    # Start the log ingestion node
    log_ingestion_node = LogIngestionNode(
        host=config.LOG_INGESTION_SERVICE_HOST,
        port=config.LOG_INGESTION_SERVICE_PORT,
        certfile=config.CA_FILE,
        keyfile=config.KEY_FILE,
        cafile=config.CA_FILE,
    )

    # Start the log ingestion node
    threading.Thread(target=log_ingestion_node.start_server).start()
