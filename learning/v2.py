import time

import numpy as np
from numpy.random import default_rng
from enum import Enum

from .node import Node
from .message import *
from _thread import *
import threading
import socket
import logging


lock = threading.Lock()


class Election_Algorithm(Enum):
    DETERMINISITC = 1
    RANDOM = 2
    LEARNING = 3


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
        self.previous_fail_status = False

        # MAB parameters
        self.epsilon = config.mab.epsilon
        self.decay = config.mab.decay
        self.alpha = config.mab.alpha

        # Set failure estimate of all nodes (noisy)
        self.failure_estimates = np.random.normal(
            config.failure_estimates.mean,
            config.failure_estimates.std,
            self.total_nodes
        )

        # Messages buffer and out queue
        self.out_queue = []
        self.message_buffer = {i: {} for i in range(config.num_nodes)}
        self.curret_leader_message = None

        # Keep track of how many times a node estimate is updated
        self.node_count = np.ones(n)

        # Node port
        self.my_receving_port = self.ports[id]

        # Candidate buffers
        self.candidates = []
        self.my_candidates = []

        self.rng = default_rng()
        self.ping_sleep_sec = config.node.ping_sleep_sec
        self.ping_sleep_reply = config.node.ping_sleep_reply
        self.num_leader_election_rounds = 0

        # Leader election algorithm type
        if config.election_algorithm == 'Deterministic':
            self.election_algorithm = Election_Algorithm.DETERMINISITC
        elif config.election_algorithm == 'Randomized':
            self.election_algorithm = Election_Algorithm.RANDOM
        else:
            self.election_algorithm = Election_Algorithm.LEARNING

        logging.basicConfig(level=logging.DEBUG,
            format='[%(asctime)s %(levelname)-8s %(funcName)s() %(message)s',
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
            if self.leader['id'] in ids:
                ids = np.delete(ids, np.where(ids == self.leader['id']))
            else:
                ids = ids[:topn]
        else:
            ids = (-self.failure_estimates).argsort()[-topn:]
        self.epsilon *= self.decay
        ids = np.sort(ids)
        self.my_candidates = ids
        return ids

    def send_unicast(self, message, port):
        # send point-to-point message
        host = '127.0.0.1'
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.send(message.encode('ascii'))
            s.close()
            logging.info("sending message {} to port {}".format(message, port))
        except Exception as msg:
            logging.error("Unable to send message {} to port {}".format(message, port))
            s.close()

    def send_ping_message(self):
        """Send ping message to any random node"""
        self.ping_replies = False
        host = '127.0.0.1'
        while self.run:
            time.sleep(self.ping_sleep_sec)
            if self.is_failed:
                continue
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                node = self.rng.choice(self.total_nodes, size=1, replace=False)[0]
                port = self.ports[node]
                s.connect((host, port))
                lock.acquire()
                self.ping_replies = True
                lock.release()
                message = str(PingMessage(self.id, -100, time.time()*100))
                s.send(message.encode('ascii'))
                s.close()
                logging.info("Sending ping message to node {}".format(node))
            except Exception as msg:
                logging.error("Unable to send ping message to node {} {}".format(node, msg))
                s.close()

            # Sleep for a bit before expecting reply
            time.sleep(self.ping_sleep_reply)

            # check if we received a reply
            if self.ping_replies:
                self.update_failure_estimate_up(node)
                lock.acquire()
                self.ping_replies = False
                lock.release()

    def receive_ping_reply_message(self, message):
        """Receive ping reply message, update failure prob. (down)"""
        lock.acquire()
        self.ping_replies = False
        lock.release()
        self.update_failure_estimate_down(message.sender)


    def send_broadcast(self):
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
                            self.send_unicast(message, port)
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

                # If we receive request from leader, send response
                elif isinstance(message, RequestBroadcastMessage):
                    self.receive_request_broadcast(message)

                # If we receive ping message from any other node
                elif isinstance(message, PingMessage):
                    self.receive_ping_message(message)

                # If we receive ping reply message from any other node
                elif isinstance(message, PingReplyMessage):
                    self.receive_ping_reply_message(message)

                if self.leader['id'] is not None:

                    # If we receive candidates from another node, update local candidate list 
                    if isinstance(message, ShareCandidatesMessage):
                        self.recieve_candidate_msg(message)

                    # If we receive request from client
                    # (either we are leader or leader is down!)
                    elif isinstance(message, ClientRequestMessage):
                        self.receive_request(message)
                        
                    if self.leader == self.id and isinstance(message, ReplyBroadcastMessage):
                        self.receive_broadcast_reply(message)

            # If the environement fails us!
            if isinstance(message, FailureMessage):
                self.receive_state_change_msg(message)

            else:
                continue

        connection.close()


    def receive_state_change_msg(self, message):
        """If our failure state changes"""
        previous_fail_status = self.is_failed
        if message.failureVal == "True":
            if not self.is_failed:
                self.update_failure_estimate_up(self.id)
            self.is_failed = True
        else:
            if previous_fail_status == True:
                self.leader['id'] = None
            self.is_failed = False
        logging.info("FAILED STATUS : {}".format(self.is_failed))


    def receive_request_broadcast(self, message):
        """Respond to request broadcast from leader if not failed."""
        logging.info("Request id {} from node {}"
                    .format(message.requestId, message.sender))
        if self.leader['id'] != message.leader and \
                        self.leader['stamp'] < message.stamp:
            self.leader['id'] = message.leader
            self.leader['stamp'] = message.stamp
        lock.acquire()
        self.message_buffer[message.sender][message.requestId] = 1
        lock.release()
        self.update_failure_estimate_down(message.sender)
        response_msg = str(ReplyBroadcastMessage(self.id, self.leader['id'], 0, message.requestId))
        self.send_unicast(response_msg, self.ports[self.leader['id']])


    def receive_ping_message(self, message):
        """ Decreasing the failure probability of the node it received ping from"""
        logging.info("Received ping message from node {}".format(message.sender))
        self.update_failure_estimate_down(message.sender)
        reply_message = str(PingReplyMessage(self.id, 0, time.time()*100))
        self.send_unicast(reply_message, self.ports[message.sender])


    def receive_broadcast_reply(self, message):
        """ Decreasing the failure probability of the node it received boradcast reply from"""
        logging.info("Received broadcast reply message from node {}".format(message.sender))
        self.update_failure_estimate_down(message.sender)


    def leader_election_learning_based(self):
        logging.info("Oops, leader is not responding. Starting leader election...")
        self.update_failure_estimate_up(self.leader['id'])
        ids = self._select_leader(topn=int((self.total_nodes - 1) / 2))
        logging.info("Selected candidate nodes {} for leader".format(ids))
        # add candidate message to out queue
        lock.acquire()
        self.out_queue.append(str(ShareCandidatesMessage(self.id, self.leader['id'], time.time()*100, list(ids))))
        lock.release()


    def leader_election_deterministic(self):
        logging.info("Oops, leader is not responding. Starting leader election...")
        next_candidate = (self.leader['id'] + 1)%self.total_nodes
        logging.info("The next candidate for leader election {}".format(next_candidate))
        # if I am the next leader send the confirm election
        self.leader['id'] = next_candidate
        if next_candidate == self.id and not self.is_failed:
            self.leader['stamp'] = time.time() * 100
            logging.info("I am the new leader! Broadcasting confirmation to everyone")
            self.send_unicast(str(ConfirmElectionMessage(self.id, next_candidate, self.leader['stamp'])),
                              self.client_port)


    def leader_election_randomized(self):
        logging.info("Oops, leader is not responding. Starting leader election...")
        next_candidate = (self.leader['id'] + 1)%self.total_nodes
        # if I am supposed to select the next leader
        if next_candidate == self.id:
            logging.info("I am supposed to select the next leader")
            self.leader['id'] = self.rng.choice(self.total_nodes, size=1, replace=False)
            logging.info("The new random leader selected is {}".format(self.leader['id']))
            self.leader['stamp'] = time.time() * 100
            lock.acquire()
            self.out_queue.append(str(ConfirmElectionMessage(self.id, self.leader['id'], self.leader['stamp'])))
            lock.release()
            self.send_unicast(str(ConfirmElectionMessage(self.id, self.leader['id'], self.leader['stamp'])),
                              self.client_port)

    def receive_request(self, message):
        """Received from the client, if we are the leader, """
        logging.info("From client, message : {}"
                     .format(message.requestId))

        if self.is_failed:
            pass

        requestId = message.requestId

        if self.leader['id'] == self.id:
            self.send_unicast(str(ResponseMessage(self.id, self.leader['id'], time.time()*100, requestId)),
                              self.client_port)
            lock.acquire()
            self.out_queue.append(str(RequestBroadcastMessage(self.id, self.leader['id'], time.time()*100, requestId)))
            lock.release()
        elif requestId not in self.message_buffer[self.leader['id']]:
            if self.election_algorithm == Election_Algorithm.DETERMINISITC:
                self.leader_election_deterministic()
            elif self.election_algorithm == Election_Algorithm.LEARNING:
                self.leader_election_learning_based()
            elif self.election_algorithm == Election_Algorithm.RANDOM:
                self.leader_election_randomized()


    def recieve_confirm_election_msg(self, message):
        """If candidate accepts leader role and clears candidates.
        Update new leader failure prob. 

        Args
        ----
            message (Message): Candidate
        """
        if message.stamp > self.leader['stamp']:
            self.leader['id'] = message.leader
            self.leader['stamp'] = message.stamp
            logging.info("Updated the current leader to {}".format(self.leader['id']))
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
        if self.leader['id'] != message.leader and \
            self.leader['stamp'] < message.stamp:
            self.leader['id'] = message.leader
            self.leader['stamp'] = message.stamp

        self.candidates.append(message.candidates)
        self.update_failure_estimate_down(message.sender)
        logging.info("New candidate message from {}, message : {}"
                     .format(message.sender, message.candidates))

        # If we have enough candidates to decide on leader
        if len(self.candidates) > (self.total_nodes - 1)/2 and \
            len(self.my_candidates) > 0:

            self.candidates.append(self.my_candidates)
            candidate_np = np.array(self.candidates).flatten()
            self.leader['id'] = np.argmax(np.bincount(candidate_np))
            logging.info("Enough candidate messages, new leader is {}".format(self.leader['id']))

            # If we are the leader, broadcast candidate acceptance if we
            # are not failed
            if self.leader['id'] == self.id and not self.is_failed:
                self.leader['stamp'] = time.time()*100
                logging.info("I am the new leader! Broadcasting confirmation to everyone")
                lock.acquire()
                self.out_queue.append(str(ConfirmElectionMessage(self.id, self.leader['id'], self.leader['stamp'])))
                lock.release()
                self.send_unicast(str(ConfirmElectionMessage(self.id, self.leader['id'], self.leader['stamp'])),
                                  self.client_port)


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
        send_message = threading.Thread(target=self.send_broadcast)
        send_message.start()
        send_ping = threading.Thread(target=self.send_ping_message)
        send_ping.start()


    def stop_node(self):
        """Terminate all threads of the node."""
        logging.info("Stopping node {}".format(self.id))
        self.run = False
