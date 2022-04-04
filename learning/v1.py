import numpy as np
from numpy.random import default_rng

from .node import Node
from .message import *


class v1(Node):
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
        self.rng = default_rng()

        self.leader_timeout = config.v1.leader_timeout
        self.leader_timeout_cnt = 0


    def _select_leader(self, topn=1):
        """Select candidate leaders

            topn: number of candidate to propose

        Returns
        -------
            ids (List): list of candidate ids
        """
        if np.random.rand() < self.epsilon:
            try:
                ids = self.rng.choice(self.total_nodes, size=topn+1, replace=False)
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
        if self.is_failed:
            return message_buffer
        else:
            # clear our out buffer
            while len(self.out_queue) > 0:
                dest, message = self.out_queue.pop()
                message_buffer[dest].append(message)

        return message_buffer


    def recieve(self, messages, step):
        """Recieve messages from other nodes
        
            messages: list of messages to node
            step: current timestep (reconnecting nodes to ignore stale messages)
        """

        # if we are faulty, do nothing
        if self.is_failed:
            return messages

        # If we do not recieve any messages, start time out for faulty leader
        if len(messages) == 0:
            self.leader_timeout_cnt += 1
            # if equal to threshold, create candidates
            if self.leader_timeout == self.leader_timeout_cnt:
                # Update leader dist.
                self.failure_estimates[self.leader] = \
                    (self.failure_estimates[self.leader] * \
                    self.candidate_count[self.leader]) / (self.candidate_count[self.leader] + 1)
                ids = self._select_leader(topn=int((self.total_nodes-1)/3))
                # add candidate message to out queue
                for i in range(self.total_nodes):
                    self.out_queue.append([i, CandidateMessage(self.id, step, ids)])
            else:
                return []

        candidates = []
        # Iterate over all received messages
        for message in messages:

            # Only read messages sent in last time step
            if message.step == step - 1:

                # reset time out if message is from leader (not faulty)
                if message.sender == self.leader:
                    self.leader_timeout_cnt = 0

                # if candidate leader is not faulty, update dist
                if isinstance(message, ConfirmElectionMessage):
                    self.leader = message.sender
                    self.failure_estimates[self.leader] = \
                        (self.failure_estimates[self.leader] * \
                        self.candidate_count[self.leader] + 1) / (self.self.candidate_count[self.leader] + 1)

                # if we are receiving candidate messages, store them
                if isinstance(message, CandidateMessage):
                    candidates.extend(message.candidates)

        if len(candidates) > 0:
            self.leader = np.argmax(np.bincount(candidates))

        return []