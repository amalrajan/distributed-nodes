import logging
import socket
import ssl
import threading
import time
from datetime import datetime

from logging_config import setup_logging

# Set up logging at the start of the application
setup_logging()


class Node:
    """
    Base class for a generic network node. This class provides methods to
    securely connect to other nodes, send and receive messages, and handle
    client connections.
    """

    def __init__(
        self,
        host: str,
        port: int,
        certfile: str,
        keyfile: str,
        cafile: str,
    ):
        # Network configuration
        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.cafile = cafile

        # Create a TCP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # List to store active connections
        self.connections = []

        # Create SSL contexts
        self.server_ssl_context = self.create_ssl_context(is_server=True)
        self.client_ssl_context = self.create_ssl_context(is_server=False)

        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_ssl_context(self, is_server=False):
        """
        Create an SSL context for secure connections.

        :param bool is_server: Whether the context is for a server or client.
        :param bool is_server: Default is False.
        :return: The created SSL context.
        :rtype: ssl.SSLContext

        .. note::
            Client contexts require certificate verification.
            Hostname verification is disabled by default for clients.
        """
        if is_server:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)

        if not is_server:
            context.check_hostname = False  # Change to True if server hostname is known
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_verify_locations(cafile=self.cafile)

        return context

    def start_server(self):
        """
        Starts the server by binding to the specified host and port, and begins
        listening for incoming connections.

        :return: None

        .. note::
            This method logs a message indicating the server has started.

        :raises:
            Exception: If binding to the host and port fails.
        """
        # Bind the socket to the host and port
        self.socket.bind((self.host, self.port))
        self.socket.listen()
        self.logger.info(
            f"{self.__class__.__name__} started on {self.host}:{self.port}"
        )

        # Accept incoming connections
        self.accept_connections()

    def accept_connections(self):
        """
        Continuously accepts incoming connections and establishes secure SSL
        connections.

        :return: None
        :raises: ssl.SSLError
        """

        while True:
            client_socket, client_address = self.socket.accept()
            try:
                ssl_socket = self.server_ssl_context.wrap_socket(
                    client_socket, server_side=True
                )
                self.logger.debug(
                    f"Secure connection established with {client_address}"
                )
                self.connections.append(ssl_socket)
                threading.Thread(target=self.handle_client, args=(ssl_socket,)).start()
            except ssl.SSLError as e:
                self.logger.debug(f"SSL error occurred: {e}")
                client_socket.close()

    def handle_client(self, client_socket):
        """
        Handles communication with a connected client.

        Continuously receives and processes messages from the client until the
        connection is closed.

        :param client_socket: The SSL-wrapped socket for the client connection.
        :return: None
        :raises: ConnectionResetError
        """
        while True:
            try:
                message = client_socket.recv(1024).decode("utf-8")
                if message:
                    self.logger.debug(f"Received a new message at {datetime.now()}")
                    self.process_message(message, client_socket)
                else:
                    client_socket.close()
                    self.connections.remove(client_socket)
                    break
            except ConnectionResetError:
                client_socket.close()
                self.connections.remove(client_socket)
                break

        # Cleanup
        client_socket.close()
        if client_socket in self.connections:
            self.connections.remove(client_socket)

    def process_message(self, message, client_socket):
        # To be overridden by the child class
        raise NotImplementedError("process_message method must be overridden")

    def connect_to_node(self, host, port, retry_delay=10, max_retries=10):
        """
        Establishes a secure SSL connection to a remote node.

        Continuously retries connection attempts until successful.

        :param host: The hostname or IP address of the remote node.
        :param port: The port number of the remote node.
        :param retry_delay: The delay in seconds between retry attempts (default: 2).
        :return: True if connection is established successfully.
        :raises: Exception
        """
        while max_retries > 0:
            try:
                remote_socket = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                )
                ssl_socket = self.client_ssl_context.wrap_socket(
                    remote_socket, server_hostname=host
                )
                ssl_socket.connect((host, port))
                self.connections.append(ssl_socket)
                threading.Thread(
                    target=self.handle_client,
                    args=(ssl_socket,),
                ).start()

                self.logger.debug(f"Securely connected to {host}:{port}")

                return True
            except Exception as e:
                self.logger.debug(f"Connection failed: {e}")
                self.logger.debug(f"Retrying in {retry_delay} seconds...")

                time.sleep(retry_delay)
                max_retries -= 1

    def send_message(self, message):
        """
        Broadcasts a message to all connected clients.

        :param message: The message to be sent.
        :return: None
        """
        for conn in self.connections:
            try:
                conn.send(message.encode("utf-8"))
            except Exception as e:
                self.logger.debug(f"Error sending message: {e}")
