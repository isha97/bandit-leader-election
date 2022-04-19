import ast


class Message():
    def __init__(self, id, leader, stamp=0):
        """Base message class with sender id, leader id, message time stamp

            id: id of sender
            leader: id of leader
            stamp: time stamp
        """
        self.sender = int(id)
        self.leader = int(leader)
        self.stamp = int(stamp)


class ShareEstimatesMessage(Message):
    def __init__(self, id, leader, stamp, estimates):
        """Share estimates with destination

            id: id of sender
            leader: id of leader
            stamp: time stamp
            estimates: np.array of all node failure estimates
        """
        super().__init__(id, leader, stamp)
        self.estimates = estimates

    def parse_estimates(self):
        """Parse estimates if initialized as string"""
        self.estimates = ast.literal_eval(self.estimates)

    def __str__(self):
        return('ShareEstimatesMsg {} {} {} {}'.format(
            self.sender,
            self.stamp,
            self.leader,
            self.estimates
            ))


class ShareCandidatesMessage(Message):
    def __init__(self, id, leader, stamp, candidates):
        """Share you candidates with destination

            id: id of sender
            leader: id of leader
            stamp: time stamp
            candidates: np.array of all node failure candidates
        """
        super().__init__(id, leader, stamp)
        self.candidates = candidates

    def parse_candidates(self):
        """Parse candidates if initialized as string"""
        self.candidates = ast.literal_eval(self.candidates)

    def __str__(self):
        return('ShareCandidatesMsg {} {} {} {}'.format(
            self.sender,
            self.stamp,
            self.leader,
            self.candidates
            ))


class ClientRequestMessage(Message):
    def __init__(self, id, leader, stamp, requestId):
        """Client request message

            id: id of sender
            leader: id of leader
            stamp: time stamp
            requestId: request Id of the request
        """
        super().__init__(id, leader, stamp)
        self.requestId = int(requestId)

    def __str__(self):
        return ('ClientRequestMsg {} {} {} {}'.format(
            self.sender,
            self.stamp,
            self.leader,
            self.requestId
            ))


class RequestBroadcastMessage(Message):
    def __init__(self, id, leader, stamp, requestId):
        """Leader request broadcast to all nodes

            id: id of sender
            leader: id of leader
            stamp: time stamp
            requestId: request id of the request
        """
        super().__init__(id, leader, stamp)
        self.requestId = int(requestId)

    def __str__(self):
        return ('RequestBroadcastMsg {} {} {} {}'.format(
            self.sender,
            self.stamp,
            self.leader,
            self.requestId
            ))


class ResponseMessage(Message):
    def __init__(self, id, leader, stamp, requestId):
        """Reply to request

            id: id of sender
            leader: id of leader
            stamp: time stamp
            requestId: request id of the request
        """
        super().__init__(id, leader, stamp)
        self.requestId = int(requestId)

    def __str__(self):
        return ('ResponseMsg {} {} {} {}'.format(
            self.sender,
            self.stamp,
            self.leader,
            self.requestId
            ))


class ConfirmElectionMessage(Message):
    def __init__(self, id, leader, stamp):
        """Broadcast message to confirm sender is leader

            id: id of sender
            leader: id of leader
            stamp: time stamp
        """
        super().__init__(id, leader, stamp)
        pass

        def __str__(self):
            return('ConfirmElectionMsg {} {} {}'.format(
                self.sender,
                self.stamp,
                self.leader
                ))


class FailureMessage(Message):
    def __init__(self, id, leader, stamp, failureVal):
        """Environment fails destination node

            id: id of sender
            leader: id of leader
            stamp: time stamp
            failureVal: True (fail) or False (operational)
        """
        super().__init__(id, leader, stamp)
        self.failureVal = failureVal

    def __str__(self):
        return('FailureMsg {} {} {} {}'.format(
            self.sender,
            self.stamp,
            self.leader,
            self.failureVal
            ))


def parse_and_construct(data):
    """Parse data string and construct message object"""

    if data.startswith("ConfirmElectionMsg"):
        data = data.split(" ")
        message = ConfirmElectionMessage(data[1], data[2], data[3])

    elif data.startswith("ShareCandidatesMsg"):
        data = data.split(" ")
        message = ShareCandidatesMessage(data[1], data[2], data[3], data[4])
        message.parse_candidates()

    elif data.startswith("ClientRequestMsg"):
        data = data.split(" ")
        message = ClientRequestMessage(data[1], data[2], data[3], data[4])

    elif data.startswith("RequestBroadcastMsg"):
        data = data.split(" ")
        message = RequestBroadcastMessage(data[1], data[2], data[3], data[4])

    elif data.startswith("FailureMsg"):
        data = data.split(" ")
        message = FailureMessage(data[1], data[2], data[3], data[4])

    elif data.startswith("ResponseMsg"):
        data = data.split(" ")
        message = ResponseMessage(data[1], data[2], data[3], data[4])

    elif data.startswith("ShareEstimatesMsg"):
        data = data.split(" ")
        message = ShareEstimatesMessage(data[1], data[2], data[3], data[4])
        message.parse_estimates()

    else:
        assert False, 'Error parsing message, received unknown {}!'.format(data)

    return message