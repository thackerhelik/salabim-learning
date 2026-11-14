import salabim as sim


class Customer(sim.Component):
    def process(self):
        self.enter(waitingline)
        for clerk in clerks:
            if clerk.ispassive():
                clerk.activate()
                break # activate at most one clerk
        self.passivate()


class Clerk(sim.Component):
    def process(self):
        while True:
            while len(waitingline) == 0:
                self.passivate()
            self.customer = waitingline.pop()
            self.hold(30)
            self.customer.activate()


env = sim.Environment(trace=True)
env.ComponentGenerator(Customer, iat=env.Uniform(5, 15), force_at=True)
#sim.ComponentGenerator(Customer, iat=env.Uniform(5, 15), at=10, till=30, number=10, force_at=True) generates maximum 10 customers according to uniform arrival from t=10 to t=30, first arrival forced at t=10 

clerks = [Clerk() for _ in range(3)]

waitingline = env.Queue("waitingline")

env.run(till=50000)
waitingline.print_histograms()

waitingline.print_info()