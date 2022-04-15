import time

import numpy as np
from numpy.random import default_rng

from .node import Node
from .message import *
from _thread import *
import threading
import socket

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
        ports = []
        for i in range(n):
            ports.append(49153 + i)
        self.ports = ports
        self.my_receving_port = ports[id]
        self.message_buffer = {i: [] for i in range(config.num_nodes)}
        self.rng = default_rng()

        self.leader_timeout = config.v1.leader_timeout
        self.leader_timeout_cnt = 0
        self.candidates = []

    def _select_leader(self, topn=1):
        """Select candidate leaders

            topn: number of candidate to propose

        Returns
        -------
            ids (List): list of candidate ids
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
        return ids

    def send(self, message_buffer):
        """Send message to other nodes

            message_buffer: (dict) key = idx of receiver, value = message

        Returns
        -------
            messages (dict): dict with keys as ids and values as messages
        """
        # if we are faulty, do not send anything
        while self.run:
            if self.is_failed:
                pass
            else:
                # clear our out buffer
                host = '127.0.0.1'
                while len(self.out_queue) > 0:
                    dest, message = self.out_queue.pop()
                    for port in self.ports:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        if port != self.my_receving_port:
                            try:
                                s.connect((host, port))
                                s.send(message.encode('ascii'))
                                s.close()
                            except Exception as msg:
                                print(msg)
                                s.close()


    def multi_threaded_client(self,connection):
        while True:
            data = str(connection.recv(2048).decode('ascii'))
            if data.startswith("ConfirmElectionMsg"):
                message = ConfirmElectionMessage(data.split(" ")[1], data.split(" ")[2])
                self.recieve_confirm_election_msg(message)
            if data.startswith("CandidateMsg"):
                message = CandidateMessage(data.split(" ")[1], data.split(" ")[2], data.split(" ")[3])
                self.recieve_candidate_msg(message)
            if data.startswith("PingMsg"):
                self.recieve_ping()
            if data.startswith("ReplyPingMsg"):
                message = ReplyPingMessage(data.split(" ")[1], data.split(" ")[2])
                self.message_buffer[message.sender] = message
            if data.startswith("FailureMsg"):
                message = FailureMessage(data.split(" ")[1])
                lock.acquire()
                if message.failureVal == "True":
                    self.is_failed = False
                else:
                    self.is_failed = True
                lock.release()
            if not data:
                break
        connection.close()

    def reveive_messages(self):
        host = '127.0.0.1'
        port = self.my_receving_port
        receiving_socket = socket.socket()
        try:
            receiving_socket.bind((host, port))
        except socket.error as e:
            print(str(e))
        receiving_socket.listen(5)
        while self.run:
            Client, address = receiving_socket.accept()
            start_new_thread(self.multi_threaded_client, (Client,))

    def recieve_ping(self):
        # How to act when a ping is received
        if self.is_failed:
            pass

        if self.leader == self.id:
            self.out_queue.append(ReplyPingMessage(self.id, 0))
        else:
            if len(self.message_buffer[self.leader]) == 0:
                time.sleep(self.leader_timeout)
                # if equal to threshold, create candidates
                if len(self.message_buffer[self.leader]) == 0:
                    # Update leader dist.
                    self.failure_estimates[self.leader] = \
                        (self.failure_estimates[self.leader] *
                         self.candidate_count[self.leader]) / (self.candidate_count[self.leader] + 1)
                    ids = self._select_leader(topn=int((self.total_nodes - 1) / 3))
                    # add candidate message to out queue
                    for i in range(self.total_nodes):
                        if i != self.id:
                            self.out_queue.append(str(CandidateMessage(self.id, 0, ids)))
            else:
                self.message_buffer[self.leader].clear()


    def recieve_candidate_msg(self, message):
        self.candidates.extend(message.candidates)

        if len(self.candidates) > 2*(self.total_nodes - 1)/3:
            self.leader = np.argmax(np.bincount(self.candidates))
            self.candidates = []
            if self.leader == self.id:
                # Broadcast candidate acceptance
                for i in range(self.total_nodes):
                    if i != self.id:
                        self.out_queue.append(str(ConfirmElectionMessage(self.id, 0)))


    def recieve_confirm_election_msg(self, message):
        self.leader = message.sender
        self.candidates = []
        self.failure_estimates[self.leader] = \
            (self.failure_estimates[self.leader] *
             self.candidate_count[self.leader] + 1) / (self.candidate_count[self.leader] + 1)

    def run_node(self):
        """Run threads to send and receive messages"""
        self.run = True
        receive = threading.Thread(target=self.reveive_messages)
        receive.start()
        send_message = threading.Thread(target=self.send([]))
        send_message.start()


    def stop_node(self):
        """Terminate threads"""
        self.run = False
