"""
===============================================================================
                              EVALUATION LOGIC MODULE
===============================================================================

This module provides comprehensive evaluation capabilities for railroad 
construction scheduling optimization solutions. It implements a complete 
evaluation framework that calculates objective function values, solution 
metrics, and incremental delta calculations for neighborhood moves in 
multi-objective optimization algorithms.

CORE FUNCTIONALITY:
------------------
1. Solution Evaluation Framework
   - Complete solution evaluation with all 7 objectives
   - Incremental delta calculations for neighborhood moves
   - Normalized objective value computation for fair comparison
   - Resource utilization and constraint violation detection

2. Objective Function Calculations
   - Driver Violation: Penalties for non-default driver-machine assignments
   - Commute Distance: Worker travel distances to construction sites
   - Transport Distance: Machine routing and transportation costs
   - Attachment Distance: Attachment equipment transportation efficiency
   - Worker Count: Total workforce resource requirements
   - Machine Count: Total machinery resource requirements
   - Attachment Count: Total attachment equipment requirements

3. Delta Calculation Methods
   - Insert Shift Delta: Adding new order items to routes
   - Swap Shift External Delta: Swapping internal/external order items
   - Swap Shift Machine Delta: Swapping items between machines
   - Swap Shift Worker Delta: Swapping items between workers
   - Swap Shift Attachment Delta: Swapping items between attachments
   - Replace Shift Machine Delta: Moving items between machines
   - Replace Shift Worker Delta: Moving items between workers
   - Replace Shift Attachment Delta: Moving items between attachments

4. Solution Quality Metrics
   - Order completion percentage tracking
   - Dynamic percentage calculations for order fulfillment
   - Resource utilization efficiency measurements
   - Feasibility checking and constraint validation
"""

# Imports for data structures and solution evaluation
from Code.InputData import InputData
from Code.OutputData import Solution

