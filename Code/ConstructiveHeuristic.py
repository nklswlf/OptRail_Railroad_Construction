
from OutputData import *
from InputData import *
from EvaluationLogic import *

class ConstructiveHeuristics:
    ''' Class for creating objects to run different constructive heuristics'''

    def __init__(self,  solutionPool:SolutionPool, evaluationLogic:EvaluationLogic):

        self.EvaluationLogic = evaluationLogic
        self._SolutionPool = solutionPool


    def Run(self, inputdata:InputData):
        ''' Run the constructive heuristic on the input data'''

        self.Greedy(inputdata)
    

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



        # Add % of sites to greedy_sites for initial solution
        percentage = 1 # 100% of sites
        total_order_amount = len(inputdata.orders)
        greedy_sites_amount = int(total_order_amount * 1)
        greedy_order_items = dict()
        for order in inputdata.orders:
            if order._priority["overall"] <= greedy_sites_amount:
                greedy_order_items[order] = [order_item for order_item in inputdata.order_items if order_item.order_number == order.order_number]

    
        route_plan_worker = dict()
        route_plan_machine = dict()

        machine_planned = dict()
        for machine in inputdata.machines:
            machine_planned[machine] = 0
            route_plan_machine[machine.id] = list()
            

        for worker in inputdata.workers:
            attractiveness = dict()
            route_plan_worker[worker.personal_number] = list()

            # Initialize attractiveness for each possible order item
            for order, order_items in greedy_order_items.items():
                for order_item in order_items:
                        if any(order_item in value_list for value_list in worker._possible_order_items.values()):
                            if order_item not in inputdata.planned_shifts_worker[order]:
                                time_difference = inputdata.start_date - order_item.start_time
                                time_difference = time_difference.total_seconds() / inputdata._seconds_a_day
                                attractiveness[order_item] = (1/order.priority["overall"]) + order.dynamic_percentage + (time_difference/2)

            sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)
            index = 0

            # Add order items to route plan for each worker
            while worker.work_hours <= inputdata._max_working_hours and len(attractiveness) > 0:
                
                if index == len(sorted_attractiveness):
                    break

                best_order_item = sorted_attractiveness[index]
                best_order = [order for order in inputdata.orders if order.order_number == best_order_item.order_number][0]
                
                # Break if worker is overworked
                if best_order_item.duration + worker.work_hours > inputdata._max_working_hours:
                    break
                

                # Assign machine to order item according to machine attractiveness
                machine_attractiveness = dict()
                for machine in inputdata.machines:
                    if best_order_item in machine._possible_order_items[best_order]:
                        
                        if worker.personal_number in machine._default_drivers:
                            default_driver_value = 10
                        else:
                            default_driver_value = 0

                        possible_order_items_best_order = [order_item for order_item in inputdata.order_items if order_item.order_number == best_order_item.order_number]
                        machine_attractiveness[machine] = machine_planned[machine] + len(machine._default_drivers) + len(possible_order_items_best_order) + default_driver_value
                



                sorted_machines = sorted(machine_attractiveness, key=machine_attractiveness.get, reverse=True)
                machine_index = 0

                
                task_assigned = False
                while not task_assigned:
                    
                    if machine_index == len(sorted_machines):
                        index += 1
                        break

                    best_machine = sorted_machines[machine_index]

                    if len(route_plan_machine[best_machine.id]) == 0:

                        route_plan_machine[best_machine.id].append(best_order_item.id)
                        machine_planned[best_machine] += 1
                        task_assigned = True
                        inputdata.planned_shifts_machine[best_order].append(best_order_item)

                    elif len(route_plan_machine[best_machine.id]) > 0:
                        order_item_index = 0
                        
                        while not task_assigned:
                            current_order_item = next((order_item for order_item in inputdata.order_items if order_item.id == route_plan_machine[best_machine.id][order_item_index]))
                            if current_order_item not in best_machine._successors[best_order_item] and current_order_item not in best_machine._predecessors[best_order_item]:
                                machine_index += 1
                                break
                            
                            
                            if current_order_item in best_machine._successors[best_order_item]:
                                route_plan_machine[best_machine.id].insert(order_item_index, best_order_item.id)
                                machine_planned[best_machine] += 1
                                task_assigned = True
                                inputdata.planned_shifts_machine[best_order].append(best_order_item)
                            
                            order_item_index += 1

                            if order_item_index == len(route_plan_machine[best_machine.id]):
                                if current_order_item in best_machine._predecessors[best_order_item]:
                                    route_plan_machine[best_machine.id].append(best_order_item.id)
                                    machine_planned[best_machine] += 1
                                    task_assigned = True
                                    inputdata.planned_shifts_machine[best_order].append(best_order_item)
                                else:
                                    machine_index += 1
                                    break

                
                if task_assigned:                       
                    #print(f"Route plan for machine {best_machine.id}: {route_plan_machine[best_machine.id]}")

                    # Update data
                    inputdata.planned_shifts_worker[best_order].append(best_order_item)
                    best_order.dynamic_percentage = len(inputdata.planned_shifts_worker[best_order]) / len(greedy_order_items[best_order])

                    route_plan_worker[worker.personal_number].append(best_order_item.id)

                    worker.work_hours += best_order_item.duration
                    attractiveness = dict()
                    for order, order_items in greedy_order_items.items():
                        for order_item in order_items:
                            if order_item not in inputdata.planned_shifts_worker[order]:
                                if order_item in worker._successors[best_order_item]:
                                    time_difference = best_order_item.end_time - order_item.start_time
                                    time_difference = time_difference.total_seconds() / inputdata._seconds_a_day
                                    attractiveness[order_item] = (1/order.priority["overall"]) + order.dynamic_percentage + (time_difference/2)
                                    sorted_attractiveness = sorted(attractiveness, key=attractiveness.get, reverse=True)
                                    index = 0


        for worker in inputdata.workers:        
            print(f"Route plan for worker {worker.personal_number}: {route_plan_worker[worker.personal_number]}")
            print(f"Work hours for worker {worker.personal_number}: {worker.work_hours}")


        # Calculate evaluation
        print("Dynamic percentage of order items")
        for order in greedy_order_items.keys():
            print(f"Order {order.order_number} has dynamic percentage {order.dynamic_percentage}")


        for machine in inputdata.machines:
            print(f"Route plan for machine {machine.id}: {route_plan_machine[machine.id]}")
        
        for order in inputdata.orders:
            order.dynamic_percentage = len(inputdata.planned_shifts_machine[order]) / len(greedy_order_items[order])
            print(f"Order {order.order_number} has dynamic percentage {order.dynamic_percentage}")




        Solution(route_plan_worker, route_plan_machine, inputdata).feasibility_check()



        '''
        
        for machine in inputdata.machines:
            route_plan_machine[machine.id] = list()
            possible_sites = list()

            # Finding first order item for each machine
            for order, order_items in greedy_order_items.items():
                for order_item in order_items:
                    if order_item in inputdata.planned_shifts_worker[order]:
                        if order_item not in inputdata.planned_shifts_machine[order]:
                            if order_item in machine._possible_order_items:
                                if order_item not in inputdata.planned_shifts_machine[order]:
                                    inputdata.planned_shifts_machine[order].append(order_item)
                                    route_plan_machine[machine.id].append(order_item.id)
                                    best_order_item = order_item
                                    possible_sites = machine._successors[order_item]
                                    route_plan_machine[machine.id].append(order_item.id)
                                    break
                if best_order_item:
                    break

            # Add order items to route plan for each machine
            while len(possible_sites) > 0:
                for order, order_items in greedy_order_items.items():
                    for order_item in order_items:
                        if order_item in inputdata.planned_shifts_worker[order]:
                            if order_item not in inputdata.planned_shifts_machine[order]:
                                if order_item in machine._successors[best_order_item]:
                                    if order_item not in inputdata.planned_shifts_machine[order]:
                                        inputdata.planned_shifts_machine[order].append(order_item)
                                        route_plan_machine[machine.id].append(order_item.id)
                                        best_order_item = order_item
                                        possible_sites = machine._successors[order_item]
                                        route_plan_machine[machine.id].append(order_item.id)

            

            print(f"Route plan for machine {machine.id}: {route_plan_machine[machine.id]}")

        # Calculate evaluation
        for order in inputdata.orders:
            order.dynamic_percentage = len(inputdata.planned_shifts_machine[order]) / len(greedy_order_items[order])

        # Perecentag dynamic percentage of order items
        print("Dynamic percentage of order items")
        for order in greedy_order_items.keys():
            print(f"Order {order.order_number} has dynamic percentage {order.dynamic_percentage}")
                    
                                    
        '''
            

                    




