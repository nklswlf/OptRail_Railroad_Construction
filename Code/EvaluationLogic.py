import numpy 
from copy import deepcopy
from InputData import InputData
from OutputData import Solution

class EvaluationLogic:
    ''' Evalution Objects to calculate objectives of the given solutions'''

    def __init__(self, data:InputData):
        ''' Initialize by addinbg data'''
        self.data = data      


    def evaluate(self, solution:Solution):
        
        self.categorizing_orders(solution)
        self.calculate_finished_order_items(solution)
        self.calculate_commute_distance(solution)
        self.calculate_transport_distance(solution)
        self.calculate_driver_violation(solution)
        self.calculate_machine_worker_count_and_utilization_time(solution)



    def categorizing_orders(self, solution:Solution):
        ''' Categorize the orders into finished, semi-finished and not started orders'''
        print("\nCategorizing orders...")

        all_planned_order_item_ids = [order_item_id for route in solution.route_plan_worker.values() for order_item_id in route]

        for order in self.data.orders:
            solution.finished_orders.append(order)
            solution.not_started_orders.append(order)

        for order in self.data.orders:
            for order_item_id in order.order_item_ids:
                if order_item_id not in all_planned_order_item_ids:
                    solution.finished_orders.remove(order)
                    break

        for order in self.data.orders:
            for order_item_id in order.order_item_ids:
                if order_item_id in all_planned_order_item_ids:
                    solution.not_started_orders.remove(order)
                    break

        solution.semifinished_orders = [order for order in self.data.orders if order not in solution.finished_orders and order not in solution.not_started_orders]

        solution.share_finished_orders = len(solution.finished_orders) / len(self.data.orders) * 100

        solution.number_of_finished_orders = len(solution.finished_orders)



    def calculate_finished_order_items(self, solution:Solution):
        ''' Calculate the number of finished order items'''
        print("\nCalculating finished order items...")

        for worker_id, route in solution.route_plan_worker.items():
            for i in range(len(route)):
                solution.number_of_finished_order_items += 1

        checker = 0
        for machine_id, route in solution.route_plan_machine.items():
            for i in range(len(route)):
                checker += 1

        if checker == solution.number_of_finished_order_items:
            pass
        else:
            raise Exception("Number of finished order items is not equal to the number of finished order items of the machines")




    def calculate_commute_distance(self, solution:Solution):
        ''' Calculate the total commute distance of the workers'''
        print("\nCalculating commute distance...")

        for worker_id, route in solution.route_plan_worker.items():
            solution.commute_distance_per_worker[worker_id] = 0
            for i in range(len(route)):
                solution.commute_distance_per_worker[worker_id] += 2 * self.data.work_routes_order_item[worker_id][route[i]]
        

        solution.total_commute_distance = sum(solution.commute_distance_per_worker.values())

    
    def calculate_transport_distance(self, solution:Solution):
        ''' Calculate the total transport distance of the machines'''
        print("\nCalculating transport distance...")

        for machine_id, route in solution.route_plan_machine.items():
            solution.transport_distance_per_machine[machine_id] = 0
            for i in range(len(route) - 1):
                solution.transport_distance_per_machine[machine_id] += self.data.transport_routes_order_item[route[i]][route[i + 1]]

        solution.total_transport_distance = sum(solution.transport_distance_per_machine.values())


    def calculate_driver_violation(self, solution:Solution):
        ''' Calculate the total driver violation time of the workers'''
        print("\nCalculating driver violation...")

        for worker_id, route in solution.route_plan_worker.items():
            for i in range(len(route)):
                involved_machine_id = next((machine_id for machine_id in solution.route_plan_machine.keys() if route[i] in solution.route_plan_machine[machine_id]), None)
                involved_machine = next((machine for machine in self.data.machines if machine.id == involved_machine_id), None)
                if worker_id not in involved_machine.default_drivers:
                    solution.driver_violation += 1


    
    def calculate_machine_worker_count_and_utilization_time(self, solution:Solution):
        ''' Calculate the number of workers and machines'''
        print("\nCalculating machine and worker count...")

        for machine_id, route in solution.route_plan_machine.items():
            solution.machine_utilization_time[machine_id] = 0
            if len(route) > 0:
                solution.number_of_machines += 1
            for order_item_id in route:
                solution.machine_utilization_time[machine_id] += self.data.order_items[order_item_id].duration


        for worker_id, route in solution.route_plan_worker.items():
            solution.worker_work_time[worker_id] = 0
            if len(route) > 0:
                solution.number_of_workers += 1
            for order_item_id in route:
                solution.worker_work_time[worker_id] += self.data.order_items[order_item_id].duration

    
    
