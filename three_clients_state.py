import salabim as sim


class CustomerGenerator(sim.Component):
    def process(self):
        while True:
            Customer()
            self.hold(sim.Uniform(5, 15).sample())


class Customer(sim.Component):
    def process(self):
        self.enter(waitingline)
        worktodo.trigger(max=1) # Tells the simulation: there is work available. Wake up at most one clerk waiting for work. The trigger temporarily sets the State to True, wakes up one eligible waiter, and then restores its previous value (False by default)
        self.passivate()


class Clerk(sim.Component):
    def process(self):
        while True:
            if len(waitingline) == 0:
                self.wait((worktodo, True, 1)) # Clerk waits until the State worktodo becomes True, 1 is the waiter's request priority
            self.customer = waitingline.pop()
            self.hold(30)
            self.customer.activate()


env = sim.Environment()
CustomerGenerator()
for _ in range(3):
    Clerk()
waitingline = sim.Queue("waitingline")
worktodo = sim.State("worktodo") # worktodo is a State that initially has the value False

env.run(till=50000)
waitingline.print_histograms()
worktodo.print_histograms()