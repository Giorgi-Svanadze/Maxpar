"""library to create maximally parallel task systems"""
import threading
import time
import random
import itertools
import networkx as nx
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, wait

"""Task class definition"""
class Task:
    def __init__(self, name, reads=None, writes=None, run=None):
        self.name = name
        self.reads = reads if reads is not None else []
        self.writes = writes if writes is not None else []
        self.run = run
    def __repr__(self):
        return f"Task({self.name})"

"""TaskSystem class definition"""
class TaskSystem:
    """constructor bulds TaskSystem from tasks list and precedence dictionary"""
    def __init__(self, tasks, precedence):
        self.tasks = tasks
        self.precedence = precedence
        # task dictionary for quick lookup
        self.task_dict = {}
        #checking for duplicates
        for task in tasks:
            if task.name in self.task_dict:
                raise ValueError(f"Duplicate task found: {task.name}")
            self.task_dict[task.name] = task
        #validating the precedence dictionary if all the tasks in it exists in tasks dict
        for tname, deps in precedence.items():
            if tname not in self.task_dict:
                raise ValueError(f"Task {tname} in precedence dictionary is not defined in tasks list.")
            for dep in deps:
                if dep not in self.task_dict:
                    raise ValueError(f"Dependency {dep} for task {tname} is not defined in tasks list.")
        #creating the dependency graph (directed graph) using networkx library
        self.graph = nx.DiGraph()
        for task in tasks:
            self.graph.add_node(task.name)
        #edges are created according to precedence dictionary
        for tname, deps in precedence.items():
            for dep in deps:
                self.graph.add_edge(dep, tname)
        #conflicts are prevented by enforcing bernsteins's conditions. 
        #tasks T1 and T2 conflict if: (T1.writes intersects with (T2.reads or T2.writes)) or (T2.writes intersects with (T1.reads or T1.writes))
        task_names = list(self.task_dict.keys())
        #iterating through all possible pairs in graph
        for t1_name, t2_name in itertools.combinations(task_names, 2):
            #reads and writes sets are collected for both tasks
            t1 = self.task_dict[t1_name]
            t2 = self.task_dict[t2_name]
            t1_writes = set(t1.writes)
            t1_reads = set(t1.reads)
            t2_writes = set(t2.writes)
            t2_reads = set(t2.reads)
            #bernstein's conditions check
            conflict = (t1_writes & (t2_reads | t2_writes)) or (t2_writes & (t1_reads | t1_writes))
            #if conflict occured an arbitrary order is imposed
            if conflict:
                #check if tasks are already ordered
                if nx.has_path(self.graph, t1_name, t2_name) or nx.has_path(self.graph, t2_name, t1_name):
                    continue  #if ordered no additional edge needed
                #arbitrary order is imposed (lexicographical order is used)
                if t1_name < t2_name:
                    self.graph.add_edge(t1_name, t2_name)
                else:
                    self.graph.add_edge(t2_name, t1_name)
        #check if graph is acyclic
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Dependency graph has cycles.")
        #for use in determinism and cost tests, used global variables are being tracked
        self.globals_used = set()
        for task in tasks:
            self.globals_used.update(task.reads)
            self.globals_used.update(task.writes)
    """returns the list of tasks that must execute before task"""
    def getDependencies(self, task):
        if task not in self.graph.nodes:
            raise ValueError(f"Task {task} is not found in the task system.")
        print(f"\nAncestors of task {task}: {list(nx.ancestors(self.graph, task))}")
        #P.S. as i understood all of ancestors were needed. but if only direct predecessors were needed than the statement below is the right one
        #print(f"\nPredecessors of task {task}: {list(self.graph.predecessors(task))}")
    """executes tasks sequentially, in a topologically sorted order"""
    def runSeq(self):
        #ordering graph topologically
        order = list(nx.topological_sort(self.graph))
        # Execute tasks in order.
        for tname in order:
            task = self.task_dict[tname]
            if task.run is None:
                raise RuntimeError(f"Task {tname} does not have a run() function defined.")
            task.run()
    """executes tasks in parallel, according to precedence constraints. function uses multithreading"""
    def run(self):
        #dictionary stores the number of parents (tasks that must be completed before running each task)
        in_degrees = {node: self.graph.in_degree(node) for node in self.graph.nodes()}
        #dictionary stores number of successors (tasks which depend on each task)
        successors = {node: list(self.graph.successors(node)) for node in self.graph.nodes()}
        #initialization of synchronization
        lock = threading.Lock()
        pending_tasks = 0
        condition = threading.Condition(lock)
        #initialization of thread pool with as many threads as tasks
        executor = ThreadPoolExecutor(max_workers=len(self.graph.nodes()))
        #runs task and changes dependency information accordingly 
        def task_runner(task_name):
            #try ensures cleanup in the case of error
            try:
                #task is executed
                task = self.task_dict[task_name]
                task.run()
                #after run parents of successors are decreased since this parent finished work
                with lock:
                    for succ in successors[task_name]:
                        in_degrees[succ] -= 1
                        #if all parents are done for the successor task it is submited to execute in another thread
                        if in_degrees[succ] == 0:
                            nonlocal pending_tasks
                            pending_tasks += 1
                            executor.submit(task_runner, succ)
            #if pending tasks is empty notifies the waiting condition so run can proceed and ensures that pending tasks will be decremented in the case of execution fail
            finally:
                with lock:
                    pending_tasks -= 1
                    if pending_tasks == 0:
                        condition.notify_all()
        #finds a tasks without parents (initial tasks) and starts them
        with lock:
            initial_tasks = [node for node, deg in in_degrees.items() if deg == 0]
            pending_tasks = len(initial_tasks)
            for task_name in initial_tasks:
                executor.submit(task_runner, task_name)
        #main thread waits before all the tasks are done
        with lock:
            while pending_tasks > 0:
                condition.wait()
        #shuts down the thread pool
        executor.shutdown(wait=True)
    """randomized determinism test"""
    #randomizes the initial values for all global variables for each iteration, then runs the parallel system few times with the same starting state
    #if the final global state is different between runs, then the task system is nondeterministic
    def detTestRnd(self, iterations=5, runs_per_iteration=3):
        nondet = False
        results = []
        for it in range(iterations):
            #random initial states are prepared for all globals used
            init_state = {var: random.randint(0, 100) for var in self.globals_used}
            run_results = []
            #multiple runs for each iteration
            for run_num in range(runs_per_iteration):
                #current globals are saved to restore later
                saved_state = {var: globals().get(var, None) for var in self.globals_used}
                #globals are set to the random initial state
                for var, value in init_state.items():
                    globals()[var] = value
                #parallel execution
                self.run()
                #capturing the final state of variables
                final_state = {var: globals().get(var, None) for var in self.globals_used}
                run_results.append(final_state)
                #globals are restored, so each run starts from the same state
                for var, value in saved_state.items():
                    globals()[var] = value
            #results from different runs are compared
            first = run_results[0]
            for res in run_results[1:]:
                if res != first:
                    print(f"Iteration {it}: Nondeterministic results found: {run_results}")
                    nondet = True
                    break
            results.append((init_state, run_results))
        if not nondet:
            print("Test is passed.")
    """compares execution time of sequential and parallel runs. system is run few times and then average times are computed."""
    def parCost(self, iterations=5):
        globals_used = self.globals_used
        #resets the globals for initial state
        init_state = {var: 0 for var in globals_used}
        seq_times = []
        par_times = []
        #executes both types of run few times
        for i in range(iterations):
            #current globals are captured
            saved_state = {var: globals().get(var, None) for var in globals_used}
            #resets globals to initial state.
            for var, value in init_state.items():
                globals()[var] = value
            #sequential run timing
            start = time.perf_counter()
            self.runSeq()
            end = time.perf_counter()
            seq_times.append(end - start)

            #globals are restored to saved state
            for var, value in saved_state.items():
                globals()[var] = value
            #globals are reset to the initial state
            for var, value in init_state.items():
                globals()[var] = value
            #parallel run timing
            start = time.perf_counter()
            self.run()
            end = time.perf_counter()
            par_times.append(end - start)
            #globals are restored to saved state
            for var, value in saved_state.items():
                globals()[var] = value
        #calculation of averages
        avg_seq = sum(seq_times) / iterations
        avg_par = sum(par_times) / iterations
        print(f"Average sequential run time over {iterations} iterations: {avg_seq:.6f} seconds")
        print(f"Average parallel run time over {iterations} iterations:   {avg_par:.6f} seconds")
    """displays the dependency graph"""
    def draw(self):
        plt.figure(figsize=(8, 6))
        pos = nx.spring_layout(self.graph)
        nx.draw_networkx(self.graph, pos, with_labels=True, node_color='lightblue', edge_color='gray', node_size=1500)
        plt.title("Maxpar Dependency Graph")
        plt.axis('off')
        plt.show()
