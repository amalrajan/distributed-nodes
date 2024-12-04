import logging
import os
import signal
import subprocess
import threading
import time

import psutil

import config
from logging_config import setup_logging

# Set up logging at the start of the application
setup_logging()


class NodeSupervisor:
    def __init__(self):
        self.nodes = {
            "log_ingestion": {
                "process": None,
                "command": [
                    config.PYTHON_PATH,
                    "src/log_ingestion_node.py",
                ],
                "is_server": True,
            },
            "log_processing": {
                "process": None,
                "command": [
                    config.PYTHON_PATH,
                    "src/log_processing_node.py",
                ],
                "is_server": False,
            },
        }
        self.stop_flag = False

        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)

    def start_node(self, node_name) -> int:
        """
        Starts a specific node if it's not already running.

        :param node_name: Name of the node to start.
        :return: int - PID of the started process.
        """
        node = self.nodes[node_name]
        if node["process"] is None or not self.is_process_running(node["process"]):
            node["process"] = subprocess.Popen(node["command"])

            # Wait for the process to start
            time.sleep(1)

            self.logger.info(f"Started {node_name} node with PID {node['process'].pid}")

            # Send SIGUSR1 signal to the process to connect to the server if it's a client
            if not node["is_server"]:
                self.logger.debug(
                    f"Connecting {node_name} - {node["process"].pid} node to the server..."
                )
                os.kill(node["process"].pid, signal.SIGUSR1)

        return node["process"].pid

    def is_process_running(self, process):
        """
        Checks if a process is running.

        :param process: subprocess.Popen object.
        :return: True if process is running, False otherwise.
        """
        return process is not None and process.poll() is None

    def monitor_nodes(self):
        """
        Continuously monitors node processes and restarts them if necessary.

        Runs indefinitely until stopped.
        :return: None
        """
        while not self.stop_flag:
            for node_name in self.nodes:
                node = self.nodes[node_name]
                if not self.is_process_running(node["process"]):
                    self.logger.critical(f"{node_name} node is down. Restarting...")

                    if node["is_server"]:
                        # If the node is a server, start the server node first
                        self.start_node(node_name)

                        # Wait for the server node to start
                        time.sleep(1)

                        # And then send SIGUSR1 signal to all client nodes to reconnect
                        for client_name in self.nodes:
                            if not self.nodes[client_name]["is_server"]:
                                self.logger.info(
                                    f"Reconnecting {client_name} - {self.nodes[client_name]["process"].pid} node to the server..."
                                )
                                os.kill(
                                    self.nodes[client_name]["process"].pid,
                                    signal.SIGUSR1,
                                )
                    else:
                        # If the node is a client, restart the client node
                        self.start_node(node_name)

            self.clean_up_zombies()
            time.sleep(1)  # Check every 1 seconds

    def clean_up_zombies(self):
        """
        Cleans up zombie processes.

        Removes terminated processes from tracking.
        :return: None
        """
        for node_name, node in self.nodes.items():
            if node["process"] and node["process"].poll() is not None:
                # Process has terminated, wait to reap the zombie
                try:
                    node["process"].wait(timeout=1)
                except psutil.TimeoutExpired:
                    pass
                node["process"] = None
                self.logger.info(f"Cleaned up zombie process for {node_name}")

    def start(self):
        """
        Starts all nodes and begins monitoring.

        Initializes node processes and monitoring thread.
        :return: None
        """
        # Start server nodes first
        for node_name in self.nodes:
            if self.nodes[node_name]["is_server"]:
                self.start_node(node_name)

        # Wait for server nodes to start
        self.logger.debug("Waiting for server nodes to start...")
        time.sleep(1)

        # Start client nodes
        for node_name in self.nodes:
            if not self.nodes[node_name]["is_server"]:
                self.start_node(node_name)

        monitor_thread = threading.Thread(target=self.monitor_nodes)
        monitor_thread.start()

    def stop(self):
        """
        Stops all nodes and monitoring.

        Terminates node processes and monitoring thread.
        :return: None
        """
        self.stop_flag = True
        for node in self.nodes.values():
            if node["process"]:
                node["process"].terminate()
                node["process"].wait()


if __name__ == "__main__":
    supervisor = NodeSupervisor()
    try:
        supervisor.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        supervisor.stop()
