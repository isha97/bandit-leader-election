import socket
from learning.message import *
import socket

class CLient:
    def __init__(self, n, config):
        """Initialize node

            id: Node id
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

    def receive_messages(self):

    def send_request(self):
        message = str(RequestMessage(self.request_id))
        self.request_id += 1
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