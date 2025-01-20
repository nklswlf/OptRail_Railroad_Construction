
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

        # Add % of sites to greedy_sites for initial solution
        percentage = 1 # 100% of sites
        total_order_amount = len(inputdata.orders)
        greedy_sites_amount = int(total_order_amount * 1)
        greedy_order_items = dict()
        for order in inputdata.orders:
            if order._priority["overall"] <= greedy_sites_amount:
                greedy_order_items[order] = [order_item for order_item in inputdata.order_items if order_item.order_number == order.order_number]

    
        route_plan_worker = dict()
        for worker in inputdata.workers:
            attractiveness = dict()
            route_plan_worker[worker.personal_number] = list()

            # Initialize attractiveness for each possible order item
            for order, order_items in greedy_order_items.items():
                for order_item in order_items:
                    if order_item in worker._possible_order_items:
                        if order_item not in inputdata.planned_shifts[order]:
                            time_difference = inputdata.start_date - order_item.start_time
                            time_difference = time_difference.total_seconds() / inputdata._seconds_a_day
                            attractiveness[order_item] = (1/order_item.priority) + order.dynamic_percentage + (time_difference/2)
                            #print(f"Attractiveness of order item {order_item.id} is {attractiveness[order_item]}")

            # Add order items to route plan for each worker
            while worker.work_hours <= inputdata._max_working_hours and len(attractiveness) > 0:

                best_order_item = max(attractiveness, key=attractiveness.get)
                best_order = [order for order in inputdata.orders if order.order_number == best_order_item.order_number][0]
                inputdata.planned_shifts[best_order].append(best_order_item)
                best_order.dynamic_percentage = len(inputdata.planned_shifts[best_order]) / len(greedy_order_items[best_order])

                
                route_plan_worker[worker.personal_number].append(best_order_item.id)

                # Update data
                worker.work_hours += best_order_item.duration
                attractiveness = dict()
                for order, order_items in greedy_order_items.items():
                    for order_item in order_items:
                        if order_item not in inputdata.planned_shifts[order]:
                            if order_item in worker._successors[best_order_item]:
                                time_difference = best_order_item.end_time - order_item.start_time
                                time_difference = time_difference.total_seconds() / inputdata._seconds_a_day
                                attractiveness[order_item] = (1/order_item.priority) + order.dynamic_percentage + (time_difference/2)
                
            print(f"Route plan for worker {worker.personal_number}: {route_plan_worker[worker.personal_number]}")
            print(f"Work hours for worker {worker.personal_number}: {worker.work_hours}")

        # Perecentag dynamic percentage of order items
        print("Dynamic percentage of order items")
        for order in greedy_order_items.keys():
            print(f"Order {order.order_number} has dynamic percentage {order.dynamic_percentage}")



                

        
        route_plan_machine = dict()
        for machine in inputdata.machines:
            route_plan_machine[machine.id] = list()

