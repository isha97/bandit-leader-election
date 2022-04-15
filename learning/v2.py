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
        self.my_candidates = []

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
        self.my_candidates = ids
        return ids

    def simulate_client(self):
        while True:
            print("Leader ", self.leader)
            print("id ", self.id)
            if True:
                print('Leader sending pings..')
                host = '127.0.0.1'
                for port in self.ports:
                    if port != self.my_receving_port:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        message = str(PingMessage())
                        try:
                            s.connect((host, port))
                            s.send(message.encode('ascii'))
                            s.close()
                        except Exception as msg:
                            print(msg)
                            s.close()
            time.sleep(5)




    def send(self, message_buffer):
        """Send message to other nodes

            message_buffer: (dict) key = idx of receiver, value = message

        Returns
        -------
            messages (dict): dict with keys as ids and values as messages
        """
        # if we are faulty, do not send anything
        # TODO : retry on send
        while self.run:
            if self.is_failed:
                pass
            else:
                # clear our out buffer
                host = '127.0.0.1'
                while len(self.out_queue) > 0:
                    message = self.out_queue.pop()
                    for port in self.ports:
                        if port != self.my_receving_port:
                            print("Sending message {} to node {}".format(message, port))
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
            print("Received message {} from node", data)
            if data.startswith("ConfirmElectionMsg"):
                message = ConfirmElectionMessage(data.split(" ")[1], data.split(" ")[2])
                self.recieve_confirm_election_msg(message)
            if data.startswith("CandidateMsg"):
                message = CandidateMessage(data.split(" ")[1], data.split(" ")[2], data.split(" ")[3])
                message.parse_candidates()
                self.recieve_candidate_msg(message)
            if data.startswith("PingMsg"):
                self.recieve_ping()
            if data.startswith("ReplyPingMsg"):
                #TODO : add request id
                #TODO: decrease the failure probability of the leader
                message = ReplyPingMessage(data.split(" ")[1])
                lock.acquire()
                self.message_buffer[message.sender].append(message)
                lock.release()
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
            self.out_queue.append(str(ReplyPingMessage(self.id, 0)))
            #TODO : reply to client
        else:
            # TODO: checing if the node received a ReplyPing from leader for the request id
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
                            self.out_queue.append(str(CandidateMessage(self.id, 0, list(ids))))
            else:
                self.message_buffer[self.leader].clear()


    def recieve_candidate_msg(self, message):
        self.candidates.append(message.candidates)
        print("message candidates", type(message.candidates))

        if len(self.candidates) > 2*(self.total_nodes - 1)/3 and len(self.my_candidates) > 0:
            self.candidates.append(self.my_candidates)
            #self.candidates.clear()
            # TODO : how to clear the self.candidates list
            candidate_np =  np.array(self.candidates).flatten()
            print("candidate_np: ", candidate_np)
            print("candidate_np_type: ", type(candidate_np))
            self.leader = np.argmax(np.bincount(candidate_np))
            if self.leader == self.id:
                # Broadcast candidate acceptance
                lock.acquire()
                self.out_queue.append(str(ConfirmElectionMessage(self.id, 0)))
                lock.release()



    def recieve_confirm_election_msg(self, message):
        self.leader = message.sender
        self.candidates = []
        self.failure_estimates[self.leader] = \
            (self.failure_estimates[self.leader] *
             self.candidate_count[self.leader] + 1) / (self.candidate_count[self.leader] + 1)

    def run_node(self):
        """Run threads to send and receive messages"""
        self.run = True
        # receive = threading.Thread(target=self.reveive_messages)
        # receive.start()
        # send_message = threading.Thread(target=self.send([]))
        # send_message.start()
        client_simulation = threading.Thread(target=self.simulate_client)
        client_simulation.start()


    def stop_node(self):
        """Terminate threads"""
        self.run = False
