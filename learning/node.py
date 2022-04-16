import numpy as np

class Node(object):
    def __init__(self, id, n, config):
        """Initialize node

            id: Node id
            n: total number of nodes
            config: config parameters
        """ 
        self.id = id
        self.is_failed = False
        self.total_nodes = n
        # Set failure estimate of all nodes (noisy)
        self.failure_estimates = np.random.normal(
            config.failure_estimates.mean,
            config.failure_estimates.std,
            self.total_nodes
        )
        # Keep track of how many times a node estimate is updated
        self.node_count = np.zeros(n)
        self.leader = 1 # Leader index

        # Queue messages for sending
        self.out_queue = []


    def send(self, message_buffer):
        """Send message to other nodes

            message_buffer: (dict) key = idx of receiver, value = message
            step: current timestep (reconnecting nodes to ignore stale messages)

        Returns
        -------
            messages (dict): dict with keys as ids and values as messages
        """
        pass


    def recieve(self, messages, step):
        """Recieve messages from other nodes
        
            messages: list of messages to node
        """
        pass