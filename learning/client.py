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

        self.run = True
        self.message_buffer = {}
        self.num_leader_election = 0 # total number of times the leader election happens
        self.num_requests = config.client.num_requests
        logging.basicConfig(level=logging.DEBUG,
                            format='[%(asctime)s %(levelname)-8s %(funcName)s() %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', handlers=[
                                logging.FileHandler("logs/client.log"),
                                logging.StreamHandler()
                                ]
        )


    def receive_confirm_election_msg(self, message):
        """Receive message of new leader"""
        if message.stamp > self.leader['stamp']:
            self.leader['id'] = message.leader
            self.leader['stamp'] = message.stamp
            logging.info("Changed leader to {} @ {}".format(self.leader['id'], self.leader['stamp']))
        logging.info("Received confirm election message from {} @ {}, msg = {}"
                     .format(message.sender, message.stamp, message))


    def receive_response_msg(self, message):
        """Receive response for request."""
        if self.leader['id'] != message.leader:
            if self.leader['stamp'] < message.stamp:
                self.leader['id'] = message.sender
                self.leader['stamp'] = message.stamp
                logging.info("Changed leader to {} @ {}".format(self.leader['id'], self.leader['stamp']))
        requestId = message.requestId
        self.message_buffer[requestId] = 1
        logging.info("Received response from {} @ {}, msg = {}".format(message.sender, message.stamp, message))


    def multi_threaded_client(self, connection):
        """Read message and perform action."""
        while True:
            data = str(connection.recv(2048).decode('ascii'))

            if not data:
                break

            message = parse_and_construct(data)

            if isinstance(message, ConfirmElectionMessage):
                self.receive_confirm_election_msg(message)

            elif isinstance(message, ResponseMessage):
                self.receive_response_msg(message)

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


    def send_request(self, request_id):
        """Send client requests"""
        message = str(ClientRequestMessage(-1, self.leader['id'], time.time()*100, request_id))
        port = self.ports[self.leader['id']]
        host = '127.0.0.1'
        logging.info("Sending request {} to the current leader {}".format(request_id, self.leader['id']))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.send(message.encode('ascii'))
            s.close()
        except Exception as msg:
            logging.error(str(msg))
            s.close()


    def send_request_broadcast(self, request_id):
        """If leader is not responding, broadcast request"""
        message = str(ClientRequestMessage(-1, self.leader['id'], time.time()*100, request_id))
        host = '127.0.0.1'
        logging.info("Sending request broadcast for request {}".format(request_id))
        for port in self.ports:
            if port != self.ports[self.leader['id']]:
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
        i = 0
        while i < self.num_requests:
            # current_leader : The leader to which request i is sent
            current_leader = self.leader['id']
            # is_broadcast : Did the client broadcast the request?
            is_broadcast = False
            self.send_request(i)
            time.sleep(5)
            if i in self.message_buffer.keys():
                del self.message_buffer[i]
                i += 1
            else:
                self.send_request_broadcast(i)
                self.num_leader_election += 1 # Every time a client sends a broadcast, it means the leader failed and election will happen
                is_broadcast = True
            time.sleep(5)
            if is_broadcast:
                # If the client broadcasted the request and the leader still didn't change, it will re-send the same request
                if int(current_leader) != int(self.leader['id']):
                    i += 1

        print("Total Requests : {}, Number of Leader Elections : {}", self.num_requests. self.num_leader_election)

