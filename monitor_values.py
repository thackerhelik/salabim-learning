import salabim as sim

env = sim.Environment()

monitor_names = sim.Monitor(name='names')

for _ in range(10000):
    name = sim.Pdf(('John', 30, 'Peter', 20, 'Mike', 20, 'Andrew', 20, 'Ruud', 5, 'Jan', 5)).sample() # Sample a name according to the distribution
    monitor_names.tally(name) # Record which name comes (keep track of how many times each distinct name comes)

monitor_names.print_histogram(values=True)
monitor_names.print_histogram(values=('John', 'Andrew', 'Ruud', 'Fred'))
monitor_names.print_histogram(values=True, sort_on_weight=True) # Sort the histogram on the weight (number of entries) of the value