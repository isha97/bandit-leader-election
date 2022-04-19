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

        # Node properties
        self.is_failed = False

        # Bandit properties
        self.epsilon = config.v1.epsilon
        self.decay = config.v1.decay
        self.alpha = config.v1.alpha

        # Set failure estimate of all nodes (noisy)
        self.failure_estimates = np.random.normal(
            config.failure_estimates.mean,
            config.failure_estimates.std,
            self.total_nodes
        )

        # Messages buffer and out queue
        self.out_queue = []
        self.message_buffer = {i: {} for i in range(config.num_nodes)}

        # Keep track of how many times a node estimate is updated
        self.node_count = np.ones(n)

        # Node port
        self.my_receving_port = self.ports[id]

        # Candidate buffers
        self.candidates = []
        self.my_candidates = []

        self.rng = default_rng()

        logging.basicConfig(level=logging.DEBUG,
            format='[%(asctime)s %(levelname)-8s %(funcName)s()] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S', handlers=[
                logging.FileHandler('logs/node_{}.log'.format(self.id)),
                logging.StreamHandler()
                ]
        )

        logging.info("Initial failure estimates {}".format(self.failure_estimates))


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
        """Send message only to client"""
        host = '127.0.0.1'
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, self.client_port))
            s.send(message.encode('ascii'))
            s.close()
            logging.info("Replied to client, message : {}".format(message))
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
                    logging.info("BCAST message : {}".format(message))
                    # Broadcast to all other nodes
                    receiver = self.ports + [self.client_port]
                    for port in receiver:
                        if port != self.my_receving_port:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            try:
                                s.connect((host, port))
                                s.send(message.encode('ascii'))
                                s.close()
                            except Exception as msg:
                                logging.error("Unable to send message {} to port {}".format(msg, port))
                                s.close()
            time.sleep(1)


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

            # Parse data, construct message 
            message = parse_and_construct(data)

            if not self.is_failed:
                # If candidate accepts leader role
                if isinstance(message, ConfirmElectionMessage):
                    self.recieve_confirm_election_msg(message)

                # If we receive candidates from another node, update local candidate list 
                elif isinstance(message, ShareCandidatesMessage):
                    self.recieve_candidate_msg(message)

                # If we receive request from client
                # (either we are leader or leader is down!)
                elif isinstance(message, ClientRequestMessage):
                    self.receive_request(message)

                # If we receive request from leader, send response
                elif isinstance(message, RequestBroadcastMessage):
                    self.receive_request_broadcast(message)

            # If the environement fails us!
            if isinstance(message, FailureMessage):
                if message.failureVal == "True":
                    if not self.is_failed:
                        self.update_failure_estimate_up(self.id)
                    self.is_failed = True
                else:
                    self.is_failed = False
                logging.info("FAILED STATUS : {}".format(self.is_failed))

            else:
                continue

        connection.close()


    def receive_request_broadcast(self, message):
        """Respond to request broadcast from leader if not failed."""
        logging.info("Request id {} from node {}"
                    .format(message.requestId, message.sender))
        if self.leader != message.leader:
            # either we failed or the sender failed!
            # TODO: Compare timestamp
            self.leader == message.leader

        lock.acquire()
        self.message_buffer[message.sender][message.requestId] = 1
        lock.release()
        self.update_failure_estimate_down(message.sender)


    def receive_request(self, message):
        """Received from the client, if we are the leader, """
        logging.info("From client, message : {}"
                     .format(message.requestId))

        if self.is_failed:
            pass

        requestId = message.requestId

        if self.leader == self.id:
            self.send_to_client(str(ResponseMessage(self.id, self.leader, 0, requestId)))
            lock.acquire()
            self.out_queue.append(str(RequestBroadcastMessage(self.id, self.leader, 0, requestId)))
            lock.release()
        elif requestId not in self.message_buffer[self.leader]:
            logging.info("Oops, leader is not responding. Starting leader election...")
            self.update_failure_estimate_up(self.leader)
            ids = self._select_leader(topn=int((self.total_nodes - 1) / 3))
            logging.info("Selected candidate nodes {} for leader".format(ids))
            # add candidate message to out queue
            lock.acquire()
            self.out_queue.append(str(ShareCandidatesMessage(self.id, self.leader, 0, list(ids))))
            lock.release()


    def recieve_confirm_election_msg(self, message):
        """If candidate accepts leader role and clears candidates.
        Update new leader failure prob. 

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


    def receive_messages(self):
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
            Client.settimeout(60)
            start_new_thread(self.multi_threaded_client, (Client,))


    def recieve_candidate_msg(self, message):
        """On receiving candidates from nodes, update local candidate buffer.
        If we have enough candidates, then update the leader. Update sender
        failure prob.

        Broadcast ConfirmElection if we are new leader and not failed.

        Args
        ----
            Message (Message): CandidateElection message
        """
        if self.leader != message.leader:
            # either we failed or the sender failed!
            # TODO: Compare timestamp
            self.leader == message.leader

        self.candidates.append(message.candidates)
        self.update_failure_estimate_down(message.sender)
        logging.info("New candidate message from {}, message : {}"
                     .format(message.sender, message.candidates))

        # If we have enough candidates to decide on leader
        if len(self.candidates) > 2*(self.total_nodes - 1)/3 and \
            len(self.my_candidates) > 0:

            self.candidates.append(self.my_candidates)
            candidate_np = np.array(self.candidates).flatten()
            self.leader = np.argmax(np.bincount(candidate_np))
            logging.info("Enough candidate messages, new leader is {}".format(self.leader))

            # If we are the leader, broadcast candidate acceptance if we
            # are not failed
            if self.leader == self.id and not self.is_failed:
                logging.info("I am the new leader! Broadcasting confirmation to everyone")
                lock.acquire()
                self.out_queue.append(str(ConfirmElectionMessage(self.id, self.leader, 0)))
                lock.release()
                self.send_to_client(str(ConfirmElectionMessage(self.id, self.leader, 0)))


    def update_failure_estimate_down(self, id: int):
        """On receiving a message from node_id, update its local failure
        estimate.

        Args
        ----
            id (int): Node ID to update.
        """
        self.failure_estimates[id] = \
            (self.failure_estimates[id] * self.node_count[id]) / (self.node_count[id] + 1)
        self.node_count[id] += 1
        logging.info("@ node {} : {}".format(id, self.failure_estimates))


    def update_failure_estimate_up(self, id: int):
        """On node_id failure, update its local failure estimate.

        Args
        ----
            id (int): Node ID to update.
        """
        self.failure_estimates[id] = \
            (self.failure_estimates[id] * self.node_count[id] + 1) / (self.node_count[id] + 1)
        self.node_count[id] += 1
        logging.info("@ node {} : {}".format(id, self.failure_estimates))


    def run_node(self):
        """Run threads to send and receive messages"""
        self.run = True
        logging.info("Starting node {}".format(self.id))
        receive = threading.Thread(target=self.receive_messages)
        receive.start()
        send_message = threading.Thread(target=self.send)
        send_message.start()


    def stop_node(self):
        """Terminate all threads of the node."""
        logging.info("Stopping node {}".format(self.id))
        self.run = False
