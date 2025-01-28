
from OutputData import *
from InputData import *
from EvaluationLogic import *
import random

class ConstructiveHeuristics:
    ''' Class for creating objects to run different constructive heuristics'''

    def __init__(self,  solutionPool:SolutionPool, evaluationLogic:EvaluationLogic):

        self.EvaluationLogic = evaluationLogic
        self._SolutionPool = solutionPool


    def Run(self, input_data:InputData, order_item_attractiveness_technique, machine_attractiveness_technique):
        ''' Run the constructive heuristic on the input data'''

        self.data = input_data
        self.order_item_attractiveness_technique = order_item_attractiveness_technique
        self.machine_attractiveness_technique = machine_attractiveness_technique
        start_solution = self.Greedy()

        return start_solution
    

    def Greedy(self):
        
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
        total_order_amount = len(self.data.orders)
        greedy_order_items = dict()
        for order in self.data.orders:
            if order._priority["overall"] <= total_order_amount:
                greedy_order_items[order] = [order_item for order_item in self.data.order_items if order_item.order_number == order.order_number]

        # Initialize route plan for workers and machines
        route_plan_worker = dict()
        route_plan_machine = dict()

        # All machines are available at the start - machine planned needed for machine attractiveness
        machine_planned = dict()
        for machine in self.data.machines:
            machine_planned[machine] = 0
            route_plan_machine[machine.id] = list()
            
        # Fill route plan worker by worker in sequenced time order
        for worker in self.data.workers:
            
            # Initialize variables for each worker
            attractiveness = dict()
            route_plan_worker[worker.personal_number] = list()
            current_consecutive_night_shifts = 0
            current_shifts_in_time_period = list()

            # Calulate attractiveness to place the first order item
            for order, order_items in greedy_order_items.items():
                for order_item in order_items:
                        if any(order_item in value_list for value_list in worker._possible_order_items.values()):
                            if order_item not in self.data.planned_shifts_worker[order]:
                                time_difference = order_item.start_time - self.data.start_date
                                time_difference = time_difference.total_seconds() / self.data._seconds_a_day
                                # Attractiveness function can be tuned
                                attractiveness[order_item] = {"order_priority": order.priority["overall"], "dynamic_percentage": order.dynamic_percentage, "time_difference": time_difference}

            # Activate Attractiveness function
            sorted_attractiveness = self.order_item_attractiveness_function(attractiveness)

            

            # Index needed to iterate through sorted order items if a specific order item is not suitable
            index = 0
            

            # Add order items to route plan for each worker until worker is overworked or no suitable order item is left
            while worker.work_hours <= self.data._max_working_hours and len(attractiveness) > 0:
                
                # Break to next worker if there is no suitable order item fo the current worker
                if index == len(sorted_attractiveness):
                    break

                
                # Select the best order item for the worker --> Could be changed to roulette wheel selection
                best_order_item = sorted_attractiveness[index]
                best_order = [order for order in self.data.orders if order.order_number == best_order_item.order_number][0]
                


                # Continue to next order item if worker is overworked
                if best_order_item.duration + worker.work_hours > self.data._max_working_hours:
                    index += 1
                    continue
                

                # Continue to next order item if worker has too many consecutive night shifts
                if best_order_item.night_shift:
                    if current_consecutive_night_shifts + 1 > self.data._max_consecutive_night_shifts:
                        index += 1
                        continue
                
                # Continue to next order item if worker has too many shifts in time period
                if len(current_shifts_in_time_period) == self.data._max_shifts_in_time_period:
                    if best_order_item.start_time - current_shifts_in_time_period[0].start_time <= self.data._time_period_for_max_shifts:
                        index += 1
                        continue

                

                # Assign machine to order item according to machine attractiveness
                machine_attractiveness = dict()
                for machine in self.data.machines:
                    if best_order_item in machine._possible_order_items[best_order]:
                        
                        # Default driver value for machine attractiveness --> Highers chances to select a machine with the worker as default driver
                        if worker.personal_number in machine._default_drivers:
                            default_driver_value = 10
                        else:
                            default_driver_value = 0
                        
                        # Calculate machine attractiveness for this order item for all potential machines
                        possible_order_items_best_order = [order_item for order_item in self.data.order_items if order_item.order_number == best_order_item.order_number]
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
                        self.data.planned_shifts_machine[best_order].append(best_order_item)

                    # If the machine has planned order items, assign the order item to the machine according to the order item's predecessors and successors
                    elif len(route_plan_machine[best_machine.id]) > 0:
                        order_item_index = 0
                        
                        # Check predecerssor and successor of the order item
                        while not task_assigned:
                            current_order_item = next((order_item for order_item in self.data.order_items if order_item.id == route_plan_machine[best_machine.id][order_item_index]))
                            
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
                                self.data.planned_shifts_machine[best_order].append(best_order_item)
                            
                            # Check next order item in route plan of the machine for predecessors and successors
                            order_item_index += 1

                            # If length of route plan is reached, check if the current order item is a predecessor of the best order item
                            if order_item_index == len(route_plan_machine[best_machine.id]):
                                # If the current order item is a predecessor of the best order item, assign the best order item to the machine after the current order item (in the end of the route plan)
                                if current_order_item in best_machine._predecessors[best_order_item]:
                                    route_plan_machine[best_machine.id].append(best_order_item.id)
                                    machine_planned[best_machine] += 1
                                    task_assigned = True
                                    self.data.planned_shifts_machine[best_order].append(best_order_item)
                                # If the current order item is not a predecessor of the best order item, continue to next machine in machine_attractiveness
                                else:
                                    machine_index += 1
                                    break

                
                # If the order item is assigned to a machine, assign the order item to the worker
                if task_assigned:                       

                    # Update current shifts in time period for controlling the maximum shifts in a time period
                    for i in range(len(current_shifts_in_time_period) - 1, -1, -1):
                        if best_order_item.start_time - current_shifts_in_time_period[i].start_time > self.data._time_period_for_max_shifts:
                            current_shifts_in_time_period.pop(i)
                    
                    current_shifts_in_time_period.append(best_order_item)
                    
                    # Update consecutive night shifts for controlling the maximum consecutive night shifts
                    if best_order_item.night_shift:
                        current_consecutive_night_shifts += 1
                    elif best_order_item.day_shift:
                        current_consecutive_night_shifts = 0

                    # Update planned shifts for the worker and dynamic percentage of the order
                    self.data.planned_shifts_worker[best_order].append(best_order_item)
                    best_order.dynamic_percentage = len(self.data.planned_shifts_worker[best_order]) / len(greedy_order_items[best_order])

                    # Include the order item in the route plan of the worker
                    route_plan_worker[worker.personal_number].append(best_order_item.id)

                    # Update work hours of the worker
                    worker.work_hours += best_order_item.duration

                    # Calculate attractiveness for the next order item
                    attractiveness = dict()
                    for order, order_items in greedy_order_items.items():
                        for order_item in order_items:
                            if order_item not in self.data.planned_shifts_worker[order]:
                                if order_item in worker._successors[best_order_item]:
                                    time_difference = order_item.start_time - best_order_item.end_time
                                    time_difference = time_difference.total_seconds() / self.data._seconds_a_day
                                    attractiveness[order_item] = {"order_priority": order.priority["overall"], "dynamic_percentage": order.dynamic_percentage, "time_difference": time_difference}

                    # Activate Attractiveness function
                    sorted_attractiveness = self.order_item_attractiveness_function(attractiveness)

                    # Reset index for the next iteration
                    index = 0

                    

        # Caluclate sum of planned shifts in comparison to all order items
        sum_of_planned_shifts = 0
        for order in self.data.orders:
            sum_of_planned_shifts += len(self.data.planned_shifts_worker[order])
        sum_of_order_items = 0
        for order in self.data.orders:
            sum_of_order_items += len(greedy_order_items[order])
        


        # Check feasibility of the solution
        start_solution = Solution(route_plan_worker, route_plan_machine, self.data)
        
        feasible = start_solution.feasibility_check()

        if feasible:
            return start_solution
        else:
            raise Exception("Solution is not feasible")



    def order_item_attractiveness_function(self, attractiveness):
        ''' Attractiveness function for order items'''

        if self.order_item_attractiveness_technique == "balanced_greedy":
            for order_item, attributes in attractiveness.items():
                attractiveness[order_item] = (1/attributes["order_priority"]) + attributes["dynamic_percentage"] + (1/attributes["time_difference"])

            sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)


        elif self.order_item_attractiveness_technique == "time_difference_importance":
            for order_item, attributes in attractiveness.items():
                attractiveness[order_item]["value"] = (1/attributes["order_priority"]) + attributes["dynamic_percentage"]

            sorted_attractiveness = sorted(attractiveness, key=lambda x: (attractiveness[x]["time_difference"], -attractiveness[x]["value"]))


        elif self.order_item_attractiveness_technique == "dynamic_percentage_importance":
            for order_item, attributes in attractiveness.items():
                attractiveness[order_item]["value"] = (1/attributes["order_priority"]) + (1/attributes["time_difference"])

            sorted_attractiveness = sorted(attractiveness, key=lambda x: (attractiveness[x]["dynamic_percentage"], -attractiveness[x]["value"]))


        elif self.order_item_attractiveness_technique == "order_priority_importance":
            for order_item, attributes in attractiveness.items():
                attractiveness[order_item]["value"] = attributes["dynamic_percentage"] + (1/attributes["time_difference"])

            sorted_attractiveness = sorted(attractiveness, key=lambda x: (attractiveness[x]["order_priority"], -attractiveness[x]["value"]))


        return sorted_attractiveness
    


    def machine_attractiveness_function(self, attractiveness):
        ''' Attractiveness function for machines'''

        if self.machine_attractiveness_technique == "balanced_greedy":
            for machine, value in attractiveness.items():
                attractiveness[machine] = value

            sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)


        elif self.machine_attractiveness_technique == "default_driver_importance":
            for machine, value in attractiveness.items():
                attractiveness[machine] = value

            sorted_attractiveness = sorted(attractiveness, key=lambda x: (attractiveness[x], -len(x._default_drivers)))


        return sorted_attractiveness
