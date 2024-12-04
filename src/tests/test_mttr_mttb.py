import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

import psutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
from logging_config import setup_logging


class TestMTTRandMTBF:
    def __init__(self):
        self.num_tests = 5
        self.python_path = config.PYTHON_PATH
        self.logger = logging.getLogger(self.__class__.__name__)

        self.start_time = datetime.now()

        # Define the nodes
        self.nodes = {
            "log_ingestion": {
                "is_server": True,
            },
            "log_processing": {
                "is_server": False,
            },
        }

    def set_up(self):
        # Log
        self.logger.info("Starting the supervisor and the nodes")

        # Run the node supervisor and get PID in a new thread
        subprocess.Popen(
            [
                self.python_path,
                "src/supervisor.py",
            ]
        )

        # Wait for the supervisor to start
        time.sleep(5)

    def kill_node(self, process_name):
        # Kill the process
        try:
            subprocess.run(
                ["pkill", "-9", "-f", process_name],
                check=True,
            )
        except Exception as e:
            self.logger.debug(f"Could not terminate process: {e}")

    def tear_down(self):
        # Kill processes
        processes_to_kill = [
            "log_ingestion_node.py",
            "log_processing_node.py",
            "supervisor.py",
        ]

        for process in processes_to_kill:
            self.kill_node(process)

    def poll_for_process(self, process_name):
        while True:
            # Run ps aux | grep process_name
            process = subprocess.run(["ps", "aux"], stdout=subprocess.PIPE)

            # Decode the bytes output to a string
            output = process.stdout.decode("utf-8")
            if output and process_name in output:
                break

    def calculate_mttr(self, node_name):
        # Kill the node using pkill
        self.kill_node(node_name)

        # Start timer
        start_time = datetime.now()

        # Wait for the node to recover
        self.logger.debug(f"Waiting for {node_name} to recover...")
        self.poll_for_process(node_name)

        # Calculate MTTR
        mttr = datetime.now() - start_time

        return mttr.total_seconds()

    def run_tests(self):
        # Calculate MTTR
        mttr = {
            "log_ingestion_node.py": [],
            "log_processing_node.py": [],
        }

        for _ in range(self.num_tests):
            for node in mttr:
                mttr[node].append(self.calculate_mttr(node))

                # Wait for the node to recover
                time.sleep(10)

        for node in mttr:
            avg_mttr = sum(mttr[node]) / len(mttr[node])
            self.logger.info(f"Average MTTR for {node}: {avg_mttr}")

        # Calculate MTBF
        total_time = datetime.now() - self.start_time
        mtbf = total_time.total_seconds() / self.num_tests

        self.logger.info(f"Average MTBF: {mtbf}")
        self.logger.info(f"Total time taken: {total_time}")


if __name__ == "__main__":
    setup_logging()

    test_obj = TestMTTRandMTBF()
    test_obj.set_up()
    test_obj.run_tests()
    test_obj.tear_down()
