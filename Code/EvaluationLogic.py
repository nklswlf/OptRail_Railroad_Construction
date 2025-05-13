from Code.InputData import InputData
from Code.OutputData import Solution

class EvaluationLogic:
    ''' Evalution Objects to calculate objectives of the given solutions'''

    def __init__(self, data:InputData):
        ''' Initialize by adding data'''
        self.data = data

    def calculate_insert_shift_delta(self, move):
        ''' Calculate the delta of the objective function value when inserting an order item into a route'''
        

        # Calculate the extra commute distance
        delta_commute_distance = ((self.data.work_routes_order_item[move.WorkerID][move.OrderItemID] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
        delta_commute_distance *= 2

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
        delta_attachment_distance = 0
        for i in range(move.NumberOfAttachments):
            if len(getattr(move, f"AttachmentRoute_{i}")) == 1:
                predecessor_id = None
                successor_id = None
            elif getattr(move, f"AttachmentRouteIndex_{i}") == 0:
                predecessor_id = None
                successor_id = getattr(move, f"AttachmentRoute_{i}")[getattr(move, f"AttachmentRouteIndex_{i}") + 1]
                delta_attachment_distance += (self.data.transport_routes_order_item[getattr(move, f"AttachmentID_{i}")][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif getattr(move, f"AttachmentRouteIndex_{i}") == len(getattr(move, f"AttachmentRoute_{i}")) - 1:
                predecessor_id = getattr(move, f"AttachmentRoute_{i}")[getattr(move, f"AttachmentRouteIndex_{i}") - 1]
                successor_id = None
                delta_attachment_distance += (self.data.transport_routes_order_item[getattr(move, f"AttachmentID_{i}")][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = getattr(move, f"AttachmentRoute_{i}")[getattr(move, f"AttachmentRouteIndex_{i}") - 1]
                successor_id = getattr(move, f"AttachmentRoute_{i}")[getattr(move, f"AttachmentRouteIndex_{i}") + 1]
                delta_attachment_distance += (((self.data.transport_routes_order_item[getattr(move, f"AttachmentID_{i}")][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[getattr(move, f"AttachmentID_{i}")][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                
            

        

        # 1️⃣ Single Delta Details as Dictionary
        delta_details = {
            "dynamic_percentage_order": -delta_dynamic_percentage_order,
            "commute_distance": delta_commute_distance,
            "transport_distance": delta_transport_distance,
            "attachment_distance": delta_attachment_distance,
            "driver_violation": delta_driver_violation,
            "machine_count": delta_machine_count,
            "worker_count": delta_worker_count,
            "attachment_count": delta_attachment_count,
        }


        # 2️⃣ Summary as List
        delta_summary = [
            delta_details["dynamic_percentage_order"],
            delta_details["commute_distance"]
            + delta_details["transport_distance"]
            + delta_details["driver_violation"]
            + delta_details["machine_count"]
            + delta_details["worker_count"]
            + delta_details["attachment_count"]
            + delta_details["attachment_distance"],
        ]


        return delta_summary, delta_details
    
    def calculate_swap_shift_external_delta(self, move):
        ''' Calculate the delta of the objective function value when swapping two order items between two external workers'''
        
        # Calculate the extra commute distance
        delta_commute_distance = (((self.data.work_routes_order_item[move.WorkerID][move.OrderItemIDExt] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                - ((self.data.work_routes_order_item[move.WorkerID][move.OrderItemIDInt] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance)))
        delta_commute_distance *= 2

        # Calculate the extra transport distance
        delta_transport_distance = 0


        if move.SameMachine:
            
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
                                            + (self.data.transport_routes_order_item[move.OrderItemIDExt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemIDInt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemIDInt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))

        else:
            if len(move.MachineRouteExt) == 1:
                predecessor_id = None
                successor_id = None
            elif move.MachineRouteIndexExt == 0:
                predecessor_id = None
                successor_id = move.MachineRouteExt[move.MachineRouteIndexExt + 1]
                delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemIDExt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif move.MachineRouteIndexExt == len(move.MachineRouteExt) - 1:
                predecessor_id = move.MachineRouteExt[move.MachineRouteIndexExt - 1]
                successor_id = None
                delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemIDExt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = move.MachineRouteExt[move.MachineRouteIndexExt - 1]
                successor_id = move.MachineRouteExt[move.MachineRouteIndexExt + 1]
                delta_transport_distance += (((self.data.transport_routes_order_item[move.OrderItemIDExt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemIDExt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                
            if len(move.MachineRouteInt) == 0:
                predecessor_id = None
                successor_id = None
            elif move.MachineRouteIndexInt == 0:
                predecessor_id = None
                successor_id = move.MachineRouteInt[move.MachineRouteIndexInt]
                delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemIDInt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif move.MachineRouteIndexInt == len(move.MachineRouteInt):
                predecessor_id = move.MachineRouteInt[move.MachineRouteIndexInt - 1]
                successor_id = None
                delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemIDInt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = move.MachineRouteInt[move.MachineRouteIndexInt - 1]
                successor_id = move.MachineRouteInt[move.MachineRouteIndexInt]
                delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemIDInt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemIDInt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
            
        # Calculate the extra driver violation
        machine_new = self.data.machines[move.MachineIDExt]
        machine_old = self.data.machines[move.MachineIDInt]

        delta_driver_violation = 0
        if move.WorkerID in machine_new.default_drivers:
            delta_driver_violation -= 1
        if move.WorkerID in machine_old.default_drivers:
            delta_driver_violation += 1


        # Calculate the extra transport distance of the attachments
        delta_attachment_distance = 0
        for i in range(move.NumberOfAttachmentsExt):
            if len(getattr(move, f"AttachmentRouteExt_{i}")) == 1:
                predecessor_id = None
                successor_id = None
            elif getattr(move, f"AttachmentRouteIndexExt_{i}") == 0:
                predecessor_id = None
                successor_id = getattr(move, f"AttachmentRouteExt_{i}")[getattr(move, f"AttachmentRouteIndexExt_{i}") + 1]
                delta_attachment_distance += (self.data.transport_routes_order_item[move.OrderItemIDExt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif getattr(move, f"AttachmentRouteIndexExt_{i}") == len(getattr(move, f"AttachmentRouteExt_{i}")) - 1:
                predecessor_id = getattr(move, f"AttachmentRouteExt_{i}")[getattr(move, f"AttachmentRouteIndexExt_{i}") - 1]
                successor_id = None
                delta_attachment_distance += (self.data.transport_routes_order_item[move.OrderItemIDExt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = getattr(move, f"AttachmentRouteExt_{i}")[getattr(move, f"AttachmentRouteIndexExt_{i}") - 1]
                successor_id = getattr(move, f"AttachmentRouteExt_{i}")[getattr(move, f"AttachmentRouteIndexExt_{i}") + 1]
                delta_attachment_distance += (((self.data.transport_routes_order_item[move.OrderItemIDExt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemIDExt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                
        for i in range(move.NumberOfAttachmentsInt):
            if len(getattr(move, f"AttachmentRouteInt_{i}")) == 0:
                predecessor_id = None
                successor_id = None
            elif getattr(move, f"AttachmentRouteIndexInt_{i}") == 0:
                predecessor_id = None
                successor_id = getattr(move, f"AttachmentRouteInt_{i}")[getattr(move, f"AttachmentRouteIndexInt_{i}")]
                delta_attachment_distance -= (self.data.transport_routes_order_item[move.OrderItemIDInt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif getattr(move, f"AttachmentRouteIndexInt_{i}") == len(getattr(move, f"AttachmentRouteInt_{i}")):
                predecessor_id = getattr(move, f"AttachmentRouteInt_{i}")[getattr(move, f"AttachmentRouteIndexInt_{i}") - 1]
                successor_id = None
                delta_attachment_distance -= (self.data.transport_routes_order_item[move.OrderItemIDInt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = getattr(move, f"AttachmentRouteInt_{i}")[getattr(move, f"AttachmentRouteIndexInt_{i}") - 1]
                successor_id = getattr(move, f"AttachmentRouteInt_{i}")[getattr(move, f"AttachmentRouteIndexInt_{i}")]
                delta_attachment_distance -= (((self.data.transport_routes_order_item[move.OrderItemIDInt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemIDInt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                

            

        # Calculate the extra machine count
        delta_machine_count = 0
        if not move.SameMachine:
            if len(move.MachineRouteExt) == 1:
                delta_machine_count += 1
            if len(move.MachineRouteInt) == 0:
                delta_machine_count -= 1

        # Calculate the extra attachment count
        delta_attachment_count = 0
        for i in range(move.NumberOfAttachmentsExt):
            if len(getattr(move, f"AttachmentRouteExt_{i}")) == 1:
                delta_attachment_count += 1
        for i in range(move.NumberOfAttachmentsInt):
            if len(getattr(move, f"AttachmentRouteInt_{i}")) == 0:
                delta_attachment_count -= 1

        
  
        # Calculate the precentage difference this order item makes
        delta_dynamic_percentage_order = 0
        for order in self.data.orders:
            if move.OrderItemIDExt in order.order_item_ids:
                delta_dynamic_percentage_order += (1 / len(order.order_item_ids)) + move.DynamicPercentageExt
            if move.OrderItemIDInt in order.order_item_ids:
                delta_dynamic_percentage_order -= (1 / len(order.order_item_ids)) + move.DynamicPercentageInt


        # 1️⃣ Store individual delta values as a dictionary (details)
        delta_details = {
            "dynamic_percentage_order": -delta_dynamic_percentage_order,
            "commute_distance": delta_commute_distance,
            "transport_distance": delta_transport_distance,
            "attachment_distance": delta_attachment_distance,
            "driver_violation": delta_driver_violation,
            "machine_count": delta_machine_count,
            "attachment_count": delta_attachment_count,
        }
        ##print(f"Delta Details: {delta_details}")

        # 2️⃣ Create a summary as a list (summary)
        # First value: dynamic percentage order
        # Second value: sum of commute_distance and transport_distance
        delta_summary = [
            delta_details["dynamic_percentage_order"],
            delta_details["commute_distance"]
            + delta_details["transport_distance"]
            + delta_details["driver_violation"]
            + delta_details["machine_count"]
            + delta_details["attachment_count"]
            + delta_details["attachment_distance"],
        ]

        ##print(f"Delta Summary: {delta_summary[0]}")
        ##print(f"Delta Summary: {delta_summary}")

        # 3️⃣ Return both summary (list) and details (dictionary)
        return delta_summary, delta_details


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


        # 1️⃣ Store individual delta values as a dictionary (details)
        delta_details = {
            "transport_distance": delta_transport_distance,
            "driver_violation": delta_driver_violation,
        }

        #print(f"Delta Details: {delta_details}")

        # 2️⃣ Create the summary (scalar value = sum of both deltas)
        delta_summary = delta_details["transport_distance"] + delta_details["driver_violation"]


        #print(f"Delta Summary: {delta_summary}")

        # 3️⃣ Return both summary (scalar) and details (dictionary)
        return delta_summary, delta_details

    def calculate_swap_shift_worker_delta(self, move):
        ''' Calculate the delta of the objective function value when swapping two order items between two workers'''

        # Calculate the extra commute distance
        delta_commute_distance = (+ ((self.data.work_routes_order_item[move.WorkerID1][move.OrderItemID2] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 + ((self.data.work_routes_order_item[move.WorkerID2][move.OrderItemID1] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 - ((self.data.work_routes_order_item[move.WorkerID1][move.OrderItemID1] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 - ((self.data.work_routes_order_item[move.WorkerID2][move.OrderItemID2] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance)))
        delta_commute_distance *= 2

        if abs(delta_commute_distance) < 1e-10:
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


        # 1️⃣ Store individual delta values as a dictionary (details)
        delta_details = {
            "commute_distance": delta_commute_distance,
            "driver_violation": delta_driver_violation,
        }

        #print(f"Delta Details: {delta_details}")

        # 2️⃣ Create the summary (scalar value as the sum of both)
        delta_summary = delta_details["commute_distance"] + delta_details["driver_violation"]


        #print(f"Delta Summary: {delta_summary}")

        # 3️⃣ Return both summary (scalar) and details (dictionary)
        return delta_summary, delta_details
  
    def calculate_swap_shift_attachment_delta(self, move):
            
            # Calculate the extra transport distance
            move.AttachmentRouteIndex1 = move.AttachmentRoute1.index(move.OrderItemID2)
            delta_transport_distance = 0
            if len(move.AttachmentRoute1) == 1:
                predecessor_id = None
                successor_id = None
            elif move.AttachmentRouteIndex1 == 0:
                predecessor_id = None
                successor_id = move.AttachmentRoute1[move.AttachmentRouteIndex1 + 1]
                delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID2][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif move.AttachmentRouteIndex1 == len(move.AttachmentRoute1) - 1:
                predecessor_id = move.AttachmentRoute1[move.AttachmentRouteIndex1 - 1]
                successor_id = None
                delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID2][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = move.AttachmentRoute1[move.AttachmentRouteIndex1 - 1]
                successor_id = move.AttachmentRoute1[move.AttachmentRouteIndex1 + 1]
                delta_transport_distance += (((self.data.transport_routes_order_item[move.OrderItemID2][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemID2][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                
            move.AttachmentRouteIndex2 = move.AttachmentRoute2.index(move.OrderItemID1)
            if len(move.AttachmentRoute2) == 1:
                predecessor_id = None
                successor_id = None
            elif move.AttachmentRouteIndex2 == 0:
                predecessor_id = None
                successor_id = move.AttachmentRoute2[move.AttachmentRouteIndex2 + 1]
                delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID1][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif move.AttachmentRouteIndex2 == len(move.AttachmentRoute2) - 1:
                predecessor_id = move.AttachmentRoute2[move.AttachmentRouteIndex2 - 1]
                successor_id = None
                delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID1][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = move.AttachmentRoute2[move.AttachmentRouteIndex2 - 1]
                successor_id = move.AttachmentRoute2[move.AttachmentRouteIndex2 + 1]
                delta_transport_distance += (((self.data.transport_routes_order_item[move.OrderItemID1][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemID1][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                
            if len(move.AttachmentRoute1Original) == 1:
                predecessor_id = None
                successor_id = None
            elif move.AttachmentRouteTakenIndex1 == 0:
                predecessor_id = None
                successor_id = move.AttachmentRoute1Original[move.AttachmentRouteTakenIndex1 + 1]
                delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID1][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif move.AttachmentRouteTakenIndex1 == len(move.AttachmentRoute1Original) - 1:
                predecessor_id = move.AttachmentRoute1Original[move.AttachmentRouteTakenIndex1 - 1]
                successor_id = None
                delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID1][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = move.AttachmentRoute1Original[move.AttachmentRouteTakenIndex1 - 1]
                successor_id = move.AttachmentRoute1Original[move.AttachmentRouteTakenIndex1 + 1]
                delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemID1][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemID1][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                
            if len(move.AttachmentRoute2Original) == 1:
                predecessor_id = None
                successor_id = None
            elif move.AttachmentRouteTakenIndex2 == 0:
                predecessor_id = None
                successor_id = move.AttachmentRoute2Original[move.AttachmentRouteTakenIndex2 + 1]
                delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID2][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            elif move.AttachmentRouteTakenIndex2 == len(move.AttachmentRoute2Original) - 1:
                predecessor_id = move.AttachmentRoute2Original[move.AttachmentRouteTakenIndex2 - 1]
                successor_id = None
                delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID2][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
            else:
                predecessor_id = move.AttachmentRoute2Original[move.AttachmentRouteTakenIndex2 - 1]
                successor_id = move.AttachmentRoute2Original[move.AttachmentRouteTakenIndex2 + 1]
                delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemID2][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemID2][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                
            # 1️⃣ Store individual delta values as a dictionary (details)
            delta_details = {
                "attachment_distance": delta_transport_distance,
            }

            ##print(f"Delta Details: {delta_details}")

            # 2️⃣ Create summary (scalar) → Since only 1 value, just extract it
            delta_summary = delta_details["attachment_distance"]

            ##print(f"Delta Summary: {delta_summary}")

            # 3️⃣ Return both summary (scalar) and details (dictionary)
            return delta_summary, delta_details
        

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

        # 1️⃣ Store individual delta values as a dictionary (details)
        delta_details = {
            "transport_distance": delta_transport_distance,
            "driver_violation": delta_driver_violation,
            "machine_count": delta_machine_count,
        }

        # Optional for debugging
        # #print(f"Delta Details: {delta_details}")

        # 2️⃣ Create the summary (scalar) as the sum of all values
        delta_summary = (
            delta_details["transport_distance"]
            + delta_details["driver_violation"]
            + delta_details["machine_count"]
        )

        # Optional for debugging
        # #print(f"Delta Summary: {delta_summary}")

        # 3️⃣ Return both summary (scalar) and details (dictionary)
        return delta_summary, delta_details
  
    def calculate_replace_shift_worker_delta(self, move):
        ''' Calculate the delta of the objective function value when replacing an order item between two workers'''

        # Calculate the extra commute distance
        delta_commute_distance = (((self.data.work_routes_order_item[move.WorkerID2][move.OrderItemID] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 - ((self.data.work_routes_order_item[move.WorkerID1][move.OrderItemID] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance)))
        delta_commute_distance *= 2

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

        

        # 1️⃣ Store individual delta values as a dictionary (details)
        delta_details = {
            "commute_distance": delta_commute_distance,
            "driver_violation": delta_driver_violation,
            "worker_count": delta_worker_count,
        }

        # Optional for debugging
        # #print(f"Delta Details: {delta_details}")

        # 2️⃣ Create summary (scalar) as the sum of all deltas
        delta_summary = (
            delta_details["commute_distance"]
            + delta_details["driver_violation"]
            + delta_details["worker_count"]
        )

        # Optional for debugging
        # #print(f"Delta Summary: {delta_summary}")

        # 3️⃣ Return both summary (scalar) and details (dictionary)
        return delta_summary, delta_details

    def calculate_replace_shift_attachment_delta(self, move):
        ''' Calculate the delta of the objective function value when replacing an order item between two attachments'''

        # Calculate the extra transport distance
        delta_transport_distance = 0
        if len(move.AttachmentRoute2) == 1:
            predecessor_id = None
            successor_id = None
        elif move.AttachmentRouteIndex2 == 0:
            predecessor_id = None
            successor_id = move.AttachmentRoute2[move.AttachmentRouteIndex2 + 1]
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.AttachmentRouteIndex2 == len(move.AttachmentRoute2) - 1:
            predecessor_id = move.AttachmentRoute2[move.AttachmentRouteIndex2 - 1]
            successor_id = None
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.AttachmentRoute2[move.AttachmentRouteIndex2 - 1]
            successor_id = move.AttachmentRoute2[move.AttachmentRouteIndex2 + 1]
            delta_transport_distance += (((self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)) 
        
        if len(move.AttachmentRoute1) == 0:
            predecessor_id = None
            successor_id = None
            delta_transport_distance -= 0
        elif move.AttachmentRouteIndex1 == 0:
            predecessor_id = None
            successor_id = move.AttachmentRoute1[move.AttachmentRouteIndex1]
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.AttachmentRouteIndex1 == len(move.AttachmentRoute1):
            predecessor_id = move.AttachmentRoute1[move.AttachmentRouteIndex1 - 1]
            successor_id = None
            delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            predecessor_id = move.AttachmentRoute1[move.AttachmentRouteIndex1 - 1]
            successor_id = move.AttachmentRoute1[move.AttachmentRouteIndex1]
            delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
            
        # Calculate the extra attachment count
        if len(move.AttachmentRoute1) == 0:
            delta_attachment_count = -1
        else:
            delta_attachment_count = 0

        if len(move.AttachmentRoute2) == 1:
            delta_attachment_count += 1

        # 1️⃣ Store individual delta values as a dictionary (details)
        delta_details = {
            "attachment_distance": delta_transport_distance,
            "attachment_count": delta_attachment_count,
        }

        # Optional: Debug output for inspection
        # #print(f"Delta Details: {delta_details}")

        # 2️⃣ Create summary (scalar) as the sum of both values
        delta_summary = (
            delta_details["attachment_distance"]
            + delta_details["attachment_count"]
        )

        # Optional: Debug output for summary
        # #print(f"Delta Summary: {delta_summary}")

        # 3️⃣ Return both summary (scalar) and details (dictionary)
        return delta_summary, delta_details


    def evaluate(self, solution:Solution):
        
        self.categorizing_orders(solution)
        self.calculate_finished_order_items(solution)
        self.calculate_commute_distance(solution)
        self.calculate_transport_distance(solution)
        self.calculate_driver_violation(solution)
        self.calculate_worker_count_and_utilization_time(solution)
        self.calculate_dynamic_percentage_order(solution)
        self.calculate_attachment_distance(solution)
        self.calculate_cummulative_distance(solution)
        self.calculate_machine_attachment_count_and_utilization_time(solution)

    
    def calculate_cummulative_distance(self, solution:Solution):

        solution.total_distance = solution.total_commute_distance + solution.total_transport_distance + solution.total_transport_distance_attachments

    def calculate_attachment_distance(self, solution:Solution):
            ''' Calculate the total transport distance of the attachments'''

            for attachment_id, route in solution.route_plan_attachment.items():
                solution.transport_distance_per_attachment[attachment_id] = 0
                for i in range(len(route) - 1):
                    solution.transport_distance_per_attachment[attachment_id] += self.data.transport_routes_order_item[route[i]][route[i + 1]]
                
            solution.total_transport_distance_attachments = sum(solution.transport_distance_per_attachment.values())


    def calculate_dynamic_percentage_order(self, solution: Solution):
        """Efficiently calculates the dynamic percentage of the solution."""
        finished_order_item_ids = {
            order_item_id
            for route in solution.route_plan_worker.values()
            for order_item_id in route
        }

        solution.dynamic_percentage_order = {
            order.order_number: sum(1 for oid in order.order_item_ids if oid in finished_order_item_ids) / len(order.order_item_ids)
            for order in self.data.orders
        }

        solution.total_dynamic_percentage = sum(solution.dynamic_percentage_order.values())
                
    def categorizing_orders(self, solution: Solution):
        ''' Categorize the orders into finished, semi-finished and not started orders '''
        
        solution.finished_orders = []
        solution.not_started_orders = []
        solution.not_recognized_orders = []
        solution.semifinished_orders = []
        solution.not_started_order_item_ids = []
        solution.not_recognized_order_item_ids = []

        all_planned_order_item_ids = set(order_item_id for route in solution.route_plan_worker.values() for order_item_id in route)

        # Categorize order items
        for order_item in self.data.order_items:
            if order_item.id not in all_planned_order_item_ids:
                if order_item.status:
                    solution.not_started_order_item_ids.append(order_item.id)
                else:
                    solution.not_recognized_order_item_ids.append(order_item.id)

        # Categorize orders
        for order in self.data.orders:
            if not order.status:
                solution.not_recognized_orders.append(order)
                continue

            planned_count = sum(1 for oid in order.order_item_ids if oid in all_planned_order_item_ids)
            if planned_count == 0:
                solution.not_started_orders.append(order)
            elif planned_count == len(order.order_item_ids):
                solution.finished_orders.append(order)
            else:
                solution.semifinished_orders.append(order)

        solution.share_finished_orders = len(solution.finished_orders) / len(self.data.orders) * 100
        solution.number_of_finished_orders = len(solution.finished_orders)
        solution.number_of_unrecognized_orders = len(solution.not_recognized_orders)


    def calculate_finished_order_items(self, solution:Solution):
        ''' Calculate the number of finished order items'''

        solution.number_of_finished_order_items = 0


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
            #raise Exception("Number of finished order items is not equal to the number of finished order items of the machines")
            print("Number of finished order items is not equal to the number of finished order items of the machines")

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

    def calculate_driver_violation(self, solution: Solution):
        """Calculate the total driver violation time of the workers"""

        # Precompute mapping from order_item_id to machine_id
        order_to_machine = {
            order_item_id: machine_id
            for machine_id, route in solution.route_plan_machine.items()
            for order_item_id in route
        }

        # Precompute machine_id → machine
        machine_dict = {machine.id: machine for machine in self.data.machines}

        solution.driver_violation = 0

        for worker_id, route in solution.route_plan_worker.items():
            for order_item_id in route:
                machine_id = order_to_machine.get(order_item_id)
                if machine_id is not None:
                    if worker_id not in machine_dict[machine_id].default_drivers:
                        solution.driver_violation += 1
  


    def calculate_worker_count_and_utilization_time(self, solution: Solution) -> None:
        solution.number_of_workers = 0

        for worker_id, route in solution.route_plan_worker.items():
            duration = sum(self.data.order_items[oid].duration for oid in route)
            solution.worker_work_time[worker_id] = duration
            if duration > 0:
                solution.number_of_workers += 1

    def calculate_machine_attachment_count_and_utilization_time(self, solution: Solution) -> None:
        solution.number_of_machines = 0
        solution.number_of_attachments = 0

        for machine_id, route in solution.route_plan_machine.items():
            duration = sum(self.data.order_items[oid].duration for oid in route)
            solution.machine_utilization_time[machine_id] = duration
            if duration > 0:
                solution.number_of_machines += 1


        for attachment_id, route in solution.route_plan_attachment.items():
            duration = sum(self.data.order_items[oid].duration for oid in route)
            solution.attachment_utilization_time[attachment_id] = duration
            if duration > 0:
                solution.number_of_attachments += 1



### NOT IN USE

    def categorizing_machine_worker(self, solution:Solution):
        ''' Categorize the machines and workers into finished, semi-finished and not started machines and workers'''

        solution.used_machines = []
        solution.unused_machines = []
        solution.used_workers = []
        solution.unused_workers = []
        solution.used_attachments = []
        solution.unused_attachments = []
        
        
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