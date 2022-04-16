import ast
class Message():
    def __init__(self, id, step=None):
        """Base message class with just sender id

            id: id of sender
            step: time step
        """
        self.sender = id
        self.step = step


class EstimatesMessage(Message):
    def __init__(self, id, step, estimates):
        """Share you estimates with destination

            id: id of sender
            step: time step
            estimates: np.array of all node failure estimates
        """
        super().__init__(int(id), step)
        self.estimates = estimates

    def __str__(self):
        return('EstimateMsg {} {} {}'.format(self.sender, self.step, self.estimates))


class CandidateMessage(Message):
    def __init__(self, id, step, candidates):
        """Share you candidates with destination

            id: id of sender
            step: time step
            candidates: np.array of all node failure candidates
        """
        super().__init__(int(id), step)
        self.candidates = candidates

    def parse_candidates(self):
        self.candidates = ast.literal_eval(self.candidates)

    def __str__(self):
        return('CandidateMsg {} {} {}'.format(self.sender, self.step, self.candidates))


class RequestMessage():
    def __init__(self, requestId):
        """client expecting reply

            requestId: request Id of the request
        """
        self.requestId = int(requestId)

    def __str__(self):
        return ('RequestMsg {}'.format(self.requestId))

class RequestBroadcastMessage():
    def __init__(self, id, requestId):
        """Reply to the client

            id: id of sender
            requestId: request id of the request
        """
        self.sender = id
        self.requestId = requestId


    def __str__(self):
        return ('RequestBroadcastMsg {} {}'.format(self.sender, self.requestId))


class ResponseBroadcastMessage():
    def __init__(self):
        """Ping destination expecting reply

            id: id of sender
            step: time step
        """
        pass

    def __str__(self):
        return ('ResponseBroadcastMsg')


class ResponseMessage():
    def __init__(self, id, requestId):
        """Reply to the client

            id: id of sender
            requestId: request id of the request
        """
        self.sender = id
        self.requestId = requestId

    def __str__(self):
        return ('ResponseMsg {} {}'.format(self.sender, self.requestId))


class ConfirmElectionMessage(Message):
    def __init__(self, id, step=None):
        """Broadcast message to confirm sender is leader

            id: id of sender
            step: time step
        """
        super().__init__(int(id), step)
        pass

        def __str__(self):
            return('ConfirmElectionMsg {} {}'.format(self.id, self.step))

class FailureMessage():
    def __init__(self, failureVal):
        """Share you candidates with destination

            id: id of sender
            step: time step
            candidates: np.array of all node failure candidates
        """
        self.failureVal = failureVal

    def __str__(self):
        return('FailureMsg {}'.format(self.failureVal))