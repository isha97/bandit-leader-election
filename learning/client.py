import logging
import time

from .node import Node
from learning.message import *
from _thread import *
import socket
import threading

class Client(Node):
    def __init__(self, id, n, config):
        """Initialize client node

            id: Node id (-1 for client)
            n: total number of nodes
            config: config parameters
        """
        super().__init__(id, n, config)

        self.request_id = 0
        self.run = True
        self.message_buffer = {}
        self.total_requests = config.client.num_requests
        logging.basicConfig(level=logging.DEBUG,
                            format='[%(asctime)s %(levelname)-8s %(funcName)s() %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', handlers=[
                                logging.FileHandler("logs/client.log"),
                                logging.StreamHandler()
                                ]
        )


    def recieve_confirm_election_msg(self, message):
        """Receive message of new leader"""
        self.leader = message.sender
        logging.info("Changed leader to {}".format(self.leader))


    def recieve_response_msg(self, message):
        """Receive response for request."""
        if self.leader != message.leader:
            self.leader = message.leader
            logging.info("Changed leader to {}".format(self.leader))
        requestId = message.requestId
        self.message_buffer[requestId] = 1

    def send_current_leader(self, message):
        host = '127.0.0.1'
        port = self.ports[message.sender]
        msg = str(CurrentLeaderMessage(self.client_port, self.leader, 0))
        logging.info("Sending current leader {} to node {}".format(self.leader, message.sender))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.send(msg.encode('ascii'))
            s.close()
        except Exception as ex:
            logging.error(str(ex))
            s.close()



    def multi_threaded_client(self, connection):
        """Read message and perform action."""
        while True:
            data = str(connection.recv(2048).decode('ascii'))

            if not data:
                break

            message = parse_and_construct(data)

            if isinstance(message, ConfirmElectionMessage):
                self.recieve_confirm_election_msg(message)

            elif isinstance(message, ResponseMessage):
                self.recieve_response_msg(message)

            elif isinstance(message, GetLeaderMessage):
                self.send_current_leader(message)

        connection.close()


    def receive_messages(self):
        """Receive message"""
        host = '127.0.0.1'
        port = self.client_port
        receiving_socket = socket.socket()
        try:
            receiving_socket.bind((host, port))
        except socket.error as e:
            logging.error(str(e))
        receiving_socket.listen(5)
        while self.run:
            Client, address = receiving_socket.accept()
            start_new_thread(self.multi_threaded_client, (Client,))


    def send_request(self):
        """Send client requests"""
        self.request_id += 1
        message = str(ClientRequestMessage(-1, self.leader, 0, self.request_id))
        port = self.ports[self.leader]
        host = '127.0.0.1'
        logging.info("Sending request {} to the current leader {}".format(self.request_id, self.leader))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.send(message.encode('ascii'))
            s.close()
        except Exception as msg:
            logging.error(str(msg))
            s.close()


    def send_request_broadcast(self):
        """If leader is not responding, broadcast request"""
        message = str(ClientRequestMessage(-1, self.leader, 0, self.request_id))
        host = '127.0.0.1'
        logging.info("Sending request broadcast for request {}".format(self.request_id))
        for port in self.ports:
            if port != self.ports[self.leader]:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect((host, port))
                    s.send(message.encode('ascii'))
                    s.close()
                except Exception as msg:
                    logging.error(str(msg))
                    s.close()


    def run_node(self):
        """Run send, receive threads"""
        receive = threading.Thread(target=self.receive_messages)
        receive.start()
        for i in range(self.total_requests):
            self.send_request()
            time.sleep(2)
            if self.request_id in self.message_buffer.keys():
                del self.message_buffer[self.request_id]
            else:
                self.send_request_broadcast()
            time.sleep(5)
