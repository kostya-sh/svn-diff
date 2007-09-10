"""
  Very simple scheduler.
  Calls given function
  
  TODO: docs, tests
"""

from threading import Thread, Event

class Scheduler(Thread):
    """Call a function regularly:

    s = Scheduler(30.0, f, args=[], kwargs={})
    s.start()
    s.cancel() # stop the scheduler
    """

    def __init__(self, interval, function, args=[], kwargs={}):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.finished = Event()

    def cancel(self):
        """Stop the scheduler"""
        self.finished.set()

    def run(self):
        while True:        
            if not self.finished.isSet():
                self.function(*self.args, **self.kwargs)
            else:
                break
            self.finished.wait(self.interval)
