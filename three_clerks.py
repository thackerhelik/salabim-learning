# Bank, 3 clerk
# Example of a critically loaded state system

import salabim as sim

class CustomerGenerator(sim.Component):
    def process(self):
        while True:
            Customer()
            self.hold(sim.Uniform(5, 15).sample()) # will do the statistical sampling and wait for that time till the next customer is created

class Customer(sim.Component):
    def process(self):
        self.enter(waitingline) # The customer places itself at the tail of the waiting line
        for clerk in clerks:
            if clerk.ispassive(): # The customer then checks whether the clerk is idle, and if so, activates him immediately
                clerk.activate()
                break # activate at most one clerk
        self.passivate()

class Clerk(sim.Component):
    def process(self):
        while True:
            while len(waitingline) == 0:
                self.passivate()
            self.customer = waitingline.pop() # Get the first customer out of the waiting line
            self.hold(30) # Holds for 30 time units
            self.customer.activate() # After that hold, the customer is activated and will terminate


env = sim.Environment(trace = False)

CustomerGenerator()
clerks = [Clerk() for _ in range(3)] # Can also use salabim queue instead

waitingline = sim.Queue("waitingline")

env.run(till=50000)
waitingline.print_histograms()
waitingline.print_info()