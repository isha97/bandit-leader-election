import time


class Node(object):
    def __init__(self, id, n, config):
        """Initialize node

            id: Node id
            n: total number of nodes
            config: config parameters
        """ 
        self.id = id
        self.total_nodes = n
        self.ports = [int(config.port.replica_base_port) + i for i in range(n)]

        # client port
        self.client_port = config.port.client_port
        self.config = config

        # [timestamp, Initial Leader ID]
        self.leader = {'stamp': time.time()*100, 'id': 0}


    def send(self):
        """Send messages"""
        pass


    def receive_messages(self):
        """Receive messages from other nodes"""
        pass


    def run_node(self):
        """Run threads to send and receive messages"""
        pass


    def stop_node(self):
        """Terminate all threads of the node."""
        pass
