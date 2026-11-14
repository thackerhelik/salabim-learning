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

    Methods:
        process: simulates processessing the task by holding for duration time units, this ensures that no tasks can be performed simultaneously by a machine.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.waitingline = sim.Queue('waitingline')

    def process(self):
        while True:
            while len(self.waitingline) == 0:
                self.passivate()
            self.task = self.waitingline.pop()
            # print(self.task)
            self.hold(self.task.process_duration)
            self.task.activate()
        

    # def process_task(self, duration):
    #     """
    #     Process task by holding for duration time units and then activating the job whose task it was

    #     Arguments: duration
    #     """
    #     self.job = 
    #     self.hold(duration) # Process the task => hold for duration time units
    #     self.activate(self.job)

    # def attach_agent(self, agent):
        ### Can such a method be used to attach each machine with an langgraph agent later?



class Task(sim.Component):
    """
    
    """
    def __init__(self, job_id, machine_id, process_duration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.machine_id = machine_id
        self.process_duration = process_duration

    def process_task(self): # If we name this process, then it will be activated when created which is not what we want right now.
        self.enter(machines[self.machine_id].waitingline)
        if machines[self.machine_id].ispassive():
            machines[self.machine_id].activate()
        self.passivate()
        jobs[self.job_id].activate()

class Job(sim.Component):
    """
    Represents the job which is composed of several tasks which need to be completed sequentially

    Attributes:

    Methods:

    """
    def __init__(self, tasks: list[Task], *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.tasks: list[tuple[int, int]] = tasks
        self.tasks: list[Task] = tasks

    def process(self):
        print(self.name, 'enter')
        for i in range(len(self.tasks)):
            print(self.name, i, self.tasks[i])
            self.tasks[i].activate(process='process_task')
            self.passivate()

    # def process(self):
    #     for machine_number, duration in self.tasks:
    #         # machines[machine_number](duration)
    #         self.enter(waitingline[machine_number]) # Job shouldn't enter, a task should i guess
    #         if machines[machine_number].ispassive():
    #             machines[machine_number].activate()
    #         self.passivate()

    # def populate_tasks(self, tasks):
    #     self.tasks = tasks

env = sim.Environment(trace=False)

machines = [Machine() for _ in range(NUM_MACHINES)]

# waitingline = [sim.Queue(f"waitingline_{i}") for i in range(NUM_MACHINES)] 

# jobs = [Job() for _ in range(NUM_JOBS)]

jobs = []
# Maybe can simulate this with Taskgenerator? but i guess this makes more sense to hardcode for now or take user input. easier to monitor i guess

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

env.run()

