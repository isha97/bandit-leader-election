from this import d
import time

import numpy as np
from numpy.random import default_rng

from .node import Node
from .message import *
from _thread import *
import threading
import socket
import logging

lock = threading.Lock()


class v2(Node):
    def __init__(self, id, n, config):
        """Initialize node

            id: Node id
            n: total number of nodes
            config: config parameters
        """
        super().__init__(id, n, config)
        self.epsilon = config.v1.epsilon
        self.decay = config.v1.decay
        self.alpha = config.v1.alpha
        self.ports = [int(config.port.replica_base_port) + i for i in range(n)]
        self.my_receving_port = self.ports[id]
        self.message_buffer = {i: {} for i in range(config.num_nodes)}
        self.rng = default_rng()

        self.leader_timeout = config.v1.leader_timeout
        self.leader_timeout_cnt = 0
        self.candidates = []
        self.my_candidates = []
        self.client_port = config.port.client_port
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)-8s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S', handlers=[
                                logging.FileHandler('logs/node_{}.log'.format(self.id)),
                                logging.StreamHandler()
                                ]
        )


    def _select_leader(self, topn:int = 1):
        """Select candidate leaders. Use e-greedy strategy

        Args
        ----
            topn (int): number of candidate to propose (default = 1)

        Returns
        -------
            ids (np.ndarray): ndarray of candidate ids
        """

        if np.random.rand() < self.epsilon:
            try:
                # using topn + 1 so that current failed leader doesn't get selected again
                ids = self.rng.choice(self.total_nodes, size=topn + 1, replace=False)
            except:
                ids = np.arange(-1, self.total_nodes)
            if self.leader in ids:
                ids = np.delete(ids, np.where(ids == self.leader))
            else:
                ids = ids[:topn]
        else:
            ids = (-self.failure_estimates).argsort()[-topn:]
        self.epsilon *= self.decay
        ids = np.sort(ids)
        self.my_candidates = ids
        return ids


    def send_to_client(self, message):
        host = '127.0.0.1'
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, self.client_port))
            s.send(message.encode('ascii'))
            s.close()
            logging.info("sending the reply to client, reply message : {}".format(message))
        except Exception as msg:
            logging.error("Unable to send the reply to client, reply message : {}".format(message))
            s.close()


    def send(self):
        """Send message in the out_buffer to other nodes"""
        while self.run:
            # if we are faulty, do not send anything
            if self.is_failed:
                pass
            else:
                host = '127.0.0.1'
                # clear our out_buffer
                while len(self.out_queue) > 0:
                    message = self.out_queue.pop()
                    # Broadcast to all other nodes
                    for port in self.ports:
                        if port != self.my_receving_port:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            try:
                                s.connect((host, port))
                                s.send(message.encode('ascii'))
                                s.close()
                            except Exception as msg:
                                logging.error("Unable to send message to port {}".format(port))
                                s.close()


    def multi_threaded_client(self, connection):
        """Read from the socket until no more messages are available.
        
        Args
        ----
            connection: socket connection
        """
        while True:
            data = str(connection.recv(2048).decode('ascii'))

            # If there is no message
            if not data:
                break

            # If candidate accepts leader role
            if data.startswith("ConfirmElectionMsg"):
                message = ConfirmElectionMessage(data.split(" ")[1], data.split(" ")[2])
                self.recieve_confirm_election_msg(message)

            # If we receive candidates from another node, update local candidate list 
            elif data.startswith("CandidateMsg"):
                message = CandidateMessage(data.split(" ")[1], data.split(" ")[2], data.split(" ")[3])
                message.parse_candidates()
                self.recieve_candidate_msg(message)

            # If we receive request from client (leader is down!)
            elif data.startswith("RequestMsg"):
                message = RequestMessage(data.split(" ")[1])
                self.recieve_request(message)

            # If we receive request from leader, send response
            elif data.startswith("RequestBroadcastMsg"):
                message = RequestBroadcastMessage(data.split(" ")[1], data.split(" ")[2])
                self.receive_request_broadcast(message)

            # If the environement fails us!
            elif data.startswith("FailureMsg"):
                message = FailureMessage(data.split(" ")[1])
                lock.acquire()
                if message.failureVal == "True":
                    self.is_failed = False
                else:
                    self.is_failed = True
                lock.release()
                self.update_failure_estimate_up(self.id)

            else:
                continue
        connection.close()


    def receive_request_broadcast(self, message):
        """Update leader failure estimate when we get request from leader.
        """
        logging.info("received request broadcast for request {} from node {}"
                     .format(message.requestId, message.sender))
        if not self.is_failed:
            lock.acquire()
            self.message_buffer[message.sender][message.requestId] = 1
            lock.release()
            self.update_failure_estimate_down(message.sender)


    def recieve_request(self, message):
        """Received from the client, check if leader is down"""
        logging.info("received request request {} from client"
                     .format(message.requestId))

        if self.is_failed:
            pass
        
        requestId = message.requestId

        if self.leader == self.id:
            self.send_to_client(str(ResponseMessage(self.id, requestId)))
            self.out_queue.append(str(RequestBroadcastMessage(self.id, requestId)))
        elif requestId not in self.message_buffer[self.leader]:
            logging.info("oops leader is not responding, starting leader election")
            self.update_failure_estimate_up(self.leader)
            ids = self._select_leader(topn=int((self.total_nodes - 1) / 3))
            logging.info("selected candidate nodes for leader {}".format(ids))
            # add candidate message to out queue
            self.out_queue.append(str(CandidateMessage(self.id, 0, list(ids))))


    def recieve_confirm_election_msg(self, message):
        """If candidate accepts leader role and clears candidates.

        Args
        ----
            message (Message): Candidate
        """
        self.leader = message.sender
        logging.info("Updated the current leader to {}".format(self.leader))
        # Clear out candidates now that we have a leader
        self.candidates = []
        self.my_candidates = []
        self.update_failure_estimate_down(message.sender)


    def reveive_messages(self):
        """Listener that starts a new thread and reads messages from port"""
        host = '127.0.0.1'
        port = self.my_receving_port
        receiving_socket = socket.socket()
        try:
            receiving_socket.bind((host, port))
        except socket.error as e:
            logging.error(str(e))
        receiving_socket.listen(5)
        while self.run:
            Client, _ = receiving_socket.accept()
            start_new_thread(self.multi_threaded_client, (Client,))


    def recieve_candidate_msg(self, message):
        """On receiving candidates from nodes, update local candidate buffer.
        If we have enough candidates, then update the leader.

        Args
        ----
            Message (Message): CandidateElection message
        """
        self.candidates.append(message.candidates)
        logging.info("received new candidate messagefrom {}, message =  {}"
                     .format(message.sender, message.candidates))

        # If we have enough candidates to decide on leader
        if len(self.candidates) > 2*(self.total_nodes - 1)/3 and \
            len(self.my_candidates) > 0:
            self.update_failure_estimate_down(message.sender)

            self.candidates.append(self.my_candidates)
            candidate_np =  np.array(self.candidates).flatten()
            self.leader = np.argmax(np.bincount(candidate_np))
            logging.info("received enough candidate messages, current new leader would be {}".format(self.leader))

            # If we are the leader, Broadcast candidate acceptance if we
            # are not failed
            if self.leader == self.id and not self.is_failed:
                logging.info("I am the new leader! Broadcasting confirmation to everyone")
                lock.acquire()
                self.out_queue.append(str(ConfirmElectionMessage(self.id, 0)))
                lock.release()
                self.send_to_client(str(ConfirmElectionMessage(self.id, 0)))


    def update_failure_estimate_down(self, id: int):
        """On receiving a message from node_id, update its local failure
        estimate.

        Args
        ----
            id (int): Node ID to update.
        """
        self.failure_estimates[id] = \
            (self.failure_estimates[id] *
             self.node_count[id]) / (self.node_count[id] + 1)
        logging.info("current failure estimates {}".format(self.failure_estimates))


    def update_failure_estimate_up(self, id: int):
        """On node_id failure, update its local failure estimate.

        Args
        ----
            id (int): Node ID to update.
        """
        self.failure_estimates[id] = \
            (self.failure_estimates[id] *
             self.node_count[id] + 1) / (self.node_count[id] + 1)
        logging.info("current failure estimates {}".format(self.failure_estimates))


    def run_node(self, client: bool = False):
        """Run threads to send and receive messages

        Args
        ----
            client (bool): If node should behave as client, set client=True.
                (default=False)
        """
        self.run = True
        logging.info("Starting node {}".format(self.id))
        receive = threading.Thread(target=self.reveive_messages)
        receive.start()
        send_message = threading.Thread(target=self.send)
        send_message.start()


    def stop_node(self):
        """Terminate all threads of the node."""
        self.run = False
