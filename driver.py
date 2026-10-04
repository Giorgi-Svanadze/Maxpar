"""driver file to demonstrate work of maxpar.py"""
from maxpar import Task, TaskSystem
import time

#global varables
A = None
B = None
C = None
D = None
E = None
F = None
G = None
H = None
I = None
J = None

#run functions of tasks
def runT1():
    global A
    time.sleep(0.1) #simulation of work
    A = 10
def runT2():
    global B
    time.sleep(0.1)
    B = 20
def runT3():
    global C
    time.sleep(0.1)
    C = 30
def runT4():
    global D
    time.sleep(0.2)
    D = A + B
def runT5():
    global E
    time.sleep(0.2)
    E = B + C
def runT6():
    global F
    time.sleep(0.1)
    F = D * 2
def runT7():
    global G
    time.sleep(0.2)
    G = E * 2
def runT8():
    global H
    time.sleep(0.3)
    H = F + G
def runT9():
    global I
    time.sleep(0.1)
    I = H - 5
def runT10():
    global J
    time.sleep(0.2)
    J = I * 3

#list of tasks
tasks = [
    Task(name="T1", writes=["A"], run=runT1),
    Task(name="T2", writes=["B"], run=runT2),
    Task(name="T3", writes=["C"], run=runT3),
    Task(name="T4", reads=["A", "B"], writes=["D"], run=runT4),
    Task(name="T5", reads=["B", "C"], writes=["E"], run=runT5),
    Task(name="T6", reads=["D"], writes=["F"], run=runT6),
    Task(name="T7", reads=["E"], writes=["G"], run=runT7),
    Task(name="T8", reads=["F", "G"], writes=["H"], run=runT8),
    Task(name="T9", reads=["H"], writes=["I"], run=runT9),
    Task(name="T10", reads=["I"], writes=["J"], run=runT10),
]

#precedence dictionary
precedence = {
    "T1": [],
    "T2": [],
    "T3": [],
    "T4": ["T1", "T2"],
    "T5": ["T2", "T3"],
    "T6": ["T4"],
    "T7": ["T5"],
    "T8": ["T6", "T7"],
    "T9": ["T8"],
    "T10": ["T9"],
}

#task system creation
task_system = TaskSystem(tasks, precedence)

#example usage of getDependencies
task_system.getDependencies("T8")

#sequential run
A = B = C = D = E = F = G = H = I = J = None
task_system.runSeq()
print(f"\nSequential results: A={A}, B={B}, C={C}, D={D}, E={E}, F={F}, G={G}, H={H}, I={I}, J={J}")

#parallel run
A = B = C = D = E = F = G = H = I = J = None
task_system.run()
print(f"\nParallel results: A={A}, B={B}, C={C}, D={D}, E={E}, F={F}, G={G}, H={H}, I={I}, J={J}")

#randomized determinism test
print("\nRandomized determinism test result:")
task_system.detTestRnd(iterations=3, runs_per_iteration=3)

#execution times comparison
print("\nComparision of times:")
task_system.parCost(iterations=5)

#dependency graph visualization
task_system.draw()