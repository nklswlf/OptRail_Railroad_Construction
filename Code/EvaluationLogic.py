import numpy 
from copy import deepcopy
from InputData import InputData
from OutputData import Solution

class EvaluationLogic:
    ''' Evalution Objects to calculate objectives of the given solutions'''

    def __init__(self, data:InputData):
        ''' Initialize by adding data'''
        self.data = data




    def calculate_insert_shift_delta(self, move):
        ''' Calculate the delta of the objective function value when inserting an order item into a route'''
        

        # Calculate the extra commute distance
        delta_commute_distance = self.data.work_routes_order_item[move.WorkerID][move.OrderItemID] * 2

        # Calculate the extra transport distance
        if move.MachineRouteIndex == 0:
            predecessor_id = None
            successor_id = move.MachineRoute[move.MachineRouteIndex + 1] 
            delta_transport_distance = self.data.transport_routes_order_item[move.OrderItemID][successor_id] 
        elif move.MachineRouteIndex == len(move.MachineRoute) - 1:
            predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
            successor_id = None
            delta_transport_distance = self.data.transport_routes_order_item[move.OrderItemID][predecessor_id]
        else:
            predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
            successor_id = move.MachineRoute[move.MachineRouteIndex + 1]
            delta_transport_distance = self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] + self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.transport_routes_order_item[predecessor_id][successor_id]
        
        # Calculate the extra driver violation
        machine = self.data.machines[move.MachineID]
        if move.WorkerID not in machine.default_drivers:
            delta_driver_violation = 1
        else:
            delta_driver_violation = 0

        # Calculate if extra machine is used
        if len(move.MachineRoute) == 1:
            delta_machine_count = 1
        else:
            delta_machine_count = 0

        # Calculate the extra worker count
        if len(move.WorkerRoute) == 1:
            delta_worker_count = 1
        else:
            delta_worker_count = 0

        # Calculate the best dynamic percentage order




        delta = {}
        delta["commute_distance"] = delta_commute_distance
        delta["transport_distance"] = delta_transport_distance
        delta["driver_violation"] = delta_driver_violation
        delta["machine_count"] = delta_machine_count
        delta["worker_count"] = delta_worker_count

        delta = delta["commute_distance"] + delta["transport_distance"] + delta["driver_violation"] + delta["machine_count"] + delta["worker_count"]



        return delta






    def evaluate(self, solution:Solution):
        
        self.categorizing_orders(solution)
        self.categorizing_machine_worker(solution)
        self.calculate_finished_order_items(solution)
        self.calculate_commute_distance(solution)
        self.calculate_transport_distance(solution)
        self.calculate_driver_violation(solution)
        self.calculate_machine_worker_count_and_utilization_time(solution)
        self.calculate_dynamic_percentage_order(solution)


    def calculate_dynamic_percentage_order(self, solution:Solution):
        ''' Calculate the dynamic percentage of the solution'''
        print("\nCalculating dynamic percentage...")

        finished_order_item_ids = [order_item_id for route in solution.route_plan_worker.values() for order_item_id in route]
       
        for order in self.data.orders:
            solution.dynamic_percentage_order[order.order_number] = 0
            for order_item_id in order.order_item_ids:
                if order_item_id in finished_order_item_ids:
                    solution.dynamic_percentage_order[order.order_number] += 1

            solution.dynamic_percentage_order[order.order_number] = solution.dynamic_percentage_order[order.order_number] / len(order.order_item_ids)
                



    def categorizing_orders(self, solution:Solution):
        ''' Categorize the orders into finished, semi-finished and not started orders'''
        print("\nCategorizing orders...")

        all_planned_order_item_ids = [order_item_id for route in solution.route_plan_worker.values() for order_item_id in route]

        for order_item in self.data.order_items:
            if order_item.id not in all_planned_order_item_ids:
                solution.not_started_order_items.append(order_item)
        

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

    
    def categorizing_machine_worker(self, solution:Solution):
        ''' Categorize the machines and workers into finished, semi-finished and not started machines and workers'''
        print("\nCategorizing machines and workers...")

        all_planned_order_item_ids = [order_item_id for route in solution.route_plan_worker.values() for order_item_id in route]
        
        for machine, route in solution.route_plan_machine.items():
            if len(route) == 0:
                solution.unused_machines.append(machine)
            elif len(route) > 0:
                solution.used_machines.append(machine)

        for worker, route in solution.route_plan_worker.items():
            if len(route) == 0:
                solution.unused_workers.append(worker)
            elif len(route) > 0:
                solution.used_workers.append(worker)



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
            print("Number of finished order items is not equal to the number of finished order items of the machines")
            #raise Exception("Number of finished order items is not equal to the number of finished order items of the machines")




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

    
    
