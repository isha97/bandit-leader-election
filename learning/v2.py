import time
from os.path import join
import numpy as np
from numpy.random import default_rng
from enum import Enum

from .node import Node
from .message import *
from utils.logger import FailureEstimatesLogger
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
        self.name = '{}_{}_{}'.format(self.id, self.total_nodes, self.explore_exploit)

        # MAB parameters
        self.epsilon = config.mab.epsilon
        self.decay = config.mab.decay
        self.alpha = config.mab.alpha
        self.explore_exploit = config.mab.algo
        self.tradeoff = config.mab.c
        self.arm_counts = np.zeros((self.total_nodes))
        self.t = 0

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
        self.seed = config.random_seed

        self.rng = default_rng(self.seed)
        self.ping_sleep_sec = config.node.ping_sleep_sec
        self.ping_sleep_reply = config.node.ping_sleep_reply
        self.num_leader_election_rounds = 0
        self.num_reqests = config.client.num_requests
        self.local_leader = None
        self.penalize_values = np.zeros((self.total_nodes))
        self.request_broadcast_id = None


        # Set failure estimate of all nodes (noisy)
        self.failure_estimates = self.rng.normal(
            config.failure_estimates.mean,
            config.failure_estimates.std,
            self.total_nodes
        )
        self.fail_est_logger = FailureEstimatesLogger(time.time()*100, self.failure_estimates)

        # Leader election algorithm type
        if config.election_algorithm == 'Deterministic':
            self.election_algorithm = Election_Algorithm.DETERMINISITC
        elif config.election_algorithm == 'Randomized':
            self.election_algorithm = Election_Algorithm.RANDOM
        else:
            self.election_algorithm = Election_Algorithm.LEARNING

        logging.basicConfig(level=logging.INFO,
            format='%(asctime)s %(levelname)-8s [Node {}] %(funcName)s() %(message)s'.format(self.id),
            datefmt='%Y-%m-%d %H:%M:%S', handlers=[
                logging.FileHandler('logs/node_{}_{}_{}.log'.format(self.id, self.total_nodes,
                                                                    self.explore_exploit)),
                logging.StreamHandler()
                ]
        )


    def _select_node_exploitation(self, topn:int = 1):
        """Select candidate leaders.

        Args
        ----
            topn (int): number of candidate to propose (default = 1)

        Returns
        -------
            ids (np.ndarray): ndarray of candidate ids
        """

        if self.explore_exploit == 'egreedy':
            if self.rng.random() < self.epsilon:
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
                ids = (-self.failure_estimates - self.penalize_values).argsort()[-topn:]
            self.epsilon *= self.decay
            ids = np.sort(ids)
            lock.acquire()
            self.my_candidates = ids
            lock.release()
            return ids
        elif self.explore_exploit == 'UCB':
            choice = (
                self.failure_estimates
                - self.tradeoff*np.sqrt(np.log(self.t)/self.arm_counts)
            ).argsort()[:topn]
            lock.acquire()
            self.my_candidates = list(choice)
            lock.release()
            return choice
        elif self.explore_exploit == 'UCB-penalize':
            choice = (
                self.failure_estimates + self.penalize_values
                - self.tradeoff*np.sqrt(np.log(self.t)/self.arm_counts)
            ).argsort()[:topn]
            lock.acquire()
            self.my_candidates = list(choice)
            lock.release()
            return choice


    def _select_node_exploration(self):
        """Algorithm to use for exploration in bandits"""
        # if self.explore_exploit == 'egreedy':
        #     return self.rng.choice(self.total_nodes, size=1, replace=False)[0]
        # elif self.explore_exploit == 'UCB':
        choice = np.argmax(
              self.failure_estimates + self.tradeoff*np.sqrt(np.log(self.t)/self.arm_counts)
        )
        self.t += 1
        # self.arm_counts[choice] += 1
        return choice

    def penalize(self):
        # Penalize the local_leader which was selected  but isn't alive so that it doesn't get selected again
        self.penalize_values[self.local_leader] += 0.5
        logging.info("Penalizing {}, values = {}".format(self.local_leader, self.penalize_values))


    def send_unicast(self, message, port):
        """Send point-to-point message"""
        host = '127.0.0.1'
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.send(message.encode('ascii'))
            s.close()
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
                # Select a node to send ping message -- bandit exploration
                node = self._select_node_exploration()
                port = self.ports[node]
                s.connect((host, port))
                lock.acquire()
                self.ping_replies = True
                lock.release()
                logging.info("[SEND][FailEst] [Message]PingMsg to: {}".format(node))
                message = str(PingMessage(self.id, -100, time.time()*100))
                s.send(message.encode('ascii'))
                s.close()
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
        self.penalize_values[message.sender] = 0
        logging.info("[RECV] [Message]PingReplyMsg from: {} @ {}, msg: {}".format(message.sender, message.stamp, message))


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
                    # Broadcast to all other nodes
                    receiver = self.ports
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

            # If candidate accepts leader role
            if isinstance(message, ConfirmElectionMessage):
                self.receive_confirm_election_msg(message)

            # If we receive request from leader, send response
            if isinstance(message, RequestBroadcastMessage):
                self.receive_request_broadcast(message)

            if not self.is_failed:

                # If we receive ping message from any other node
                if isinstance(message, PingMessage):
                    self.receive_ping_message(message)

                # If we receive ping reply message from any other node
                elif isinstance(message, PingReplyMessage):
                    self.receive_ping_reply_message(message)

                # if self.leader['id'] is not None:

                # If we receive request from client
                # (either we are leader or leader is down!)
                elif isinstance(message, ClientRequestMessage):
                    self.receive_request(message)

                # If we receive candidates from another node, update local candidate list
                elif isinstance(message, ShareCandidatesMessage):
                    self.receive_candidate_msg(message)

                elif self.leader == self.id and isinstance(message, ReplyBroadcastMessage):
                    self.receive_broadcast_reply(message)

            # If the environement fails us!
            if isinstance(message, FailureMessage):
                self.receive_state_change_msg(message)

        connection.close()


    def receive_state_change_msg(self, message):
        """If our failure state changes"""
        previous_fail_status = self.is_failed
        if message.failureVal == "True":
            if not self.is_failed:
                self.update_failure_estimate_up(self.id)
            lock.acquire()
            self.is_failed = True
            lock.release()
        else:
            # if previous_fail_status == True:
            #     self.leader['id'] = None
            lock.acquire()
            self.is_failed = False
            lock.release()
        logging.info("[Status] Failed Status: {}".format(self.is_failed))


    def receive_request_broadcast(self, message):
        """Respond to request broadcast from leader if not failed."""
        logging.info("[RECV] RequestBroadcastMsg ID: {} from: {}, msg: {}"
                    .format(message.requestId, message.sender, message))
        self.request_broadcast_id = None
        if self.leader['id'] != message.leader and \
                        self.leader['stamp'] < message.stamp:
            lock.acquire()
            self.leader['id'] = int(message.leader)
            self.leader['stamp'] = message.stamp
            lock.release()
            logging.info("[Leader] Changed leader to {} @ {}".format(self.leader['id'], self.leader['stamp']))

        lock.acquire()
        self.message_buffer[message.sender][message.requestId] = 1
        lock.release()
        if not self.is_failed:
            self.update_failure_estimate_down(message.sender)
            logging.info("[SEND] [Message]ReplyBroadcastMsg to: {}".format(self.leader['id']))
            response_msg = str(ReplyBroadcastMessage(self.id, self.leader['id'], 0, message.requestId))
            self.send_unicast(response_msg, self.ports[self.leader['id']])

        # Hack to shut down the node
        if message.requestId == self.num_reqests - 1:
            time.sleep(5)
            self.stop_node()


    def receive_ping_message(self, message):
        """ Decreasing the failure probability of the node it received ping from"""
        logging.info("[RECV][FailEst] [Message]PingMsg from: {} @ {}, msg: {}".format(message.sender, message.stamp, message))
        self.update_failure_estimate_down(message.sender)
        logging.info("[SEND][FailEst] [Message]PingReplyMsg to: {}".format(message.sender))
        reply_message = str(PingReplyMessage(self.id, 0, time.time()*100))
        self.send_unicast(reply_message, self.ports[message.sender])


    def receive_broadcast_reply(self, message):
        """ Decreasing the failure probability of the node it received boradcast reply from"""
        logging.info("[RECV] [Message]ReplyBroadcastMsg from: {} @ {}, msg: {}".format(message.sender, message.stamp, message))
        self.update_failure_estimate_down(message.sender)


    def leader_election_learning_based(self):
        """Learning Leader Election"""
        self.update_failure_estimate_up(self.leader['id'])
        ids = self._select_node_exploitation(topn=int((self.total_nodes - 1) / 2))
        logging.info("[LeaderElec] Candidates: {}".format(ids))
        # add candidate message to out queue
        lock.acquire()
        msg = str(ShareCandidatesMessage(self.id, self.leader['id'], time.time()*100, list(ids)))
        logging.info("[SEND][LeaderElec] [Message]ShareCandidatesMsg {}".format(msg))
        self.out_queue.append(msg)
        lock.release()


    def leader_election_deterministic(self):
        """Deterministic Leader Election"""
        next_candidate = (self.leader['id'] + 1)%self.total_nodes
        logging.info("[LeaderElec] Candidate: {}".format(next_candidate))
        # if I am the next leader send the confirm election
        # TODO: Fix this line below!
        self.leader['id'] = next_candidate
        if next_candidate == self.id and not self.is_failed:
            self.leader['stamp'] = time.time() * 100
            logging.info("[LeaderElec] I am next leader!")
            logging.info("[SEND][LeaderElec] ConfirmElectionMsg")
            self.send_unicast(str(ConfirmElectionMessage(self.id, next_candidate, self.leader['stamp'])),
                              self.client_port)


    def leader_election_randomized(self):
        """Randomized Leader Election"""
        next_candidate = (self.leader['id'] + 1)%self.total_nodes
        # if I am supposed to select the next leader
        if next_candidate == self.id:
            logging.info("[LeaderElec] I am next leader!")
            self.leader['id'] = self.rng.choice(self.total_nodes, size=1, replace=False)

            logging.info("[LeaderElec] New leader: {}".format(self.leader['id']))
            self.leader['stamp'] = time.time() * 100

            lock.acquire()
            logging.info("[SEND][LeaderElec] ConfirmElectionMsg")
            self.out_queue.append(str(ConfirmElectionMessage(self.id, self.leader['id'], self.leader['stamp'])))
            lock.release()

            logging.info("[SEND][Client][LeaderElec] ConfirmElectionMsg")
            self.send_unicast(str(ConfirmElectionMessage(self.id, self.leader['id'], self.leader['stamp'])),
                              self.client_port)


    def receive_request(self, message):
        """Received from the client, if we are the leader, or the leader failed """
        logging.info("[RECV][Client] Request ID: {}, message = {}"
                     .format(message.requestId, message))

        requestId = message.requestId

        if self.leader['id'] == self.id:
            logging.info("[SEND][Client] ResponseMsg msg: {}".format(message))
            self.send_unicast(str(ResponseMessage(self.id, self.leader['id'], time.time()*100, requestId)),
                            self.client_port)
            lock.acquire()
            logging.info("[SEND][Client] RequestBroadcastMsg msg: {}".format(message))
            self.out_queue.append(str(RequestBroadcastMessage(self.id, self.leader['id'], time.time()*100, requestId)))
            lock.release()
        elif requestId not in self.message_buffer[self.leader['id']]:
            # Function overloads for when a node is rejoining the node pool
            # When this happens, update the leader with the client leader and
            # take part in leader election.
            # lock.acquire()
            # self.leader['id'] = int(message.leader)
            # lock.release()
            if self.request_broadcast_id is not None and self.request_broadcast_id == requestId:
                self.penalize()
            else:
                self.request_broadcast_id = requestId
            if self.election_algorithm == Election_Algorithm.DETERMINISITC:
                logging.info("[LeaderElec] Starting Deterministic LE...")
                self.leader_election_deterministic()
            elif self.election_algorithm == Election_Algorithm.LEARNING:
                logging.info("[LeaderElec] Starting Learning LE...")
                self.leader_election_learning_based()
            elif self.election_algorithm == Election_Algorithm.RANDOM:
                logging.info("[LeaderElec] Starting Random LE...")
                self.leader_election_randomized()

        # Hack to shut down the node
        if message.requestId == self.num_reqests - 1:
            time.sleep(10)
            self.stop_node()


    def receive_confirm_election_msg(self, message):
        """If candidate accepts leader role and clears candidates.
        Update new leader failure prob. 

        Args
        ----
            message (Message): Candidate
        """
        logging.info("[RECV][LeaderElec] ConfirmElectionMsg from: {} @ {}, msg = {}"
                     .format(message.sender, message.stamp, message))
        if message.stamp > self.leader['stamp']:
            lock.acquire()
            self.leader['id'] = int(message.leader)
            self.leader['stamp'] = message.stamp
            lock.release()
            logging.info("[Leader] Changed leader to {} @ {}".format(self.leader['id'], self.leader['stamp']))
            # Clear out candidates now that we have a leader
            lock.acquire()
            self.candidates = []
            self.my_candidates = []
            lock.release()
            if not self.is_failed:
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


    def receive_candidate_msg(self, message):
        """On receiving candidates from nodes, update local candidate buffer.
        If we have enough candidates, then update the leader. Update sender
        failure prob.

        Broadcast ConfirmElection if we are new leader and not failed.

        Args
        ----
            Message (Message): CandidateElection message
        """
        # if self.leader['id'] != message.leader and \
        #     self.leader['stamp'] < message.stamp:
        #     self.leader['id'] = message.leader
        #     self.leader['stamp'] = message.stamp
        #     logging.info("[Leader] Changed leader to {} @ {}".format(self.leader['id'], self.leader['stamp']))

        lock.acquire()
        self.candidates.append(message.candidates)
        lock.release()
        self.update_failure_estimate_down(message.sender)
        logging.info("[RECV][LeaderElec] ShareCandidatesMsg from: {}, msg: {}"
                     .format(message.sender, message))

        # If we have enough candidates to decide on leader
        if len(self.candidates) > int((self.total_nodes - 1) / 2 - 1) and \
                len(self.my_candidates) > 0:
            time.sleep(3)

            lock.acquire()
            self.candidates.append(self.my_candidates)
            local_candidates = self.candidates
            self.candidates = []
            lock.release()
            candidate_np = np.array(local_candidates).flatten()
            #self.leader['id'] = np.argmax(np.bincount(candidate_np))
            leader_id = np.argsort(np.bincount(candidate_np))[-1]
            lock.acquire()
            if leader_id != self.leader['id']:
                self.local_leader = leader_id
            else:
                self.local_leader = np.argsort(np.bincount(candidate_np))[-2]
            lock.release()
            logging.info("[LeaderElec] Got enough ShareCandidatesMsg's, New leader: {}".format(self.local_leader))
            self.send_unicast(str(NewLeaderMessage(self.id, self.local_leader, time.time() * 100)),
                              self.client_port)

            # If we are the leader, broadcast candidate acceptance if we
            # are not failed
            if self.local_leader == self.id and not self.is_failed:
                lock.acquire()
                self.leader['stamp'] = time.time() * 100
                self.leader['id'] = self.local_leader
                lock.release()
                logging.info("[LeaderElec] I am the new leader! Broadcasting ConfirmElectionMsg")
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
        self.arm_counts[int(id)] += 1
        self.failure_estimates[id] = \
            (self.failure_estimates[id] * self.node_count[id]) / (self.node_count[id] + 1)
        self.node_count[id] += 1
        self.fail_est_logger.tick(time.time()*100, self.failure_estimates)
        logging.info("[FailEst DOWN] Updating Node: {} New FailEst: {}".format(id, self.failure_estimates))


    def update_failure_estimate_up(self, id: int):
        """On node_id failure, update its local failure estimate.

        Args
        ----
            id (int): Node ID to update.
        """
        self.arm_counts[int(id)] += 1
        self.failure_estimates[id] = \
            (self.failure_estimates[id] * self.node_count[id] + 1) / (self.node_count[id] + 1)
        self.node_count[id] += 1
        self.fail_est_logger.tick(time.time()*100, self.failure_estimates)
        logging.info("[FailEst UP] Updating Node: {} New FailEst: {}".format(id, self.failure_estimates))


    def run_node(self):
        """Run threads to send and receive messages"""
        self.run = True
        logging.info("[Status] Starting Node: {}".format(self.id))
        logging.info("[FailEst] Init. FailureEst: {}".format(self.failure_estimates))
        receive = threading.Thread(target=self.receive_messages)
        receive.start()
        send_message = threading.Thread(target=self.send_broadcast)
        send_message.start()
        send_ping = threading.Thread(target=self.send_ping_message)
        send_ping.start()


    def stop_node(self):
        """Terminate all threads of the node."""
        logging.info("[Status] Stopping Node: {}".format(self.id))
        lock.acquire()
        self.run = False
        lock.release()
        self.fail_est_logger.save(join('..', self.name, '_failEst.pbz2'))
