import numpy 
from copy import deepcopy
from InputData import InputData
from OutputData import Solution

class EvaluationLogic:
    ''' Evalution Objects to calculate objectives of the given solutions'''

    def __init__(self, data:InputData):
        ''' Initialize by adding data'''
        self.data = data


    def calculate_swap_shift_machine_delta(self, move):
        
        # Calculate the extra transport distance
        move.MachineRouteIndex1 = move.MachineRoute1.index(move.OrderItemID2)
        delta_transport_distance = 0
        if len(move.MachineRoute1) == 1:
            predecessor_id = None
            successor_id = None
        elif move.MachineRouteIndex1 == 0:
            predecessor_id = None
            successor_id = move.MachineRoute1[move.MachineRouteIndex1 + 1]
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID2][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteIndex1 == len(move.MachineRoute1) - 1:
            predecessor_id = move.MachineRoute1[move.MachineRouteIndex1 - 1]
            successor_id = None
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID2][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.MachineRoute1[move.MachineRouteIndex1 - 1]
            successor_id = move.MachineRoute1[move.MachineRouteIndex1 + 1]
            delta_transport_distance += (((self.data.transport_routes_order_item[move.OrderItemID2][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID2][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
        
        move.MachineRouteIndex2 = move.MachineRoute2.index(move.OrderItemID1)
        if len(move.MachineRoute2) == 1:
            predecessor_id = None
            successor_id = None
        elif move.MachineRouteIndex2 == 0:
            predecessor_id = None
            successor_id = move.MachineRoute2[move.MachineRouteIndex2 + 1]
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID1][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteIndex2 == len(move.MachineRoute2) - 1:
            predecessor_id = move.MachineRoute2[move.MachineRouteIndex2 - 1]
            successor_id = None
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID1][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.MachineRoute2[move.MachineRouteIndex2 - 1]
            successor_id = move.MachineRoute2[move.MachineRouteIndex2 + 1]
            delta_transport_distance += (((self.data.transport_routes_order_item[move.OrderItemID1][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID1][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
            
        

        if len(move.MachineRoute1Original) == 1:
            predecessor_id = None
            successor_id = None
        elif move.MachineRouteTakenIndex1 == 0:
            predecessor_id = None
            successor_id = move.MachineRoute1Original[move.MachineRouteTakenIndex1 + 1]
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID1][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteTakenIndex1 == len(move.MachineRoute1Original) - 1:
            predecessor_id = move.MachineRoute1Original[move.MachineRouteTakenIndex1 - 1]
            successor_id = None
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID1][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.MachineRoute1Original[move.MachineRouteTakenIndex1 - 1]
            successor_id = move.MachineRoute1Original[move.MachineRouteTakenIndex1 + 1]
            delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemID1][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID1][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
            
        if len(move.MachineRoute2Original) == 1:
            predecessor_id = None
            successor_id = None
        elif move.MachineRouteTakenIndex2 == 0:
            predecessor_id = None
            successor_id = move.MachineRoute2Original[move.MachineRouteTakenIndex2 + 1]
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID2][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteTakenIndex2 == len(move.MachineRoute2Original) - 1:
            predecessor_id = move.MachineRoute2Original[move.MachineRouteTakenIndex2 - 1]
            successor_id = None
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID2][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.MachineRoute2Original[move.MachineRouteTakenIndex2 - 1]
            successor_id = move.MachineRoute2Original[move.MachineRouteTakenIndex2 + 1]
            delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemID2][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID2][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
        
                                                                                                                                                                        
        # Calculate the extra driver violation
        machine_1 = self.data.machines[move.MachineID1]
        machine_2 = self.data.machines[move.MachineID2]

        delta_driver_violation = 0
        if move.WorkerID1 in machine_1.default_drivers:
            delta_driver_violation += 1

        if move.WorkerID2 in machine_2.default_drivers:
            delta_driver_violation += 1
        
        if move.WorkerID1 in machine_2.default_drivers:
            delta_driver_violation -= 1
        
        if move.WorkerID2 in machine_1.default_drivers:
            delta_driver_violation -= 1


        delta = {}
        delta["transport_distance"] = delta_transport_distance
        delta["driver_violation"] = delta_driver_violation

        print(f"Delta: {delta}")

        delta = delta["transport_distance"] + delta["driver_violation"]

        print(f"Delta: {delta}")

        return delta
        
    def calculate_swap_shift_external_delta(self, move):
        ''' Calculate the delta of the objective function value when swapping two order items between two external workers'''

        # Calculate the extra commute distance
        delta_commute_distance = (+ ((2*self.data.work_routes_order_item[move.WorkerID][move.OrderItemIDExt] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                - ((2*self.data.work_routes_order_item[move.WorkerID][move.OrderItemIDInt] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance)))


        # Calculate the extra transport distance
        delta_transport_distance = 0

        if len(move.MachineRoute) == 1:
            predecessor_id = None
            successor_id = None
        elif move.MachineRouteIndex == 0:
            predecessor_id = None
            successor_id = move.MachineRoute[move.MachineRouteIndex + 1]
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemIDExt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemIDInt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteIndex == len(move.MachineRoute) - 1:
            predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
            successor_id = None
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemIDExt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemIDInt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
            successor_id = move.MachineRoute[move.MachineRouteIndex + 1]
            delta_transport_distance += (((self.data.transport_routes_order_item[move.OrderItemIDExt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemIDExt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
            delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemIDInt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemIDInt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
            
        
        # Calculate the precentage difference this order item makes
        delta_dynamic_percentage_order = 0
        for order in self.data.orders:
            if move.OrderItemIDExt in order.order_item_ids:
                delta_dynamic_percentage_order += (1 / len(order.order_item_ids)) + move.DynamicPercentageExt
            if move.OrderItemIDInt in order.order_item_ids:
                delta_dynamic_percentage_order -= (1 / len(order.order_item_ids)) + move.DynamicPercentageInt


        delta = {}
        delta["dynamic_percentage_order"] = delta_dynamic_percentage_order
        delta["commute_distance"] = delta_commute_distance
        delta["transport_distance"] = delta_transport_distance

        print(f"Delta: {delta}")

        delta = [delta["dynamic_percentage_order"], delta["commute_distance"] + delta["transport_distance"]]

        print(f"Delta: {delta}")

        return delta
    
    def calculate_replace_shift_machine_delta(self, move):
        ''' Calculate the delta of the objective function value when replacing an order item between two machines'''

        # Calculate the extra transport distance
        delta_transport_distance = 0
        if len(move.MachineRoute2) == 1:
            predecessor_id = None
            successor_id = None
        elif move.MachineRouteIndex2 == 0:
            predecessor_id = None
            successor_id = move.MachineRoute2[move.MachineRouteIndex2 + 1]
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteIndex2 == len(move.MachineRoute2) - 1:
            predecessor_id = move.MachineRoute2[move.MachineRouteIndex2 - 1]
            successor_id = None
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.MachineRoute2[move.MachineRouteIndex2 - 1]
            successor_id = move.MachineRoute2[move.MachineRouteIndex2 + 1]
            delta_transport_distance += (((self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)) 
        
        if len(move.MachineRoute1) == 0:
            predecessor_id = None
            successor_id = None
            delta_transport_distance -= 0
        elif move.MachineRouteIndex1 == 0:
            predecessor_id = None
            successor_id = move.MachineRoute1[move.MachineRouteIndex1]
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteIndex1 == len(move.MachineRoute1):
            predecessor_id = move.MachineRoute1[move.MachineRouteIndex1 - 1]
            successor_id = None
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.MachineRoute1[move.MachineRouteIndex1 - 1]
            successor_id = move.MachineRoute1[move.MachineRouteIndex1]
            delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))


        # Calculate the extra driver violation
        machine_1 = self.data.machines[move.MachineID1]
        machine_2 = self.data.machines[move.MachineID2]

        delta_driver_violation = 0
        if move.WorkerID in machine_1.default_drivers:
            delta_driver_violation += 1

        if move.WorkerID in machine_2.default_drivers:
            delta_driver_violation -= 1

        # Calculate if a machine lost his last order item
        if len(move.MachineRoute1) == 0:
            delta_machine_count = -1
        else:
            delta_machine_count = 0

        if len(move.MachineRoute2) == 1:
            delta_machine_count += 1

        delta = {}
        delta["transport_distance"] = delta_transport_distance
        delta["driver_violation"] = delta_driver_violation
        delta["machine_count"] = delta_machine_count

        #print(f"Delta: {delta}")

        delta = delta["transport_distance"] + delta["driver_violation"] + delta["machine_count"]

        #print(f"Delta: {delta}")

        return delta

    def calculate_insert_shift_delta(self, move):
        ''' Calculate the delta of the objective function value when inserting an order item into a route'''
        

        # Calculate the extra commute distance
        delta_commute_distance = ((2*self.data.work_routes_order_item[move.WorkerID][move.OrderItemID] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))

        # Calculate the extra transport distance
        if len(move.MachineRoute) == 1:
            predecessor_id = None
            successor_id = None
            delta_transport_distance = 0
        elif move.MachineRouteIndex == 0:
            predecessor_id = None
            successor_id = move.MachineRoute[move.MachineRouteIndex + 1] 
            delta_transport_distance = (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteIndex == len(move.MachineRoute) - 1:
            predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
            successor_id = None
            delta_transport_distance = (self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
            successor_id = move.MachineRoute[move.MachineRouteIndex + 1]
            delta_transport_distance = (((self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
        
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

        # Calculate percentage difference this order item makes
        for order in self.data.orders:
            if move.OrderItemID in order.order_item_ids:
                delta_dynamic_percentage_order = (1 / len(order.order_item_ids)) + move.DynamicPercentage

        
        # Calculate the number of attachments
        delta_attachment_count = 0
        for i in range(move.NumberOfAttachments):
            if len(getattr(move, f"AttachmentRoute_{i}")) > 0:
                delta_attachment_count += 1

        
        # Calculate the extra transport distance of the attachments
        delta_transport_distance_attachments = 0
        for i in range(move.NumberOfAttachments):
            if len(getattr(move, f"AttachmentRoute_{i}")) == 1:
                predecessor_id = None
                successor_id = None
            elif getattr(move, f"AttachmentRouteIndex_{i}") == 0:
                predecessor_id = None
                successor_id = getattr(move, f"AttachmentRoute_{i}")[getattr(move, f"AttachmentRouteIndex_{i}") + 1]
                delta_transport_distance_attachments += (self.data.transport_routes_order_item[getattr(move, f"AttachmentID_{i}")][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif getattr(move, f"AttachmentRouteIndex_{i}") == len(getattr(move, f"AttachmentRoute_{i}")) - 1:
                predecessor_id = getattr(move, f"AttachmentRoute_{i}")[getattr(move, f"AttachmentRouteIndex_{i}") - 1]
                successor_id = None
                delta_transport_distance_attachments += (self.data.transport_routes_order_item[getattr(move, f"AttachmentID_{i}")][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = getattr(move, f"AttachmentRoute_{i}")[getattr(move, f"AttachmentRouteIndex_{i}") - 1]
                successor_id = getattr(move, f"AttachmentRoute_{i}")[getattr(move, f"AttachmentRouteIndex_{i}") + 1]
                delta_transport_distance_attachments += (((self.data.transport_routes_order_item[getattr(move, f"AttachmentID_{i}")][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[getattr(move, f"AttachmentID_{i}")][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                
            

        



        delta = {}
        delta["dynamic_percentage_order"] = delta_dynamic_percentage_order
        delta["commute_distance"] = delta_commute_distance
        delta["transport_distance"] = delta_transport_distance
        delta["transport_distance_attachments"] = delta_transport_distance_attachments
        delta["driver_violation"] = delta_driver_violation
        delta["machine_count"] = delta_machine_count
        delta["worker_count"] = delta_worker_count
        delta["attachment_count"] = delta_attachment_count
        
        print(f"Delta: {delta}")


        delta = [delta["dynamic_percentage_order"], delta["commute_distance"] + delta["transport_distance"] + delta["driver_violation"] + delta["machine_count"] + delta["worker_count"] + delta["attachment_count"] + delta["transport_distance_attachments"]]
        #delta =[delta["dynamic_percentage_order"], delta["attachment_count"]]

        print(f"Delta: {delta}")

        return delta
    
    def calculate_swap_shift_worker_delta(self, move):
        ''' Calculate the delta of the objective function value when swapping two order items between two workers'''

        # Calculate the extra commute distance
        delta_commute_distance = (+ ((2*self.data.work_routes_order_item[move.WorkerID1][move.OrderItemID2] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 + ((2*self.data.work_routes_order_item[move.WorkerID2][move.OrderItemID1] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 - ((2*self.data.work_routes_order_item[move.WorkerID1][move.OrderItemID1] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 - ((2*self.data.work_routes_order_item[move.WorkerID2][move.OrderItemID2] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance)))
                                  
        if delta_commute_distance > -1**-2 and delta_commute_distance < 0:
            delta_commute_distance = 0


        # Calculate extra driver violation
        machine_1 = self.data.machines[move.MachineID1]
        machine_2 = self.data.machines[move.MachineID2]

        delta_driver_violation = 0
        if move.WorkerID1 in machine_1.default_drivers:
            delta_driver_violation += 1

        if move.WorkerID2 in machine_2.default_drivers:
            delta_driver_violation += 1

        if move.WorkerID1 in machine_2.default_drivers:
            delta_driver_violation -= 1
        
        if move.WorkerID2 in machine_1.default_drivers:
            delta_driver_violation -= 1


        delta = {}
        delta["commute_distance"] = delta_commute_distance
        delta["driver_violation"] = delta_driver_violation

        print(f"Delta: {delta}")



        delta = (delta["commute_distance"] + delta["driver_violation"])

        print(f"Delta: {delta}")


        return delta
    
    def calculate_replace_shift_worker_delta(self, move):
        ''' Calculate the delta of the objective function value when replacing an order item between two workers'''

        # Calculate the extra commute distance
        delta_commute_distance = (((2*self.data.work_routes_order_item[move.WorkerID2][move.OrderItemID] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 - ((2*self.data.work_routes_order_item[move.WorkerID1][move.OrderItemID] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance)))
        

        # Calculate extra driver violation
        machine = self.data.machines[move.MachineID]

        delta_driver_violation = 0
        if move.WorkerID1 in machine.default_drivers:
            delta_driver_violation += 1

        if move.WorkerID2 in machine.default_drivers:
            delta_driver_violation -= 1

        # Calculate if a worker lost his last order item
        if len(move.WorkerRoute1) == 0:
            delta_worker_count = -1
        else:
            delta_worker_count = 0

        if len(move.WorkerRoute2) == 1:
            delta_worker_count += 1

        

        delta = {}
        delta["commute_distance"] = delta_commute_distance
        delta["driver_violation"] = delta_driver_violation
        delta["worker_count"] = delta_worker_count

        print(f"Delta: {delta}")

        delta = delta["commute_distance"] + delta["driver_violation"] + delta["worker_count"]

        print(f"Delta: {delta}")


        return delta



    def evaluate(self, solution:Solution):
        
        self.categorizing_orders(solution)
        self.categorizing_machine_worker(solution)
        self.calculate_finished_order_items(solution)
        self.calculate_commute_distance(solution)
        self.calculate_transport_distance(solution)
        self.calculate_driver_violation(solution)
        self.calculate_machine_worker_attachment_count_and_utilization_time(solution)
        self.calculate_dynamic_percentage_order(solution)
        self.calculate_transport_distance_attachments(solution)


    def calculate_transport_distance_attachments(self, solution:Solution):
            ''' Calculate the total transport distance of the attachments'''

            for attachment_id, route in solution.route_plan_attachment.items():
                solution.transport_distance_per_attachment[attachment_id] = 0
                for i in range(len(route) - 1):
                    solution.transport_distance_per_attachment[attachment_id] += self.data.transport_routes_order_item[route[i]][route[i + 1]]
                print(f"Attachment: {attachment_id} --> Transport Distance: {solution.transport_distance_per_attachment[attachment_id]}")
                
            solution.total_transport_distance_attachments = sum(solution.transport_distance_per_attachment.values())

    def calculate_dynamic_percentage_order(self, solution:Solution):
        ''' Calculate the dynamic percentage of the solution'''

        finished_order_item_ids = [order_item_id for route in solution.route_plan_worker.values() for order_item_id in route]
       
        for order in self.data.orders:
            solution.dynamic_percentage_order[order.order_number] = 0
            for order_item_id in order.order_item_ids:
                if order_item_id in finished_order_item_ids:
                    solution.dynamic_percentage_order[order.order_number] += 1

            solution.dynamic_percentage_order[order.order_number] = solution.dynamic_percentage_order[order.order_number] / len(order.order_item_ids)
                
    def categorizing_orders(self, solution:Solution):
        ''' Categorize the orders into finished, semi-finished and not started orders'''

        all_planned_order_item_ids = [order_item_id for route in solution.route_plan_worker.values() for order_item_id in route]

        for order_item in self.data.order_items:
            if order_item.id not in all_planned_order_item_ids:
                solution.not_started_order_item_ids.append(order_item.id)
        

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

        for worker_id, route in solution.route_plan_worker.items():
            solution.commute_distance_per_worker[worker_id] = 0
            for i in range(len(route)):
                solution.commute_distance_per_worker[worker_id] += 2 * self.data.work_routes_order_item[worker_id][route[i]]
        

        solution.total_commute_distance = sum(solution.commute_distance_per_worker.values())

    def calculate_transport_distance(self, solution:Solution):
        ''' Calculate the total transport distance of the machines'''

        for machine_id, route in solution.route_plan_machine.items():
            solution.transport_distance_per_machine[machine_id] = 0
            for i in range(len(route) - 1):
                solution.transport_distance_per_machine[machine_id] += self.data.transport_routes_order_item[route[i]][route[i + 1]]

        solution.total_transport_distance = sum(solution.transport_distance_per_machine.values())

    def calculate_driver_violation(self, solution:Solution):
        ''' Calculate the total driver violation time of the workers'''

        for worker_id, route in solution.route_plan_worker.items():
            for i in range(len(route)):
                involved_machine_id = next((machine_id for machine_id in solution.route_plan_machine.keys() if route[i] in solution.route_plan_machine[machine_id]), None)
                involved_machine = next((machine for machine in self.data.machines if machine.id == involved_machine_id), None)
                if worker_id not in involved_machine.default_drivers:
                    solution.driver_violation += 1
  
    def calculate_machine_worker_attachment_count_and_utilization_time(self, solution:Solution):
        ''' Calculate the number of workers and machines'''

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


        for attachment_id, route in solution.route_plan_attachment.items():
            solution.attachment_utilization_time[attachment_id] = 0
            if len(route) > 0:
                solution.number_of_attachments += 1
            for order_item_id in route:
                solution.attachment_utilization_time[attachment_id] += self.data.order_items[order_item_id].duration
