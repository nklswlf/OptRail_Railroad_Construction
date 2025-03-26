
from OutputData import *
from InputData import *
from EvaluationLogic import *

class ConstructiveHeuristics:
    ''' Class for creating objects to run different constructive heuristics'''

    def __init__(self,  paretoSolutions: ParetoSolutions, evaluationLogic: EvaluationLogic):

        self.EvaluationLogic = evaluationLogic
        self.ParetoSolutions = paretoSolutions


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
        greedy_order_items = dict()
        for order in self.data.orders:
            if order.status == True:
                greedy_order_items[order] = [order_item for order_item in self.data.order_items if order_item.order_number == order.order_number]

        # Initialize route plan for workers and machines
        route_plan_worker = dict()
        route_plan_machine = dict()
        route_plan_attachment = dict()

        # All machines are available at the start - machine planned needed for machine attractiveness
        machine_planned = dict()
        for machine in self.data.machines:
            machine_planned[machine] = False
            route_plan_machine[machine.id] = list()

        attachment_planned = dict()
        for attachment in self.data.attachments:
            attachment_planned[attachment] = False
            route_plan_attachment[attachment.id] = list()
            
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
                                attractiveness[order_item] = {"order_priority": order.priority["borda_count_ahp"], "dynamic_percentage": order.dynamic_percentage, "time_difference": time_difference}

            # Activate Attractiveness function and break to continue with next worker if no suitable order item is left
            if len(attractiveness) > 0:
                sorted_attractiveness = self.order_item_attractiveness_function(attractiveness)
            else:
                continue

            
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

                # Add order item to route plan for attachment
                if len(best_order_item.equipment_types) > 0:
                    order_item_impossible = False
                    for equipment_type in best_order_item.equipment_types:
                        attachment_task_assigned = False
                        if order_item_impossible:
                            break
                        attachment_attractiveness = dict()
                        for attachment in self.data.attachments:
                            if best_order_item in attachment._possible_order_items[best_order] and attachment.type == equipment_type:
                                attachment_attractiveness[attachment] = {"attachment_planned": attachment_planned[attachment]}


                        # Sort attachments by attractiveness
                        if len(attachment_attractiveness) > 0:
                            true_list = [att for att in attachment_attractiveness if attachment_attractiveness[att]["attachment_planned"]]
                            false_list = [att for att in attachment_attractiveness if not attachment_attractiveness[att]["attachment_planned"]]
                            #random.shuffle(true_list)
                            #random.shuffle(false_list)
                            sorted_attachment_attractiveness = true_list + false_list
                        else: # Break to next order item if one equipment type is not available
                            index += 1
                            # Remove order item from route plan of all attachments if it is not possible to assign it to all necessary attachments
                            for attachment, route in route_plan_attachment.items():
                                if best_order_item.id in route:
                                    route.remove(best_order_item.id)
                            break

                        # Index needed to iterate through sorted attachments if a specific attachment is not suitable
                        attachment_index = 0
                        
                        # Assign order item to attachment as long as no suitable attachment is found
                        while not attachment_task_assigned:
                            
                            # Break to next order item if there is no suitable attachment for the current order item
                            if attachment_index == len(sorted_attachment_attractiveness):
                                index += 1
                                order_item_impossible = True
                                # Remove order item from route plan of all attachments if it is not possible to assign it to all necessary attachments
                                for attachment, route in route_plan_attachment.items():
                                    if best_order_item.id in route:
                                        route.remove(best_order_item.id)
                                break

                            # Select the best attachment for the order item
                            best_attachment = sorted_attachment_attractiveness[attachment_index]

                            # If the attachment has no planned order items yet, assign the order item to the attachment
                            if len(route_plan_attachment[best_attachment.id]) == 0:
                                route_plan_attachment[best_attachment.id].append(best_order_item.id)
                                attachment_planned[best_attachment] = True
                                attachment_task_assigned = True

                            # If the attachment has planned order items, assign the order item to the attachment according to the order item's predecessors and successors
                            elif len(route_plan_attachment[best_attachment.id]) > 0:
                                order_item_index_attachment_route = 0

                                # Check predecerssor and successor of the order item
                                while not attachment_task_assigned:
                                    current_order_item = next((order_item for order_item in self.data.order_items if order_item.status == True and order_item.id == route_plan_attachment[best_attachment.id][order_item_index_attachment_route]))

                                    # If the best order item is not a successor or predecessor of the current order item it can not be assigned to the attachment
                                    # Continue to next attachment in attachment_attractiveness
                                    if current_order_item not in best_attachment._successors[best_order_item] and current_order_item not in best_attachment._predecessors[best_order_item]:
                                        attachment_index += 1
                                        break

                                    # If the current order item is a successor of the best order item, assign the best order item to the attachment before the current order item
                                    if current_order_item in best_attachment._successors[best_order_item]:
                                        route_plan_attachment[best_attachment.id].insert(order_item_index_attachment_route, best_order_item.id)
                                        attachment_task_assigned = True

                                    # Check next order item in route plan of the attachment for predecessors and successors
                                    order_item_index_attachment_route += 1

                                    # If length of route plan is reached, check if the current order item is a predecessor of the best order item
                                    if order_item_index_attachment_route == len(route_plan_attachment[best_attachment.id]):
                                        # If the current order item is a predecessor of the best order item, assign the best order item to the attachment after the current order item (in the end of the route plan)
                                        if current_order_item in best_attachment._predecessors[best_order_item]:
                                            route_plan_attachment[best_attachment.id].append(best_order_item.id)
                                            attachment_task_assigned = True

                            
                # Continue to next order item if order item is not assigned to an attachment
                if len(best_order_item.equipment_types) > 0:
                    if not attachment_task_assigned:
                        continue
                

                # Assign machine to order item according to machine attractiveness
                machine_attractiveness = dict()
                for machine in self.data.machines:
                    if best_order_item in machine._possible_order_items[best_order]:
                        
                        # Default driver value for machine attractiveness --> Highers chances to select a machine with the worker as default driver
                        if worker.personal_number in machine._default_drivers:
                            default_driver = True
                        else:
                            default_driver = False
                        
                        # Calculate machine attractiveness for this order item for all potential machines
                        #possible_order_items_best_order = [order_item for order_item in self.data.order_items if order_item in machine._possible_order_items[best_order] and order_item not in self.data.planned_shifts_machine[best_order]]
                        machine_attractiveness[machine] = {"machine_planned": machine_planned[machine],
                                                           "worker_default_driver": default_driver,
                                                           "possible_default_drivers": len(machine._default_drivers)}
                                                           #"posible_order_items_best_order": len(possible_order_items_best_order)}                        


                # Sort machines by attractiveness
                if len(machine_attractiveness) > 0:
                    sorted_machine_attractiveness = self.machine_attractiveness_function(machine_attractiveness)
                else:
                    index += 1
                    continue

                # Index needed to iterate through sorted machines if a specific machine is not suitable
                machine_index = 0

                # Assign order item to machine as long as no suitable machine is found
                machine_task_assigned = False
                while not machine_task_assigned:
                    
                    # Break to next order item if there is no suitable machine for the current order item
                    if machine_index == len(sorted_machine_attractiveness):
                        index += 1
                        # Remove order item from route plan of all attachments if it is not possible to assign it to a machine
                        for attachment, route in route_plan_attachment.items():
                            if best_order_item.id in route:
                                route.remove(best_order_item.id)
                        break
                    
                    # Select the best machine for the order item --> Could be changed to roulette wheel selection
                    best_machine = sorted_machine_attractiveness[machine_index]

                    # If the machine has no planned order items yet, assign the order item to the machine
                    if len(route_plan_machine[best_machine.id]) == 0:
                        route_plan_machine[best_machine.id].append(best_order_item.id)
                        machine_planned[best_machine] = True
                        machine_task_assigned = True
                        self.data.planned_shifts_machine[best_order].append(best_order_item)

                    # If the machine has planned order items, assign the order item to the machine according to the order item's predecessors and successors
                    elif len(route_plan_machine[best_machine.id]) > 0:
                        order_item_index_machine_route = 0
                        
                        # Check predecerssor and successor of the order item
                        while not machine_task_assigned:
                            current_order_item = next((order_item for order_item in self.data.order_items if order_item.status == True and order_item.id == route_plan_machine[best_machine.id][order_item_index_machine_route]))
                            
                            # If the best order item is not a successor or predecessor of the current order item it can not be assigned to the machine
                            # Continue to next machine in machine_attractiveness
                            if current_order_item not in best_machine._successors[best_order_item] and current_order_item not in best_machine._predecessors[best_order_item]:
                                machine_index += 1
                                break
                            
                            # If the current order item is a successor of the best order item, assign the best order item to the machine before the current order item
                            if current_order_item in best_machine._successors[best_order_item]:
                                route_plan_machine[best_machine.id].insert(order_item_index_machine_route, best_order_item.id)
                                machine_task_assigned = True
                                self.data.planned_shifts_machine[best_order].append(best_order_item)
                            
                            # Check next order item in route plan of the machine for predecessors and successors
                            order_item_index_machine_route += 1

                            # If length of route plan is reached, check if the current order item is a predecessor of the best order item
                            if order_item_index_machine_route == len(route_plan_machine[best_machine.id]):
                                # If the current order item is a predecessor of the best order item, assign the best order item to the machine after the current order item (in the end of the route plan)
                                if current_order_item in best_machine._predecessors[best_order_item]:
                                    route_plan_machine[best_machine.id].append(best_order_item.id)
                                    machine_task_assigned = True
                                    self.data.planned_shifts_machine[best_order].append(best_order_item)
                                # If the current order item is not a predecessor of the best order item, continue to next machine in machine_attractiveness
                                else:
                                    machine_index += 1
                                    break

                
                # If the order item is assigned to a machine, assign the order item to the worker
                if machine_task_assigned:                       

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
                                    attractiveness[order_item] = {"order_priority": order.priority["borda_count_ahp"], "dynamic_percentage": order.dynamic_percentage, "time_difference": time_difference}

                    # Activate Attractiveness function and break to next worker if no suitable order item is left
                    if len(attractiveness) > 0:
                        sorted_attractiveness = self.order_item_attractiveness_function(attractiveness)
                    else:
                        break

                    # Reset index for the next iteration
                    index = 0

                    

        # Caluclate sum of planned shifts in comparison to all order items
        sum_of_planned_shifts = 0
        for order in self.data.orders:
            if order.status == True:
                sum_of_planned_shifts += len(self.data.planned_shifts_worker[order])
        sum_of_order_items = 0
        for order in self.data.orders:
            if order.status == True:
                sum_of_order_items += len(greedy_order_items[order])
        


        # Check feasibility of the solution
        start_solution = Solution(route_plan_worker, route_plan_machine, route_plan_attachment, self.data)
        
        feasible = start_solution.feasibility_check()

        if feasible:
            print("Solution is feasible")
            self.EvaluationLogic.evaluate(start_solution)
            #self.ParetoSolutions.ParetoFront.append(start_solution)
            return start_solution
        else:
            raise Exception("Solution is not feasible")



    def order_item_attractiveness_function(self, attractiveness):
        ''' Attractiveness function for order items'''


        min_order_priority = min(attributes["order_priority"] for attributes in attractiveness.values())
        max_order_priority = max(attributes["order_priority"] for attributes in attractiveness.values())

        min_time_difference = min(attributes["time_difference"] for attributes in attractiveness.values())
        max_time_difference = max(attributes["time_difference"] for attributes in attractiveness.values())

        if self.order_item_attractiveness_technique == "balanced_greedy":
            for order_item, attributes in attractiveness.items():
                order_priority_value = (max_order_priority - attributes["order_priority"]) / (max_order_priority - min_order_priority + 1e-6)
                dynamic_percentage_value = attributes["dynamic_percentage"]
                time_difference_value = (max_time_difference - attributes["time_difference"]) / (max_time_difference - min_time_difference + 1e-6)

                attractiveness[order_item] = order_priority_value + dynamic_percentage_value + time_difference_value

            sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)

        
        elif self.order_item_attractiveness_technique == "order_priority_importance":
            for order_item, attributes in attractiveness.items():
                order_priority_value = (max_order_priority - attributes["order_priority"]) / (max_order_priority - min_order_priority + 1e-6)
                dynamic_percentage_value = attributes["dynamic_percentage"]
                time_difference_value = (max_time_difference - attributes["time_difference"]) / (max_time_difference - min_time_difference + 1e-6)

                attractiveness[order_item] = {"order_priority": order_priority_value, "value": dynamic_percentage_value + time_difference_value}

            sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["order_priority"], attractiveness[x]["value"]), reverse=True)


        elif self.order_item_attractiveness_technique == "dynamic_percentage_importance":
            for order_item, attributes in attractiveness.items():
                order_priority_value = (max_order_priority - attributes["order_priority"]) / (max_order_priority - min_order_priority + 1e-6)
                dynamic_percentage_value = attributes["dynamic_percentage"]
                time_difference_value = (max_time_difference - attributes["time_difference"]) / (max_time_difference - min_time_difference + 1e-6)

                attractiveness[order_item] = {"dynamic_percentage": dynamic_percentage_value, "value": order_priority_value + time_difference_value}

            sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["dynamic_percentage"], attractiveness[x]["value"]), reverse=True)


        elif self.order_item_attractiveness_technique == "time_difference_importance":
            for order_item, attributes in attractiveness.items():
                order_priority_value = (max_order_priority - attributes["order_priority"]) / (max_order_priority - min_order_priority + 1e-6)
                dynamic_percentage_value = attributes["dynamic_percentage"]
                time_difference_value = (max_time_difference - attributes["time_difference"]) / (max_time_difference - min_time_difference + 1e-6)

                attractiveness[order_item] = {"time_difference": time_difference_value, "value": order_priority_value + dynamic_percentage_value}

            sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["time_difference"], attractiveness[x]["value"]), reverse=True)

        

        return sorted_attractiveness



        # Non scaled version
        '''
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

            sorted_attractiveness = sorted(attractiveness, key=lambda x: (-attractiveness[x]["dynamic_percentage"], -attractiveness[x]["value"]))


        elif self.order_item_attractiveness_technique == "order_priority_importance":
            for order_item, attributes in attractiveness.items():
                attractiveness[order_item]["value"] = attributes["dynamic_percentage"] + (1/attributes["time_difference"])

            sorted_attractiveness = sorted(attractiveness, key=lambda x: (attractiveness[x]["order_priority"], -attractiveness[x]["value"]))
        
            
        return sorted_attractiveness
        '''

        
    def machine_attractiveness_function(self, attractiveness):
            ''' Attractiveness function for machines'''

            

            min_drivers = min(attributes["possible_default_drivers"] for attributes in attractiveness.values())
            max_drivers = max(attributes["possible_default_drivers"] for attributes in attractiveness.values())


            if self.machine_attractiveness_technique == "balanced_greedy":
                for machine, attributes in attractiveness.items():
                    machine_planned_value = 1 if attributes["machine_planned"] else 0
                    default_driver_value = 1 if attributes["worker_default_driver"] else 0

                    possible_default_drivers_value = ((attributes["possible_default_drivers"] - min_drivers) / (max_drivers - min_drivers + 1e-6))

                    attractiveness[machine] = (machine_planned_value + default_driver_value + possible_default_drivers_value)

                sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)


            elif self.machine_attractiveness_technique == "machine_planned_importance":
                for machine, attributes in attractiveness.items():
                    machine_planned_value = 1 if attributes["machine_planned"] else 0
                    default_driver_value = 1 if attributes["worker_default_driver"] else 0

                    possible_default_drivers_value = ((attributes["possible_default_drivers"] - min_drivers) / (max_drivers - min_drivers + 1e-6))

                    attractiveness[machine] = {"machine_planned": machine_planned_value, "value": default_driver_value + possible_default_drivers_value}

                sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["machine_planned"], attractiveness[x]["value"]), reverse=True)

            
            elif self.machine_attractiveness_technique == "worker_default_driver_importance":
                for machine, attributes in attractiveness.items():
                    machine_planned_value = 1 if attributes["machine_planned"] else 0
                    default_driver_value = 1 if attributes["worker_default_driver"] else 0

                    possible_default_drivers_value = ((attributes["possible_default_drivers"] - min_drivers) / (max_drivers - min_drivers + 1e-6))

                    attractiveness[machine] = {"worker_default_driver": default_driver_value, "value": machine_planned_value + possible_default_drivers_value}

                sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["worker_default_driver"], attractiveness[x]["value"]), reverse=True)

            
            elif self.machine_attractiveness_technique == "possible_default_drivers_importance":
                for machine, attributes in attractiveness.items():
                    machine_planned_value = 1 if attributes["machine_planned"] else 0
                    default_driver_value = 1 if attributes["worker_default_driver"] else 0

                    possible_default_drivers_value = ((attributes["possible_default_drivers"] - min_drivers) / (max_drivers - min_drivers + 1e-6))

                    attractiveness[machine] = {"possible_default_drivers": possible_default_drivers_value, "value": machine_planned_value + default_driver_value}

                sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["possible_default_drivers"], attractiveness[x]["value"]), reverse=True)



            
            return sorted_attractiveness
        
    # Version with possible order items best order which is the same for every machine that might be possible
    '''
    def machine_attractiveness_function(self, attractiveness):
        Attractiveness function for machines

        

        min_drivers = min(attributes["possible_default_drivers"] for attributes in attractiveness.values())
        max_drivers = max(attributes["possible_default_drivers"] for attributes in attractiveness.values())

        min_order_items = min(attributes["posible_order_items_best_order"] for attributes in attractiveness.values())
        max_order_items = max(attributes["posible_order_items_best_order"] for attributes in attractiveness.values())


        if self.machine_attractiveness_technique == "balanced_greedy":
            for machine, attributes in attractiveness.items():
                machine_planned_value = 1 if attributes["machine_planned"] else 0
                default_driver_value = 1 if attributes["worker_default_driver"] else 0

                possible_default_drivers_value = ((attributes["possible_default_drivers"] - min_drivers) / (max_drivers - min_drivers + 1e-6))
                possible_order_items_value = ((attributes["posible_order_items_best_order"] - min_order_items) / (max_order_items - min_order_items + 1e-6))

                attractiveness[machine] = (machine_planned_value + default_driver_value + possible_default_drivers_value + possible_order_items_value)

            sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)


        elif self.machine_attractiveness_technique == "machine_planned_importance":
            for machine, attributes in attractiveness.items():
                machine_planned_value = 1 if attributes["machine_planned"] else 0
                default_driver_value = 1 if attributes["worker_default_driver"] else 0

                possible_default_drivers_value = ((attributes["possible_default_drivers"] - min_drivers) / (max_drivers - min_drivers + 1e-6))
                possible_order_items_value = ((attributes["posible_order_items_best_order"] - min_order_items) / (max_order_items - min_order_items + 1e-6))

                attractiveness[machine] = {"machine_planned": machine_planned_value, "value": default_driver_value + possible_default_drivers_value + possible_order_items_value}

            sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["machine_planned"], attractiveness[x]["value"]), reverse=True)

        
        elif self.machine_attractiveness_technique == "worker_default_driver_importance":
            for machine, attributes in attractiveness.items():
                machine_planned_value = 1 if attributes["machine_planned"] else 0
                default_driver_value = 1 if attributes["worker_default_driver"] else 0

                possible_default_drivers_value = ((attributes["possible_default_drivers"] - min_drivers) / (max_drivers - min_drivers + 1e-6))
                possible_order_items_value = ((attributes["posible_order_items_best_order"] - min_order_items) / (max_order_items - min_order_items + 1e-6))

                attractiveness[machine] = {"worker_default_driver": default_driver_value, "value": machine_planned_value + possible_default_drivers_value + possible_order_items_value}

            sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["worker_default_driver"], attractiveness[x]["value"]), reverse=True)

        
        elif self.machine_attractiveness_technique == "possible_default_drivers_importance":
            for machine, attributes in attractiveness.items():
                machine_planned_value = 1 if attributes["machine_planned"] else 0
                default_driver_value = 1 if attributes["worker_default_driver"] else 0

                possible_default_drivers_value = ((attributes["possible_default_drivers"] - min_drivers) / (max_drivers - min_drivers + 1e-6))
                possible_order_items_value = ((attributes["posible_order_items_best_order"] - min_order_items) / (max_order_items - min_order_items + 1e-6))

                attractiveness[machine] = {"possible_default_drivers": possible_default_drivers_value, "value": machine_planned_value + default_driver_value + possible_order_items_value}

            sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["possible_default_drivers"], attractiveness[x]["value"]), reverse=True)




        elif self.machine_attractiveness_technique == "posible_order_items_best_order_importance":
            for machine, attributes in attractiveness.items():
                machine_planned_value = 1 if attributes["machine_planned"] else 0
                default_driver_value = 1 if attributes["worker_default_driver"] else 0

                possible_default_drivers_value = ((attributes["possible_default_drivers"] - min_drivers) / (max_drivers - min_drivers + 1e-6))
                possible_order_items_value = ((attributes["posible_order_items_best_order"] - min_order_items) / (max_order_items - min_order_items + 1e-6))

                attractiveness[machine] = {"posible_order_items_best_order": possible_order_items_value, "value": machine_planned_value + default_driver_value + possible_default_drivers_value}

            sorted_attractiveness = sorted(attractiveness.keys(), key=lambda x: (attractiveness[x]["posible_order_items_best_order"], attractiveness[x]["value"]), reverse=True)

        
        return sorted_attractiveness
 

        # Non scaled version

        if self.machine_attractiveness_technique == "balanced_greedy":
            for machine, attributes in attractiveness.items():
                machine_planned_value = 1 if attributes["machine_planned"] else 0
                default_driver_value = 1 if attributes["worker_default_driver"] else 0

                attractiveness[machine] = (machine_planned_value + default_driver_value - (1/(attributes["possible_default_drivers"] + 0.001)) - (1/attributes["posible_order_items_best_order"] + 0.001))

            sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)


        elif self.machine_attractiveness_technique == "machine_planned_importance":
            for machine, attributes in attractiveness.items():
                machine_planned_value = 1 if attributes["machine_planned"] else 0
                default_driver_value = 1 if attributes["worker_default_driver"] else 0

                attractiveness[machine]["value"] = (default_driver_value) - (1/(attributes["possible_default_drivers"] + 0.001)) - (1/attributes["posible_order_items_best_order"] + 0.001)

            sorted_attractiveness = sorted(attractiveness, key=lambda x: (attractiveness[x]["machine_planned"], -attractiveness[x]["value"]))

        return sorted_attractiveness
        '''




        