class EvaluationLogic:
    """
    Evaluation logic class for calculating objective function values and solution metrics.
    
    This class provides comprehensive evaluation capabilities for railroad optimization solutions,
    including calculation of distances, violations, resource utilization, and solution quality metrics.
    It supports both full solution evaluation and incremental delta calculations for neighborhood moves.
    """

    def __init__(self, data: InputData):
        """
        Initialize the evaluation logic with input data.
        
        Args:
            data: InputData object containing all problem instance information
        """
        self.data = data  # Store reference to input data for evaluation calculations

    def calculate_insert_shift_delta(self, move):
        """
        Calculate delta values when inserting an order item into a route.
        
        This method computes the change in objective function value when a new order item
        is inserted into worker, machine, and attachment routes. It calculates impacts on
        commute distance, transport distance, driver violations, and resource counts.
        
        Args:
            move: Move object containing insertion details (worker, machine, attachments, positions)
            
        Returns:
            tuple: (delta_summary, delta_details) where summary is a list of aggregated values
                  and details is a dictionary with individual metric changes
        """

        # Calculate extra commute distance (normalized to [0,1] range)
        # Commute distance = 2 * distance from worker home to work site
        delta_commute_distance = ((self.data.work_routes_order_item[move.WorkerID][move.OrderItemID] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
        delta_commute_distance *= 2  # Round trip distance

        # Calculate extra transport distance for machine routing
        # Transport distance depends on position in route and neighboring order items
        if len(move.MachineRoute) == 1:
            # Case 1: Only one order item in route - no transport distance
            predecessor_id = None
            successor_id = None
            delta_transport_distance = 0
        elif move.MachineRouteIndex == 0:
            # Case 2: Inserted at beginning of route - only distance to successor
            predecessor_id = None
            successor_id = move.MachineRoute[move.MachineRouteIndex + 1] 
            delta_transport_distance = (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteIndex == len(move.MachineRoute) - 1:
            # Case 3: Inserted at end of route - only distance from predecessor
            predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
            successor_id = None
            delta_transport_distance = (self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            # Case 4: Inserted in middle of route - distance to both neighbors minus removed direct connection
            predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
            successor_id = move.MachineRoute[move.MachineRouteIndex + 1]
            delta_transport_distance = (((self.data.transport_routes_order_item[move.OrderItemID][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                        + (self.data.transport_routes_order_item[move.OrderItemID][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                        - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
        
        # Calculate driver violation penalty
        # Check if assigned worker is a default driver for the machine
        machine = self.data.machines[move.MachineID]
        if move.WorkerID not in machine.default_drivers:
            delta_driver_violation = 1  # Penalty for non-default driver assignment
        else:
            delta_driver_violation = 0  # No penalty for default driver

        # Calculate machine count increase
        # New machine is used if this is the first order item assigned to it
        if len(move.MachineRoute) == 1:
            delta_machine_count = 1  # New machine activated
        else:
            delta_machine_count = 0  # Machine already in use

        # Calculate worker count increase
        # New worker is used if this is the first order item assigned to them
        if len(move.WorkerRoute) == 1:
            delta_worker_count = 1  # New worker activated
        else:
            delta_worker_count = 0  # Worker already in use

        # Calculate dynamic percentage change for order completion
        # Find the order this order item belongs to and calculate completion impact
        for order in self.data.orders:
            if move.OrderItemID in order.order_item_ids:
                delta_dynamic_percentage_order = (1 / len(order.order_item_ids)) + move.DynamicPercentage

        


        

        # Store individual delta components for detailed analysis
        delta_details = {
            "dynamic_percentage_order": -delta_dynamic_percentage_order,  # Negative because higher completion is better
            "commute_distance": delta_commute_distance,                   # Extra worker commute distance
            "transport_distance": delta_transport_distance,               # Extra machine transport distance
            "driver_violation": delta_driver_violation,                   # Driver assignment violation penalty
            #"machine_count": delta_machine_count,                         # Number of new machines used
            #"worker_count": delta_worker_count                            # Number of new workers used
        }


        # Create aggregated summary for multi-objective optimization
        # First objective: Order completion (negative because maximization)
        # Second objective: Total cost (sum of all distance, violation, and resource costs)
        delta_summary = [
            delta_details["dynamic_percentage_order"],
            delta_details["commute_distance"]
            + delta_details["transport_distance"]
            + delta_details["driver_violation"]
            #+ delta_details["machine_count"]
            #+ delta_details["worker_count"]
        ]


        return delta_summary, delta_details
    
    def calculate_swap_shift_external_delta(self, move):
        """
        Calculate delta values when swapping an external order item with an internal order item.
        
        This method computes the change in objective function value when an order item
        from the external pool (unplanned) is swapped with an order item from the internal
        route (currently planned). The external item gets inserted into all three route plans
        (worker, machine, attachment) while the internal item gets removed from all routes.
        
        Args:
            move: Move object containing swap details (worker, machines, order items, routes)
            
        Returns:
            tuple: (delta_summary, delta_details) where summary is a list of aggregated values
                  and details is a dictionary with individual metric changes
        """
        
        # Calculate change in commute distance
        # Replace internal order item with external order item for the same worker
        delta_commute_distance = (((self.data.work_routes_order_item[move.WorkerID][move.OrderItemIDExt] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                - ((self.data.work_routes_order_item[move.WorkerID][move.OrderItemIDInt] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance)))
        delta_commute_distance *= 2  # Round trip distance

        # Calculate change in machine transport distance
        # Depends on whether the swap involves the same machine or different machines
        delta_transport_distance = 0


        if move.SameMachine:
            # Case 1: Both order items use the same machine - replace internal item with external item
            
            if len(move.MachineRoute) == 1:
                # Only one item in route after swap
                predecessor_id = None
                successor_id = None
            elif move.MachineRouteIndex == 0:
                # Replaced item at beginning of route
                predecessor_id = None
                successor_id = move.MachineRoute[move.MachineRouteIndex + 1]
                delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemIDExt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemIDInt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)

            elif move.MachineRouteIndex == len(move.MachineRoute) - 1:
                # Replaced item at end of route
                predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
                successor_id = None
                delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemIDExt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                delta_transport_distance -= (self.data.transport_routes_order_item[move.OrderItemIDInt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)

            else:
                # Replaced item in middle of route
                predecessor_id = move.MachineRoute[move.MachineRouteIndex - 1]
                successor_id = move.MachineRoute[move.MachineRouteIndex + 1]
                delta_transport_distance += (((self.data.transport_routes_order_item[move.OrderItemIDExt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemIDExt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                delta_transport_distance -= (((self.data.transport_routes_order_item[move.OrderItemIDInt][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))
                                            + (self.data.transport_routes_order_item[move.OrderItemIDInt][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
                                            - (self.data.transport_routes_order_item[predecessor_id][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance))

        else:
            # Case 2: Different machines - external item goes to new machine, internal item is removed from old machine
            
            # Calculate transport distance change for external machine (receiving new order item from external pool)
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
                
            # Calculate transport distance change for internal machine (losing planned order item)
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
            
        # Calculate change in driver violation penalties
        # Check if worker fits better or worse with new machine assignment
        machine_new = self.data.machines[move.MachineIDExt]  # Machine receiving the order item
        machine_old = self.data.machines[move.MachineIDInt]  # Machine losing the order item

        delta_driver_violation = 0
        if move.WorkerID in machine_new.default_drivers:
            delta_driver_violation -= 1  # Improvement - worker is default driver for new machine
        if move.WorkerID in machine_old.default_drivers:
            delta_driver_violation += 1  # Deterioration - worker was default driver for old machine




        # Calculate change in machine resource count
        # Check if machines are activated or deactivated by the swap
        delta_machine_count = 0
        if not move.SameMachine:
            if len(move.MachineRouteExt) == 1:
                delta_machine_count += 1  # New machine activated
            if len(move.MachineRouteInt) == 0:
                delta_machine_count -= 1  # Machine deactivated


        
        # Calculate change in order completion percentage
        # Account for changes in both orders affected by the swap
        delta_dynamic_percentage_order = 0
        for order in self.data.orders:
            if move.OrderItemIDExt in order.order_item_ids:
                delta_dynamic_percentage_order += (1 / len(order.order_item_ids)) + move.DynamicPercentageExt
            if move.OrderItemIDInt in order.order_item_ids:
                delta_dynamic_percentage_order -= (1 / len(order.order_item_ids)) + move.DynamicPercentageInt


        # Store individual delta components for detailed analysis
        delta_details = {
            "dynamic_percentage_order": -delta_dynamic_percentage_order,  # Negative because higher completion is better
            "commute_distance": delta_commute_distance,                   # Change in worker commute distance
            "transport_distance": delta_transport_distance,               # Change in machine transport distance
            "driver_violation": delta_driver_violation,                   # Change in driver assignment violations
            #"machine_count": delta_machine_count                          # Change in number of machines used

        }

        # Create aggregated summary for multi-objective optimization
        # First objective: Order completion (negative because maximization)
        # Second objective: Total cost (sum of all distance, violation, and resource costs)
        delta_summary = [
            delta_details["dynamic_percentage_order"],
            delta_details["commute_distance"]
            + delta_details["transport_distance"]
            + delta_details["driver_violation"]
            #+ delta_details["machine_count"],
        ]

        # Return both detailed breakdown and aggregated summary
        return delta_summary, delta_details


    def calculate_swap_shift_machine_delta(self, move):
        """
        Calculate delta values when swapping order items between two different machines.
        
        This method computes the change in objective function value when two order items
        are swapped between different machines. It calculates changes in transport distance
        and driver violation penalties.
        
        Args:
            move: Move object containing machine swap details (machines, order items, routes)
            
        Returns:
            tuple: (delta_summary, delta_details) where summary is a scalar value
                  and details is a dictionary with individual metric changes
        """
        
        # Calculate change in transport distance for machine swaps
        # Need to account for both machines and their route changes
        move.MachineRouteIndex1 = move.MachineRoute1.index(move.OrderItemID2)
        delta_transport_distance = 0
        
        # Calculate new transport distance for machine 1 (receiving OrderItemID2)
        if len(move.MachineRoute1) == 1:
            # Only one item in route
            predecessor_id = None
            successor_id = None
        elif move.MachineRouteIndex1 == 0:
            # Item at beginning of route
            predecessor_id = None
            successor_id = move.MachineRoute1[move.MachineRouteIndex1 + 1]
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID2][successor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        elif move.MachineRouteIndex1 == len(move.MachineRoute1) - 1:
            # Item at end of route
            predecessor_id = move.MachineRoute1[move.MachineRouteIndex1 - 1]
            successor_id = None
            delta_transport_distance += (self.data.transport_routes_order_item[move.OrderItemID2][predecessor_id] - self.data.min_transport_distance) / (self.data.max_transport_distance - self.data.min_transport_distance)
        else:
            # Item in middle of route
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
        """
        Calculate delta values when swapping order items between two workers.
        
        This method computes the change in objective function value when two order items
        are swapped between different workers. It calculates changes in commute distance
        and driver violation penalties.
        
        Args:
            move: Move object containing worker swap details
            
        Returns:
            tuple: (delta_summary, delta_details) where summary is a scalar value
                  and details is a dictionary with individual metric changes
        """

        # Calculate change in commute distance for both workers
        delta_commute_distance = (+ ((self.data.work_routes_order_item[move.WorkerID1][move.OrderItemID2] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 + ((self.data.work_routes_order_item[move.WorkerID2][move.OrderItemID1] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 - ((self.data.work_routes_order_item[move.WorkerID1][move.OrderItemID1] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 - ((self.data.work_routes_order_item[move.WorkerID2][move.OrderItemID2] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance)))
        delta_commute_distance *= 2  # Round trip distance

        # Handle floating point precision issues
        if abs(delta_commute_distance) < 1e-10:
            delta_commute_distance = 0


        # Calculate change in driver violation penalties
        machine_1 = self.data.machines[move.MachineID1]
        machine_2 = self.data.machines[move.MachineID2]

        delta_driver_violation = 0
        # Check new assignments after swap
        if move.WorkerID1 in machine_1.default_drivers:
            delta_driver_violation += 1  # Worker1 becomes worse fit
        if move.WorkerID2 in machine_2.default_drivers:
            delta_driver_violation += 1  # Worker2 becomes worse fit
        # Check old assignments before swap
        if move.WorkerID1 in machine_2.default_drivers:
            delta_driver_violation -= 1  # Worker1 becomes better fit
        if move.WorkerID2 in machine_1.default_drivers:
            delta_driver_violation -= 1  # Worker2 becomes better fit

        
        # Calculate the change in deviation from desired hours
        delta_hours_deviation = 0
        duration_worker_1 = sum(self.data.order_items[oid].duration for oid in move.WorkerRoute1)
        duration_worker_2 = sum(self.data.order_items[oid].duration for oid in move.WorkerRoute2)

        distance_prev_worker_1 = abs(move.PreviousDurationWorker1 - move.DesiredWorkHours)
        distance_worker_1 = abs(duration_worker_1 - move.DesiredWorkHours)

        distance_prev_worker_2 = abs(move.PreviousDurationWorker2 - move.DesiredWorkHours)
        distance_worker_2 = abs(duration_worker_2 - move.DesiredWorkHours)


        if distance_prev_worker_1 < distance_worker_1:
            delta_hours_deviation += abs(duration_worker_1 - move.PreviousDurationWorker1) / abs(self.data.min_duration - self.data.max_duration)
        elif distance_prev_worker_1 > distance_worker_1:
            delta_hours_deviation -= abs(duration_worker_1 - move.PreviousDurationWorker1) / abs(self.data.min_duration - self.data.max_duration)

        if distance_prev_worker_2 < distance_worker_2:
            delta_hours_deviation += abs(duration_worker_2 - move.PreviousDurationWorker2) / abs(self.data.min_duration - self.data.max_duration)
        elif distance_prev_worker_2 > distance_worker_2:
            delta_hours_deviation -= abs(duration_worker_2 - move.PreviousDurationWorker2) / abs(self.data.min_duration - self.data.max_duration)

        # Store individual delta components for detailed analysis
        delta_details = {
            "commute_distance": delta_commute_distance,
            "driver_violation": delta_driver_violation,
            "deviation_from_desired_hours": delta_hours_deviation
        }

        # Create scalar summary (sum of both components)
        delta_summary = delta_details["commute_distance"] + delta_details["driver_violation"] + delta_details["deviation_from_desired_hours"]

        # Return both detailed breakdown and scalar summary
        return delta_summary, delta_details
 

    def calculate_replace_shift_machine_delta(self, move):
        """
        Calculate delta values when replacing an order item between two machines.
        
        This method computes the change when an order item is moved from one machine
        to another, considering transport distance, driver violations, and machine count changes.
        
        Args:
            move: Move object containing machine replacement details
            
        Returns:
            tuple: (delta_summary, delta_details) - scalar summary and detailed breakdown
        """

        # Calculate change in transport distance (add new route, subtract old route)
        delta_transport_distance = 0
        
        # Add transport distance for new machine assignment
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
        
        # Subtract transport distance from old machine assignment
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


        # Calculate change in driver violation penalties
        machine_1 = self.data.machines[move.MachineID1]  # Old machine
        machine_2 = self.data.machines[move.MachineID2]  # New machine

        delta_driver_violation = 0
        if move.WorkerID in machine_1.default_drivers:
            delta_driver_violation += 1  # Lost good assignment
        if move.WorkerID in machine_2.default_drivers:
            delta_driver_violation -= 1  # Gained good assignment

        # Calculate change in machine count (machine activation/deactivation)
        if len(move.MachineRoute1) == 0:
            delta_machine_count = -1  # Machine 1 becomes unused
        else:
            delta_machine_count = 0
        if len(move.MachineRoute2) == 1:
            delta_machine_count += 1  # Machine 2 becomes used

        # Store detailed breakdown
        delta_details = {
            "transport_distance": delta_transport_distance,
            "driver_violation": delta_driver_violation,
            #"machine_count": delta_machine_count,
        }

        # Create scalar summary
        delta_summary = (
            delta_details["transport_distance"]
            + delta_details["driver_violation"]
            #+ delta_details["machine_count"]
        )

        return delta_summary, delta_details
  
    def calculate_replace_shift_worker_delta(self, move):
        """
        Calculate delta values when replacing an order item between two workers.
        
        Args:
            move: Move object containing worker replacement details
            
        Returns:
            tuple: (delta_summary, delta_details) - scalar summary and detailed breakdown
        """

        # Calculate change in commute distance (new worker - old worker)
        delta_commute_distance = (((self.data.work_routes_order_item[move.WorkerID2][move.OrderItemID] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance))
                                 - ((self.data.work_routes_order_item[move.WorkerID1][move.OrderItemID] - self.data.min_work_distance) / (self.data.max_work_distance - self.data.min_work_distance)))
        delta_commute_distance *= 2  # Round trip

        # Calculate change in driver violation penalties
        machine = self.data.machines[move.MachineID]

        delta_driver_violation = 0
        if move.WorkerID1 in machine.default_drivers:
            delta_driver_violation += 1  # Lost good assignment
        if move.WorkerID2 in machine.default_drivers:
            delta_driver_violation -= 1  # Gained good assignment

        # Calculate change in worker count (worker activation/deactivation)
        if len(move.WorkerRoute1) == 0:
            delta_worker_count = -1  # Worker 1 becomes unused
        else:
            delta_worker_count = 0
        if len(move.WorkerRoute2) == 1:
            delta_worker_count += 1  # Worker 2 becomes used


        # Calculate change in hours deviation
        delta_hours_deviation = 0
        worker_count = move.PreviousWorkerCount + delta_worker_count

        previous_desired_hours = self.data.work_hour_sum / move.PreviousWorkerCount
        desired_hours = self.data.work_hour_sum / worker_count

        duration_worker_1 = sum(self.data.order_items[oid].duration for oid in move.WorkerRoute1)
        duration_worker_2 = sum(self.data.order_items[oid].duration for oid in move.WorkerRoute2)

        distance_prev_worker_1 = abs(move.PreviousDurationWorker1 - previous_desired_hours)
        distance_worker_1 = abs(duration_worker_1 - desired_hours)

        distance_prev_worker_2 = abs(move.PreviousDurationWorker2 - previous_desired_hours)
        distance_worker_2 = abs(duration_worker_2 - desired_hours)

        if distance_prev_worker_1 < distance_worker_1:
            delta_hours_deviation += abs(duration_worker_1 - move.PreviousDurationWorker1) / abs(self.data.min_duration - self.data.max_duration)
        elif distance_prev_worker_1 > distance_worker_1:
            delta_hours_deviation -= abs(duration_worker_1 - move.PreviousDurationWorker1) / abs(self.data.min_duration - self.data.max_duration)

        if distance_prev_worker_2 < distance_worker_2:
            delta_hours_deviation += abs(duration_worker_2 - move.PreviousDurationWorker2) / abs(self.data.min_duration - self.data.max_duration)
        elif distance_prev_worker_2 > distance_worker_2:
            delta_hours_deviation -= abs(duration_worker_2 - move.PreviousDurationWorker2) / abs(self.data.min_duration - self.data.max_duration)

        # Store detailed breakdown
        delta_details = {
            "commute_distance": delta_commute_distance,
            "driver_violation": delta_driver_violation,
            #"worker_count": delta_worker_count,
            "deviation_from_desired_hours": delta_hours_deviation
        }

        # Create scalar summary
        delta_summary = (
            delta_details["commute_distance"]
            + delta_details["driver_violation"]
            #+ delta_details["worker_count"]
        )

        return delta_summary, delta_details


    def evaluate(self, solution: Solution):
        """
        Main evaluation method for comprehensive solution analysis.
        
        This method performs a complete evaluation of a solution by calculating
        all relevant metrics including distances, violations, resource utilization,
        and order completion statistics.
        
        Args:
            solution: Solution object to be evaluated
        """
        
        # Execute all evaluation components in sequence
        self.categorizing_orders(solution)                              # Classify orders by completion status
        self.calculate_finished_order_items(solution)                   # Count completed order items
        self.calculate_commute_distance(solution)                       # Calculate worker travel distances
        self.calculate_transport_distance(solution)                     # Calculate machine transport distances
        self.calculate_driver_violation(solution)                       # Count driver assignment violations
        self.calculate_worker_count_and_utilization_time(solution)      # Calculate worker metrics
        self.calculate_dynamic_percentage_order(solution)               # Calculate order completion percentages
        self.calculate_cummulative_distance(solution)                   # Sum all distance components
        self.calculate_machine_count_and_utilization_time(solution)     # Calculate machine/attachment metrics
        self.calculate_desired_work_hours(solution)

    def calculate_desired_work_hours(self, solution: Solution):
        """
        Calculate desired work hours based on planned order items.
        """
        solution.desired_work_hours = self.data.work_hour_sum / solution.number_of_workers

        solution.deviation_from_desired_hours = 0

        for worker_id, route in solution.route_plan_worker.items():
            duration = sum(self.data.order_items[oid].duration for oid in route)
            solution.worker_work_time[worker_id] = duration
            solution.deviation_from_desired_hours += abs(duration - solution.desired_work_hours)

    def calculate_cummulative_distance(self, solution: Solution):
        """
        Calculate total distance by summing all distance components.
        
        Args:
            solution: Solution object to update with total distance
        """
        # Sum commute, machine transport, and attachment transport distances
        solution.total_distance = solution.total_commute_distance + solution.total_transport_distance



    def calculate_dynamic_percentage_order(self, solution: Solution):
        """
        Calculate order completion percentages efficiently.
        
        This method determines what percentage of each order has been completed
        by counting the number of planned order items vs total order items.
        
        Args:
            solution: Solution object to update with completion percentages
        """
        
        # Get set of all planned order item IDs for efficient lookup
        finished_order_item_ids = {
            order_item_id
            for route in solution.route_plan_worker.values()
            for order_item_id in route
        }

        # Calculate completion percentage for each order
        solution.dynamic_percentage_order = {
            order.order_number: sum(1 for oid in order.order_item_ids if oid in finished_order_item_ids) / len(order.order_item_ids)
            for order in self.data.orders
        }

        # Calculate total completion across all orders
        solution.total_dynamic_percentage = sum(solution.dynamic_percentage_order.values())
                
    def categorizing_orders(self, solution: Solution):
        """
        Categorize orders by completion status for solution analysis.
        
        This method classifies all orders into different categories based on
        how many of their order items have been planned in the solution.
        
        Args:
            solution: Solution object to update with order categorization
        """
        
        # Initialize category lists
        solution.finished_orders = []          # Orders with all items planned
        solution.not_started_orders = []       # Orders with no items planned
        solution.not_recognized_orders = []    # Inactive orders
        solution.semifinished_orders = []      # Orders with some items planned
        solution.not_started_order_item_ids = []      # Unplanned active order items
        solution.not_recognized_order_item_ids = []   # Inactive order items

        # Get set of all planned order item IDs for efficient lookup
        all_planned_order_item_ids = set(order_item_id for route in solution.route_plan_worker.values() for order_item_id in route)

        # Categorize individual order items by planning status
        for order_item in self.data.order_items:
            if order_item.id not in all_planned_order_item_ids:
                if order_item.status:
                    solution.not_started_order_item_ids.append(order_item.id)    # Active but unplanned
                else:
                    solution.not_recognized_order_item_ids.append(order_item.id) # Inactive

        # Categorize orders based on completion percentage
        for order in self.data.orders:
            if not order.status:
                # Inactive orders
                solution.not_recognized_orders.append(order)
                continue

            # Count how many order items are planned for this order
            planned_count = sum(1 for oid in order.order_item_ids if oid in all_planned_order_item_ids)
            
            if planned_count == 0:
                solution.not_started_orders.append(order)      # No items planned
            elif planned_count == len(order.order_item_ids):
                solution.finished_orders.append(order)         # All items planned
            else:
                solution.semifinished_orders.append(order)     # Partially planned

        # Calculate summary statistics
        solution.share_finished_orders = len(solution.finished_orders) / len(self.data.orders) * 100
        solution.number_of_finished_orders = len(solution.finished_orders)
        solution.number_of_unrecognized_orders = len(solution.not_recognized_orders)


    def calculate_finished_order_items(self, solution: Solution):
        """
        Calculate total number of completed order items and verify consistency.
        
        Args:
            solution: Solution object to update with order item count
        """

        # Count order items in worker routes
        solution.number_of_finished_order_items = 0
        for worker_id, route in solution.route_plan_worker.items():
            for i in range(len(route)):
                solution.number_of_finished_order_items += 1

        # Verify consistency with machine routes
        checker = 0
        for machine_id, route in solution.route_plan_machine.items():
            for i in range(len(route)):
                checker += 1

        # Check for data consistency between worker and machine routes
        if checker == solution.number_of_finished_order_items:
            pass  # Consistency check passed
        else:
            print("Number of finished order items is not equal to the number of finished order items of the machines")

    def calculate_commute_distance(self, solution: Solution):
        """
        Calculate total commute distance for all workers.
        
        This method computes the round-trip distance from each worker's home
        to their assigned work sites.
        
        Args:
            solution: Solution object to update with commute distances
        """

        # Calculate commute distance for each worker
        for worker_id, route in solution.route_plan_worker.items():
            solution.commute_distance_per_worker[worker_id] = 0
            for i in range(len(route)):
                # Multiply by 2 for round trip (home -> work -> home)
                solution.commute_distance_per_worker[worker_id] += 2 * self.data.work_routes_order_item[worker_id][route[i]]
        
        # Calculate total commute distance across all workers
        solution.total_commute_distance = sum(solution.commute_distance_per_worker.values())

    def calculate_transport_distance(self, solution: Solution):
        """
        Calculate total transport distance for all machines.
        
        This method computes the distance traveled by each machine as it moves
        between consecutive order items in its route.
        
        Args:
            solution: Solution object to update with transport distances
        """

        # Calculate transport distance for each machine
        for machine_id, route in solution.route_plan_machine.items():
            solution.transport_distance_per_machine[machine_id] = 0
            # Sum distances between consecutive order items
            for i in range(len(route) - 1):
                solution.transport_distance_per_machine[machine_id] += self.data.transport_routes_order_item[route[i]][route[i + 1]]

        # Calculate total transport distance across all machines
        solution.total_transport_distance = sum(solution.transport_distance_per_machine.values())

    def calculate_driver_violation(self, solution: Solution):
        """
        Calculate total driver assignment violations.
        
        This method counts cases where workers are assigned to machines
        for which they are not default drivers.
        
        Args:
            solution: Solution object to update with violation count
        """

        # Create efficient lookup mapping from order_item_id to machine_id
        order_to_machine = {
            order_item_id: machine_id
            for machine_id, route in solution.route_plan_machine.items()
            for order_item_id in route
        }

        # Create efficient lookup mapping from machine_id to machine object
        machine_dict = {machine.id: machine for machine in self.data.machines}

        solution.driver_violation = 0

        # Check each worker's assignments for violations
        for worker_id, route in solution.route_plan_worker.items():
            for order_item_id in route:
                machine_id = order_to_machine.get(order_item_id)
                if machine_id is not None:
                    # Check if worker is not a default driver for this machine
                    if worker_id not in machine_dict[machine_id].default_drivers:
                        solution.driver_violation += 1  # Count violation


    def calculate_worker_count_and_utilization_time(self, solution: Solution) -> None:
        """
        Calculate number of active workers and their utilization times.
        
        Args:
            solution: Solution object to update with worker metrics
        """
        solution.number_of_workers = 0

        # Calculate work time and count active workers
        for worker_id, route in solution.route_plan_worker.items():
            duration = sum(self.data.order_items[oid].duration for oid in route)
            solution.worker_work_time[worker_id] = duration
            if duration > 0:
                solution.number_of_workers += 1  # Count workers with assignments

    def calculate_machine_count_and_utilization_time(self, solution: Solution) -> None:
        """
        Calculate number of active machines/attachments and their utilization times.
        
        Args:
            solution: Solution object to update with machine and attachment metrics
        """
        solution.number_of_machines = 0

        # Calculate machine utilization and count active machines
        for machine_id, route in solution.route_plan_machine.items():
            duration = sum(self.data.order_items[oid].duration for oid in route)
            solution.machine_utilization_time[machine_id] = duration
            if duration > 0:
                solution.number_of_machines += 1  # Count machines with assignments




    # ===== LEGACY METHODS (NOT IN USE) =====
    
    def categorizing_machine_worker(self, solution: Solution):
        """
        Legacy method for categorizing machines and workers by usage status.
        
        Note: This method is marked as "NOT IN USE" in the original code
        and appears to be superseded by the more efficient counting methods above.
        
        Args:
            solution: Solution object to update with resource categorization
        """

        # Initialize category lists for resources
        solution.used_machines = []      # Machines with assigned tasks
        solution.unused_machines = []    # Machines without assigned tasks
        solution.used_workers = []       # Workers with assigned tasks
        solution.unused_workers = []     # Workers without assigned tasks
        solution.used_attachments = []   # Attachments with assigned tasks
        solution.unused_attachments = [] # Attachments without assigned tasks
        
        # Categorize machines by usage
        for machine, route in solution.route_plan_machine.items():
            if len(route) == 0:
                solution.unused_machines.append(machine)
            elif len(route) > 0:
                solution.used_machines.append(machine)

        # Categorize workers by usage
        for worker, route in solution.route_plan_worker.items():
            if len(route) == 0:
                solution.unused_workers.append(worker)
            elif len(route) > 0:
                solution.used_workers.append(worker)