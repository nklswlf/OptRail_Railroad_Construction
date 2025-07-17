
"""
===============================================================================
                           CONSTRUCTIVE HEURISTIC MODULE
===============================================================================

This module implements comprehensive constructive heuristics for generating 
initial feasible solutions in the OptRail railroad construction scheduling 
optimization system. It provides multiple greedy algorithms that systematically 
build solutions by intelligently assigning resources (workers, machines, 
attachments) to construction tasks while respecting complex constraints.

CORE FUNCTIONALITY:
------------------
1. Greedy Algorithm Framework
   - Worker-Greedy: Resource-centric approach starting with workers
   - Order-Item-Greedy: Task-centric approach starting with order items
   - Configurable attractiveness functions for resource selection
   - Systematic constraint validation and feasibility checking

2. Resource Assignment Strategies
   - Multi-criteria attractiveness evaluation for workers, machines, attachments
   - Predecessor/successor relationship management for task sequencing
   - Dynamic resource activation tracking and optimization
   - Intelligent tie-breaking mechanisms with randomization

3. Constraint Management
   - Maximum working hours per worker validation
   - Consecutive night shift limitations
   - Maximum shifts within time periods
   - Resource capacity and availability constraints
   - Temporal ordering and precedence relationships

4. Solution Construction Process
   - Systematic route plan generation for all resource types
   - Feasibility validation at each assignment step
   - Rollback mechanisms for infeasible assignments
   - Complete solution evaluation and validation

"""

# Imports for data structures and evaluation logic
from Code.OutputData import *
from Code.InputData import *
from Code.EvaluationLogic import *
from copy import deepcopy

