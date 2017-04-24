import blinker


class Signalman:
    def __init__(self):
        for sig in self.signals:
            setattr(self, sig, blinker.Signal())

