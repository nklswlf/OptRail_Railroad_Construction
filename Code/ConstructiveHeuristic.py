
from OutputData import *
from InputData import *
from EvaluationLogic import *
import random

class ConstructiveHeuristics:
    ''' Class for creating objects to run different constructive heuristics'''

    def __init__(self,  solutionPool:SolutionPool, evaluationLogic:EvaluationLogic):

        self.EvaluationLogic = evaluationLogic
        self._SolutionPool = solutionPool


    def Run(self, inputdata:InputData):
        ''' Run the constructive heuristic on the input data'''

        start_solution = self.Greedy(inputdata)

        return start_solution
    

    def Greedy(self, inputdata:InputData):
        
        print("Greedy")

        '''
        Greedy with potential GRASPS elements
        Roulette wheel selection for order items with attractiveness as fitness
        But sorting order items by attractiveness and including only alpha % of them
        Alpha is a parameter that can be tuned
        Alpha = 1 means 100% of order items are included
        Or a two step approach:
            1. Include alpha % of order items ranked after their time difference to the start date or current time
            2. Roulette wheel selection for order items with attractiveness as fitness

        Moreover, order.priority calculated in input data can have different elements to consider

        In total there are many options to consider and test


        GRASP element repair might be necessary
        Repair could be done by local search or mathematical optimization
        '''


        # Create Order and Order Item dictionary
        total_order_amount = len(inputdata.orders)
        greedy_order_items = dict()
        for order in inputdata.orders:
            if order._priority["overall"] <= total_order_amount:
                greedy_order_items[order] = [order_item for order_item in inputdata.order_items if order_item.order_number == order.order_number]

        # Initialize route plan for workers and machines
        route_plan_worker = dict()
        route_plan_machine = dict()

        # All machines are available at the start - machine planned needed for machine attractiveness
        machine_planned = dict()
        for machine in inputdata.machines:
            machine_planned[machine] = 0
            route_plan_machine[machine.id] = list()
            
        # Fill route plan worker by worker in sequenced time order
        for worker in inputdata.workers:
            
            # Initialize variables for each worker
            attractiveness = dict()
            route_plan_worker[worker.personal_number] = list()
            current_consecutive_night_shifts = 0
            current_shifts_in_time_period = list()

            # Calulate attractiveness to place the first order item
            for order, order_items in greedy_order_items.items():
                for order_item in order_items:
                        if any(order_item in value_list for value_list in worker._possible_order_items.values()):
                            if order_item not in inputdata.planned_shifts_worker[order]:
                                time_difference = order_item.start_time - inputdata.start_date
                                time_difference = time_difference.total_seconds() / inputdata._seconds_a_day
                                # Attractiveness function can be tuned
                                attractiveness[order_item] = (1/order.priority["overall"]) + order.dynamic_percentage - (time_difference / 2)

            # Sort order items by attractiveness
            sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)

            # Roulette wheel shaking of sorted order items if randomness is True
            

            # Index needed to iterate through sorted order items if a specific order item is not suitable
            index = 0
            

            # Add order items to route plan for each worker until worker is overworked or no suitable order item is left
            while worker.work_hours <= inputdata._max_working_hours and len(attractiveness) > 0:
                
                # Break to next worker if there is no suitable order item fo the current worker
                if index == len(sorted_attractiveness):
                    break

                
                # Select the best order item for the worker --> Could be changed to roulette wheel selection
                best_order_item = sorted_attractiveness[index]
                best_order = [order for order in inputdata.orders if order.order_number == best_order_item.order_number][0]
                


                # Continue to next order item if worker is overworked
                if best_order_item.duration + worker.work_hours > inputdata._max_working_hours:
                    index += 1
                    continue
                

                # Continue to next order item if worker has too many consecutive night shifts
                if best_order_item.night_shift:
                    if current_consecutive_night_shifts + 1 > inputdata._max_consecutive_night_shifts:
                        index += 1
                        continue
                
                # Continue to next order item if worker has too many shifts in time period
                if len(current_shifts_in_time_period) == inputdata._max_shifts_in_time_period:
                    if best_order_item.start_time - current_shifts_in_time_period[0].start_time <= inputdata._time_period_for_max_shifts:
                        index += 1
                        continue

                

                # Assign machine to order item according to machine attractiveness
                machine_attractiveness = dict()
                for machine in inputdata.machines:
                    if best_order_item in machine._possible_order_items[best_order]:
                        
                        # Default driver value for machine attractiveness --> Highers chances to select a machine with the worker as default driver
                        if worker.personal_number in machine._default_drivers:
                            default_driver_value = 10
                        else:
                            default_driver_value = 0
                        
                        # Calculate machine attractiveness for this order item for all potential machines
                        possible_order_items_best_order = [order_item for order_item in inputdata.order_items if order_item.order_number == best_order_item.order_number]
                        machine_attractiveness[machine] = machine_planned[machine] + len(machine._default_drivers) + len(possible_order_items_best_order) + default_driver_value
                

                # Sort machines by attractiveness
                sorted_machines = sorted(machine_attractiveness, key=machine_attractiveness.get, reverse=True)

                # Index needed to iterate through sorted machines if a specific machine is not suitable
                machine_index = 0

                # Assign order item to machine as long as no suitable machine is found
                task_assigned = False
                while not task_assigned:
                    
                    # Break to next order item if there is no suitable machine for the current order item
                    if machine_index == len(sorted_machines):
                        index += 1
                        break
                    
                    # Select the best machine for the order item --> Could be changed to roulette wheel selection
                    best_machine = sorted_machines[machine_index]

                    # If the machine has no planned order items yet, assign the order item to the machine
                    if len(route_plan_machine[best_machine.id]) == 0:
                        route_plan_machine[best_machine.id].append(best_order_item.id)
                        machine_planned[best_machine] += 1
                        task_assigned = True
                        inputdata.planned_shifts_machine[best_order].append(best_order_item)

                    # If the machine has planned order items, assign the order item to the machine according to the order item's predecessors and successors
                    elif len(route_plan_machine[best_machine.id]) > 0:
                        order_item_index = 0
                        
                        # Check predecerssor and successor of the order item
                        while not task_assigned:
                            current_order_item = next((order_item for order_item in inputdata.order_items if order_item.id == route_plan_machine[best_machine.id][order_item_index]))
                            
                            # If the best order item is not a successor or predecessor of the current order item it can not be assigned to the machine
                            # Continue to next machine in machine_attractiveness
                            if current_order_item not in best_machine._successors[best_order_item] and current_order_item not in best_machine._predecessors[best_order_item]:
                                machine_index += 1
                                break
                            
                            # If the current order item is a successor of the best order item, assign the best order item to the machine before the current order item
                            if current_order_item in best_machine._successors[best_order_item]:
                                route_plan_machine[best_machine.id].insert(order_item_index, best_order_item.id)
                                machine_planned[best_machine] += 1
                                task_assigned = True
                                inputdata.planned_shifts_machine[best_order].append(best_order_item)
                            
                            # Check next order item in route plan of the machine for predecessors and successors
                            order_item_index += 1

                            # If length of route plan is reached, check if the current order item is a predecessor of the best order item
                            if order_item_index == len(route_plan_machine[best_machine.id]):
                                # If the current order item is a predecessor of the best order item, assign the best order item to the machine after the current order item (in the end of the route plan)
                                if current_order_item in best_machine._predecessors[best_order_item]:
                                    route_plan_machine[best_machine.id].append(best_order_item.id)
                                    machine_planned[best_machine] += 1
                                    task_assigned = True
                                    inputdata.planned_shifts_machine[best_order].append(best_order_item)
                                # If the current order item is not a predecessor of the best order item, continue to next machine in machine_attractiveness
                                else:
                                    machine_index += 1
                                    break

                
                # If the order item is assigned to a machine, assign the order item to the worker
                if task_assigned:                       

                    # Update current shifts in time period for controlling the maximum shifts in a time period
                    for i in range(len(current_shifts_in_time_period) - 1, -1, -1):
                        if best_order_item.start_time - current_shifts_in_time_period[i].start_time > inputdata._time_period_for_max_shifts:
                            current_shifts_in_time_period.pop(i)
                    
                    current_shifts_in_time_period.append(best_order_item)
                    
                    # Update consecutive night shifts for controlling the maximum consecutive night shifts
                    if best_order_item.night_shift:
                        current_consecutive_night_shifts += 1
                    elif best_order_item.day_shift:
                        current_consecutive_night_shifts = 0

                    # Update planned shifts for the worker and dynamic percentage of the order
                    inputdata.planned_shifts_worker[best_order].append(best_order_item)
                    best_order.dynamic_percentage = len(inputdata.planned_shifts_worker[best_order]) / len(greedy_order_items[best_order])

                    # Include the order item in the route plan of the worker
                    route_plan_worker[worker.personal_number].append(best_order_item.id)

                    # Update work hours of the worker
                    worker.work_hours += best_order_item.duration

                    # Calculate attractiveness for the next order item
                    attractiveness = dict()
                    for order, order_items in greedy_order_items.items():
                        for order_item in order_items:
                            if order_item not in inputdata.planned_shifts_worker[order]:
                                if order_item in worker._successors[best_order_item]:
                                    time_difference = order_item.start_time - best_order_item.end_time
                                    time_difference = time_difference.total_seconds() / inputdata._seconds_a_day
                                    print(f"Time difference: {time_difference}")
                                    # Attractiveness function can be tuned
                                    attractiveness[order_item] = (1/order.priority["overall"]) + order.dynamic_percentage - (time_difference / 2)
                    
                    # Sort order items by attractiveness for the next iteration
                    sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)

                    # Roulette wheel shaking of sorted order items if randomness is True
                    

                    # Reset index for the next iteration
                    index = 0

                    


        # Print results
        for worker in inputdata.workers:        
            print(f"Route plan for worker {worker.personal_number}: {route_plan_worker[worker.personal_number]}")
            print(f"Work hours for worker {worker.personal_number}: {worker.work_hours}")


        for machine in inputdata.machines:
            print(f"Route plan for machine {machine.id}: {route_plan_machine[machine.id]}")
        
        sum_of_dynamic_percentage = 0
        for order in inputdata.orders:
            order.dynamic_percentage = len(inputdata.planned_shifts_machine[order]) / len(greedy_order_items[order])
            sum_of_dynamic_percentage += order.dynamic_percentage
            print(f"Order {order.order_number} has dynamic percentage {order.dynamic_percentage}")
        print(f"Sum of dynamic percentage: {sum_of_dynamic_percentage}")

        # Caluclate sum of planned shifts in comparison to all order items
        sum_of_planned_shifts = 0
        for order in inputdata.orders:
            sum_of_planned_shifts += len(inputdata.planned_shifts_worker[order])
        sum_of_order_items = 0
        for order in inputdata.orders:
            sum_of_order_items += len(greedy_order_items[order])
        


        # Check feasibility of the solution
        start_solution = Solution(route_plan_worker, route_plan_machine, inputdata)
        
        feasible = start_solution.feasibility_check()

        if feasible:
            return start_solution
        else:
            raise Exception("Solution is not feasible")



    def roulette_shuffle(self,input_dict):
        """
        Creates a new shuffled dictionary based on a roulette-wheel approach, 
        preserving relative probabilities even for float weights.
        
        Args:
            input_dict (dict): A dictionary where keys are 'order_item' (objects) 
                            and values are 'attractiveness' (weights as floats).
        
        Returns:
            dict: A newly shuffled dictionary where order is influenced by the attractiveness values.
        """
        # Extract keys (items) and their associated weights (attractiveness values)
        items = list(input_dict.keys())
        weights = list(input_dict.values())
        
        # Scale weights to integers while preserving proportionality
        scale_factor = 1000  # Use a large enough scale to preserve relative differences
        scaled_weights = [round(weight * scale_factor) for weight in weights]
        

        # Create a new shuffled list using the roulette-wheel approach
        shuffled_items = random.sample(items, len(items), counts=scaled_weights)
        
        # Create a new dictionary based on the shuffled order
        shuffled_dict = {item: input_dict[item] for item in shuffled_items}
        
        return shuffled_dict