class ConstructiveHeuristics:
    """
    Class for implementing various constructive heuristics for the railroad optimization problem.
    
    This class implements two different greedy algorithms:
    1. Worker-Greedy: Starts with workers and assigns tasks to them step by step
    2. Order-Item-Greedy: Starts with tasks and assigns resources to them step by step
    
    Both algorithms use attractiveness functions to evaluate and select the best
    assignments between workers, machines, attachments, and tasks.
    """

    def __init__(self, evaluationLogic: EvaluationLogic, rng):
        """
        Initializes the constructive heuristic with evaluation logic and random generator.
        
        Args:
            evaluationLogic: Object for evaluating solutions
            rng: Random generator for tie-breaking when attractiveness values are equal
        """
        self.EvaluationLogic = evaluationLogic  # Logic for solution evaluation
        self.RNG = rng  # Random generator for stochastic decisions

        # Initialization of route plans for different resource types
        self.route_plan_worker = dict()      # Assignment of tasks to workers
        self.route_plan_machine = dict()     # Assignment of tasks to machines
        self.route_plan_attachment = dict()  # Assignment of tasks to attachments



    def Run(self, input_data: InputData, greedy_technique: dict):
        """
        Main method for executing the constructive heuristic.
        
        Selects between different greedy algorithms based on configuration
        and executes the corresponding algorithm.
        
        Args:
            input_data: Input data with orders, workers, machines etc.
            greedy_technique: Dictionary with algorithm configuration
            
        Returns:
            Solution: The generated initial solution
        """
        self.data = input_data  # Store input data

        # Extract the name of the greedy technique from configuration
        self.GreedyTechnique = next(iter(greedy_technique))
        settings = greedy_technique[self.GreedyTechnique]

        print(f"\nFinding initial solution with {self.GreedyTechnique}...")

        # Selection and execution of the corresponding algorithm
        if self.GreedyTechnique == "worker_greedy":
            # Configuration for Worker-Greedy algorithm
            self.order_item_attractiveness_technique = settings['order_item_attractiveness_technique']
            self.machine_attractiveness_technique = settings['machine_attractiveness_technique']
            start_solution = self.WorkerGreedy()

        elif self.GreedyTechnique == "order_item_greedy":
            # Configuration for Order-Item-Greedy algorithm
            self.worker_attractiveness_technique = settings['worker_attractiveness_technique']
            self.machine_attractiveness_technique = settings['machine_attractiveness_technique']
            start_solution = self.OrderItemGreedy()

        return start_solution

    

    def WorkerGreedy(self):
        """
        Worker-centered greedy heuristic for creating an initial solution.
        
        This algorithm iterates through all available workers and assigns each
        worker the most attractive available tasks step by step.
        
        The algorithm follows a sequential assignment approach:
        1. Iterate through all workers
        2. For each worker, find most attractive available order items
        3. For selected order item, find best machine
        4. For selected order item, find best attachments
        5. Continue until worker is overloaded or no tasks available
        
        Returns:
            Solution: Feasible solution or Exception if infeasible
        """

        # Create dictionary with active orders and their tasks
        greedy_order_items = dict()
        for order in self.data.orders:
            if order.status == True:  # Only consider active orders
                greedy_order_items[order] = [order_item for order_item in self.data.order_items 
                                           if order_item.order_number == order.order_number]

        # Initialize route plans for all resource types
        route_plan_worker = dict()      # Workers -> List of task IDs
        route_plan_machine = dict()     # Machines -> List of task IDs  
        route_plan_attachment = dict()  # Attachments -> List of task IDs

        # Tracking dictionary for already planned machines (for attractiveness calculation)
        machine_planned = dict()
        for machine in self.data.machines:
            machine_planned[machine] = False
            route_plan_machine[machine.id] = list()

        # Tracking dictionary for already planned attachments
        attachment_planned = dict()
        for attachment in self.data.attachments:
            attachment_planned[attachment] = False
            route_plan_attachment[attachment.id] = list()
            
        # Main loop: Iterate through all workers and plan their routes
        for worker in self.data.workers:
            
            # Initialize worker-specific variables
            attractiveness = dict()                    # Attractiveness values for available tasks
            route_plan_worker[worker.personal_number] = list()  # Empty route for current worker
            current_consecutive_night_shifts = 0       # Counter for consecutive night shifts
            current_shifts_in_time_period = list()     # List of shifts in current time window

            # Calculate initial attractiveness for first task assignment
            for order, order_items in greedy_order_items.items():
                for order_item in order_items:
                    # Check if task can be assigned to the worker
                    if any(order_item in value_list for value_list in worker._possible_order_items.values()):
                        if order_item not in self.data.planned_shifts_worker[order]:
                            # Calculate time difference to project start (in days)
                            time_difference = order_item.start_time - self.data.start_date
                            time_difference = time_difference.total_seconds() / self.data._seconds_a_day
                            
                            # Attractiveness function: Considers dynamic progress and time difference
                            # Optional extension with order priority (commented out)
                            attractiveness[order_item] = {
                                "dynamic_percentage": order.dynamic_percentage,  # Progress of the order
                                "time_difference": time_difference               # Temporal proximity to start
                            }

            # Activate attractiveness function or skip worker if no tasks available
            if len(attractiveness) > 0:
                sorted_attractiveness = self.order_item_attractiveness_function(attractiveness)
            else:
                continue  # Next worker

            # Index for iteration through sorted tasks (if a task cannot be assigned)
            index = 0

            # Main loop for task assignment to current worker
            # Continue until worker is overloaded or no more tasks available
            while worker.work_hours <= self.data._max_working_hours and len(attractiveness) > 0:
                # Check if all tasks have been processed
                if index == len(sorted_attractiveness):
                    break  # No more workers available

                # Select the best available task for the worker
                # Potential extension: Roulette wheel selection instead of deterministic selection
                best_order_item = sorted_attractiveness[index]
                best_order = [order for order in self.data.orders 
                             if order.order_number == best_order_item.order_number][0]

                # Check: Working time constraint
                # Skip task if worker would be overloaded
                if best_order_item.duration + worker.work_hours > self.data._max_working_hours:
                    index += 1
                    continue

                # Check: Maximum consecutive night shifts
                # Skip night shift if limit would be reached
                if best_order_item.night_shift:
                    if current_consecutive_night_shifts + 1 > self.data._max_consecutive_night_shifts:
                        index += 1
                        continue
                
                # Check: Maximum shifts in time period
                # Skip task if too many shifts are planned in time window
                if len(current_shifts_in_time_period) == self.data._max_shifts_in_time_period:
                    if best_order_item.start_time - current_shifts_in_time_period[0].start_time <= self.data._time_period_for_max_shifts:
                        index += 1
                        continue

                # ===== ATTACHMENT ASSIGNMENT =====
                # Assign task to required attachments (if necessary)
                if len(best_order_item.equipment_types) > 0:
                    order_item_impossible = False  # Flag for impossible assignment
                    
                    # Iterate through all required equipment types
                    for equipment_type in best_order_item.equipment_types:
                        attachment_task_assigned = False  # Flag for successful attachment assignment
                        
                        if order_item_impossible:
                            break  # Task already marked as impossible
                        
                        # Calculate attractiveness of all available attachments for this equipment type
                        attachment_attractiveness = dict()
                        for attachment in self.data.attachments:
                            if (best_order_item in attachment._possible_order_items[best_order] and 
                                attachment.type == equipment_type):
                                attachment_attractiveness[attachment] = {
                                    "attachment_planned": attachment_planned[attachment]
                                }

                        # Sort attachments by attractiveness (already planned preferred)
                        if len(attachment_attractiveness) > 0:
                            # Split into already planned and unplanned attachments
                            true_list = [att for att in attachment_attractiveness 
                                       if attachment_attractiveness[att]["attachment_planned"]]
                            false_list = [att for att in attachment_attractiveness 
                                        if not attachment_attractiveness[att]["attachment_planned"]]
                            # Combine lists (already planned first)
                            sorted_attachment_attractiveness = true_list + false_list
                        else:
                            # No available attachment for this equipment type
                            index += 1
                            # Remove task from all attachment route plans (cleanup)
                            for attachment, route in route_plan_attachment.items():
                                if best_order_item.id in route:
                                    route.remove(best_order_item.id)
                            break

                        # Index for iteration through sorted attachments
                        attachment_index = 0
                        
                        # Search for suitable attachment for the task
                        while not attachment_task_assigned:
                            
                            # No suitable attachment found
                            if attachment_index == len(sorted_attachment_attractiveness):
                                index += 1
                                order_item_impossible = True
                                # Cleanup: Remove task from all attachment route plans
                                for attachment, route in route_plan_attachment.items():
                                    if best_order_item.id in route:
                                        route.remove(best_order_item.id)
                                break

                            # Select best available attachment
                            best_attachment = sorted_attachment_attractiveness[attachment_index]

                            # Case 1: Attachment has no planned tasks yet
                            if len(route_plan_attachment[best_attachment.id]) == 0:
                                route_plan_attachment[best_attachment.id].append(best_order_item.id)
                                attachment_planned[best_attachment] = True
                                attachment_task_assigned = True

                            # Case 2: Attachment has already planned tasks
                            # Check predecessor/successor relationships for correct order
                            elif len(route_plan_attachment[best_attachment.id]) > 0:
                                order_item_index_attachment_route = 0

                                # Traverse existing route and find correct insertion position
                                while not attachment_task_assigned:
                                    current_order_item = next((order_item for order_item in self.data.order_items 
                                                             if order_item.status == True and 
                                                             order_item.id == route_plan_attachment[best_attachment.id][order_item_index_attachment_route]))

                                    # Check if current task has predecessor/successor relationship
                                    if (current_order_item not in best_attachment._successors[best_order_item] and 
                                        current_order_item not in best_attachment._predecessors[best_order_item]):
                                        attachment_index += 1  # Try next attachment
                                        break

                                    # Insert before successor task
                                    if current_order_item in best_attachment._successors[best_order_item]:
                                        route_plan_attachment[best_attachment.id].insert(order_item_index_attachment_route, best_order_item.id)
                                        attachment_task_assigned = True

                                    # Move to next position in route
                                    order_item_index_attachment_route += 1

                                    # End of route reached: Check appending at end
                                    if order_item_index_attachment_route == len(route_plan_attachment[best_attachment.id]):
                                        # Append after predecessor task
                                        if current_order_item in best_attachment._predecessors[best_order_item]:
                                            route_plan_attachment[best_attachment.id].append(best_order_item.id)
                                            attachment_task_assigned = True

                # Skip to next task if attachment assignment failed
                if len(best_order_item.equipment_types) > 0:
                    if not attachment_task_assigned:
                        continue

                # ===== MACHINE ASSIGNMENT =====
                # Assign task to a suitable machine
                machine_attractiveness = dict()
                for machine in self.data.machines:
                    if best_order_item in machine._possible_order_items[best_order]:
                        
                        # Check if worker is default driver for this machine
                        # Increases machine attractiveness
                        if worker.personal_number in machine._default_drivers:
                            default_driver = True
                        else:
                            default_driver = False
                        
                        # Calculate machine attractiveness based on various factors
                        machine_attractiveness[machine] = {
                            "machine_planned": machine_planned[machine],           # Already planned machine
                            "worker_default_driver": default_driver,              # Worker is default driver
                            "possible_default_drivers": len(machine._default_drivers)  # Number of possible drivers
                        }

                # Sort machines by attractiveness
                if len(machine_attractiveness) > 0:
                    sorted_machine_attractiveness = self.machine_attractiveness_function(machine_attractiveness)
                else:
                    index += 1
                    continue

                # Index for iteration through sorted machines
                machine_index = 0
                machine_task_assigned = False

                # Search for suitable machine for the task
                while not machine_task_assigned:
                    # No suitable machine found for the current order item
                    if machine_index == len(sorted_machine_attractiveness):
                        index += 1
                        # Remove order item from route plan of all attachments if assignment to machine failed
                        for attachment, route in route_plan_attachment.items():
                            if best_order_item.id in route:
                                route.remove(best_order_item.id)
                        break
                    
                    # Select the best machine for the order item
                    # Potential extension: Roulette wheel selection instead of deterministic choice
                    best_machine = sorted_machine_attractiveness[machine_index]

                    # Case 1: Machine has no planned order items yet
                    if len(route_plan_machine[best_machine.id]) == 0:
                        route_plan_machine[best_machine.id].append(best_order_item.id)
                        machine_planned[best_machine] = True
                        machine_task_assigned = True
                        self.data.planned_shifts_machine[best_order].append(best_order_item)

                    # Case 2: Machine has planned order items
                    # Assign order item according to predecessor/successor relationships
                    elif len(route_plan_machine[best_machine.id]) > 0:
                        order_item_index_machine_route = 0
                        
                        # Check predecessor and successor relationships
                        while not machine_task_assigned:
                            current_order_item = next((order_item for order_item in self.data.order_items 
                                                     if order_item.status == True and 
                                                     order_item.id == route_plan_machine[best_machine.id][order_item_index_machine_route]))
                            
                            # If order item has no predecessor/successor relationship, try next machine
                            if (current_order_item not in best_machine._successors[best_order_item] and 
                                current_order_item not in best_machine._predecessors[best_order_item]):
                                machine_index += 1
                                break
                            
                            # Insert before successor task
                            if current_order_item in best_machine._successors[best_order_item]:
                                route_plan_machine[best_machine.id].insert(order_item_index_machine_route, best_order_item.id)
                                machine_task_assigned = True
                                self.data.planned_shifts_machine[best_order].append(best_order_item)
                            
                            # Move to next order item in machine route
                            order_item_index_machine_route += 1

                            # End of route reached: Check if current item is predecessor
                            if order_item_index_machine_route == len(route_plan_machine[best_machine.id]):
                                # Append after predecessor task
                                if current_order_item in best_machine._predecessors[best_order_item]:
                                    route_plan_machine[best_machine.id].append(best_order_item.id)
                                    machine_task_assigned = True
                                    self.data.planned_shifts_machine[best_order].append(best_order_item)
                                # If not a predecessor, try next machine
                                else:
                                    machine_index += 1
                                    break

                # ===== WORKER ASSIGNMENT =====
                # If order item is successfully assigned to machine, assign it to worker
                if machine_task_assigned:                       

                    # Update current shifts in time period for controlling maximum shifts constraint
                    for i in range(len(current_shifts_in_time_period) - 1, -1, -1):
                        if best_order_item.start_time - current_shifts_in_time_period[i].start_time > self.data._time_period_for_max_shifts:
                            current_shifts_in_time_period.pop(i)
                    
                    current_shifts_in_time_period.append(best_order_item)
                    
                    # Update consecutive night shifts counter
                    if best_order_item.night_shift:
                        current_consecutive_night_shifts += 1
                    elif best_order_item.day_shift:
                        current_consecutive_night_shifts = 0

                    # Update planned shifts for worker and dynamic percentage of order
                    self.data.planned_shifts_worker[best_order].append(best_order_item)
                    best_order.dynamic_percentage = len(self.data.planned_shifts_worker[best_order]) / len(greedy_order_items[best_order])

                    # Add order item to worker's route plan
                    route_plan_worker[worker.personal_number].append(best_order_item.id)

                    # Update worker's total work hours
                    worker.work_hours += best_order_item.duration

                    # Calculate attractiveness for next order item (only successors)
                    attractiveness = dict()
                    for order, order_items in greedy_order_items.items():
                        for order_item in order_items:
                            if order_item not in self.data.planned_shifts_worker[order]:
                                if order_item in worker._successors[best_order_item]:
                                    time_difference = order_item.start_time - best_order_item.end_time
                                    time_difference = time_difference.total_seconds() / self.data._seconds_a_day
                                    # Optional order priority consideration (commented out)
                                    attractiveness[order_item] = {
                                        "dynamic_percentage": order.dynamic_percentage, 
                                        "time_difference": time_difference
                                    }

                    # Activate attractiveness function or break to next worker
                    if len(attractiveness) > 0:
                        sorted_attractiveness = self.order_item_attractiveness_function(attractiveness)
                    else:
                        break

                    # Reset index for next iteration
                    index = 0

        # Calculate statistics: planned shifts vs total order items
        sum_of_planned_shifts = 0
        for order in self.data.orders:
            if order.status == True:
                sum_of_planned_shifts += len(self.data.planned_shifts_worker[order])
        
        sum_of_order_items = 0
        for order in self.data.orders:
            if order.status == True:
                sum_of_order_items += len(greedy_order_items[order])

        # Create and validate solution
        start_solution = Solution(route_plan_worker, route_plan_machine, route_plan_attachment, self.data)
        
        feasible = start_solution.feasibility_check()

        if feasible:
            self.EvaluationLogic.evaluate(start_solution)
            print(f"Greedy solution with {self.GreedyTechnique}")
            print(start_solution)
            return start_solution
        else:
            raise Exception("Solution is not feasible")



    def OrderItemGreedy(self):
        """
        Order-item-centered greedy heuristic for creating an initial solution.
        
        This algorithm iterates through all order items sorted by start time and
        assigns each order item to the most suitable available resources (worker,
        machine, attachments) step by step.
        
        The algorithm follows a sequential assignment approach:
        1. Sort order items by start time
        2. For each order item, find best worker
        3. For assigned worker, find best machine  
        4. For assigned worker/machine, find best attachments
        
        Returns:
            Solution: Feasible solution or Exception if infeasible
        """

        # Create list of all active order items
        greedy_order_items = list()
        for order_item in self.data.order_items:
            if order_item.status == True:  # Only active order items
                greedy_order_items.append(order_item)

        # Sort order items by start time (earliest first)
        sorted_greedy_order_items = sorted(greedy_order_items, key=lambda x: x.start_time)

        # Create tracking dictionaries for resource planning status
        worker_planned = dict()      # Track if worker has been assigned tasks
        machine_planned = dict()     # Track if machine has been assigned tasks
        attachment_planned = dict()  # Track if attachment has been assigned tasks

        # Initialize route plans for all workers
        for worker in self.data.workers:
            self.route_plan_worker[worker.personal_number] = list()
            worker_planned[worker] = False

        # Initialize route plans for all machines
        for machine in self.data.machines:
            self.route_plan_machine[machine.id] = list()
            machine_planned[machine] = False

        # Initialize route plans for all attachments
        for attachment in self.data.attachments:
            self.route_plan_attachment[attachment.id] = list()
            attachment_planned[attachment] = False

        # Main loop: Process each order item in chronological order
        for order_item in sorted_greedy_order_items:

            # ===== WORKER ASSIGNMENT =====
            # Start with worker assignment based on attractiveness
            worker_attractiveness = dict()
            for worker in self.data.workers:
                # Check working hours constraint
                if worker.work_hours + order_item.duration <= self.data._max_working_hours:
                    # Check if worker can perform this order item
                    if order_item.id in worker._possible_order_item_ids[order_item.order_number]:
                        # Calculate worker attractiveness
                        worker_attractiveness[worker] = {
                            'worker_planned': worker_planned[worker],    # Already has assignments
                            'qualifications': len(worker.qualifications) # Number of qualifications
                        }

            # Sort workers by attractiveness or skip if none available
            if len(worker_attractiveness) > 0:
                sorted_worker_attractiveness = self.worker_attractiveness_function(worker_attractiveness)
            else:
                continue  # No suitable worker, skip this order item

            # Try to assign order item to a worker
            worker_index = 0
            worker_task_assigned = False

            while not worker_task_assigned:
                # No more workers to try
                if worker_index == len(sorted_worker_attractiveness):
                    break

                # Select best available worker
                best_worker = sorted_worker_attractiveness[worker_index]

                # Case 1: Worker has no planned order items yet
                if len(self.route_plan_worker[best_worker.personal_number]) == 0:
                    worker_task_assigned = True
                    break

                # Case 2: Worker has existing route - check predecessor relationships
                elif len(self.route_plan_worker[best_worker.personal_number]) > 0:
                    # Get last order item in worker's route
                    order_item_index_worker_route = len(self.route_plan_worker[best_worker.personal_number]) - 1
                    order_item_id = self.route_plan_worker[best_worker.personal_number][order_item_index_worker_route]

                    current_order_item = self.data.order_items[order_item_id]

                    # Check if current item is predecessor of new order item
                    if current_order_item in best_worker._predecessors[order_item]:
                        # Additional feasibility check for worker constraints
                        feasible = self.worker_route_feasibility(best_worker, order_item)
                        if feasible:
                            worker_task_assigned = True
                            break
                        else:
                            worker_index += 1
                            continue
                    else:
                        worker_index += 1  # Try next worker
                        continue

            # ===== MACHINE ASSIGNMENT =====
            # If order item is assigned to worker, proceed with machine assignment
            if worker_task_assigned:
                machine_attractiveness = dict()

                # Calculate machine attractiveness for all compatible machines
                for machine in self.data.machines:
                    if order_item.id in machine._possible_order_item_ids[order_item.order_number]:
                        # Check if worker is default driver (increases attractiveness)
                        if best_worker.personal_number in machine._default_drivers:
                            default_driver = True
                        else:
                            default_driver = False

                        # Calculate machine attractiveness based on various factors
                        machine_attractiveness[machine] = {
                            "machine_planned": machine_planned[machine],      # Already has assignments
                            "worker_default_driver": default_driver,         # Worker is default driver
                            "possible_default_drivers": len(machine._default_drivers)  # Total default drivers
                        }

                # Sort machines by attractiveness or skip if none available
                if len(machine_attractiveness) > 0:
                    sorted_machine_attractiveness = self.machine_attractiveness_function(machine_attractiveness)
                else:
                    continue  # No suitable machine, skip this order item

                # Try to assign order item to a machine
                machine_index = 0
                machine_task_assigned = False

                while not machine_task_assigned:
                    # No more machines to try
                    if machine_index == len(sorted_machine_attractiveness):
                        break

                    # Select best available machine
                    best_machine = sorted_machine_attractiveness[machine_index]

                    # Case 1: Machine has no planned order items yet
                    if len(self.route_plan_machine[best_machine.id]) == 0:
                        machine_task_assigned = True
                        break

                    # Case 2: Machine has existing route - check predecessor relationships
                    elif len(self.route_plan_machine[best_machine.id]) > 0:
                        # Get last order item in machine's route
                        order_item_index_machine_route = len(self.route_plan_machine[best_machine.id]) - 1
                        order_item_id = self.route_plan_machine[best_machine.id][order_item_index_machine_route]

                        current_order_item = self.data.order_items[order_item_id]

                        # Check if current item is predecessor of new order item
                        if current_order_item in best_machine._predecessors[order_item]:
                            machine_task_assigned = True
                            break
                        else:
                            machine_index += 1  # Try next machine
                            continue

                # ===== ATTACHMENT ASSIGNMENT =====
                # If order item is assigned to worker and machine, proceed with attachment assignment
                if machine_task_assigned:
                    
                    attachment_info = list()      # Store assigned attachment IDs
                    order_item_impossible = False # Flag for impossible assignment
                    
                    # Process each required equipment type
                    if len(order_item.equipment_types) > 0:
                        
                        for equipment_type in order_item.equipment_types:

                            if order_item_impossible:
                                break  # Skip if already marked impossible
 
                            # Calculate attachment attractiveness for this equipment type
                            attachment_attractiveness = dict()
                            for attachment in self.data.attachments:
                                # Skip if attachment already assigned to this order item
                                if attachment.id in attachment_info:
                                    continue
                                # Check compatibility
                                if (order_item.id in attachment._possible_order_item_ids[order_item.order_number] and 
                                    attachment.type == equipment_type):
                                    attachment_attractiveness[attachment] = {
                                        "attachment_planned": attachment_planned[attachment]
                                    }
                            
                            # Sort attachments by attractiveness or mark as impossible
                            if len(attachment_attractiveness) > 0:
                                sorted_attachment_attractiveness = self.attachment_attractiveness_function(attachment_attractiveness)
                            else:
                                attachment_task_assigned = False
                                break  # No suitable attachment for this equipment type
                            
                            # Try to assign order item to an attachment
                            attachment_index = 0
                            attachment_task_assigned = False

                            while not attachment_task_assigned:
                                # No more attachments to try
                                if attachment_index == len(sorted_attachment_attractiveness):
                                    order_item_impossible = True
                                    break

                                # Select best available attachment
                                best_attachment = sorted_attachment_attractiveness[attachment_index]

                                # Case 1: Attachment has no planned order items yet
                                if len(self.route_plan_attachment[best_attachment.id]) == 0:
                                    attachment_info.append(best_attachment.id)
                                    attachment_task_assigned = True
                                    break

                                # Case 2: Attachment has existing route - check predecessor relationships
                                elif len(self.route_plan_attachment[best_attachment.id]) > 0:
                                    # Get last order item in attachment's route
                                    order_item_index_attachment_route = len(self.route_plan_attachment[best_attachment.id]) - 1
                                    order_item_id = self.route_plan_attachment[best_attachment.id][order_item_index_attachment_route]

                                    current_order_item = self.data.order_items[order_item_id]

                                    # Check if current item is predecessor of new order item
                                    if current_order_item in best_attachment._predecessors[order_item]:
                                        attachment_info.append(best_attachment.id)
                                        attachment_task_assigned = True
                                        break
                                    else:
                                        attachment_index += 1  # Try next attachment
                                        continue

                    else:
                        # No equipment types required - assignment successful
                        attachment_task_assigned = True

            # ===== FINAL ASSIGNMENT =====
            # If all resources (worker, machine, attachments) are successfully assigned
            if worker_task_assigned and machine_task_assigned and attachment_task_assigned:
                
                # Add order item to worker's route and update status
                self.route_plan_worker[best_worker.personal_number].append(order_item.id)
                worker_planned[best_worker] = True
                best_worker.work_hours += order_item.duration

                # Add order item to machine's route and update status
                self.route_plan_machine[best_machine.id].append(order_item.id)
                machine_planned[best_machine] = True

                # Add order item to all required attachments' routes
                for attachment_id in attachment_info:
                    self.route_plan_attachment[attachment_id].append(order_item.id)
                    attachment_planned[attachment_id] = True

        # Create and validate final solution
        greedy_solution = Solution(self.route_plan_worker, self.route_plan_machine, self.route_plan_attachment, self.data)
        self.EvaluationLogic.evaluate(greedy_solution)

        # Check feasibility of the solution
        feasible = greedy_solution.feasibility_check()

        if feasible:
            print(f"Greedy solution with {self.GreedyTechnique}")
            print(greedy_solution)
            return greedy_solution
        else:
            raise Exception("Solution is not feasible")

                
       


                
    def worker_route_feasibility(self, worker, order_item):
        """
        Checks if adding an order item to a worker's route maintains feasibility.
        
        Validates worker constraints:
        1. Maximum consecutive night shifts
        2. Maximum shifts within a time period
        
        Args:
            worker: Worker object to check
            order_item: Order item to potentially add
            
        Returns:
            bool: True if feasible, False otherwise
        """

        # Create temporary route with new order item added
        worker_route = deepcopy(self.route_plan_worker[worker.personal_number])
        worker_route.append(order_item.id)

        # Check constraint: Maximum consecutive night shifts
        night_shifts = 0
        for order_item_id in worker_route:
            if order_item_id in worker.night_shift_ids:
                night_shifts += 1  # Increment consecutive night shift counter
            else:
                night_shifts = 0   # Reset counter for non-night shifts
            
            # Violation: Too many consecutive night shifts
            if night_shifts > self.data._max_consecutive_night_shifts:
                return False
        
        # Check constraint: Maximum shifts in time period (e.g., 10 shifts in 14 days)
        order_items = [self.data.order_items[order_item_id] for order_item_id in worker_route]
        
        for i, order_item_i in enumerate(order_items):
            # Define time window starting from current order item
            window_start = order_item_i.start_time.date()
            window_end = window_start + self.data._time_period_for_max_shifts
            
            # Count shifts within this time window
            shift_count = 0
            for order_item_j in order_items:
                if window_start <= order_item_j.start_time.date() < window_end:
                    shift_count += 1
            
            # Violation: Too many shifts in time period
            if shift_count > self.data._max_shifts_in_time_period:
                return False

        return True  # All constraints satisfied



    def attachment_attractiveness_function(self, attractiveness):
        """
        Calculates attractiveness scores for attachments with tie-breaking.
        
        Simple attractiveness function that prioritizes already planned attachments
        over unplanned ones to promote resource consolidation.
        
        Args:
            attractiveness: Dictionary with attachment objects as keys and attributes as values
            
        Returns:
            list: Sorted list of attachments by attractiveness (descending)
        """

        # Convert boolean planned status to numeric score
        for attachment, attr in attractiveness.items():
            ap = 1 if attr["attachment_planned"] else 0  # 1 for planned, 0 for unplanned
            attractiveness[attachment] = ap

        # Group attachments by attractiveness value for tie-breaking
        unique_values = set(attractiveness.values())
        value_to_attachments = {v: [a for a in attractiveness if attractiveness[a] == v] for v in unique_values}
        
        # Shuffle within each group to break ties randomly
        for attachments in value_to_attachments.values():
            self.RNG.shuffle(attachments)

        # Sort by attractiveness (descending) with random tie-breaking
        return sorted(attractiveness.keys(), 
                     key=lambda a: (attractiveness[a], value_to_attachments[attractiveness[a]].index(a)), 
                     reverse=True)



    def worker_attractiveness_function(self, attractiveness):
        """
        Calculates attractiveness scores for workers based on different techniques.
        
        Supports three different attractiveness calculation methods:
        1. balanced_greedy: Combines planned status and qualifications equally
        2. worker_planned_importance: Prioritizes planned status over qualifications
        3. qualifications_importance: Prioritizes qualifications over planned status
        
        Args:
            attractiveness: Dictionary with worker objects as keys and attributes as values
            
        Returns:
            list: Sorted list of workers by attractiveness (descending)
        """
        
        # Normalize qualifications to [0,1] range for fair comparison
        min_qualifications = min(attributes["qualifications"] for attributes in attractiveness.values())
        max_qualifications = max(attributes["qualifications"] for attributes in attractiveness.values())

        if self.worker_attractiveness_technique == "balanced_greedy":
            # Equal weight for planned status and qualifications
            for worker, attributes in attractiveness.items():
                worker_planned_value = 1 if attributes["worker_planned"] else 0
                qualifications_value = (attributes["qualifications"] - min_qualifications) / (max_qualifications - min_qualifications + 1e-6)
                attractiveness[worker] = worker_planned_value + qualifications_value

            # Group by attractiveness value and shuffle for tie-breaking
            unique_values = set(attractiveness.values())
            value_to_items = {v: [w for w in attractiveness if attractiveness[w] == v] for v in unique_values}
            for items in value_to_items.values():
                self.RNG.shuffle(items)

            return sorted(attractiveness.keys(), 
                         key=lambda w: (attractiveness[w], value_to_items[attractiveness[w]].index(w)), 
                         reverse=True)

        elif self.worker_attractiveness_technique == "worker_planned_importance":
            # Prioritize planned status, then qualifications
            for worker, attributes in attractiveness.items():
                wp = 1 if attributes["worker_planned"] else 0
                q = (attributes["qualifications"] - min_qualifications) / (max_qualifications - min_qualifications + 1e-6)
                attractiveness[worker] = {"worker_planned": wp, "value": q}

            # Create tuples for lexicographic sorting
            value_tuples = {w: (attractiveness[w]["worker_planned"], attractiveness[w]["value"]) for w in attractiveness}
            unique_pairs = set(value_tuples.values())
            tie_map = {pair: [w for w in value_tuples if value_tuples[w] == pair] for pair in unique_pairs}
            
            # Shuffle within each tie group
            for workers in tie_map.values():
                self.RNG.shuffle(workers)

            return sorted(attractiveness.keys(), 
                         key=lambda w: (value_tuples[w], tie_map[value_tuples[w]].index(w)), 
                         reverse=True)

        elif self.worker_attractiveness_technique == "qualifications_importance":
            # Prioritize qualifications, then planned status
            for worker, attributes in attractiveness.items():
                wp = 1 if attributes["worker_planned"] else 0
                q = (attributes["qualifications"] - min_qualifications) / (max_qualifications - min_qualifications + 1e-6)
                attractiveness[worker] = {"qualifications": q, "value": wp}

            # Create tuples for lexicographic sorting (qualifications first)
            value_tuples = {w: (attractiveness[w]["qualifications"], attractiveness[w]["value"]) for w in attractiveness}
            unique_pairs = set(value_tuples.values())
            tie_map = {pair: [w for w in value_tuples if value_tuples[w] == pair] for pair in unique_pairs}
            
            # Shuffle within each tie group
            for workers in tie_map.values():
                self.RNG.shuffle(workers)

            return sorted(attractiveness.keys(), 
                         key=lambda w: (value_tuples[w], tie_map[value_tuples[w]].index(w)), 
                         reverse=True)



    def machine_attractiveness_function(self, attractiveness):
        """
        Calculates attractiveness scores for machines based on different techniques.
        
        Supports three different attractiveness calculation methods:
        1. balanced_greedy: Combines planned status and default driver status equally
        2. machine_planned_importance: Prioritizes planned status over default driver
        3. worker_default_driver_importance: Prioritizes default driver over planned status
        
        Args:
            attractiveness: Dictionary with machine objects as keys and attributes as values
            
        Returns:
            list: Sorted list of machines by attractiveness (descending)
        """

        if self.machine_attractiveness_technique == "balanced_greedy":
            # Equal weight for planned status and default driver status
            for machine, attr in attractiveness.items():
                mp = 1 if attr["machine_planned"] else 0      # Machine already planned
                dd = 1 if attr["worker_default_driver"] else 0 # Worker is default driver

                attractiveness[machine] = mp + dd

            # Group by attractiveness value and shuffle for tie-breaking
            unique_values = set(attractiveness.values())
            value_to_machines = {v: [m for m in attractiveness if attractiveness[m] == v] for v in unique_values}
            for machines in value_to_machines.values():
                self.RNG.shuffle(machines)

            return sorted(attractiveness.keys(), 
                         key=lambda m: (attractiveness[m], value_to_machines[attractiveness[m]].index(m)), 
                         reverse=True)

        elif self.machine_attractiveness_technique == "machine_planned_importance":
            # Prioritize planned status, then default driver status
            for machine, attr in attractiveness.items():
                mp = 1 if attr["machine_planned"] else 0
                dd = 1 if attr["worker_default_driver"] else 0

                attractiveness[machine] = {"machine_planned": mp, "value": dd}

            # Create tuples for lexicographic sorting
            value_tuples = {m: (attractiveness[m]["machine_planned"], attractiveness[m]["value"]) for m in attractiveness}
            unique_pairs = set(value_tuples.values())
            tie_map = {pair: [m for m in value_tuples if value_tuples[m] == pair] for pair in unique_pairs}
            
            # Shuffle within each tie group
            for machines in tie_map.values():
                self.RNG.shuffle(machines)

            return sorted(attractiveness.keys(), 
                         key=lambda m: (value_tuples[m], tie_map[value_tuples[m]].index(m)), 
                         reverse=True)

        elif self.machine_attractiveness_technique == "worker_default_driver_importance":
            # Prioritize default driver status, then planned status
            for machine, attr in attractiveness.items():
                mp = 1 if attr["machine_planned"] else 0
                dd = 1 if attr["worker_default_driver"] else 0
                attractiveness[machine] = {"worker_default_driver": dd, "value": mp}

            # Create tuples for lexicographic sorting (default driver first)
            value_tuples = {m: (attractiveness[m]["worker_default_driver"], attractiveness[m]["value"]) for m in attractiveness}
            unique_pairs = set(value_tuples.values())
            tie_map = {pair: [m for m in value_tuples if value_tuples[m] == pair] for pair in unique_pairs}
            
            # Shuffle within each tie group
            for machines in tie_map.values():
                self.RNG.shuffle(machines)

            return sorted(attractiveness.keys(), 
                         key=lambda m: (value_tuples[m], tie_map[value_tuples[m]].index(m)), 
                         reverse=True)




    def order_item_attractiveness_function(self, attractiveness):
        """
        Calculates attractiveness scores for order items based on different techniques.
        
        Supports three different attractiveness calculation methods:
        1. balanced_greedy: Combines dynamic percentage and time difference equally
        2. dynamic_percentage_importance: Prioritizes order completion progress
        3. time_difference_importance: Prioritizes temporal proximity
        
        Args:
            attractiveness: Dictionary with order item objects as keys and attributes as values
            
        Returns:
            list: Sorted list of order items by attractiveness (descending)
        """

        # Normalize time differences to [0,1] range for fair comparison
        min_time_difference = min(attr["time_difference"] for attr in attractiveness.values())
        max_time_difference = max(attr["time_difference"] for attr in attractiveness.values())

        if self.order_item_attractiveness_technique == "balanced_greedy":
            # Equal weight for dynamic percentage and time difference
            for item, attr in attractiveness.items():
                dp = attr["dynamic_percentage"]  # Order completion progress
                # Invert time difference (closer to start = higher attractiveness)
                td = (max_time_difference - attr["time_difference"]) / (max_time_difference - min_time_difference + 1e-6)
                attractiveness[item] = dp + td

            # Group by attractiveness value and shuffle for tie-breaking
            values = set(attractiveness.values())
            tie_map = {v: [i for i in attractiveness if attractiveness[i] == v] for v in values}
            for tied_items in tie_map.values():
                self.RNG.shuffle(tied_items)

            return sorted(attractiveness.keys(), 
                         key=lambda i: (attractiveness[i], tie_map[attractiveness[i]].index(i)), 
                         reverse=True)

        elif self.order_item_attractiveness_technique == "dynamic_percentage_importance":
            # Prioritize order completion progress, then time difference
            for item, attr in attractiveness.items():
                dp = attr["dynamic_percentage"]
                td = (max_time_difference - attr["time_difference"]) / (max_time_difference - min_time_difference + 1e-6)
                attractiveness[item] = {"dynamic_percentage": dp, "value": td}

            # Create tuples for lexicographic sorting
            tuples = {i: (attractiveness[i]["dynamic_percentage"], attractiveness[i]["value"]) for i in attractiveness}
            tie_map = {v: [i for i in tuples if tuples[i] == v] for v in set(tuples.values())}
            
            # Shuffle within each tie group
            for items in tie_map.values():
                self.RNG.shuffle(items)

            return sorted(attractiveness.keys(), 
                         key=lambda i: (tuples[i], tie_map[tuples[i]].index(i)), 
                         reverse=True)

        elif self.order_item_attractiveness_technique == "time_difference_importance":
            # Prioritize temporal proximity, then order completion progress
            for item, attr in attractiveness.items():
                dp = attr["dynamic_percentage"]
                td = (max_time_difference - attr["time_difference"]) / (max_time_difference - min_time_difference + 1e-6)
                attractiveness[item] = {"time_difference": td, "value": dp}

            # Create tuples for lexicographic sorting (time difference first)
            tuples = {i: (attractiveness[i]["time_difference"], attractiveness[i]["value"]) for i in attractiveness}
            tie_map = {v: [i for i in tuples if tuples[i] == v] for v in set(tuples.values())}
            
            # Shuffle within each tie group
            for items in tie_map.values():
                self.RNG.shuffle(items)

            return sorted(attractiveness.keys(), 
                         key=lambda i: (tuples[i], tie_map[tuples[i]].index(i)), 
                         reverse=True)
