from OutputData import Solution
from OutputData import *
import itertools        
from EvaluationLogic import EvaluationLogic
import concurrent.futures  # For parallelism
from copy import deepcopy
from itertools import chain
import itertools


class BaseMove:

    def __init__(self):
        self.Delta = None

    def setDelta(self,delta_tuple):
        ''' Set the Delta of the Move'''
        self.Delta = delta_tuple[0]
        self.DeltaDetails = delta_tuple[1]

class BaseNeighborhood:

    def __init__(self, data: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        self.data = data
        self.evaluationLogic = evaluationLogic
        self.ParetoSolutions = paretoSolutions
        self.RNG = rng

        # Create empty lists for discovering different moves
        self.Moves = []
        self.MoveSolutions = []
        self.type = 'None'

    def DiscoverMoves(self) -> None:
        ''' Find all possible moves for particular neighborhood and permutation
            And shuffles them! 
        '''
        raise Exception('DiscoverMoves() is not implemented for the abstract BaseNeighborhood class.')

    def EvaluateMoves(self, evaluationStrategy: str) -> None:
        ''' Define a strategy for the local search of the neighborhood and "activate" it'''

        if evaluationStrategy == 'BestImprovement':
            self.EvaluateMovesBestImprovement()
        elif evaluationStrategy == 'FirstImprovement':
            self.EvaluateMovesFirstImprovement()
        else:
            raise Exception(f'Evaluation strategy {evaluationStrategy} not implemented.')

    def EvaluateMove(self, move: BaseMove) -> None:
        ''' Calculates the MakeSpan of the certain move - adds to recent Solution'''
        raise Exception('EvaluateMove() is not implemented for the abstract BaseNeighborhood class.')

    def EvaluateMovesBestImprovement(self) -> None:
        """ Evaluate all moves for best improvement and adds the calculated solutions to list MoveSolutions"""
        for move in self.Moves:
            self.EvaluateMove(move)
            self.MoveSolutions.append(move)

    def EvaluateMovesFirstImprovement(self) -> None:
        """ Evaluate all moves until the first one is found that improves the best solution found so far. """
        raise Exception('EvaluateMovesFirstImprovement() is not implemented for the abstract BaseNeighborhood class.')

    def MakeBestMove(self) -> BaseMove:
        ''' Returns the best move found from the list Move Solutions'''
        raise Exception('MakeBestMove() is not implemented for the abstract BaseNeighborhood class.')
    
    def Update(self) -> None:
        ''' Updates the actual permutation and deletes all saved Moves and Move Solutions'''
        self.Moves.clear()
        self.MoveSolutions.clear()


    def WorkerRouteFeasibilityCheck(self, worker_id, worker_route: list) -> bool:
        ''' Checks if the worker route is feasible'''

        worker = self.data.workers[worker_id]

        # Check if the worker does not work more than 5 consecutive night shifts
        night_shifts = 0
        for order_item_id in worker_route:
            if order_item_id in worker.night_shift_ids:
                night_shifts += 1
            else:
                night_shifts = 0
            if night_shifts > self.data._max_consecutive_night_shifts:
                return False
        
        # Check if the worker does not work more than 10 shifts in 14 days
        order_items = [self.data.order_items[order_item_id] for order_item_id in worker_route]
        for i, order_item_i in enumerate(order_items):
            window_start = order_item_i.start_time.date()
            window_end = window_start + self.data._time_period_for_max_shifts
            shift_count = 0
            for order_item_j in order_items:
                if window_start <= order_item_j.start_time.date() < window_end:
                    shift_count += 1
            if shift_count > self.data._max_shifts_in_time_period:
                return False
        

        return True



class OutputNeighborhood(BaseNeighborhood):

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

    def EvaluateMove(self, move: BaseMove) -> None:
        raise Exception('EvaluateMove() is not implemented for the abstract OutputNeighborhood class.')

    def MakeBestMove(self) -> BaseMove:
        
        # Sorting will be handled by the child classes
        self.sort_move_solutions()
        
        for move_solution in self.MoveSolutions:
            if self.WorkerRouteFeasibilityCheck(move_solution.WorkerID, move_solution.WorkerRoute):
                return move_solution
                    
        return None

    def sort_move_solutions(self):
        # Placeholder method to be overridden by child classes
        raise NotImplementedError('sort_move_solutions() must be implemented in the child class')
            
    def EvaluateMovesFirstImprovement(self) -> None:
        """ Evaluate all moves until the first one is found that improves the best solution found so far. """

        for move in self.Moves:
            self.EvaluateMove(move)

            ### NEED OF FEASIBILITY CHECK!! 
            if self.WorkerRouteFeasibilityCheck(move.RouteDayCohort):
                self.MoveSolutions.append(move)
                return None
        
        ### Return None, if no feasible moves found! 
        return None 


    def LocalSearch(self, neighborhoodEvaluationStrategy:str, solution:Solution) -> None:
        ''' Tries to find a better solution from the start solution by searching the neighborhod'''

        hasSolutionImproved = True
        bestNeighborhoodSolution = deepcopy(solution)

        iterator = 1
        while hasSolutionImproved:
            
            # Sets Algorithm back!
            self.Update() 
            self.DiscoverMoves(bestNeighborhoodSolution)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()


            if bestNeighborhoodMove is not None:
                
                #print(f"\nIteration: {iterator}")

                worker_route, machine_route, attachement_route = self.constructCompleteRoutes(bestNeighborhoodMove, bestNeighborhoodSolution)
                bestNeighborhoodSolution = Solution(worker_route, machine_route, attachement_route, self.data)
                self.evaluationLogic.evaluate(bestNeighborhoodSolution)

                #self.solutionPool.AddSolution(bestNeighborhoodSolution)

                #print(f"Best Neighborhood Solution: \n{bestNeighborhoodSolution}")

            else:
                print(f"\nNo better solution found in iteration {iterator}")
                hasSolutionImproved = False

            iterator += 1

        return bestNeighborhoodSolution
    

class InsertShiftMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """

    def __init__(self, machine_id, worker_id, machine_route, worker_route, machine_route_index, worker_route_index, order_item_id, dynamic_percentage, attachment_information=None):


        self.MachineRoute = list(machine_route)
        self.WorkerRoute = list(worker_route)

        self.MachineRouteIndex = machine_route_index
        self.WorkerRouteIndex = worker_route_index

        self.OrderItemID = order_item_id
        
        self.MachineID = machine_id
        self.WorkerID = worker_id

        

        self.MachineRoute.insert(self.MachineRouteIndex, self.OrderItemID)
        self.WorkerRoute.insert(self.WorkerRouteIndex, self.OrderItemID)


        self.DynamicPercentage = dynamic_percentage

        

        if attachment_information is not None:
            index = 0
            for attachment_id, attachment_index, attachment_route in attachment_information:
                # Dynamically set the attributes using f-string formatting
                setattr(self, f"AttachmentRoute_{index}", list(attachment_route))
                setattr(self, f"AttachmentRouteIndex_{index}", attachment_index)
                setattr(self, f"AttachmentID_{index}", attachment_id)
                
                # Retrieve the newly created route attribute and insert the order item
                route = getattr(self, f"AttachmentRoute_{index}")
                route.insert(attachment_index, self.OrderItemID)
                
                index += 1

            self.NumberOfAttachments = index

        else:
            self.NumberOfAttachments = 0



        #print(f"Machine ID: {self.MachineID}")
        #print(f"Machine Route: {self.MachineRoute}")
        #print(f"Worker ID: {self.WorkerID}")
        #print(f"Worker Route: {self.WorkerRoute}")

class InsertShiftNeighborhood(OutputNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData:InputData, evaluationLogic:EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData,  evaluationLogic, paretoSolutions, rng)

        self.Type = 'Insert_Shift'


    def DiscoverMoves(self, solution:Solution, not_used_shifts = None):
        """ Generate all $n choose 2$ moves and shuffle them """

        if not_used_shifts is None:
            unused_order_item_ids = solution.not_started_order_item_ids

        
        for order_item_id in unused_order_item_ids:

            # Dictionary to store information about the position of the order_item in machine routes
            order_item_position_machine_route = dict() # This will map machine ids to the corresponding insertion information which is a list of the form [position, route]
            order_item_position_worker_route = dict() # This will map worker ids to the corresponding insertion information which is a list of the form [position, route]
            possible_attachment_positions = dict()  # This will map a key (tuple of attachment ids) to the corresponding insertion information which is a tuple of the form [(position, route), ...]

            for machine_id, machine_route in solution.route_plan_machine.items():
                machine = solution.data.machines[machine_id]

                # Continue to next machine if order_item cannot be processed by current machine
                machine_possible_order_item_ids = [order_item_ids for orders in machine.possible_order_item_ids.values() for order_item_ids in orders]
                if order_item_id not in machine_possible_order_item_ids:
                    continue

                # If (possible) machine is not included in current solution, order item can be inserted at first position
                if len(machine_route) == 0:
                    order_item_position_machine_route[machine_id] = [0, list(machine_route)]
                    continue

                # Find the position of the order_item in the machine route
                for order_item_id_machine in machine_route:
                    # Break to next machine if order_item is not a predecessor or successor of current order_item_machine
                    if order_item_id not in machine.predecessor_ids[order_item_id_machine] and order_item_id not in machine.successor_ids[order_item_id_machine]:
                        break

                    # If order_item is a predecessor of order_item_machine, it can be inserted before order_item_id_machine
                    if order_item_id in machine.predecessor_ids[order_item_id_machine]:
                        order_item_position_machine_route[machine_id] = [machine_route.index(order_item_id_machine), list(machine_route)]
                        break
                    
                    # If order_item is a successor of the last order_item in the machine route, it can be inserted at the end of the machine route
                    if len(machine_route) == machine_route.index(order_item_id_machine) + 1:
                        if order_item_id in machine.successor_ids[order_item_id_machine]:
                            order_item_position_machine_route[machine_id] = [machine_route.index(order_item_id_machine) + 1, list(machine_route)]
                            break
                                

            for worker_id, worker_route in solution.route_plan_worker.items():
                worker = solution.data.workers[worker_id]

                # Continue to next worker if order_item cannot be processed by current worker
                worker_possible_order_item_ids = [order_item_ids for orders in worker.possible_order_item_ids.values() for order_item_ids in orders]
                if order_item_id not in worker_possible_order_item_ids:
                    continue
                
                # Continue to next worker if the work time would exceed the maximum working hours
                if solution.worker_work_time[worker_id] + solution.data.order_items[order_item_id].duration > self.data._max_working_hours:
                    continue
  
                # If (possible) worker is not included in current solution, order item can be inserted at first position
                if len(worker_route) == 0:
                    order_item_position_worker_route[worker_id] = [0, list(worker_route)]
                    continue
                
                # Find the position of the order_item in the worker route
                for order_item_id_worker in worker_route:
                    
                    # Break to next worker if order_item is not a predecessor or successor of current order_item_worker
                    if order_item_id not in worker.predecessor_ids[order_item_id_worker] and order_item_id not in worker.successor_ids[order_item_id_worker]:
                        break


                    # If order_item is a predecessor of order_item_worker, it can be inserted before order_item_id_worker
                    if order_item_id in worker.predecessor_ids[order_item_id_worker]:
                        order_item_position_worker_route[worker_id] = [worker_route.index(order_item_id_worker), list(worker_route)]
                        break
                    
                    # If order_item is a successor of the last order_item in the worker route, it can be inserted at the end of the worker route
                    if len(worker_route) == worker_route.index(order_item_id_worker) + 1:
                        if order_item_id in worker.successor_ids[order_item_id_worker]:
                            order_item_position_worker_route[worker_id] = [worker_route.index(order_item_id_worker) + 1, list(worker_route)]
                            break


            # Only search for attachment positions if the order item requires attachments
            order_item_obj = solution.data.order_items[order_item_id]
            

            if order_item_obj.equipment_types:
                # For each required equipment occurrence (order_item_obj.equipment_types can have duplicates), collect possible insertion positions from the attachment route plan
                positions_for_each_occurrence = []
                for equipment_type in order_item_obj.equipment_types:
                    possible_positions_for_type = []
                    for attachment_id, attachment_route in solution.route_plan_attachment.items():
                        attachment = solution.data.attachments[int(attachment_id)]

                        # Only consider attachments that can process this equipment type
                        if equipment_type != attachment.type:
                            continue

                        # Check if the order item is allowed for this attachment
                        attachment_possible_order_item_ids = [oid for orders in attachment.possible_order_item_ids.values() for oid in orders]
                        if order_item_id not in attachment_possible_order_item_ids:
                            continue

                        # If the attachment route is empty, insertion position is 0
                        if len(attachment_route) == 0:
                            possible_positions_for_type.append((attachment_id, 0, list(attachment_route)))
                            continue

                        # Otherwise, find a valid insertion position based on predecessor/successor relationships
                        for order_item_id_attachment in attachment_route:
                            pred = attachment.predecessor_ids.get(order_item_id_attachment, [])
                            succ = attachment.successor_ids.get(order_item_id_attachment, [])
                            # If the order item is neither a predecessor nor a successor, skip this element.
                            if order_item_id not in pred and order_item_id not in succ:
                                continue

                            # If the order item is a predecessor, it can be inserted before the current item.
                            if order_item_id in pred:
                                pos = attachment_route.index(order_item_id_attachment)
                                possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                                break

                            # If it is a successor of the last element, insert at the end.
                            if attachment_route.index(order_item_id_attachment) == len(attachment_route) - 1:
                                if order_item_id in succ:
                                    pos = attachment_route.index(order_item_id_attachment) + 1
                                    possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                                    break

                    positions_for_each_occurrence.append(possible_positions_for_type)

                attachment_insertion_combinations = list(itertools.product(*positions_for_each_occurrence))
                # Store the valid combinations in the dictionary.
                for combo in attachment_insertion_combinations:
                    # Create a key tuple consisting of the attachment IDs from each insertion option in the combo.
                    attachment_ids_tuple = tuple(pos[0] for pos in combo)
                    # Filter out combinations where the same attachment is used more than once.
                    if len(set(attachment_ids_tuple)) < len(attachment_ids_tuple):
                        continue  # Skip this combination if there's a duplicate attachment ID.
                    possible_attachment_positions[attachment_ids_tuple] = combo

            order = [order.order_number for order in solution.data.orders if order_item_id in order.order_item_ids][0]

            for machine_id, machine_index_and_route in order_item_position_machine_route.items():
                for worker_id, worker_index_and_route in order_item_position_worker_route.items():
                    if order_item_obj.equipment_types:
                        for attachment_ids_tuple, attachment_info in possible_attachment_positions.items():
                            self.Moves.append(InsertShiftMove(
                                machine_id,
                                worker_id,
                                machine_index_and_route[1],  # machine route snapshot
                                worker_index_and_route[1],   # worker route snapshot
                                machine_index_and_route[0],  # machine insertion index
                                worker_index_and_route[0],   # worker insertion index
                                order_item_id,
                                dynamic_percentage = solution.dynamic_percentage_order[order],
                                attachment_information=attachment_info  # attachment insertion information tuple
                            ))
                    else:
                        self.Moves.append(InsertShiftMove(
                            machine_id,
                            worker_id,
                            machine_index_and_route[1],
                            worker_index_and_route[1],
                            machine_index_and_route[0],
                            worker_index_and_route[0],
                            order_item_id,
                            dynamic_percentage = solution.dynamic_percentage_order[order]
                        ))


            #print(f"Order Item Position Machine Route: {order_item_position_machine_route}")
            #print(f"Order Item Position Worker Route: {order_item_position_worker_route}")
                                

    def EvaluateMove(self, move:InsertShiftMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_insert_shift_delta(move))

    
    def sort_move_solutions(self):

        # Sort with highest Delta[0] first, if equal sort with lowest Delta[1] first
        self.MoveSolutions.sort(key=lambda move: (move.Delta[0], -move.Delta[1]), reverse=True)


    def constructCompleteRoutes(self, move:InsertShiftMove, solution:Solution) -> dict: 
        ''' Constructs the comlete Route from the Move'''
        
        machine_route_plan = deepcopy(solution.route_plan_machine)
        worker_route_plan = deepcopy(solution.route_plan_worker)
        attachment_route_plan = deepcopy(solution.route_plan_attachment)

        machine_route_plan[move.MachineID] = move.MachineRoute
        worker_route_plan[move.WorkerID] = move.WorkerRoute
        
        for index in range(move.NumberOfAttachments):
            attachment_route_plan[getattr(move, f"AttachmentID_{index}")] = getattr(move, f"AttachmentRoute_{index}")

        return worker_route_plan, machine_route_plan, attachment_route_plan

        
class SwapShiftExternalMove(BaseMove):
    
    def __init__(self, machine_id, worker_id, machine_route, worker_route, machine_index, worker_index, order_item_id_int, order_item_id_ext, dynamic_percentage_int, dynamic_percentage_ext, attachment_information_int=None, attachment_information_ext=None):
        
        self.MachineRoute = list(machine_route)
        self.WorkerRoute = list(worker_route)

        self.MachineRouteIndex = machine_index
        self.WorkerRouteIndex = worker_index

        self.OrderItemIDInt = order_item_id_int
        self.OrderItemIDExt = order_item_id_ext

        self.MachineID = machine_id
        self.WorkerID = worker_id

        self.MachineRoute.insert(self.MachineRouteIndex, self.OrderItemIDExt)
        self.WorkerRoute.insert(self.WorkerRouteIndex, self.OrderItemIDExt)

        self.MachineRoute.remove(self.OrderItemIDInt)
        self.WorkerRoute.remove(self.OrderItemIDInt)

        self.DynamicPercentageInt = dynamic_percentage_int
        self.DynamicPercentageExt = dynamic_percentage_ext


        if attachment_information_ext is not None:
            index = 0
            for attachment_id, attachment_index, attachment_route in attachment_information_ext:
                # Dynamically set the attributes using f-string formatting
                setattr(self, f"AttachmentRouteExt_{index}", list(attachment_route))
                setattr(self, f"AttachmentRouteIndexExt_{index}", attachment_index)
                setattr(self, f"AttachmentIDExt_{index}", attachment_id)
                
                # Retrieve the newly created route attribute and insert the order item
                route = getattr(self, f"AttachmentRouteExt_{index}")
                route.insert(attachment_index, self.OrderItemIDExt)
                
                index += 1

            self.NumberOfAttachmentsExt = index

        else:
            self.NumberOfAttachmentsExt = 0
                


        if attachment_information_int is not None:
            index = 0
            for attachment_id, attachment_index_route in attachment_information_int.items():
                setattr(self, f"AttachmentRouteInt_{index}", list(attachment_index_route[1]))
                setattr(self, f"AttachmentRouteIndexInt_{index}", attachment_index_route[0])
                setattr(self, f"AttachmentIDInt_{index}", attachment_id)

                route = getattr(self, f"AttachmentRouteInt_{index}")
                route.remove(self.OrderItemIDInt)
                
                index += 1

            self.NumberOfAttachmentsInt = index

        else:
            self.NumberOfAttachmentsInt = 0

class SwapShiftExternalNeighborhood(OutputNeighborhood):
    
    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

        self.Type = 'Swap_Shift_External'

    def DiscoverMoves(self, solution: Solution, not_used_shifts = None):
        """ Generate all $n choose 2$ moves """

        if not_used_shifts is None:
            unused_order_item_ids = solution.not_started_order_item_ids

        for order_item_id_ext in unused_order_item_ids:
            for machine_id, machine_route in solution.route_plan_machine.items():
                
                # Continue to next machine if current machine is not part of the solution
                if len(machine_route) == 0:
                    continue

                machine = solution.data.machines[machine_id]

                # Continue to next machine if order_item cannot be processed by current machine
                machine_possible_order_item_ids = [order_item_ids for orders in machine.possible_order_item_ids.values() for order_item_ids in orders]
                if order_item_id_ext not in machine_possible_order_item_ids:
                    continue

                # Find the position of the order_item in the machine route
                for machine_index, order_item_id_int in enumerate(machine_route):
                    
                    # If both order items collide check the following conditions
                    if order_item_id_ext not in machine.predecessor_ids[order_item_id_int] and order_item_id_ext not in machine.successor_ids[order_item_id_int]:
                        
                        # Check for the first order item in the machine route
                        if machine_index == 0:
                            # If order_item_id_ext collides with order_item_id_machine and order_item_id_ext is a predecessor of the successor of order_item_id_machine, it can be inserted in the position of order_item_id_machine
                            if order_item_id_ext in machine.predecessor_ids[machine_route[machine_index + 1]]:
                                worker_id, worker_index, worker_route = self.find_worker_route(solution, order_item_id_ext, order_item_id_int)
                                attachment_info_int, attachment_info_ext = self.find_attachment_routes(solution, order_item_id_ext, order_item_id_int)
                                if worker_id is not None:
                                    order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                    order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                    if attachment_info_int == True and attachment_info_ext == True:
                                        self.Moves.append(SwapShiftExternalMove(machine_id, worker_id, machine_route, worker_route, machine_index, worker_index,
                                                                                order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], 
                                                                                solution.dynamic_percentage_order[order_ext]))
                                    
                                    elif attachment_info_ext == True and attachment_info_int:
                                        self.Moves.append(SwapShiftExternalMove(machine_id, worker_id, machine_route, worker_route, machine_index, worker_index,
                                                                                order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int],
                                                                                solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int))
                                    
                                    elif attachment_info_int and attachment_info_ext:
                                        for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                            self.Moves.append(SwapShiftExternalMove(machine_id, worker_id, machine_route, worker_route, machine_index, worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info))
                                break

                        # Check for order_items from the second until the second last order item in the machine route
                        elif len(machine_route) > machine_index + 1:
                            # If order_item_id_ext collides with order_item_id_machine and order_item_id_ext is a predecessor of the successor of order_item_id_machine, it can be inserted in the position of order_item_id_machine
                            if order_item_id_ext in machine.predecessor_ids[machine_route[machine_index + 1]] and order_item_id_ext in machine.successor_ids[machine_route[machine_index - 1]]:
                                worker_id, worker_index, worker_route = self.find_worker_route(solution, order_item_id_ext, order_item_id_int)
                                attachment_info_int, attachment_info_ext = self.find_attachment_routes(solution, order_item_id_ext, order_item_id_int)
                                if worker_id is not None:
                                    order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                    order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                    if attachment_info_int == True and attachment_info_ext == True:
                                        self.Moves.append(SwapShiftExternalMove(machine_id, worker_id, machine_route, worker_route, machine_index, worker_index,
                                                                                order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], 
                                                                                solution.dynamic_percentage_order[order_ext]))
                                    
                                    elif attachment_info_ext == True and attachment_info_int:
                                        self.Moves.append(SwapShiftExternalMove(machine_id, worker_id, machine_route, worker_route, machine_index, worker_index,
                                                                                order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int],
                                                                                solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int))
                                    
                                    elif attachment_info_int and attachment_info_ext:
                                        for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                            self.Moves.append(SwapShiftExternalMove(machine_id, worker_id, machine_route, worker_route, machine_index, worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info))
                                break


                        # Check for the last order item in the machine route
                        elif len(machine_route) == machine_index + 1:
                            # If order_item_id_ext collides with order_item_id_machine and order_item_id_ext is a successor of the predecessor of order_item_id_machine, it can be inserted in the position of order_item_id_machine
                            if order_item_id_ext in machine.successor_ids.get(machine_index - 1, []):
                                worker_id, worker_index, worker_route = self.find_worker_route(solution, order_item_id_ext, order_item_id_int)
                                attachment_info_int, attachment_info_ext = self.find_attachment_routes(solution, order_item_id_ext, order_item_id_int)
                                if worker_id is not None:
                                    order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                    order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                    if attachment_info_int == True and attachment_info_ext == True:
                                        self.Moves.append(SwapShiftExternalMove(machine_id, worker_id, machine_route, worker_route, machine_index, worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext]))
                                    elif attachment_info_ext == True and attachment_info_int:
                                        self.Moves.append(SwapShiftExternalMove(machine_id, worker_id, machine_route, worker_route, machine_index, worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int))
                                    elif attachment_info_int and attachment_info_ext:
                                        for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                            self.Moves.append(SwapShiftExternalMove(machine_id, worker_id, machine_route, worker_route, machine_index, worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info))
                                break



    def find_worker_route(self, solution: Solution, order_item_id_ext: int, order_item_id_int: int) -> dict:
                        
            for worker_id, worker_route in solution.route_plan_worker.items():

                # Search for the worker route of the order_item_id_int
                if order_item_id_int not in worker_route:
                    continue

                # Continue to next worker if current worker is not part of the solution
                if len(worker_route) == 0:
                    continue

                worker = solution.data.workers[worker_id]
                
                # Continue to next worker if the work time would exceed the maximum working hours
                if solution.worker_work_time[worker_id] + solution.data.order_items[order_item_id_ext].duration - solution.data.order_items[order_item_id_int].duration > self.data._max_working_hours:
                    continue

                # Continue to next worker if order_item_ext cannot be processed by current worker
                worker_possible_order_item_ids = [order_item_ids for orders in worker.possible_order_item_ids.values() for order_item_ids in orders]
                if order_item_id_ext not in worker_possible_order_item_ids:
                    continue

                index = worker_route.index(order_item_id_int)

                # Check if order_item_id_ext can be inserted at position index depending on the predecessor and successor relations

                predecessor_id = worker_route[index - 1] if index > 0 else None
                successor_id = worker_route[index + 1] if index < len(worker_route) - 1 else None

                if predecessor_id in worker.predecessor_ids[order_item_id_ext] and successor_id in worker.successor_ids[order_item_id_ext]:
                    return worker_id, index, worker_route
            
            return None, None, None
    
    def find_attachment_routes(self, solution: Solution, order_item_id_ext: int, order_item_id_int: int) -> dict:
        """ Change the attachment routes to reflect the swap of the internal and external order items. """
        
        order_item_ext_obj = solution.data.order_items[order_item_id_ext]
        order_item_int_obj = solution.data.order_items[order_item_id_int]

        # If neither the internal nor the external order item requires attachments, the attachment routes do not need to be changed
        if not order_item_ext_obj.equipment_types and not order_item_int_obj.equipment_types:
            return True, True
        
        attachment_info_int = dict()
        attachment_info_ext = dict()


        # Search for the attachment routes of the internal order item
        for attachment_id, attachment_route in solution.route_plan_attachment.items():
                if order_item_id_int in attachment_route:
                    attachment_info_int[attachment_id] = [attachment_route.index(order_item_id_int), list(attachment_route)]


        # If the external order item does not require attachments, only attachments information for the internal order item is needed
        if not order_item_ext_obj.equipment_types:
            return attachment_info_int, True


        # If the external order item requires attachments, the attachment routes for both the internal and external order items need to be changed
        # Therefore in addition to the information fo internal order item, the positions of the external order item in the attachment routes is searched, depending on the number of equipment types
        positions_for_each_occurrence = []
        for equipment_type in order_item_ext_obj.equipment_types:
            possible_positions_for_type = []
            for attachment_id, attachment_route in solution.route_plan_attachment.items():
                attachment = solution.data.attachments[int(attachment_id)]

                # Only consider attachments that can process this equipment type
                if equipment_type != attachment.type:
                    continue

                # Check if the order item is allowed for this attachment
                attachment_possible_order_item_ids = [oid for orders in attachment.possible_order_item_ids.values() for oid in orders]
                if order_item_id_ext not in attachment_possible_order_item_ids:
                    continue

                # If the attachment route is empty, insertion position is 0
                if len(attachment_route) == 0:
                    possible_positions_for_type.append((attachment_id, 0, list(attachment_route)))
                    continue
                
                # If the order_item_int is in the attachment route, the order_item_ext can be inserted at the same position if it is a predecessor or successor of the order_item_int
                if order_item_id_int in attachment_route:
                    index = attachment_route.index(order_item_id_int)
                    pred_id = attachment_route[index - 1] if index > 0 else None
                    succ_id = attachment_route[index + 1] if index < len(attachment_route) - 1 else None

                    if order_item_id_ext in attachment.predecessor_ids.get(pred_id, []) and order_item_id_ext in attachment.successor_ids.get(succ_id, []):
                        possible_positions_for_type.append((attachment_id, index, list(attachment_route)))
                        continue


                # Otherwise, find a valid insertion position based on predecessor/successor relationships
                for order_item_id_attachment in attachment_route:

                    pred = attachment.predecessor_ids.get(order_item_id_attachment, [])
                    succ = attachment.successor_ids.get(order_item_id_attachment, [])
                    # If the order item is neither a predecessor nor a successor, skip this element
                    if order_item_id_ext not in pred and order_item_id_ext not in succ:
                        continue

                    # If the order item is a predecessor, it can be inserted before the current item
                    if order_item_id_ext in pred:
                        pos = attachment_route.index(order_item_id_attachment)
                        possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                        break

                    # If it is a successor of the last element, insert at the end
                    if attachment_route.index(order_item_id_attachment) == len(attachment_route) - 1:
                        if order_item_id_ext in succ:
                            pos = attachment_route.index(order_item_id_attachment) + 1
                            possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                            break

            positions_for_each_occurrence.append(possible_positions_for_type)

        attachment_insertion_combinations = list(itertools.product(*positions_for_each_occurrence))
        # Store the valid combinations in the dictionary
        for combo in attachment_insertion_combinations:
            # Create a key tuple consisting of the attachment IDs from each insertion option in the combo
            attachment_ids_tuple = tuple(pos[0] for pos in combo)
            # Filter out combinations where the same attachment is used more than once
            if len(set(attachment_ids_tuple)) < len(attachment_ids_tuple):
                continue  # Skip this combination if there's a duplicate attachment ID
            attachment_info_ext[attachment_ids_tuple] = combo

        if not attachment_info_ext:
            return False, False


        return attachment_info_int, attachment_info_ext




    def EvaluateMove(self, move: SwapShiftExternalMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_swap_shift_external_delta(move))


    def sort_move_solutions(self):
        
        # Sort with highest Delta[0] first, if equal sort with lowest Delta[1] first
        self.MoveSolutions.sort(key=lambda move: (move.Delta[0], -move.Delta[1]), reverse=True)

    
    def constructCompleteRoutes(self, move:SwapShiftExternalMove, solution:Solution) -> dict:
        
        machine_route_plan = deepcopy(solution.route_plan_machine)
        worker_route_plan = deepcopy(solution.route_plan_worker)
        attachement_route_plan = deepcopy(solution.route_plan_attachment)

        machine_route_plan[move.MachineID] = move.MachineRoute
        worker_route_plan[move.WorkerID] = move.WorkerRoute

        return worker_route_plan, machine_route_plan, attachement_route_plan
    

    def MakeBestMove(self) -> BaseMove:
        
        # Sorting will be handled by the child classes
        self.sort_move_solutions()
        
        for move_solution in self.MoveSolutions:
            if self.WorkerRouteFeasibilityCheck(move_solution.WorkerID, move_solution.WorkerRoute):
                if move_solution.Delta[0] > 0:
                    return move_solution
                    
        return None



class TimeNeighborhood(BaseNeighborhood):

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

    def EvaluateMove(self, move: BaseMove) -> None:
        raise Exception('EvaluateMove() is not implemented for the abstract OutputNeighborhood class.')

    def MakeBestMove(self) -> BaseMove:
        
        # Sorting will be handled by the child classes
        self.sort_move_solutions()
        
        for move_solution in self.MoveSolutions:
            if self.WorkerRouteFeasibilityCheck(move_solution.WorkerID1, move_solution.WorkerRoute1) and self.WorkerRouteFeasibilityCheck(move_solution.WorkerID2, move_solution.WorkerRoute2):
                return move_solution
                    
        return None

    def sort_move_solutions(self):
        # Placeholder method to be overridden by child classes
        raise NotImplementedError('sort_move_solutions() must be implemented in the child class')
            
    def EvaluateMovesFirstImprovement(self) -> None:
        """ Evaluate all moves until the first one is found that improves the best solution found so far. """

        for move in self.Moves:
            self.EvaluateMove(move)

            ### NEED OF FEASIBILITY CHECK!! 
            if self.WorkerRouteFeasibilityCheck(move.RouteDayCohort):
                self.MoveSolutions.append(move)
                return None
        
        ### Return None, if no feasible moves found! 
        return None 


    def LocalSearch(self, neighborhoodEvaluationStrategy:str, solution:Solution) -> None:
        ''' Tries to find a better solution from the start solution by searching the neighborhod'''

        hasSolutionImproved = True
        bestNeighborhoodSolution = deepcopy(solution)

        print(f"\nInitial Worker Route: \n{bestNeighborhoodSolution.route_plan_worker}")

        iterator = 1
        while hasSolutionImproved:
            
            # Sets Algorithm back!
            self.Update() 
            self.DiscoverMoves(bestNeighborhoodSolution)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()


            if bestNeighborhoodMove is not None and bestNeighborhoodMove.Delta < 0:
                #print(f"\nIteration: {iterator}")

                worker_route, machine_route, attachement_route = self.constructCompleteRoutes(bestNeighborhoodMove, bestNeighborhoodSolution)
                bestNeighborhoodSolution = Solution(worker_route, machine_route, attachement_route, self.data)
                self.evaluationLogic.evaluate(bestNeighborhoodSolution)

                #self.solutionPool.AddSolution(bestNeighborhoodSolution)

                print(f"\nIteration: {iterator}")
                if self.Type == 'Swap_Shift_Worker':
                    print(f"Best Neighborhood Move Items: \n{bestNeighborhoodMove.WorkerID1}: {bestNeighborhoodMove.WorkerRoute1} New Order Item: {bestNeighborhoodMove.OrderItemID2} \n{bestNeighborhoodMove.WorkerID2}: {bestNeighborhoodMove.WorkerRoute2} New Order Item: {bestNeighborhoodMove.OrderItemID1}")
                    print(f"Best Neighborhood Move Delta: {bestNeighborhoodMove.Delta}")
                elif self.Type == 'Replace_Shift_Worker':
                    print(f"Best Neighborhood Move Items: \n{bestNeighborhoodMove.WorkerID1}: {bestNeighborhoodMove.WorkerRoute1} \n{bestNeighborhoodMove.WorkerID2}: {bestNeighborhoodMove.WorkerRoute2} New Order Item: {bestNeighborhoodMove.OrderItemID}")

            else:
                print(f"\nNo better solution found in iteration {iterator}")
                hasSolutionImproved = False

            feasbile = bestNeighborhoodSolution.feasibility_check()
            if not feasbile:
                print(f"Feasibility Check failed in iteration {iterator}")

            iterator += 1

            #print(f"\nBest Current Solution: \n{bestNeighborhoodSolution}")

        print(f"\nBest Worker Route: \n{bestNeighborhoodSolution.route_plan_worker}")

        return bestNeighborhoodSolution
    
    def SingleMove(self, solution: Solution) -> BaseMove:
        """ Generate a single move for the given solution. """
        

        self.Update()
        
        move = self.MakeOneMove(solution)

        if move:
            self.EvaluateMove(move)
            return move
        else:
            raise Exception('No moves found in the neighborhood.')



            



class SwapShiftAttachmentMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """
                    
    def __init__(self, attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_index_1, attachment_index_2, order_item_id_1, order_item_id_2, taken_index_1, taken_index_2):

        self.AttachmentRoute1 = list(attachment_route_1)
        self.AttachmentRoute2 = list(attachment_route_2)

        self.AttachmentRoute1Original = list(attachment_route_1)
        self.AttachmentRoute2Original = list(attachment_route_2)

        self.AttachmentRouteTakenIndex1 = taken_index_1
        self.AttachmentRouteTakenIndex2 = taken_index_2

        self.AttachmentRouteIndex1 = attachment_index_1
        self.AttachmentRouteIndex2 = attachment_index_2

        self.OrderItemID1 = order_item_id_1
        self.OrderItemID2 = order_item_id_2

        self.AttachmentID1 = attachment_id_1
        self.AttachmentID2 = attachment_id_2

        self.AttachmentRoute1.insert(self.AttachmentRouteIndex1, self.OrderItemID2)
        self.AttachmentRoute2.insert(self.AttachmentRouteIndex2, self.OrderItemID1)

        self.AttachmentRoute1.remove(self.OrderItemID1)
        self.AttachmentRoute2.remove(self.OrderItemID2)

class SwapShiftAttachmentNeighborhood(TimeNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

        self.Type = 'Swap_Shift_Attachment'

    def MakeBestMove(self) -> BaseMove:
        
        # Sorting will be handled by the child classes
        self.sort_move_solutions()
        
        for move_solution in self.MoveSolutions:
            return move_solution
                    
        return None

    def DiscoverMoves(self, solution: Solution):
        """ Generate all $n choose 2$ moves """

        for attachment_id_1, attachment_route_1 in solution.route_plan_attachment.items():
            for attachment_id_2, attachment_route_2 in solution.route_plan_attachment.items():
                attachment_1_order_item_positions = {}
                attachment_2_order_item_positions = {}

                same_position_attachment_route_1 = {}
                same_position_attachment_route_2 = {}

                # Skip if one attachment route is empty
                if len(attachment_route_1) == 0:
                    break
                if len(attachment_route_2) == 0:
                    continue

                # Skip if the same attachment is selected
                if attachment_id_1 == attachment_id_2:
                    continue
                else:
                    attachment_1 = solution.data.attachments[attachment_id_1]
                    attachment_2 = solution.data.attachments[attachment_id_2]

                    if attachment_1.type != attachment_2.type:
                        continue

                    for order_item_id_1 in attachment_route_1:
                        # Continue to next order item if order_item_id_1 is not in the list of all planned order items for attachment 2
                        attachment_2_possible_order_item_ids = [order_item_ids for orders in attachment_2.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_1 not in attachment_2_possible_order_item_ids:
                            continue
                        else:
                            # Find the position of order_item_id_1 in the attachment route of attachment 2
                            for index, order_item_id_2 in enumerate(attachment_route_2):

                                # If both order items collide check the following conditions
                                if order_item_id_1 not in attachment_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in attachment_2.successor_ids[order_item_id_2]:

                                    # Check for order_items until the second last order item in the attachment route
                                    if len(attachment_route_2) > index + 1:
                                        # If order_item_id_1 collides with order_item_id_2 and order_item_id_1 is a predecessor of the successor of order_item_id_2, it can be inserted in the position of order_item_id_2
                                        if order_item_id_1 in attachment_2.predecessor_ids[attachment_route_2[index + 1]]:
                                            same_position_attachment_route_2[order_item_id_1] = [index, order_item_id_2, attachment_route_1.index(order_item_id_1)]
                                            break
                                    # Check for the last order item in the attachment route of attachment 2
                                    elif len(attachment_route_2) == index + 1:
                                        # If order_item_id_1 collides with order_item_id_2 and order_item_id_1 is a successor of the predecessor of order_item_id_2, it can be inserted in the position of order_item_id_2
                                        if order_item_id_1 in attachment_2.successor_ids.get(index - 1, []):
                                            same_position_attachment_route_2[order_item_id_1] = [index, order_item_id_2, attachment_route_1.index(order_item_id_1)]
                                            break
                                    break

                                # If order_item_id_1 is a predecessor of order_item_id_2, it can be inserted before order_item_id_2
                                if order_item_id_1 in attachment_2.predecessor_ids[order_item_id_2]:
                                    attachment_2_order_item_positions[order_item_id_1] = [index, attachment_route_1.index(order_item_id_1)]
                                    break

                                # If order_item_id_1 is a successor of the last order_item in the attachment route of attachment 2, it can be inserted at the end of the attachment route
                                if len(attachment_route_2) == index + 1:
                                    if order_item_id_1 in attachment_2.successor_ids[order_item_id_2]:
                                        attachment_2_order_item_positions[order_item_id_1] = [index + 1, attachment_route_1.index(order_item_id_1)]
                                        break

                    for order_item_id_2 in attachment_route_2:
                        # Continue to next order item if order_item_id_2 is not in the list of all planned order items for attachment 1
                        attachment_1_possible_order_item_ids = [order_item_ids for orders in attachment_1.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_2 not in attachment_1_possible_order_item_ids:
                            continue
                        else:
                            # Find the position of order_item_id_2 in the attachment route of attachment 1
                            for index, order_item_id_1 in enumerate(attachment_route_1):

                                # If both order items collide check the following conditions
                                if order_item_id_2 not in attachment_1.predecessor_ids[order_item_id_1] and order_item_id_2 not in attachment_1.successor_ids[order_item_id_1]:

                                    # Check for order_items until the second last order item in the attachment route
                                    if len(attachment_route_1) > index + 1:
                                        # If order_item_id_2 collides with order_item_id_1 and order_item_id_2 is a predecessor of the successor of order_item_id_1, it can be inserted in the position of order_item_id_1
                                        if order_item_id_2 in attachment_1.predecessor_ids[attachment_route_1[index + 1]]:
                                            same_position_attachment_route_1[order_item_id_2] = [index, order_item_id_1, attachment_route_2.index(order_item_id_2)]
                                            break
                                    # Check for the last order item in the attachment route of attachment 1
                                    elif len(attachment_route_1) == index + 1:
                                        # If order_item_id_2 collides with order_item_id_1 and order_item_id_2 is a successor of the predecessor of order_item_id_1, it can be inserted in the position of order_item_id_1
                                        if order_item_id_2 in attachment_1.successor_ids.get(index - 1, []):
                                            same_position_attachment_route_1[order_item_id_2] = [index, order_item_id_1, attachment_route_2.index(order_item_id_2)]
                                            break
                                    break

                                # If order_item_id_2 is a predecessor of order_item_id_1, it can be inserted before order_item_id_1
                                if order_item_id_2 in attachment_1.predecessor_ids[order_item_id_1]:
                                    attachment_1_order_item_positions[order_item_id_2] = [index, attachment_route_2.index(order_item_id_2)]
                                    break

                                # If order_item_id_2 is a successor of the last order_item in the attachment route of attachment 1, it can be inserted at the end of the attachment route
                                if len(attachment_route_1) == index + 1:
                                    if order_item_id_2 in attachment_1.successor_ids[order_item_id_1]:
                                        attachment_1_order_item_positions[order_item_id_2] = [index + 1, attachment_route_2.index(order_item_id_2)]
                                        break
                    
                    # Swaps where both order items go into different positions
                    for order_item_id_2, attachment_route_index_1_taken_index_2 in attachment_1_order_item_positions.items():
                        for order_item_id_1, attachment_route_index_2_taken_index_1 in attachment_2_order_item_positions.items():
                            self.Moves.append(SwapShiftAttachmentMove(attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_1_taken_index_2[0], attachment_route_index_2_taken_index_1[0], order_item_id_1, order_item_id_2, attachment_route_index_2_taken_index_1[1], attachment_route_index_1_taken_index_2[1]))
                    
                    # Swaps where both order items go into the same position
                    for order_item_id_2, attachment_route_index_1_and_order_item_id_1_and_taken_index_2 in same_position_attachment_route_1.items():
                        for order_item_id_1, attachment_route_index_2_and_order_item_id_2_and_taken_index_1 in same_position_attachment_route_2.items():
                            if order_item_id_1 != order_item_id_2:
                                if order_item_id_2 == attachment_route_index_2_and_order_item_id_2_and_taken_index_1[1] and order_item_id_1 == attachment_route_index_1_and_order_item_id_1_and_taken_index_2[1]:
                                    self.Moves.append(SwapShiftAttachmentMove(attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_1_and_order_item_id_1_and_taken_index_2[0], attachment_route_index_2_and_order_item_id_2_and_taken_index_1[0], order_item_id_1, order_item_id_2, attachment_route_index_2_and_order_item_id_2_and_taken_index_1[2], attachment_route_index_1_and_order_item_id_1_and_taken_index_2[2]))


                    # Swaps where one order item goes into the same position in the other attachment route
                    for order_item_id_2, attachment_route_index_1_and_order_item_id_1_and_taken_index_2 in same_position_attachment_route_1.items():
                        for order_item_id_1, attachment_route_index_2_taken_index_1 in attachment_2_order_item_positions.items():
                            if order_item_id_1 == attachment_route_index_1_and_order_item_id_1_and_taken_index_2[1]:
                                self.Moves.append(SwapShiftAttachmentMove(attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_1_and_order_item_id_1_and_taken_index_2[0], attachment_route_index_2_taken_index_1[0], order_item_id_1, order_item_id_2, attachment_route_index_2_taken_index_1[1], attachment_route_index_1_and_order_item_id_1_and_taken_index_2[2]))
                    # The other way around
                    for order_item_id_1, attachment_route_index_2_and_order_item_id_2_and_taken_index_1 in same_position_attachment_route_2.items():
                        for order_item_id_2, attachment_route_index_1_taken_index_2 in attachment_1_order_item_positions.items():
                            if order_item_id_2 == attachment_route_index_2_and_order_item_id_2_and_taken_index_1[1]:
                                self.Moves.append(SwapShiftAttachmentMove(attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_1_taken_index_2[0], attachment_route_index_2_and_order_item_id_2_and_taken_index_1[0], order_item_id_1, order_item_id_2, attachment_route_index_2_and_order_item_id_2_and_taken_index_1[2], attachment_route_index_1_taken_index_2[1]))

                                



    def EvaluateMove(self, move: SwapShiftAttachmentMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_swap_shift_attachment_delta(move))


    def sort_move_solutions(self):

        # Sort with smallest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    
    def constructCompleteRoutes(self, move:SwapShiftAttachmentMove, solution:Solution) -> dict:

        worker_route_plan = deepcopy(solution.route_plan_worker)
        machine_route_plan = deepcopy(solution.route_plan_machine)
        attachment_route_plan = deepcopy(solution.route_plan_attachment)

        attachment_route_plan[move.AttachmentID1] = move.AttachmentRoute1
        attachment_route_plan[move.AttachmentID2] = move.AttachmentRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan


class ReplaceShiftAttachmentMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """
    
    def __init__(self, attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_2, attachment_route_index_1, order_item_id):

        self.AttachmentRoute1 = list(attachment_route_1)
        self.AttachmentRoute2 = list(attachment_route_2)

        self.AttachmentRouteIndex1 = attachment_route_index_1
        self.AttachmentRouteIndex2 = attachment_route_index_2

        self.OrderItemID = order_item_id

        self.AttachmentID1 = attachment_id_1
        self.AttachmentID2 = attachment_id_2

        self.AttachmentRoute2.insert(self.AttachmentRouteIndex2, self.OrderItemID)

        self.AttachmentRoute1.remove(self.OrderItemID)

class ReplaceShiftAttachmentNeighborhood(TimeNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

        self.Type = 'Replace_Shift_Attachment'

    def MakeBestMove(self) -> BaseMove:
        
        # Sorting will be handled by the child classes
        self.sort_move_solutions()
        
        for move_solution in self.MoveSolutions:
            return move_solution
                    
        return None

    def DiscoverMoves(self, solution: Solution):
        """ Generate all $n choose 2$ moves """

        for attachment_id_1, attachment_route_1 in solution.route_plan_attachment.items():
            for attachment_id_2, attachment_route_2 in solution.route_plan_attachment.items():
                attachment_2_order_item_positions = {}

                # If no order item is included in attachment route 1 continue to next attachment 1, break from all attachment 2 for this attachment 1
                if len(attachment_route_1) == 0:
                    break
                
                attachment_1_obj = solution.data.attachments[attachment_id_1]
                attachment_2_obj = solution.data.attachments[attachment_id_2]

                # Skip if attachment 1 and attachment 2 have different equipment types
                if attachment_1_obj.type != attachment_2_obj.type:
                    continue


                # Skip if the same attachment is selected
                if attachment_id_1 == attachment_id_2:
                    continue
                else:
                    attachment_2 = solution.data.attachments[attachment_id_2]

                    for order_item_id_1 in attachment_route_1:

                        # Continue to next order item if order_item_id_1 is not in the list of all planned order items for attachment 2
                        attachment_2_possible_order_item_ids = [order_item_ids for orders in attachment_2.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_1 not in attachment_2_possible_order_item_ids:
                            continue


                        # Continue to next order item if order_item_id_1 is already included in the attachment route of attachment 2
                        # Order_items can be included in multiple attachments since an order item can have multiple equipment type needs of the same type
                        if order_item_id_1 in attachment_route_2:
                            continue


                        # If attachment 2 has no order items in its route, order item 1 can be inserted at the first position
                        if len(attachment_route_2) == 0:
                            attachment_2_order_item_positions[order_item_id_1] = [0, attachment_route_1.index(order_item_id_1)]
                            continue

                        # Find the position of order_item_id_1 in the attachment route of attachment 2
                        for order_item_id_2 in attachment_route_2:

                            # If both order items collide order item 1 cannot be inserted
                            if order_item_id_1 not in attachment_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in attachment_2.successor_ids[order_item_id_2]:
                                break

                            # If order_item_id_1 is a predecessor of order_item_id_2, it can be inserted before order_item_id_2
                            if order_item_id_1 in attachment_2.predecessor_ids[order_item_id_2]:
                                attachment_2_order_item_positions[order_item_id_1] = [attachment_route_2.index(order_item_id_2), attachment_route_1.index(order_item_id_1)]
                                break
                            
                            # If order_item_id_1 is a successor of the last order_item in the attachment route of attachment 2, it can be inserted at the end of the attachment route
                            if len(attachment_route_2) == attachment_route_2.index(order_item_id_2) + 1:
                                if order_item_id_1 in attachment_2.successor_ids[order_item_id_2]:
                                    attachment_2_order_item_positions[order_item_id_1] = [attachment_route_2.index(order_item_id_2) + 1 , attachment_route_1.index(order_item_id_1)]
                                    break

                for order_item_id, attachment_route_index_2_1 in attachment_2_order_item_positions.items():
                    self.Moves.append(ReplaceShiftAttachmentMove(attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_2_1[0], attachment_route_index_2_1[1], order_item_id))

            
    def EvaluateMove(self, move: ReplaceShiftAttachmentMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_replace_shift_attachment_delta(move))

    def sort_move_solutions(self):
            
            # Sort with lowest Delta first
            self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)


    def constructCompleteRoutes(self, move:ReplaceShiftAttachmentMove, solution:Solution) -> dict:
        ''' Constructs the comlete Route from the Move'''
        
        attachment_route_plan = deepcopy(solution.route_plan_attachment)
        worker_route_plan = deepcopy(solution.route_plan_worker)
        machine_route_plan = deepcopy(solution.route_plan_machine)

        attachment_route_plan[move.AttachmentID1] = move.AttachmentRoute1
        attachment_route_plan[move.AttachmentID2] = move.AttachmentRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan


class ReplaceShiftMachineMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """
    
    def __init__(self, machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_2, machine_route_index_1, order_item_id, worker_id):

        self.MachineRoute1 = list(machine_route_1)
        self.MachineRoute2 = list(machine_route_2)

        self.MachineRouteIndex1 = machine_route_index_1
        self.MachineRouteIndex2 = machine_route_index_2

        self.OrderItemID = order_item_id

        self.MachineID1 = machine_id_1
        self.MachineID2 = machine_id_2

        self.MachineRoute2.insert(self.MachineRouteIndex2, self.OrderItemID)

        self.MachineRoute1.remove(self.OrderItemID)

        self.WorkerID = worker_id

class ReplaceShiftMachineNeighborhood(TimeNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

        self.Type = 'Replace_Shift_Machine'

    def MakeBestMove(self) -> BaseMove:
        
        # Sorting will be handled by the child classes
        self.sort_move_solutions()
        
        for move_solution in self.MoveSolutions:
            return move_solution
                    
        return None

    def DiscoverMoves(self, solution: Solution):
        """ Generate all $n choose 2$ moves """

        for machine_id_1, machine_route_1 in solution.route_plan_machine.items():
            for machine_id_2, machine_route_2 in solution.route_plan_machine.items():
                machine_2_order_item_positions = {}

                # If no order item is included in machine route 1 continue to next machine 1, break from all machine 2 for this machine 1
                if len(machine_route_1) == 0:
                    break

                # Skip if the same machine is selected
                if machine_id_1 == machine_id_2:
                    continue
                else:
                    machine_2 = solution.data.machines[machine_id_2]

                    for order_item_id_1 in machine_route_1:

                        # Continue to next order item if order_item_id_1 is not in the list of all planned order items for machine 2
                        machine_2_possible_order_item_ids = [order_item_ids for orders in machine_2.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_1 not in machine_2_possible_order_item_ids:
                            continue

                        # If machine 2 has no order items in its route, order item 1 can be inserted at the first position
                        if len(machine_route_2) == 0:
                            machine_2_order_item_positions[order_item_id_1] = [0, machine_route_1.index(order_item_id_1)]
                            continue

                        # Find the position of order_item_id_1 in the machine route of machine 2
                        for order_item_id_2 in machine_route_2:

                            # If both order items collide order item 1 cannot be inserted
                            if order_item_id_1 not in machine_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in machine_2.successor_ids[order_item_id_2]:
                                break

                            # If order_item_id_1 is a predecessor of order_item_id_2, it can be inserted before order_item_id_2
                            if order_item_id_1 in machine_2.predecessor_ids[order_item_id_2]:
                                machine_2_order_item_positions[order_item_id_1] = [machine_route_2.index(order_item_id_2), machine_route_1.index(order_item_id_1)]
                                break

                            # If order_item_id_1 is a successor of the last order_item in the machine route of machine 2, it can be inserted at the end of the machine route
                            if len(machine_route_2) == machine_route_2.index(order_item_id_2) + 1:
                                if order_item_id_1 in machine_2.successor_ids[order_item_id_2]:
                                    machine_2_order_item_positions[order_item_id_1] = [machine_route_2.index(order_item_id_2) + 1 , machine_route_1.index(order_item_id_1)]
                                    break

                            
                for order_item_id, machine_route_index_2_1 in machine_2_order_item_positions.items():
                    worker_id = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id in worker_route][0]
                    self.Moves.append(ReplaceShiftMachineMove(machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_2_1[0], machine_route_index_2_1[1], order_item_id, worker_id))


    def EvaluateMove(self, move: ReplaceShiftMachineMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_replace_shift_machine_delta(move))


    def sort_move_solutions(self):
        
        # Sort with lowest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)


    def constructCompleteRoutes(self, move:ReplaceShiftMachineMove, solution:Solution) -> dict:
        
        machine_route_plan = deepcopy(solution.route_plan_machine)
        worker_route_plan = deepcopy(solution.route_plan_worker)
        attachement_route_plan = deepcopy(solution.route_plan_attachment)

        machine_route_plan[move.MachineID1] = move.MachineRoute1
        machine_route_plan[move.MachineID2] = move.MachineRoute2

        return worker_route_plan, machine_route_plan, attachement_route_plan 


class SwapShiftMachineMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """
    
    def __init__(self, machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_1, machine_route_index_2, order_item_id_1, order_item_id_2, worker_id_1, worker_id_2, taken_index_1, taken_index_2):

        self.MachineRoute1 = list(machine_route_1)
        self.MachineRoute2 = list(machine_route_2)

        self.MachineRoute1Original = list(machine_route_1)
        self.MachineRoute2Original = list(machine_route_2)

        self.MachineRouteTakenIndex1 = taken_index_1
        self.MachineRouteTakenIndex2 = taken_index_2

        self.MachineRouteIndex1 = machine_route_index_1
        self.MachineRouteIndex2 = machine_route_index_2

        self.OrderItemID1 = order_item_id_1
        self.OrderItemID2 = order_item_id_2

        self.MachineID1 = machine_id_1
        self.MachineID2 = machine_id_2

        self.MachineRoute1.insert(self.MachineRouteIndex1, self.OrderItemID2)
        self.MachineRoute2.insert(self.MachineRouteIndex2, self.OrderItemID1)

        self.MachineRoute1.remove(self.OrderItemID1)
        self.MachineRoute2.remove(self.OrderItemID2)

        self.WorkerID1 = worker_id_1
        self.WorkerID2 = worker_id_2

class SwapShiftMachineNeighborhood(TimeNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

        self.Type = 'Swap_Shift_Machine'


    def MakeBestMove(self) -> BaseMove:
        
        # Sorting will be handled by the child classes
        self.sort_move_solutions()
        
        for move_solution in self.MoveSolutions:
            return move_solution
                    
        return None

    def DiscoverMoves(self, solution: Solution):
        """ Generate all $n choose 2$ moves """

        for machine_id_1, machine_route_1 in solution.route_plan_machine.items():
            for machine_id_2, machine_route_2 in solution.route_plan_machine.items():
                machine_1_order_item_positions = {}
                machine_2_order_item_positions = {}

                same_position_machine_route_1 = {}
                same_position_machine_route_2 = {}

                # Skip if one of the machines is not included in the current solution
                if len(machine_route_1) == 0:
                    break
                if len(machine_route_2) == 0:
                    continue

                # Skip if the same machine is selected
                if machine_id_1 == machine_id_2:
                    continue
                else:
                    machine_1 = solution.data.machines[machine_id_1]
                    machine_2 = solution.data.machines[machine_id_2]

                for order_item_id_1 in machine_route_1:
                    # Continue to next order item if order_item_id_1 is not in the list of all planned order items for machine 2
                    machine_2_possible_order_item_ids = [order_item_ids for orders in machine_2.possible_order_item_ids.values() for order_item_ids in orders]
                    if order_item_id_1 not in machine_2_possible_order_item_ids:
                        continue
                    else:
                        # Find the position of order_item_id_1 in the machine route of machine 2
                        for index, order_item_id_2 in enumerate(machine_route_2):

                            # If both order items collide check the following conditions
                            if order_item_id_1 not in machine_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in machine_2.successor_ids[order_item_id_2]:
                                
                                # Check for order_items until the second last order item in the machine route of machine 2
                                if len(machine_route_2) > index + 1:
                                    # If order_item_id_1 collides with order_item_id_2 and order_item_id_1 is a predecessor of the successor of order_item_id_2, it can be inserted in the position of order_item_id_2
                                    if order_item_id_1 in machine_2.predecessor_ids[machine_route_2[index + 1]]:
                                        same_position_machine_route_2[order_item_id_1] = [index, order_item_id_2, machine_route_1.index(order_item_id_1)]
                                        break
                                # Check for the last order item in the machine route of machine 2
                                elif len(machine_route_2) == index + 1:
                                    # If order_item_id_1 collides with order_item_id_2 and order_item_id_1 is a predecessor of order_item_id_2, it can be inserted in the position of order_item_id_2
                                    if order_item_id_1 in machine_2.successor_ids.get(index - 1, []):
                                        same_position_machine_route_2[order_item_id_1] = [index, order_item_id_2, machine_route_1.index(order_item_id_1)]
                                        break
                                break


                            # If order_item_id_1 is a predecessor of order_item_id_2, it can be inserted before order_item_id_2
                            if order_item_id_1 in machine_2.predecessor_ids[order_item_id_2]:
                                machine_2_order_item_positions[order_item_id_1] = [index, machine_route_1.index(order_item_id_1)]
                                break

                            # If order_item_id_1 is a successor of order_item_id_2, it can be inserted after order_item_id_2
                            if len(machine_route_2) == index + 1:
                                if order_item_id_1 in machine_2.successor_ids[order_item_id_2]:
                                    machine_2_order_item_positions[order_item_id_1] = [index + 1, machine_route_1.index(order_item_id_1)]
                                    break

                for order_item_id_2 in machine_route_2:
                    # Continue to next order item if order_item_id_2 is not in the list of all planned order items for machine 1
                    machine_1_possible_order_item_ids = [order_item_ids for orders in machine_1.possible_order_item_ids.values() for order_item_ids in orders]
                    if order_item_id_2 not in machine_1_possible_order_item_ids:
                        continue
                    else:
                        # Find the position of order_item_id_2 in the machine route of machine 1
                        for index, order_item_id_1 in enumerate(machine_route_1):

                            # If both order items collide check the following conditions
                            if order_item_id_2 not in machine_1.predecessor_ids[order_item_id_1] and order_item_id_2 not in machine_1.successor_ids[order_item_id_1]:
                                
                                # Check for order_itesm until the second last order item in the machine route of machine 1
                                if len(machine_route_1) > index + 1:
                                    # If order_item_id_2 collides with order_item_id_1 and order_item_id_2 is a predecessor of the successor of order_item_id_1, it can be inserted in the position of order_item_id_1
                                    if order_item_id_2 in machine_1.predecessor_ids[machine_route_1[index + 1]]:
                                        same_position_machine_route_1[order_item_id_2] = [index, order_item_id_1, machine_route_2.index(order_item_id_2)]
                                        break
                                # Check for the last order item in the machine route of machine 1
                                elif len(machine_route_1) == index + 1:
                                    # If order_item_id_2 collides with order_item_id_1 and order_item_id_2 is a predecessor of order_item_id_1, it can be inserted in the position of order_item_id_1
                                    if order_item_id_2 in machine_1.successor_ids.get(index - 1, []):
                                        same_position_machine_route_1[order_item_id_2] = [index, order_item_id_1, machine_route_2.index(order_item_id_2)]
                                        break
                                break

                            # If order_item_id_2 is a predecessor of order_item_id_1, it can be inserted before order_item_id_1
                            if order_item_id_2 in machine_1.predecessor_ids[order_item_id_1]:
                                machine_1_order_item_positions[order_item_id_2] = [index, machine_route_2.index(order_item_id_2)]
                                break

                            # If order_item_id_2 is a successor of order_item_id_1, it can be inserted after order_item_id_1
                            if len(machine_route_1) == index + 1:
                                if order_item_id_2 in machine_1.successor_ids[order_item_id_1]:
                                    machine_1_order_item_positions[order_item_id_2] = [index + 1, machine_route_2.index(order_item_id_2)]
                                    break
                
                # Swaps where both order items go into different positions
                for order_item_id_2, machine_route_index_1_taken_index_2 in machine_1_order_item_positions.items():
                    for order_item_id_1, machine_route_index_2_taken_index_1 in machine_2_order_item_positions.items():
                        worker_id_1 = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id_1 in worker_route][0]
                        worker_id_2 = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id_2 in worker_route][0]
                        self.Moves.append(SwapShiftMachineMove(machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_1_taken_index_2[0], machine_route_index_2_taken_index_1[0], order_item_id_1, order_item_id_2, worker_id_1, worker_id_2, machine_route_index_2_taken_index_1[1], machine_route_index_1_taken_index_2[1]))


                # Swaps where both order items go into the same position in the other machine route
                for order_item_id_2, machine_route_index_1_and_order_item_id_1_and_taken_index_2 in same_position_machine_route_1.items():
                    for order_item_id_1, machine_route_index_2_and_order_item_id_2_and_taken_index_1 in same_position_machine_route_2.items():
                        if order_item_id_2 == machine_route_index_2_and_order_item_id_2_and_taken_index_1[1] and order_item_id_1 == machine_route_index_1_and_order_item_id_1_and_taken_index_2[1]:
                            worker_id_1 = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id_1 in worker_route][0]
                            worker_id_2 = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id_2 in worker_route][0]
                            self.Moves.append(SwapShiftMachineMove(machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_1_and_order_item_id_1_and_taken_index_2[0], machine_route_index_2_and_order_item_id_2_and_taken_index_1[0], order_item_id_1, order_item_id_2, worker_id_1, worker_id_2, machine_route_index_2_and_order_item_id_2_and_taken_index_1[2], machine_route_index_1_and_order_item_id_1_and_taken_index_2[2]))

                
                # Swaps where one order item goes into the same position in the other machine route
                for order_item_id_2, machine_route_index_1_and_order_item_id_1_and_taken_index_2 in same_position_machine_route_1.items():
                    for order_item_id_1, machine_route_index_2_taken_index_1 in machine_2_order_item_positions.items():
                        if order_item_id_1 == machine_route_index_1_and_order_item_id_1_and_taken_index_2[1]:
                            worker_id_1 = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id_1 in worker_route][0]
                            worker_id_2 = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id_2 in worker_route][0]
                            self.Moves.append(SwapShiftMachineMove(machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_1_and_order_item_id_1_and_taken_index_2[0], machine_route_index_2_taken_index_1[0], order_item_id_1, order_item_id_2, worker_id_1, worker_id_2, machine_route_index_2_taken_index_1[1], machine_route_index_1_and_order_item_id_1_and_taken_index_2[2]))
                # The other way around
                for order_item_id_1, machine_route_index_2_and_order_item_id_2_and_taken_index_1 in same_position_machine_route_2.items():
                    for order_item_id_2, machine_route_index_1_taken_index_2 in machine_1_order_item_positions.items():
                        if order_item_id_2 == machine_route_index_2_and_order_item_id_2_and_taken_index_1[1]:
                            worker_id_1 = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id_1 in worker_route][0]
                            worker_id_2 = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id_2 in worker_route][0]
                            self.Moves.append(SwapShiftMachineMove(machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_1_taken_index_2[0], machine_route_index_2_and_order_item_id_2_and_taken_index_1[0], order_item_id_1, order_item_id_2, worker_id_1, worker_id_2, machine_route_index_2_and_order_item_id_2_and_taken_index_1[2], machine_route_index_1_taken_index_2[1]))

    def EvaluateMove(self, move: SwapShiftMachineMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_swap_shift_machine_delta(move))

    
    def sort_move_solutions(self):

        # Sort with highest Delta first, if equal sort with lowest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    
    def constructCompleteRoutes(self, move:SwapShiftMachineMove, solution:Solution) -> dict:

        machine_route_plan = deepcopy(solution.route_plan_machine)
        worker_route_plan = deepcopy(solution.route_plan_worker)
        attachment_route_plan = deepcopy(solution.route_plan_attachment)

        machine_route_plan[move.MachineID1] = move.MachineRoute1
        machine_route_plan[move.MachineID2] = move.MachineRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan


class ReplaceShiftWorkerMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """
    
    def __init__(self, worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index, order_item_id, machine_id):

        self.WorkerRoute1 = list(worker_route_1)
        self.WorkerRoute2 = list(worker_route_2)

        self.WorkerRouteIndex = worker_route_index

        self.OrderItemID = order_item_id

        self.WorkerID1 = worker_id_1
        self.WorkerID2 = worker_id_2

        self.WorkerRoute2.insert(self.WorkerRouteIndex, self.OrderItemID)

        self.WorkerRoute1.remove(self.OrderItemID)

        self.MachineID = machine_id

class ReplaceShiftWorkerNeighborhood(TimeNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

        self.Type = 'Replace_Shift_Worker'

    def DiscoverMoves(self, solution: Solution):
        """ Generate all $n choose 2$ moves """


        for worker_id_1, worker_route_1 in solution.route_plan_worker.items():
            for worker_id_2, worker_route_2 in solution.route_plan_worker.items():
                worker_2_order_item_positions = {}

                # If no order item is included in worker route 1 continue to next worker 1, break from all worker 2 for this worker 1
                if len(worker_route_1) == 0:
                    break

                # Skip if the same worker is selected
                if worker_id_1 == worker_id_2:
                    continue
                else:
                    worker_2 = solution.data.workers[worker_id_2]

                    for order_item_id_1 in worker_route_1:

                        # Continue to next order item if order_item_id_1 is not in the list of all planned order items for worker 2
                        worker_2_possible_order_item_ids = [order_item_ids for orders in worker_2.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_1 not in worker_2_possible_order_item_ids:
                            continue
                        
                        # Continue to next order item if order_item_id_1 would exceed the maximum work time of worker 2
                        if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                            continue
                        
                        # If worker 2 has no order items in its route, order item 1 can be inserted at the first position
                        if len(worker_route_2) == 0:
                            worker_2_order_item_positions[order_item_id_1] = 0
                            continue

                        # Find the position of order_item_id_1 in the work route of worker 2
                        for order_item_id_2 in worker_route_2:

                            # If both order items collide order item 1 cannot be inserted
                            if order_item_id_1 not in worker_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in worker_2.successor_ids[order_item_id_2]:
                                break

                            # If order_item_id_1 is a predecessor of order_item_id_2, it can be inserted before order_item_id_2
                            if order_item_id_1 in worker_2.predecessor_ids[order_item_id_2]:
                                worker_2_order_item_positions[order_item_id_1] = worker_route_2.index(order_item_id_2)
                                break

                            # If order_item_id_1 is a successor of the last order_item in the worker route of worker 2, it can be inserted at the end of the worker route
                            if len(worker_route_2) == worker_route_2.index(order_item_id_2) + 1:
                                if order_item_id_1 in worker_2.successor_ids[order_item_id_2]:
                                    worker_2_order_item_positions[order_item_id_1] = worker_route_2.index(order_item_id_2) + 1
                                    break


                for order_item_id, worker_route_index_2 in worker_2_order_item_positions.items():
                    machine_id = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id in machine_route][0]                 
                    self.Moves.append(ReplaceShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_2, order_item_id, machine_id))


    def MakeOneMove(self, solution: Solution) -> BaseMove:
        """
        Chooses a random valid move by:
        1. Randomly selecting a pair of workers (worker_1 and worker_2) using self.RNG.
        2. Generating all valid moves for that pair based on the following conditions:
            - worker_1 must have at least one order item.
            - worker_2 must be different from worker_1.
            - The order item from worker_1 must be in worker_2's possible order items.
            - Adding its duration must not exceed worker_2's maximum working hours.
            - A valid insertion position in worker_2's route must be determined based on 
                predecessor/successor constraints.
        3. Appending each valid move (constructed via ReplaceShiftWorkerMove) to self.Moves.
        4. Randomly selecting one move from self.Moves (using self.RNG) and returning it.
        
        If no valid move is found after max_attempts, returns None.
        """
        max_attempts = 100
        worker_ids = list(solution.route_plan_worker.keys())
        attempts = 0
        # Clear any previously stored moves
        self.Moves.clear()

        while attempts < max_attempts:
            attempts += 1

            # Randomly select a worker_1; it must have at least one order item.
            worker_id_1 = self.RNG.choice(worker_ids)
            if not solution.route_plan_worker[worker_id_1]:
                continue

            # Randomly select worker_2, ensuring it's different from worker_1.
            possible_worker_2 = [wid for wid in worker_ids if wid != worker_id_1]
            if not possible_worker_2:
                continue
            worker_id_2 = self.RNG.choice(possible_worker_2)

            worker_route_1 = solution.route_plan_worker[worker_id_1]
            worker_route_2 = solution.route_plan_worker[worker_id_2]
            worker_2 = solution.data.workers[worker_id_2]

            # For each order item in worker_1's route, attempt to determine a valid insertion in worker_2.
            for order_item_id in worker_route_1:
                # Flatten worker_2's possible order item IDs.
                worker_2_possible_order_item_ids = [
                    oid for orders in worker_2.possible_order_item_ids.values() for oid in orders
                ]
                # Skip if the order item is not available for worker_2.
                if order_item_id not in worker_2_possible_order_item_ids:
                    continue

                # Check if adding the order item would exceed worker_2's maximum working hours.
                if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id].duration > self.data._max_working_hours:
                    continue

                insertion_position = None

                # If worker_2 has no order items, we can insert at position 0.
                if not worker_route_2:
                    insertion_position = 0
                else:
                    # Iterate over worker_2's route to find a valid insertion position.
                    for order_item_id_2 in worker_route_2:
                        # If the order item is neither in the predecessor nor successor lists for order_item_id_2,
                        # then insertion relative to this item ist not possible.
                        if order_item_id not in worker_2.predecessor_ids[order_item_id_2] and order_item_id not in worker_2.successor_ids[order_item_id_2]:
                            insertion_position = None
                            break
                        # If order_item_id is a predecessor of order_item_id_2, insert before it.
                        if order_item_id in worker_2.predecessor_ids[order_item_id_2]:
                            insertion_position = worker_route_2.index(order_item_id_2)
                            break
                        # If we are at the last order item and order_item_id is a successor of it, insert at the end.
                        if worker_route_2.index(order_item_id_2) == len(worker_route_2) - 1:
                            if order_item_id in worker_2.successor_ids[order_item_id_2]:
                                insertion_position = len(worker_route_2)
                                break

                # If a valid insertion position was determined, create the move.
                if insertion_position is not None:
                    # Find the machine associated with the order item from solution.route_plan_machine.
                    machine_id = None
                    for m_id, machine_route in solution.route_plan_machine.items():
                        if order_item_id in machine_route:
                            machine_id = m_id
                            break
                    if machine_id is not None:
                        move = ReplaceShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, insertion_position, order_item_id, machine_id)
                        self.Moves.append(move)

            # If we have found any valid moves for the chosen pair, select one randomly.
            if self.Moves:
                return self.RNG.choice(self.Moves)

        # If no valid move is found after max_attempts, return None.
        return None
    


    def EvaluateMove(self, move: ReplaceShiftWorkerMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_replace_shift_worker_delta(move))


    def sort_move_solutions(self):
        
        # Sort with lowest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    
    def constructCompleteRoutes(self, move:ReplaceShiftWorkerMove, solution:Solution) -> dict:

        machine_route_plan = deepcopy(solution.route_plan_machine)
        worker_route_plan = deepcopy(solution.route_plan_worker)
        attachment_route_plan = deepcopy(solution.route_plan_attachment)

        worker_route_plan[move.WorkerID1] = move.WorkerRoute1
        worker_route_plan[move.WorkerID2] = move.WorkerRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan


class SwapShiftWorkerMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """
    
    def __init__(self, worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1, worker_route_index_2, order_item_id_1, order_item_id_2, machine_id_1, machine_id_2):

        self.WorkerRoute1 = list(worker_route_1)
        self.WorkerRoute2 = list(worker_route_2)

        self.WorkerRouteIndex1 = worker_route_index_1
        self.WorkerRouteIndex2 = worker_route_index_2

        self.OrderItemID1 = order_item_id_1
        self.OrderItemID2 = order_item_id_2

        self.WorkerID1 = worker_id_1
        self.WorkerID2 = worker_id_2

        self.WorkerRoute1.insert(self.WorkerRouteIndex1, self.OrderItemID2)
        self.WorkerRoute2.insert(self.WorkerRouteIndex2, self.OrderItemID1)

        self.WorkerRoute1.remove(self.OrderItemID1)
        self.WorkerRoute2.remove(self.OrderItemID2)

        self.MachineID1 = machine_id_1
        self.MachineID2 = machine_id_2

class SwapShiftWorkerNeighborhood(TimeNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

        self.Type = 'Swap_Shift_Worker'

    def DiscoverMoves(self, solution: Solution):
        """ Generate all $n choose 2$ moves """


        for worker_id_1, worker_route_1 in solution.route_plan_worker.items():
            for worker_id_2, worker_route_2 in solution.route_plan_worker.items():
                worker_1_order_item_positions = {}
                worker_2_order_item_positions = {}

                same_position_work_route_1 = {}
                same_position_work_route_2 = {}


                # Skip if one of the workers is not included in the current solution
                if len(worker_route_1) == 0:
                    break
                if len(worker_route_2) == 0:
                    continue

                # Skip if the same worker is selected
                if worker_id_1 == worker_id_2:
                    continue
                else:
                    worker_1 = solution.data.workers[worker_id_1]
                    worker_2 = solution.data.workers[worker_id_2]

                for order_item_id_1 in worker_route_1:
                    # Continue to next order item if order_item_id_1 is not in the list of all planned order items for worker 2
                    worker_2_possible_order_item_ids = [order_item_ids for orders in worker_2.possible_order_item_ids.values() for order_item_ids in orders]
                    if order_item_id_1 not in worker_2_possible_order_item_ids:
                        continue
                    else:                        
                        # Find the position of order_item_id_1 in the worker route of worker 2
                        for index, order_item_id_2 in enumerate(worker_route_2):

                            # If both order items collide check the following conditions
                            if order_item_id_1 not in worker_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in worker_2.successor_ids[order_item_id_2]:
                                
                                # Check for order_items until the second last order_item in the worker route of worker 2
                                if len(worker_route_2) > index + 1:
                                    # If order_item_id_1 collides with order_item_id_2 and order_item_id_1 is a predecessor of the successor of order_item_id_2, it can be inserted in the position of order_item_id_2
                                    if order_item_id_1 in worker_2.predecessor_ids[worker_route_2[index + 1]]:
                                        same_position_work_route_2[order_item_id_1] = [index, order_item_id_2]
                                        break
                                # Check for the last order_item in the worker route of worker 2
                                elif len(worker_route_2) == index + 1:
                                    # If order_item_id_1 collides with order_item_id_2 and order_item_id_1 is a successor of the predecessor of order_item_id_2, it can be inserted in the position of order_item_id_2
                                    if order_item_id_1 in worker_2.successor_ids.get(index - 1, []):
                                        same_position_work_route_2[order_item_id_1] = [index, order_item_id_2]
                                        break
                                break


                            # If order_item_id_1 is a predecessor of order_item_id_2, it can be inserted before order_item_id_2
                            if order_item_id_1 in worker_2.predecessor_ids[order_item_id_2]:
                                worker_2_order_item_positions[order_item_id_1] = index
                                break

                            # If order_item_id_1 is a successor of the last order_item in the worker route of worker 2, it can be inserted at the end of the worker route
                            if len(worker_route_2) == index + 1:
                                if order_item_id_1 in worker_2.successor_ids[order_item_id_2]:
                                    worker_2_order_item_positions[order_item_id_1] = index + 1
                                    break


                for order_item_id_2 in worker_route_2:
                    # Continue to next order item if order_item_id_2 is not in the list of all planned order items for worker 1
                    worker_1_possible_order_item_ids = [order_item_ids for orders in worker_1.possible_order_item_ids.values() for order_item_ids in orders]
                    if order_item_id_2 not in worker_1_possible_order_item_ids:
                        continue
                    else:
                        # Find the position of order_item_id_2 in the worker route of worker 1
                        for index, order_item_id_1 in enumerate(worker_route_1):

                        
                            # If both order items collide check the following conditions
                            if order_item_id_2 not in worker_1.predecessor_ids[order_item_id_1] and order_item_id_2 not in worker_1.successor_ids[order_item_id_1]:
                                
                                # Check for order_items until the second last order_item in the worker route of worker 1
                                if len(worker_route_1) > index + 1:
                                    # If order_item_id_2 collides with order_item_id_1 and order_item_id_2 is a predecessor of the successor of order_item_id_1, it can be inserted in the position of order_item_id_1
                                    if order_item_id_2 in worker_1.predecessor_ids[worker_route_1[index + 1]]:
                                        same_position_work_route_1[order_item_id_2] = [index, order_item_id_1]
                                        break
                                # Check for the last order_item in the worker route of worker 1
                                elif len(worker_route_1) == index + 1:
                                    # If order_item_id_2 collides with order_item_id_1 and order_item_id_2 is a successor of the predecessor of order_item_id_1, it can be inserted in the position of order_item_id_1
                                    if order_item_id_2 in worker_1.successor_ids.get(index - 1, []):
                                        same_position_work_route_1[order_item_id_2] = [index, order_item_id_1]
                                        break
                                break

                            # If order_item_id_2 is a predecessor of order_item_id_1, it can be inserted before order_item_id_1
                            if order_item_id_2 in worker_1.predecessor_ids[order_item_id_1]:
                                worker_1_order_item_positions[order_item_id_2] = index
                                break

                            # If order_item_id_2 is a successor of the last order_item in the worker route of worker 1, it can be inserted at the end of the worker route
                            if len(worker_route_1) == index + 1:
                                if order_item_id_2 in worker_1.successor_ids[order_item_id_1]:
                                    worker_1_order_item_positions[order_item_id_2] = index + 1
                                    break


                # Swaps where order items go into different positions in other worker routes
                for order_item_id_2, worker_route_index_1 in worker_1_order_item_positions.items():
                    for order_item_id_1, worker_route_index_2 in worker_2_order_item_positions.items():
                        # Check if Swap could be executed without exceeding the maximum working hours
                        if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                            continue
                        if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                            continue
                        machine_id_1 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_1 in machine_route][0]
                        machine_id_2 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_2 in machine_route][0]
                        self.Moves.append(SwapShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1, worker_route_index_2, order_item_id_1, order_item_id_2, machine_id_1, machine_id_2))

                # Swaps where both order items go into the same position in the other worker routes
                for order_item_id_2, worker_route_index_1_and_order_item_id_1 in same_position_work_route_1.items():
                    for order_item_id_1, worker_route_index_2_and_order_item_id_2 in same_position_work_route_2.items():
                        if order_item_id_2 == worker_route_index_2_and_order_item_id_2[1] and order_item_id_1 == worker_route_index_1_and_order_item_id_1[1]:
                            # Check if Swap could be executed without exceeding the maximum working hours
                            if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                                continue
                            if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                                continue
                            
                            machine_id_1 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_1 in machine_route][0]
                            machine_id_2 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_2 in machine_route][0]
                            self.Moves.append(SwapShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1_and_order_item_id_1[0], worker_route_index_2_and_order_item_id_2[0], order_item_id_1, order_item_id_2, machine_id_1, machine_id_2))
                

                # Swaps where one order item goes into the same position in the other worker route and the other order item goes into a different position
                for order_item_id_2, worker_route_index_1_and_order_item_id_1 in same_position_work_route_1.items():
                    for order_item_id_1, worker_route_index_2 in worker_2_order_item_positions.items():
                        if order_item_id_1 == worker_route_index_1_and_order_item_id_1[1]:
                            # Check if Swap could be executed without exceeding the maximum working hours
                            if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                                continue
                            if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                                continue
                            machine_id_1 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_1 in machine_route][0]
                            machine_id_2 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_2 in machine_route][0]
                            self.Moves.append(SwapShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1_and_order_item_id_1[0], worker_route_index_2, order_item_id_1, order_item_id_2, machine_id_1, machine_id_2))

                # The other way around
                for order_item_id_1, worker_route_index_2_and_order_item_id_2 in same_position_work_route_2.items():
                    for order_item_id_2, worker_route_index_1 in worker_1_order_item_positions.items():
                        if order_item_id_2 == worker_route_index_2_and_order_item_id_2[1]:
                            # Check if Swap could be executed without exceeding the maximum working hours
                            if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                                continue
                            if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                                continue
                            machine_id_1 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_1 in machine_route][0]
                            machine_id_2 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_2 in machine_route][0]
                            self.Moves.append(SwapShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1, worker_route_index_2_and_order_item_id_2[0], order_item_id_1, order_item_id_2, machine_id_1, machine_id_2))


    def EvaluateMove(self, move: SwapShiftWorkerMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_swap_shift_worker_delta(move))


    def sort_move_solutions(self):
        
        # Sort with lowest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    
    def constructCompleteRoutes(self, move:SwapShiftWorkerMove, solution:Solution) -> dict:

        machine_route_plan = deepcopy(solution.route_plan_machine)
        worker_route_plan = deepcopy(solution.route_plan_worker)
        attachment_route_plan = deepcopy(solution.route_plan_attachment)

        worker_route_plan[move.WorkerID1] = move.WorkerRoute1
        worker_route_plan[move.WorkerID2] = move.WorkerRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan






"__________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________"

# First try to implement night shift constraints in the InsertShiftNeighborhood
'''
# Break to next worker if order_item would be inserted into a sequence of order_items that would exceed the maximum consecutive night shifts
if order_item_id in worker.night_shift_ids:
    if order_item_id_worker in worker.night_shift_ids:
        night_tracker_start += 1
        night_tracker_follower = 0
        if len(worker_route) >= self.data._max_consecutive_night_shifts:
            for i in range(worker_route.index(order_item_id_worker)+1, worker_route.index(order_item_id_worker) + self.data._max_consecutive_night_shifts - night_tracker_start + 1):
                if i >= len(worker_route):
                    break
                if worker_route[i] in worker.night_shift_ids:
                    night_tracker_follower += 1
                else:
                    night_tracker_follower = 0
                    break
            
            if night_tracker_start + night_tracker_follower >= self.data._max_consecutive_night_shifts:
                continue

    else:
        if night_tracker_start >= self.data._max_consecutive_night_shifts:
            night_tracker_start = 0
            continue
        else:
            night_tracker_start = 0
'''




# First try to implement the InsertShiftNeighborhood
'''
for order_item in not_used_shifts:

    for machine_id, machine_route in solution.route_plan_machine.items():
        machine = solution.data.machines[machine_id]
        # Continue to next machine if order_item cannot be processed by current machine
        if order_item not in machine.possible_order_items:
            continue
        
        # Continue to next machine if machine is not included in current solution
        if len(machine_route) == 0:
            continue
        
        for order_item_id_machine in machine_route:
            order_item_machine = solution.data.order_items[order_item_id_machine]
            # Break to next machine if order_item is not a predecessor or successor of current order_item_machine
            if order_item not in machine.predecessors[order_item_machine] and order_item not in machine.successors[order_item_machine]:
                break

            for worker_id, worker_route in solution.route_plan_worker.items():
                worker = solution.data.workers[worker_id]
                # Continue to next worker if order_item cannot be processed by current worker
                if order_item not in worker.possible_order_items:
                    continue

                # Continue to next worker if worker is not included in current solution
                if len(worker_route) == 0:
                    continue


                for order_item_id_worker in worker_route:
                    order_item_worker = solution.data.order_items[order_item_id_worker]
                    # Break to next worker if order_item is not a predecessor or successor of current order_item_worker
                    if order_item not in worker.predecessors[order_item_worker] and order_item not in worker.successors[order_item_worker]:
                        break
                    
                    
                    # First possibility: Insert order_item before order_item_id_machine in machine_route and before order_item_id_worker in worker_route
                    if order_item in machine.predecessors[order_item_machine] and order_item in worker.predecessors[order_item_worker]:
                        self.Moves.append(InsertShiftMove(machine_id, worker_id, machine_route, worker_route, machine_route.index(order_item_id_machine), worker_route.index(order_item_id_worker), order_item.id))
                    
                    # Second possibility: Insert order_item in last position of machine_route and before order_item_id_worker in worker_route
                    elif order_item in machine.predecessors[order_item_machine]:
                        if machine_route.index(order_item_id_machine) + 1 == len(machine_route):
                            if order_item in worker.successors[order_item_worker]:
                                self.Moves.append(InsertShiftMove(machine_id, worker_id, machine_route, worker_route, machine_route.index(order_item_id_machine), worker_route.index(order_item_id_worker) + 1, order_item.id))
                        
                    # Third possibility: Insert order_item before order_item_id_machine in machine_route and in last position of worker_route
                    elif order_item in worker.predecessors[order_item_worker]:
                        if machine_route.index(order_item_id_machine) + 1 == len(machine_route):
                            if order_item in machine.successors[order_item_machine]:
                                self.Moves.append(InsertShiftMove(machine_id, worker_id, machine_route, worker_route, machine_route.index(order_item_id_machine) + 1, worker_route.index(order_item_id_worker), order_item.id))
                        
                    # Fourth possibility: Insert order_item in last position of machine_route and in last position of worker_route
                    elif machine_route.index(order_item_id_machine) + 1 == len(machine_route) and worker_route.index(order_item_id_worker) + 1 == len(worker_route):
                        self.Moves.append(InsertShiftMove(machine_id, worker_id, machine_route, worker_route, machine_route.index(order_item_id_machine) + 1, worker_route.index(order_item_id_worker) + 1, order_item.id))




"__________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________"


class SwapIntraRouteMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """

    def __init__(self, initialRoutePlan:list, day:int, cohort:int, taskA:int, taskB:int, indexA:int, indexB:int):

        self.RouteDayCohort = initialRoutePlan.copy() # create a copy of the permutation
        self.TaskA = taskA
        self.TaskB = taskB
        self.Day = day
        self.Cohort = cohort
        self.indexA = indexA
        self.indexB = indexB

        #Swap Tasks 
        self.RouteDayCohort[self.indexA], self.RouteDayCohort[self.indexB] = self.TaskB, self.TaskA

class SwapIntraRouteNeighborhood(DeltaNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData:InputData, evaluationLogic:EvaluationLogic, solutionPool:SolutionPool, rng):
        super().__init__(inputData,  evaluationLogic, solutionPool, rng)

        self.Type = 'SwapIntraRoute'


    def DiscoverMoves(self):
        """ Generate all $n choose 2$ moves and shuffle them """

        for day in range(len(self.RoutePlan)):
            for cohort in range(len(self.RoutePlan[day])):
                # Get the cohort once and pre-filter tasks <= 1000
                cohort_tasks = self.RoutePlan[day][cohort]
                valid_tasks = {task for task in cohort_tasks if task <= 1000}

                # Generate combinations of two distinct tasks
                for task_i, task_j in itertools.combinations(valid_tasks, 2):
                    index_i = cohort_tasks.index(task_i)
                    index_j = cohort_tasks.index(task_j)
                    # Create Swap Move Objects with different permutations
                    self.Moves.append(SwapIntraRouteMove(cohort_tasks, day, cohort, task_i, task_j, index_i, index_j))

        # Shuffle the Moves at the end
        self.RNG.shuffle(self.Moves)


    def EvaluateMove(self, move:SwapIntraRouteMove) -> None:
        '''''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''
'''
        #Update the Delta of the Move
        move.setDelta(self.EvaluationLogic.CalculateSwapIntraRouteDelta(move))
    
    def MakeOneMove(self, solution: Solution) -> SwapIntraRouteMove:  
        # Randomly select a day and cohort
        day = self.RNG.integers(0, len(solution.RoutePlan))
        cohort = self.RNG.integers(0, len(solution.RoutePlan[day]))

        # Get the cohort once to avoid redundant lookups
        cohort_tasks = solution.RoutePlan[day][cohort]

        validTasks = {task for task in solution.RoutePlan[day][cohort] if task <= 1000}

        # Randomly select two distinct indices in one step
        task_i, task_j = self.RNG.choice(list(validTasks), size=2, replace=False)

        index_i, index_j = cohort_tasks.index(task_i), cohort_tasks.index(task_j)

        # Create and return the move
        return SwapIntraRouteMove(cohort_tasks, day, cohort, task_i, task_j, index_i, index_j)
       
class SwapInterRouteMove(BaseMove):
    """ Represents the swap of tasks between different routes possibly on the same or different days. """

    def __init__(self, initialRoutePlan, dayA:int, cohortA:int, taskA:int, dayB:int, cohortB:int, taskB:int):
        self.RouteDayCohortA = initialRoutePlan[dayA][cohortA].copy() 
        self.RouteDayCohortB = initialRoutePlan[dayB][cohortB].copy() # create a copy of the route plan
        self.TaskA = taskA
        self.TaskB = taskB
        self.DayA = dayA
        self.CohortA = cohortA
        self.DayB = dayB
        self.CohortB = cohortB

        # Get the indices
        self.indexA = self.RouteDayCohortA.index(self.TaskA)
        self.indexB = self.RouteDayCohortB.index(self.TaskB)

        # Swap the tasks between routes
        self.RouteDayCohortA[self.indexA], self.RouteDayCohortB[self.indexB] = self.TaskB, self.TaskA

class SwapInterRouteNeighborhood(DeltaNeighborhood):
    """ Contains all moves for swapping tasks between different routes possibly on the same or different days. """

    def __init__(self, inputData:InputData, evaluationLogic:EvaluationLogic, solutionPool:SolutionPool, rng):
        super().__init__(inputData, evaluationLogic, solutionPool, rng)
        self.Type = 'SwapInterRoute'

    def DiscoverMoves(self, actual_Solution:Solution):
    #def DiscoverMoves(self, actualSolution:Solution):
        """ Generate all possible swaps between tasks in different routes (days and different cohorts). """

        # Choose 2 random days to include in the neighborhood

        days = self.RNG.choice(range(len(self.RoutePlan)), 2)
        #days = range(len(self.RoutePlan))

        # Choose 5 random cohorts (since they are the same across all days)
        cohorts = self.RNG.choice(range(len(self.RoutePlan[0])), 5)
        #cohorts = range(len(self.RoutePlan[0]))


        # Pre-filter tasks to only include those that meet the condition task <= 1000
        valid_tasks_by_day_and_cohort = {
            (day, cohort): {task for task in self.RoutePlan[day][cohort] if task <= 1000}
            for day in days
            for cohort in cohorts
        }

        # Generate valid task pairs across different routes (days) and ensure different cohorts
        for (dayA, cohortA), (dayB, cohortB) in itertools.combinations(valid_tasks_by_day_and_cohort.keys(), 2):

            # Ensure that day and cohort are nrever the same
            if dayA == dayB and cohortA == cohortB:
                continue  # Skip if cohorts are the same
            
            tasksA = valid_tasks_by_day_and_cohort[(dayA, cohortA)]
            tasksB = valid_tasks_by_day_and_cohort[(dayB, cohortB)]
            waiting_timeA = actual_Solution.WaitingTimes[dayA, cohortA]
            waiting_timeB = actual_Solution.WaitingTimes[dayB, cohortB]

            # Precompute service times for tasks in tasksA and tasksB
            #TODO: Test the speed here! 
            service_times_A = {task: self.InputData.allTasks[task].service_time for task in tasksA}
            service_times_B = {task: self.InputData.allTasks[task].service_time for task in tasksB}


            for taskA in tasksA:
                service_time_A = service_times_A[taskA]  # Precomputed service time for taskA
                for taskB in tasksB:
                    service_time_B = service_times_B[taskB]  # Precomputed service time for taskB
                    if waiting_timeA < service_time_B - service_time_A:
                        continue
                    if waiting_timeB < service_time_A - service_time_B:
                        continue
                    # Create the move object for swapping tasks between dayA and dayB, different cohorts
                    self.Moves.append(SwapInterRouteMove(self.RoutePlan, dayA, cohortA, taskA, dayB, cohortB, taskB))
                   

        # Shuffle the generated moves
        self.RNG.shuffle(self.Moves)

    
    def SingleMove(self, solution: Solution, maxAttempts) -> Solution:
       ''' ''' Overwritten to avoid comparisons of strings''''''
        
        MAX_ATTEMPTS = maxAttempts  # Maximum attempts limit
        feasible = False
        attempt = 0
        move = None  # Placeholder for the move


        while not feasible and attempt < MAX_ATTEMPTS:
            move = self.MakeOneMove(solution)
            feasible = self.SingleRouteFeasibilityCheck(move.RouteDayCohortA) and self.SingleRouteFeasibilityCheck(move.RouteDayCohortB)
            attempt += 1

        # If a feasible move is found, evaluate and return it
        if feasible:
            self.EvaluateMove(move)
        else: 
            move = None

        return move
    

    def constructCompleteRoute(self, move:SwapInterRouteMove, solution = None) -> dict: 
        '''    ''' Constructs the comlete Route from the Move and the BaseMove''' '''   
        adapted_Route_Plan = solution.RoutePlan if solution else self.RoutePlan

        adapted_Route_Plan[move.DayA][move.CohortA] = move.RouteDayCohortA
        adapted_Route_Plan[move.DayB][move.CohortB] = move.RouteDayCohortB

        return adapted_Route_Plan
    
    def EvaluateMovesFirstImprovement(self) -> None:
        """ Evaluate all moves until the first one is found that improves the best solution found so far. 
            Overwritten to avoid string comparisons
        """

        # Retrieve best solution from Solution Pool
        for move in self.Moves:
            
            self.EvaluateMove(move)

            if move.Delta < 0:
                
                if self.SingleRouteFeasibilityCheck(move.RouteDayCohortA) and self.SingleRouteFeasibilityCheck(move.RouteDayCohortB):
                    
                    self.MoveSolutions.append(move)
                    # abort neighborhood evaluation because an improvement has been found
                    return None
        
        return None
    
    def MakeBestMove(self) -> BaseMove:
         '''   ''' Overwritten to avoid string comparisons''' '''   
        self.MoveSolutions.sort(key=lambda move: move.Delta)

        for move_solution in self.MoveSolutions:

            if self.SingleRouteFeasibilityCheck(move_solution.RouteDayCohortA) and self.SingleRouteFeasibilityCheck(move_solution.RouteDayCohortB): 
                return move_solution
                    
        return None


    def EvaluateMove(self, move:SwapInterRouteMove) -> None:

        #Update the Delta of the Move
        move.setDelta(self.EvaluationLogic.CalculateSwapInterRouteDelta(move))
    
    def MakeOneMove(self, solution:Solution) -> SwapInterRouteMove:

        
        dayA, dayB = self.RNG.choice(len(solution.RoutePlan), size=2, replace=True)
        if dayA == dayB:
            cohortA, cohortB = self.RNG.choice(len(solution.RoutePlan[dayB]), size=2, replace=False)
        else:
            cohortA, cohortB = self.RNG.choice(len(solution.RoutePlan[dayB]), size=2, replace=True)

        validTasksA = {task for task in solution.RoutePlan[dayA][cohortA] if task <= 1000}
        validTasksB = {task for task in solution.RoutePlan[dayB][cohortB] if task <= 1000}

        taskA = self.RNG.choice(list(validTasksA))
        taskB = self.RNG.choice(list(validTasksB))

        return SwapInterRouteMove(solution.RoutePlan, dayA, cohortA, taskA, dayB, cohortB, taskB)
    
    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> Solution:
         '''   ''' Own Definition to avoid string comparisons''' '''   

        hasSolutionImproved = True
        bestNeighborhoodSolution = Solution(solution.RoutePlan, self.InputData)
        self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

        while hasSolutionImproved:
            
            self.Update(bestNeighborhoodSolution.RoutePlan)
            self.DiscoverMoves(bestNeighborhoodSolution)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()

            if bestNeighborhoodMove is not None and bestNeighborhoodMove.Delta < 0:

                completeRoute = self.constructCompleteRoute(bestNeighborhoodMove)
                bestNeighborhoodSolution = Solution(completeRoute, self.InputData)
                self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

                self.SolutionPool.AddSolution(bestNeighborhoodSolution)
            else:

                hasSolutionImproved = False

        return bestNeighborhoodSolution
    
class TwoEdgeExchangeMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """

    def __init__(self, initialRoutePlan, waiting_time_old_route:int, day:int, cohort:int, taskA:int, taskB:int):
        self.RouteDayCohort = initialRoutePlan.copy()  # Create a copy for RouteDayCohort
        self.OldWaitingTime = waiting_time_old_route  # Waiting Time of old route
        self.Day = day
        self.Cohort = cohort
        self.TaskA = taskA
        self.TaskB = taskB

        # Get the indices
        self.indexA, self.indexB = self.RouteDayCohort.index(self.TaskA), self.RouteDayCohort.index(self.TaskB)

        # Reverse the necessary portion of the list in place (slice assignment)
        if self.indexA < self.indexB:
            self.RouteDayCohort[self.indexA:self.indexB+1] = reversed(self.RouteDayCohort[self.indexA:self.indexB+1])
        else:
            # If indexA is after indexB, still reverse, but handle the indices correctly
            self.RouteDayCohort[self.indexB:self.indexA+1] = reversed(self.RouteDayCohort[self.indexB:self.indexA+1])

class TwoEdgeExchangeNeighborhood(DeltaNeighborhood):         

    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData:InputData, evaluationLogic:EvaluationLogic, solutionPool:SolutionPool, rng):
        super().__init__(inputData,  evaluationLogic, solutionPool, rng)

        self.Type = 'TwoEdgeExchange'

    def DiscoverMoves(self, waiting_times):
        """ Generate all $n choose 2$ moves. """


        for day in range(len(self.RoutePlan)):
            for cohort in range(len(self.RoutePlan[day])):
                # Get the cohort once
                cohort_tasks = self.RoutePlan[day][cohort]
                
                # Filter tasks that are <= 1000 to reduce unnecessary checks
                valid_tasks = {task for task in cohort_tasks if task <= 1000}

                waiting_time_old_route = waiting_times[day,cohort]

                # Iterate over combinations of task indices (i, j) such that i < j
                for task_i, task_j in itertools.combinations(valid_tasks, 2):
                        
                    # Create the move
                    self.Moves.append(TwoEdgeExchangeMove(self.RoutePlan[day][cohort], waiting_time_old_route, day, cohort, task_i, task_j))

        
        #Shuffles the Moves
        self.RNG.shuffle(self.Moves)


    def EvaluateMove(self, move) -> None:
        '''    ''' Calculates the MakeSpan of thr certain move - adds to recent Solution''' '''   

        #Update the Delta of the Move
        move.setDelta(self.EvaluationLogic.WaitingTimeDifferenceOneRoute(move))
    
    def MakeOneMove(self, solution:Solution) -> TwoEdgeExchangeMove:

        day = self.RNG.integers(0, len(solution.RoutePlan))
        cohort = self.RNG.integers(0, len(solution.RoutePlan[day]))
        waiting_time_old = solution.WaitingTimes[day,cohort]

        cohort_tasks = solution.RoutePlan[day][cohort]
                    
        # Filter tasks that are <= 1000 to reduce unnecessary checks
        valid_tasks = {task for task in cohort_tasks if task <= 1000}

        # Randomly select two distinct tasks
        task_i, task_j = self.RNG.choice(list(valid_tasks), size=2, replace=False)

        return TwoEdgeExchangeMove(cohort_tasks, waiting_time_old,day, cohort, task_i, task_j)
    
    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> Solution:
        '''    ''' Own Definition to avoid string comparisons''' '''   

        hasSolutionImproved = True
        bestNeighborhoodSolution = Solution(solution.RoutePlan, self.InputData)
        self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

        while hasSolutionImproved:# and iterator < 50:
            
            self.Update(bestNeighborhoodSolution.RoutePlan)
            self.DiscoverMoves(bestNeighborhoodSolution.WaitingTimes)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()

            if bestNeighborhoodMove is not None and bestNeighborhoodMove.Delta < 0:

                completeRoute = self.constructCompleteRoute(bestNeighborhoodMove)
                bestNeighborhoodSolution = Solution(completeRoute, self.InputData)
                self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

                self.SolutionPool.AddSolution(bestNeighborhoodSolution)
            else:
                #print(f"\nReached local optimum of {self.Type} neighborhood in iteration {iterator}. Stop local search.\n")
                hasSolutionImproved = False

        return bestNeighborhoodSolution


class ReplaceMove(BaseMove):
    def __init__(self, initialRoutePlan, day:int, cohort:int, taskInRoute:int, unusedTask:int, deltaProfit:int):
        """
        Initializes the SwapExtMove instance.

        Args:
            initialRoutePlan (list): The initial route plan.
            day (int): The day on which the swap is made.
            cohort (int): The cohort that drives the route.
            taskInRoute (int): The task currently in the route.
            unusedTask (int): The unused task to be swapped in.
        """
        self.RouteDayCohort = initialRoutePlan.copy()  # create a copy of the route plan
        self.TaskInRoute = taskInRoute
        self.UnusedTask = unusedTask
        self.Day = day
        self.Cohort = cohort
        self.ProfitDelta = deltaProfit

        # Get the index of the task in the route
        self.indexInRoute = self.RouteDayCohort.index(self.TaskInRoute)

        # Perform the swap: replace the task in the route with the unused task
        self.RouteDayCohort[self.indexInRoute] = self.UnusedTask

class ReplaceDeltaNeighborhood(DeltaNeighborhood):

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):

        super().__init__(inputData, evaluationLogic, solutionPool, rng)

        self.Type = 'ReplaceDelta'

    def DiscoverMoves(self, actual_Solution: Solution) -> None:

        unusedTasks = actual_Solution.UnusedTasks

        # Only consider a subset of all unused tasks to reduce the number of moves
        max_number_to_consider = 100
        if len(unusedTasks) > max_number_to_consider:
            unusedTasks = self.RNG.choice(unusedTasks, max_number_to_consider, replace = False)
            
         # Precompute profits for unused tasks to avoid repeated lookups
        unused_task_profits = {task: self.InputData.allTasks[task].profit for task in unusedTasks}

        # Iterate through the route plan
        for day in range(len(self.RoutePlan)):
            for cohort in range(len(self.RoutePlan[day])):
                waiting_time = actual_Solution.WaitingTimes[day, cohort]
                for taskInRoute in self.RoutePlan[day][cohort]:
                    if taskInRoute > 1000:
                        continue
                    route_task_service_time = self.InputData.allTasks[taskInRoute].service_time
                    route_task_profit = self.InputData.allTasks[taskInRoute].profit  # Access once
                    # Filter unused tasks based on matching profit
                    for unusedTask, unused_profit in unused_task_profits.items():
                        if route_task_profit > unused_profit: #TODO Addede here smaller elkse
                            continue
                        if waiting_time < self.InputData.allTasks[unusedTask].service_time - route_task_service_time:
                            continue
                        # If profit matches, create a swap move
                        delta_profit = unused_profit-route_task_profit
                        self.Moves.append(ReplaceMove(self.RoutePlan[day][cohort], day, cohort, taskInRoute, unusedTask, delta_profit))
                
        #Shuffles the Moves
        self.RNG.shuffle(self.Moves)


    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> Solution:
         '''   ''' Own Definition to avoid string comparisons''' '''   

        hasSolutionImproved = True
        bestNeighborhoodSolution = Solution(solution.RoutePlan, self.InputData)
        self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

        while hasSolutionImproved:# and iterator < 50:
            
            self.Update(bestNeighborhoodSolution.RoutePlan)
            self.DiscoverMoves(bestNeighborhoodSolution)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()

            if bestNeighborhoodMove is not None and bestNeighborhoodMove.Delta < 0:
                #print(f"\nIteration: {iterator} in neighborhood {self.Type}")
                #print("New best solution has been found!")
                #print("Time Delta:" , bestNeighborhoodMove.Delta)
                completeRoute = self.constructCompleteRoute(bestNeighborhoodMove)
                bestNeighborhoodSolution = Solution(completeRoute, self.InputData)
                self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)
                #print("New Waiting Time:" , bestNeighborhoodSolution.WaitingTime)
                self.SolutionPool.AddSolution(bestNeighborhoodSolution)
            else:
                #print(f"\nReached local optimum of {self.Type} neighborhood in iteration {iterator}. Stop local search.\n")
                hasSolutionImproved = False

        return bestNeighborhoodSolution


    def EvaluateMove(self, move) -> None:

        #Update the Delta of the Move! 
        move.setDelta(self.EvaluationLogic.CalculateReplaceDelta(move))


    def MakeOneMove(self, solution:Solution) -> ReplaceMove:

        unusedTasksList = solution.UnusedTasks

         # Pre-filter tasks in RoutePlan that are <= 1000 to avoid looping later
        valid_tasks_by_day_and_cohort = {
            (day, cohort): {task for task in solution.RoutePlan[day][cohort] if task <= 1000}
            for day in range(len(solution.RoutePlan))
            for cohort in range(len(solution.RoutePlan[day]))
        }

        taskInRoute = None

        # If no match was found, try different day/cohort combinations
        while taskInRoute is None:
            day, cohort = self.RNG.choice(list(valid_tasks_by_day_and_cohort.keys()))
            unusedTask = self.RNG.choice(unusedTasksList, replace=False)
            unusedTaskProfit = self.InputData.allTasks[unusedTask].profit
            unusedTaskServiceTime = self.InputData.allTasks[unusedTask].service_time

            for task in valid_tasks_by_day_and_cohort[(day, cohort)]:
                task_profit = self.InputData.allTasks[task].profit
                if task_profit <= unusedTaskProfit:
                    if solution.WaitingTimes[day, cohort] >= unusedTaskServiceTime - self.InputData.allTasks[task].service_time:
                        taskInRoute = task
                        profit_delta = task_profit - unusedTaskProfit
                        break
        
        return ReplaceMove(solution.RoutePlan[day][cohort], day, cohort, taskInRoute, unusedTask, profit_delta)



        return move
    
    
    #def MakeOneMove(self, solution:Solution) -> ReplaceMove: --> möglicherweise war hier ein fehler

        day = self.RNG.integers(0, len(solution.RoutePlan))
        cohort = self.RNG.integers(0, len(solution.RoutePlan[day]))

        unusedTasks = list(solution.UnusedTasks)
        unusedTask = self.RNG.choice(unusedTasks, replace=False)

        taskInRoute = self.RNG.choice(solution.RoutePlan[day][cohort])
        while taskInRoute > 1000:
            taskInRoute = self.RNG.choice(solution.RoutePlan[day][cohort])


        while True:
            if (solution.WaitingTimes[day, cohort] >=
                (self.InputData.allTasks[unusedTask].service_time - self.InputData.allTasks[taskInRoute].service_time) and
                self.InputData.allTasks[taskInRoute].profit == self.InputData.allTasks[unusedTask].profit):
                break

            day = self.RNG.integers(0, len(solution.RoutePlan))
            cohort = self.RNG.integers(0, len(solution.RoutePlan[day]))

            unusedTask = self.RNG.choice(unusedTasks, replace=False)
            taskInRoute = self.RNG.choice(solution.RoutePlan[day][cohort])
            while taskInRoute > 1000:
                taskInRoute = self.RNG.choice(solution.RoutePlan[day][cohort])

        move = ReplaceMove(solution.RoutePlan, day, cohort, taskInRoute, unusedTask, self.InputData)

        return move
      
        '''

#_______________________________________________________________________________________________________________________

class InsertMove(BaseMove):
    """ '''   
    Represents a move that inserts a task into various positions within a route.

    Attributes:
        Route (dict): A deep copy of the initial route plan after attempting to insert the task.
    """ '''   

    def __init__(self, initialRoutePlan, task: int, day:int, cohort:int, index: int, profit:int):
        """
        Initializes the InsertMove instance by attempting to insert the given task into the route.

        Args:
            initialRoutePlan (dict): The initial route plan.
            task (int): The task to be inserted.
            inputData: Additional input data required for feasibility checks.
        """
        self.RouteDayCohort = initialRoutePlan.copy()
        self.Task = task
        self.Day = day
        self.Cohort = cohort
        self.Index = index
        self.Profit = profit

        self.RouteDayCohort.insert(index, task)

class OutputNeighborhood(ProfitNeighborhood):
    """
    Represents a neighborhood of insert moves in the context of profit optimization.

    Attributes:
        Type (str): The type of the neighborhood, which is 'Insert'.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        """
        Initializes the OutputNeighborhood instance.

        Args:
            inputData (InputData): The input data required for the neighborhood.
            evaluationLogic (EvaluationLogic): The logic used to evaluate solutions.
            solutionPool (SolutionPool): The pool of solutions.

        Returns:
            None
        """
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

        self.Type = 'Insert'

    def DiscoverMoves(self, actual_Solution:Solution):
        """
        Discovers all possible insert moves for unused tasks in the current solution.

        Args:
            actual_Solution (Solution): The current solution from which unused tasks are identified.

        Returns:
            None
        """
        
        unusedTasks = actual_Solution.UnusedTasks

        #Only consider a subset of all unused tasks to reduce the number of moves
        max_number_to_consider = 250
        if len(unusedTasks) > max_number_to_consider:
           unusedTasks = self.RNG.choice(unusedTasks, max_number_to_consider, replace=False)
        
        
        for task in unusedTasks:
            service_time_unused_task = self.InputData.allTasks[task].service_time
            profit_unused_task = self.InputData.allTasks[task].profit
            for day in range(len(self.RoutePlan)):
                for cohort in range(len(self.RoutePlan[day])):
                    for index in range(len(self.RoutePlan[day][cohort]) + 1):
                        if service_time_unused_task < actual_Solution.WaitingTimes[day, cohort]:
                            self.Moves.append(InsertMove(self.RoutePlan[day][cohort], task, day, cohort, index, profit_unused_task))

        
        #Shuffles the Moves
        self.RNG.shuffle(self.Moves)


    def sort_move_solutions(self):
        # Sort solutions by profit and extra time for 'Insert'
        self.MoveSolutions.sort(key=lambda move: (-move.Profit, move.ExtraTime))


    def EvaluateMove(self, move) -> None:

        #Update the Parameter of the Move
        move.setExtraTime(self.EvaluationLogic.CalculateInsertExtraTime(move))
    

class ReplaceProfitNeighborhood(ProfitNeighborhood):
    """
    Represents a neighborhood of Swap moves in the context of profit optimization.

    Attributes:
        Type (str): The type of the neighborhood, which is 'ReplaceProfit'.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        """
        Initializes the ReplaceProfitNeighborhood instance.

        Args:
            inputData (InputData): The input data required for the neighborhood.
            evaluationLogic (EvaluationLogic): The logic used to evaluate solutions.
            solutionPool (SolutionPool): The pool of solutions.

        Returns:
            None
        """
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

        self.Type = 'ReplaceProfit'

    
    def sort_move_solutions(self):
        # Sort solutions by profit delta and delta for 'ReplaceProfit'
        self.MoveSolutions.sort(key=lambda move: (-move.ProfitDelta, move.Delta))

    def DiscoverMoves(self,actual_Solution:Solution):
        """
        Discovers all possible swap moves for unused tasks in the current solution.

        Args:
            actual_Solution (Solution): The current solution from which unused tasks are identified.

        Returns:
            None
        """

        unusedTasks = actual_Solution.UnusedTasks

        # Precompute profits for unused tasks to avoid repeated lookups
        unused_task_profits = {task: self.InputData.allTasks[task].profit for task in unusedTasks}

        for day in range(len(self.RoutePlan)):
            for cohort in range(len(self.RoutePlan[day])):
                waiting_time = actual_Solution.WaitingTimes[day, cohort]
                for taskInRoute in self.RoutePlan[day][cohort]:
                    if taskInRoute > 1000:
                        continue
                    route_task_profit = self.InputData.allTasks[taskInRoute].profit  # Access once
                    route_task_service_time = self.InputData.allTasks[taskInRoute].service_time
                    # Filter unused tasks based on matching profit
                    for unusedTask, unused_profit in unused_task_profits.items():
                        if route_task_profit >= unused_profit: #TODO Addede here smaller elkse
                            continue
                        if waiting_time < self.InputData.allTasks[unusedTask].service_time - route_task_service_time:
                            continue
                        # If profit matches, create a swap move
                        delta_profit = unused_profit-route_task_profit
                        self.Moves.append(ReplaceMove(self.RoutePlan[day][cohort], day, cohort, taskInRoute, unusedTask, delta_profit))
        
        #Shuffles the Moves
        self.RNG.shuffle(self.Moves)

    def EvaluateMove(self, move) -> None:

        #Updates the Parameter
        move.setDelta(self.EvaluationLogic.CalculateReplaceDelta(move))


    def MakeOneMove(self, solution:Solution) -> ReplaceMove:

        unusedTasksList = list(solution.UnusedTasks)

         # Pre-filter tasks in RoutePlan that are <= 1000 to avoid looping later
        valid_tasks_by_day_and_cohort = {
            (day, cohort): {task for task in solution.RoutePlan[day][cohort] if task <= 1000}
            for day in range(len(solution.RoutePlan))
            for cohort in range(len(solution.RoutePlan[day]))
        }

        # Randomly select a day and cohort with valid tasks
        day, cohort = self.RNG.choice(list(valid_tasks_by_day_and_cohort.keys()))

        unusedTask = self.RNG.choice(unusedTasksList, replace = False)

        taskInRoute = self.RNG.choice(valid_tasks_by_day_and_cohort[(day, cohort)],replace = False)

        return ReplaceMove(solution.RoutePlan[day][cohort], day, cohort, taskInRoute, unusedTask, self.InputData)
    

    

#_______________________________________________________________________________________________________________________

'''