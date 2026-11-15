"""
jobshop.py

Simulates a job shop scheduling problem. See https://developers.google.com/optimization/scheduling/job_shop for reference to the problem.


There are NUM_MACHINES number of machines, and NUM_JOBS number of jobs, each having at max NUM_MAX_TASKS number of tasks. Each task is a tuple with (machine number, processing time). 
"""
import salabim as sim

# Hyperparameters
NUM_MACHINES = 3
NUM_JOBS = 3
NUM_MAX_TASKS = 5


class Machine(sim.Component):
    """
    Represents the machine which is responsible for completing the task

    Attributes:
        waitingline: queue associated with this machine which has the tasks which need to be processed by this machine.

    Methods:
        __init__: used for initializing the queue 'waitingline'
        process: simulates processessing the task by holding for duration time units, this ensures that no tasks can be performed simultaneously by a machine.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.waitingline = sim.Queue('waitingline')

    def process(self):
        """
        Process task by holding for duration time units and then activating the job whose task it was

        Arguments: N/A
        """
        while True:
            while len(self.waitingline) == 0:
                self.passivate()
            self.task = self.waitingline.pop()
            print(self.name, " processing ", self.task, " for ", self.task.process_duration, " time units ")
            self.hold(self.task.process_duration)
            self.task.activate()

    # def attach_agent(self, agent):
        ### Can such a method be used to attach each machine with an langgraph agent later?



class Task(sim.Component):
    """
    Represents the task.

    Attributes:
        job_id: The job id which has this particular task
        machine_id: The machine_id which this task needs to be processed on.
        process_duration: The processing duration of this task.

    Methods:
        __init__: initializes the job_id, machine_id and process_duration.
        process_task: Send the task to the machine.
    """

    def __init__(self, job_id, machine_id, process_duration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.machine_id = machine_id
        self.process_duration = process_duration

    def process_task(self): # If we name this process, then it will be activated when created which is not what we want right now.
        """
        Puts the task to queue for processing by machine. Activates the machine if it is passive, then passivates itself. Once the task is complete activate the job component which is associated with this task.
        """
        self.enter(machines[self.machine_id].waitingline)
        if machines[self.machine_id].ispassive():
            machines[self.machine_id].activate()
        self.passivate()
        jobs[self.job_id].activate()


class Job(sim.Component):
    """
    Represents the job which is composed of several tasks which need to be completed sequentially

    Attributes:
        self.tasks: The list of tasks which comprise this job.

    Methods:
        __init__: Initializes the list of tasks.
        process: Processes each task in order by activating the the task process_task and passivates itself so that next task is only activated when the current task is finished.
        
    """
    def __init__(self, tasks: list[Task], *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.tasks: list[tuple[int, int]] = tasks
        self.tasks: list[Task] = tasks

    def process(self):
        """
            Processes each task in order by activating the the task process_task and passivates itself so that next task is only activated when the current task is finished.
        """
        for i in range(len(self.tasks)):
            self.tasks[i].activate(process='process_task')
            self.passivate()


env = sim.Environment(trace=False)#, time_unit='seconds')

machines = [Machine() for _ in range(NUM_MACHINES)]

jobs: list[Job] = []
# Maybe can simulate this with Taskgenerator? but i guess this makes more sense to hardcode for now or take user input. easier to monitor i guess - or just some random task generator. Don't think TaskGenerator is required since we don't probably want tasks to be made on the fly but known from before

# task(i, j) task j for job i. Pass job_id, machine_id, duration

# Job 0
task00 = Task(0, 0, 3)
task01 = Task(0, 1, 2)
task02 = Task(0, 2, 2)
jobs.append(Job([task00, task01, task02]))

# Job 1
task10 = Task(1, 0, 2)
task11 = Task(1, 2, 1)
task12 = Task(1, 1, 4)
jobs.append(Job([task10, task11, task12]))

# Job 2
task20 = Task(2, 1, 4)
task21 = Task(2, 2, 3)
jobs.append(Job([task20, task21]))

print(task00.name, task01.name, task02.name, task10.name, task11.name, task12.name, task20.name, task21.name)

# col = ['blue', 'red', 'green']
for id, machine in enumerate(machines):
    sim.AnimateQueue(machine.waitingline, x=100, y=230-100*id, title=f"machine {id} waiting queue", direction='e') #, id=col[id]) for color ned sim.AnimateRectangle or something?

for id, machine in enumerate(machines):
    sim.AnimateMonitor(machine.waitingline.length, x=10, y=550-130*id, width=480, height=100, horizontal_scale=5, vertical_scale=5, title=f"Length of waiting line {id}")

# Add animation
env.animate(True)
env.modelname('Jobshop')

env.run()


# Print statistics from monitors
for id, machine in enumerate(machines):
    print(f"----- MACHINE {id} -------\n")
    machine.waitingline.print_histograms()