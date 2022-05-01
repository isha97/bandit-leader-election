import ast
import time


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
        return('[Message]ShareEstimatesMsg {} {} {} {}'.format(
            self.sender,
            self.leader,
            self.stamp,
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
        candidate_list = ','.join(str(i) for i in self.candidates)
        return('[Message]ShareCandidatesMsg {} {} {} [{}]'.format(
            self.sender,
            self.leader,
            self.stamp,
            candidate_list
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
        return ('[Message]ClientRequestMsg {} {} {} {}'.format(
            self.sender,
            self.leader,
            self.stamp,
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
        return ('[Message]RequestBroadcastMsg {} {} {} {}'.format(
            self.sender,
            self.leader,
            self.stamp,
            self.requestId
            ))

class ReplyBroadcastMessage(Message):
    def __init__(self, id, leader, stamp, requestId):
        """reply to the broadcast message

            id: id of sender
            leader: id of leader
            stamp: time stamp
            requestId: request id of the request
        """
        super().__init__(id, leader, stamp)
        self.requestId = int(requestId)

    def __str__(self):
        return ('[Message]ReplyBroadcastMsg {} {} {} {}'.format(
            self.sender,
            self.leader,
            self.stamp,
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
        return ('[Message]ResponseMsg {} {} {} {}'.format(
            self.sender,
            self.leader,
            self.stamp,
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
        return('[Message]ConfirmElectionMsg {} {} {}'.format(
            self.sender,
            self.leader,
            self.stamp
            ))

class NewLeaderMessage(Message):
    def __init__(self, id, leader, stamp):
        """Broadcast message to confirm sender is leader

            id: id of sender
            leader: id of leader
            stamp: time stamp
        """
        super().__init__(id, leader, stamp)
        pass

    def __str__(self):
        return('[Message]NewLeaderMsg {} {} {}'.format(
            self.sender,
            self.leader,
            self.stamp
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
        return('[Message]FailureMsg {} {} {} {}'.format(
            self.sender,
            self.stamp,
            self.leader,
            self.failureVal
            ))

class PingMessage(Message):
    def __init__(self, id, leader, stamp):
        """ping message to other nodes

            id: id of sender
            leader: id of leader
            stamp: time stamp
        """
        super().__init__(id, leader, stamp)

    def __str__(self):
        return('[Message]PingMsg {} {} {}'.format(
            self.sender,
            self.leader,
            self.stamp
            ))


class PingReplyMessage(Message):
    def __init__(self, id, leader, stamp):
        """Reply to ping message received by other node

            id: id of sender
            leader: id of leader
            stamp: time stamp
        """
        super().__init__(id, leader, stamp)

    def __str__(self):
        return('[Message]PingReplyMsg {} {} {}'.format(
            self.sender,
            self.leader,
            self.stamp
            ))


def parse_and_construct(data):
    """Parse data string and construct message object"""

    if data.startswith("[Message]ConfirmElectionMsg"):
        data = data.split(" ")
        message = ConfirmElectionMessage(data[1], data[2], data[3])

    elif data.startswith("[Message]ShareCandidatesMsg"):
        data = data.split(" ")
        message = ShareCandidatesMessage(data[1], data[2], data[3], data[4])
        message.parse_candidates()

    elif data.startswith("[Message]ClientRequestMsg"):
        data = data.split(" ")
        message = ClientRequestMessage(data[1], data[2], data[3], data[4])

    elif data.startswith("[Message]RequestBroadcastMsg"):
        data = data.split(" ")
        message = RequestBroadcastMessage(data[1], data[2], data[3], data[4])

    elif data.startswith("[Message]FailureMsg"):
        data = data.split(" ")
        message = FailureMessage(data[1], data[2], data[3], data[4])

    elif data.startswith("[Message]ResponseMsg"):
        data = data.split(" ")
        message = ResponseMessage(data[1], data[2], data[3], data[4])

    elif data.startswith("[Message]ShareEstimatesMsg"):
        data = data.split(" ")
        message = ShareEstimatesMessage(data[1], data[2], data[3], data[4])
        message.parse_estimates()

    elif data.startswith("[Message]PingMsg"):
        data = data.split(" ")
        message = PingMessage(data[1], data[2], data[3])

    elif data.startswith("[Message]PingReplyMsg"):
        data = data.split(" ")
        message = PingReplyMessage(data[1], data[2], data[3])

    elif data.startswith("[Message]ReplyBroadcastMsg"):
        data = data.split(" ")
        message = ReplyBroadcastMessage(data[1], data[2], data[3], data[4])

    elif data.startswith("[Message]NewLeaderMsg"):
        data = data.split(" ")
        message = NewLeaderMessage(data[1], data[2], data[3])

    else:
        # Error parsing message, received unknown
        message = None

    return message