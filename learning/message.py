class Message():
    def __init__(self, id, step):
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
        super().__init__(id, step)
        self.estimates = estimates

    def __str__(self):
        return('From: {} @ {} \t Estimates: {}'.format(self.sender, self.step, self.estimates))


class CandidateMessage(Message):
    def __init__(self, id, step, candidates):
        """Share you candidates with destination

            id: id of sender
            step: time step
            candidates: np.array of all node failure candidates
        """
        super().__init__(id, step)
        self.candidates = candidates

    def __str__(self):
        return('From: {} @ {} \t Candidates: {}'.format(self.sender, self.step, self.candidates))


class PingMessage(Message):
    def __init__(self, id, step):
        """Ping destination expecting reply

            id: id of sender
            step: time step
        """
        super().__init__(id, step)
        pass


class ReplyPingMessage(Message):
    def __init__(self, id, step):
        """Reply to Ping message

            id: id of sender
            step: time step
        """
        super().__init__(id, step)
        pass


class ConfirmElectionMessage(Message):
    def __init__(self, id, step):
        """Broadcast message to confirm sender is leader

            id: id of sender
            step: time step
        """
        super().__init__(id, step)
        pass