import salabim as sim

class Comp(sim.Component):
    def process(self):
        mylevel = sim.Monitor('level', level=True, initial_tally=0)

        mylevel.tally(4)
        self.hold(1)
        mylevel.tally(8)
        self.hold(1)
        mylevel.tally(10)
        print(mylevel()) # Gets the last tallied value (or also with Monitor.get())
        print(mylevel.get())

        # To get the value a particular time
        print(mylevel.get(1))
        print(mylevel(1))



env = sim.Environment()
Comp()
env.run()