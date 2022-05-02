import logging
import time

from .node import Node
from learning.message import *
from utils.logger import ViewChangeLogger, LeaderLogger
from _thread import *
import socket
import threading

lock = threading.Lock()

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
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s %(levelname)-8s [Client] %(funcName)s() %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', handlers=[
                                logging.FileHandler("logs/client_{}_{}.log".format(self.total_nodes,
                                                                                   config.mab.algo)),
                                logging.StreamHandler()
                                ]
        )
        self.candidate_leader = None
        self.leader_logger = LeaderLogger(time.time()*100)


    def receive_confirm_election_msg(self, message):
        """Receive message of new leader"""
        if message.stamp > self.leader['stamp']:
            self.leader['id'] = message.leader
            self.leader['stamp'] = message.stamp
            self.view_change_logger.tick(message.stamp, message.sender)
            logging.info("[Leader] Changed leader to {} @ {}".format(self.leader['id'], self.leader['stamp']))

        logging.info("[RECV][LeaderElec] ConfirmElectionMsg from: {} @ {}, msg: {}"
                     .format(message.sender, message.stamp, message))

    def receive_candidate_leader(self, message):
        logging.info("[RECV][CandidateLeader] NewLeaderMsg from: {} @ {}, msg: {}"
                     .format(message.sender, message.stamp, message))
        if self.candidate_leader is None:
            self.candidate_leader = message.leader

    def receive_response_msg(self, message):
        """Receive response for request."""
        if self.leader['id'] != message.leader:
            if self.leader['stamp'] < message.stamp:
                self.leader['id'] = message.sender
                self.leader['stamp'] = message.stamp
                self.view_change_logger.tick(message.stamp, message.sender)
                logging.info("[Leader] Changed leader to {} @ {}".format(self.leader['id'], self.leader['stamp']))

        requestId = message.requestId
        self.message_buffer[requestId] = 1
        logging.info("[RECV] ResponseMsg from: {} @ {}, Msg: {}".format(message.sender, message.stamp, message))


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

            elif isinstance(message, NewLeaderMessage):
                self.receive_candidate_leader(message)

            elif isinstance(message, type(None)):
                logging.warning("Error parsing message, received unknown: {}".format(message))

            else:
                logging.warning("[RECV] Unexpected message from: {} @ {}, Msg: {}".format(message.sender, message.stamp, message))

        connection.close()


    def receive_messages(self):
        """Receive message thread"""
        host = '127.0.0.1'
        port = self.client_port
        self.view_change_logger = ViewChangeLogger(time.time()*100, self.total_nodes)
        receiving_socket = socket.socket()
        try:
            receiving_socket.bind((host, port))
        except socket.error as e:
            logging.error(str(e))
        receiving_socket.listen(5)
        #receiving_socket.settimeout(30)
        while self.run:
            Client, address = receiving_socket.accept()
            start_new_thread(self.multi_threaded_client, (Client,))


    def send_request(self, request_id):
        """Send client requests"""
        message = str(ClientRequestMessage(-1, self.leader['id'], time.time()*100, request_id))
        port = self.ports[self.leader['id']]
        host = '127.0.0.1'
        logging.info("[SEND] ClientRequestMsg ID: {} Dest (Leader): {}".format(request_id, self.leader['id']))
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
        logging.info("[SEND] RequestBroadcastMsg ID: {}".format(request_id))
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
        logging.info("[Status] Starting Client: {}".format(self.client_port))
        receive = threading.Thread(target=self.receive_messages)
        receive.start()
        i = 0
        prev_request = -1
        while i < self.num_requests:
            # current_leader : The leader to which request i is sent
            current_leader = self.leader['id']
            # is_broadcast : Did the client broadcast the request?
            is_broadcast = False
            if prev_request != i:
                self.send_request(i)
            prev_request = i
            time.sleep(2)
            if i in self.message_buffer.keys():
                logging.info("[Status] Verified received ResponseMsg ID: {}".format(i))
                del self.message_buffer[i]
                i += 1  # next request id
            else:
                self.candidate_leader = None
                logging.info("[Status] Not received ResponseMsg ID: {}".format(i))
                self.send_request_broadcast(i)
                self.num_leader_election += 1 # Every time a client sends a broadcast, it means the leader failed and election will happen
                is_broadcast = True
                time.sleep(6)
            if is_broadcast:
                # If the client broadcasted the request and the leader still didn't change, it will re-send the same request
                if int(current_leader) != int(self.leader['id']):
                    logging.info("[Status] New Leader elected, next request ID...")
                    i += 1
                    # log self.local_leader and set it to None with status as not failed
                    self.leader_logger.tick(time.time()*100, self.candidate_leader, 0)
                    self.candidate_leader = None
                else:
                    # log self.local_leader and set it to None with status as failed
                    self.leader_logger.tick(time.time()*100, self.candidate_leader, 1)
                    self.candidate_leader = None


        self.view_change_logger.save('client_view_changes_{}_{}'.format(self.total_nodes, self.config.mab.algo))
        self.leader_logger.save('leader_election_rounds_{}_{}'.format(self.total_nodes, self.config.mab.algo))
        lock.acquire()
        self.run = False
        lock.release()
        print("Total Requests : {}, Number of Leader Elections : {}", self.num_requests, self.num_leader_election)
        logging.info("Total Requests : {}, Number of Leader Elections : {}".format(self.num_requests, self.num_leader_election))
