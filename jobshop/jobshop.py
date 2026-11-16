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

tasks_animations = []

# Animation
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800 
machine_positions = []

def calculate_machine_layout(total_width, n, gap):
    square_width = (total_width - (n + 1) * gap) / n

    positions = []

    for i in range(n):
        x = gap + i * (square_width + gap)
        positions.append((x, square_width))

    return positions


class Machine(sim.Component):
    """
    Represents the machine which is responsible for completing the task

    Attributes:
        waitingline: queue associated with this machine which has the tasks which need to be processed by this machine.

    Methods:
        __init__: used for initializing the queue 'waitingline'
        process: simulates processessing the task by holding for duration time units, this ensures that no tasks can be performed simultaneously by a machine.
    """

    def __init__(self, machine_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.machine_id = machine_id
        self.waitingline = sim.Queue('waitingline')
        sim.AnimateRectangle(spec = (machine_positions[self.machine_id][0], 500, machine_positions[self.machine_id][0] + machine_positions[self.machine_id][1], 600), linecolor="red", fillcolor="", linewidth=2)
        self.an_text = sim.AnimateText(text=f"Machine {self.machine_id}: idle", x = machine_positions[self.machine_id][0], y = 600+10, textcolor='fg')

    def process(self):
        """
        Process task by holding for duration time units and then activating the job whose task it was

        Arguments: N/A
        """
        while True:
            while len(self.waitingline) == 0:
                self.passivate()
            self.task = self.waitingline.pop()
            print(self.name, " processing ", self.task, " for ", self.task.process_duration, " time units -- current time ", env.now())
            print("ID: ", self.machine_id)
            tasks_animations[self.task.task_id].fillcolor = "lime"
            AnimateMachineProgress(self.machine_id, env.now(), self.task.process_duration)
            self.an_text.text = f"Machine {self.machine_id}: processing task {self.task.task_id}"
            self.hold(self.task.process_duration)
            self.an_text.text = f"Machine {self.machine_id}: idle"
            print(self.name, " finished ", self.task, " current time ", env.now())
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

    def __init__(self, task_id, job_id, machine_id, process_duration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = task_id
        self.job_id = job_id
        self.machine_id = machine_id
        self.process_duration = process_duration

    def process_task(self): # If we name this process, then it will be activated when created which is not what we want right now.
        """
        Puts the task to queue for processing by machine. Activates the machine if it is passive, then passivates itself. Once the task is complete activate the job component which is associated with this task.
        """
        self.enter(machines[self.machine_id].waitingline)
        tasks_animations[self.task_id].fillcolor = "yellow"
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
    def __init__(self, job_id, tasks: list[Task], *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.tasks: list[tuple[int, int]] = tasks
        self.job_id = job_id
        self.tasks: list[Task] = tasks
        self.an_text = sim.AnimateText(text=f"Job {self.job_id}: ", x = 25, y = 400-100*self.job_id, textcolor='fg')
        for i, task in enumerate(self.tasks):
            tasks_animations[task.task_id] = sim.AnimateRectangle(spec=(125+75*i, 400-100*self.job_id,175+75*i, 450-100*self.job_id), fillcolor="red")
        # sim.AnimateRectangle(spec = (machine_positions[self.machine_id][0], 500, machine_positions[self.machine_id][0] + machine_positions[self.machine_id][1], 600), linecolor="red", fillcolor="", linewidth=2)

    def process(self):
        """
            Processes each task in order by activating the the task process_task and passivates itself so that next task is only activated when the current task is finished.
        """
        for task in self.tasks:
            task.activate(process='process_task')
            self.passivate()
            tasks_animations[task.task_id].fillcolor = "green"


# Animation Classes
class AnimateMachineProgress(sim.AnimateRectangle):
    def __init__(self, machine_id, start_time, process_duration):
        sim.AnimateRectangle.__init__(
            self,
            fillcolor="green"
        )
        self.machine_id = machine_id
        self.start_time = start_time
        self.process_duration = process_duration

    def spec(self, t):
        # return (50, 500, max(50, 150- ((150-50)/self.process_duration)*t), 600)
        return (machine_positions[self.machine_id][0], 500, machine_positions[self.machine_id][0] + machine_positions[self.machine_id][1]*(1.0 - (t - self.start_time)/self.process_duration), 600)

    def keep(self, t):
        if (t - self.start_time >= self.process_duration):
            return False
        return True


env = sim.Environment(trace=False)#, time_unit='seconds')

machine_positions = calculate_machine_layout(SCREEN_WIDTH, NUM_MACHINES, 50)
machines = [Machine(i) for i in range(NUM_MACHINES)]


jobs: list[Job] = []
# Maybe can simulate this with Taskgenerator? but i guess this makes more sense to hardcode for now or take user input. easier to monitor i guess - or just some random task generator. Don't think TaskGenerator is required since we don't probably want tasks to be made on the fly but known from before

# task(i, j) task j for job i. Pass job_id, machine_id, duration

# Job 0
task00 = Task(0, 0, 0, 3)
task01 = Task(1, 0, 1, 2)
task02 = Task(2, 0, 2, 2)

# Job 1
task10 = Task(3, 1, 0, 2)
task11 = Task(4, 1, 2, 1)
task12 = Task(5, 1, 1, 4)

# Job 2
task20 = Task(6, 2, 1, 4)
task21 = Task(7, 2, 2, 3)

tasks_animations = [None]*8

jobs.append(Job(job_id=0, tasks=[task00, task01, task02]))
jobs.append(Job(job_id=1, tasks=[task10, task11, task12]))
jobs.append(Job(job_id=2, tasks=[task20, task21]))

print(task00.name, task01.name, task02.name, task10.name, task11.name, task12.name, task20.name, task21.name)

# TODO: 1. Color for tasks? 2. Show the processing task too not just in queue task, Figure out how to do that. 3. Better represent task in animation (maybe if we can show processing time and id of task or something) 

# col = ['blue', 'red', 'green']
# for id, machine in enumerate(machines):
#     sim.AnimateQueue(machine.waitingline, x=100, y=230-100*id, title=f"machine {id} waiting queue", direction='e') #, id=col[id]) for color ned sim.AnimateRectangle or something?

# for id, machine in enumerate(machines):
#     sim.AnimateMonitor(machine.waitingline.length, x=10, y=550-130*id, width=480, height=100, horizontal_scale=5, vertical_scale=5, title=f"Length of waiting line {id}")


# for id, machine in enumerate(machines):
#     sim.AnimateRectangle(spec = (50 + 400*id, 500, 150 + 400*id, 600), linecolor="red", fillcolor="", linewidth=2)


# Add animation
env.animate(True)
env.width(SCREEN_WIDTH)
env.height(SCREEN_HEIGHT)
env.modelname('Jobshop')

env.run()


# Print statistics from monitors
for id, machine in enumerate(machines):
    print(f"----- MACHINE {id} -------\n")
    machine.waitingline.print_histograms()