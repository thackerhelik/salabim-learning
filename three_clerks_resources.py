# Bank, 3 clerks with resources
import salabim as sim

class CustomerGenerator(sim.Component):
    def process(self):
        while True:
            Customer()
            self.hold(sim.Uniform(5, 15).sample())


class Customer(sim.Component):
    def process(self):
        self.request(clerks)
        self.hold(30)
        self.release() # not really required (good practise in general, but in this case the process terminates so resources are automatically released anyway)


env = sim.Environment(trace=True)
CustomerGenerator()
clerks = sim.Resource("clerks", capacity=3)

env.run(till=500)

clerks.print_statistics()
clerks.print_info()

clerks.requesters().print_statistics()
clerks.claimers().print_statistics()