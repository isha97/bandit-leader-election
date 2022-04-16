import socket
import time

from learning.message import *
from _thread import *
import socket
import threading

class Client:
    def __init__(self, n, config):
        """Initialize node
            n: total number of nodes
            config: config parameters
        """
        ports = []
        for i in range(n):
            ports.append(config.port.replica_base_port + i)
        self.ports = ports
        self.client_port = config.port.replica_base_port
        self.request_id = 0
        self.leader = 0
        self.run = True
        self.message_buffer = {}
        self.total_requests = config.client.num_requests

    def recieve_confirm_election_msg(self, message):
        self.leader = message.sender

    def recieve_response_msg(self, message):
        requestId = message.requestId
        self.message_buffer[requestId] = 1

    def multi_threaded_client(self,connection):
        while True:
            data = str(connection.recv(2048).decode('ascii'))
            print("Received message {} from node", data)
            if data.startswith("ConfirmElectionMsg"):
                message = ConfirmElectionMessage(data.split(" ")[1], data.split(" ")[2])
                self.recieve_confirm_election_msg(message)
            if data.startswith("ResponseMessage"):
                message = ResponseMessage(data.split(" ")[1], data.split(" ")[2])
                self.recieve_response_msg(message)
            if not data:
                break
        connection.close()

    def receive_messages(self):
        host = '127.0.0.1'
        port = self.client_port
        receiving_socket = socket.socket()
        try:
            receiving_socket.bind((host, port))
        except socket.error as e:
            print(str(e))
        receiving_socket.listen(5)
        while self.run:
            Client, address = receiving_socket.accept()
            start_new_thread(self.multi_threaded_client, (Client,))

    def send_request(self):
        self.request_id += 1
        message = str(RequestMessage(self.request_id))
        port = self.ports[self.leader]
        host = '127.0.0.1'
        print("Sending message {} to node {}".format(message, port))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.send(message.encode('ascii'))
            s.close()
        except Exception as msg:
            print(msg)
            s.close()

    def send_request_broadcast(self):
        message = str(RequestMessage(self.request_id))
        host = '127.0.0.1'
        for port in self.ports:
            if port != self.ports[self.leader]:
                print("Sending message {} to node {}".format(message, port))
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect((host, port))
                    s.send(message.encode('ascii'))
                    s.close()
                except Exception as msg:
                    print(msg)
                    s.close()

    def run_client(self):
        receive = threading.Thread(target=self.receive_messages)
        receive.start()
        for i in range(self.total_requests):
            self.send_request()
            time.sleep(10)
            if self.request_id in self.message_buffer.keys():
                del self.message_buffer[self.request_id]
            else:
                self.send_request_broadcast()
            time.sleep(10)
