from OutputData import Solution
from OutputData import *
import itertools        
from EvaluationLogic import EvaluationLogic
import concurrent.futures  # For parallelism
from copy import deepcopy
from itertools import chain
import itertools
import numpy as np


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

                #print(bestNeighborhoodSolution)

                #print(bestNeighborhoodMove.DeltaDetails)

                #self.solutionPool.AddSolution(bestNeighborhoodSolution)

                #print(f"Best Neighborhood Solution: \n{bestNeighborhoodSolution}")

            else:
                #print(f"\nNo better solution found in iteration {iterator}")
                hasSolutionImproved = False

            iterator += 1

        return bestNeighborhoodSolution
    
    def SingleMove(self, solution: Solution) -> BaseMove:
        """ Generate a single move for the given solution. """
        

        self.Update()
        
        move = self.MakeOneMove(solution)

        if move:
            self.EvaluateMove(move)
            return move
        else:
            #print(f'No moves found in SingleMove() for neighborhood {self.Type}.')
            return None
    

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


    def __str__(self):
        return f"Machine: {self.MachineID} \nMachine Route: {self.MachineRoute} \nMachine Route Index: {self.MachineRouteIndex} \nWorker: {self.WorkerID} \nWorker Route: {self.WorkerRoute} \nWorker Route Index: {self.WorkerRouteIndex} \nOrder Item ID: {self.OrderItemID} \nDynamic Percentage: {self.DynamicPercentage} \nNumber of Attachments: {self.NumberOfAttachments}"


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
                                break

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


    def find_first_insertion_position(self, route, order_item_id, predecessor_ids, successor_ids):
        """
        Scans the route linearly and returns the first valid insertion position
        for order_item_id based on the predecessor/successor constraints.
        
        If the route is empty, returns 0.
        If no valid position is found, returns None.
        """
        if not route:
            return 0
        for pos in range(len(route)):
            if order_item_id not in predecessor_ids.get(route[pos], []) and order_item_id not in successor_ids.get(route[pos], []):
                return None
            # Check if order_item_id is acceptable as predecessor for the element at pos.
            if order_item_id in predecessor_ids.get(route[pos], []):
                return pos
        # Check insertion at the end.
        if order_item_id in successor_ids.get(route[-1], []):
            return len(route)
        return None


    def MakeOneMove(self, solution: Solution, not_used_shifts=None) -> BaseMove:
        """
        Chooses a random valid "Insert Shift (external)" move in a cascading manner.
        
        Procedure:
        1. Randomly select an unused order item.
        2. For the machine: from all machines that can process the order item,
            randomly shuffle the candidate list and for each candidate scan linearly for the first valid insertion position.
            If found, select this machine and insertion index.
        3. Repeat similarly for the worker:
            Randomly select a candidate worker (that can process the order item and does not exceed max working hours),
            then scan linearly for the first valid insertion position.
        4. For attachments (if required):
            For each required equipment type, randomly shuffle the list of candidate attachments (of matching type)
            and for each candidate, scan linearly for the first valid insertion position.
            Ensure that the same attachment is not used more than once for this order item.
        5. If valid insertion positions are found for all components (machine, worker, and attachments if needed),
            create and return an InsertShiftMove.
        6. Otherwise, skip this order item and try another.
        """
        max_attempts = 100
        attempts = 0
        self.Moves.clear()
        
        if not_used_shifts is None:
            unused_order_item_ids = solution.not_started_order_item_ids
        else:
            unused_order_item_ids = not_used_shifts

        if not unused_order_item_ids:
            return None

        while attempts < max_attempts:
            attempts += 1
            order_item_id = self.RNG.choice(unused_order_item_ids)
            order_item_obj = solution.data.order_items[order_item_id]
            
            # --- MACHINE Component ---
            candidate_machines = []
            for machine_id, machine_route in solution.route_plan_machine.items():
                machine = solution.data.machines[machine_id]
                possible_ids = [oid for orders in machine.possible_order_item_ids.values() for oid in orders]
                if order_item_id in possible_ids:
                    candidate_machines.append(machine_id)
            if not candidate_machines:
                continue
            self.RNG.shuffle(candidate_machines)
            machine_choice = None
            machine_pos = None
            machine_route_snapshot = None
            for m_id in candidate_machines:
                route = solution.route_plan_machine[m_id]
                machine = solution.data.machines[m_id]
                pos = self.find_first_insertion_position(route, order_item_id, machine.predecessor_ids, machine.successor_ids)
                if pos is not None:
                    machine_choice = m_id
                    machine_pos = pos
                    machine_route_snapshot = list(route)
                    break
            if machine_choice is None:
                continue
            
            # --- WORKER Component ---
            candidate_workers = []
            for worker_id, worker_route in solution.route_plan_worker.items():
                worker = solution.data.workers[worker_id]
                possible_ids = [oid for orders in worker.possible_order_item_ids.values() for oid in orders]
                if order_item_id in possible_ids:
                    if solution.worker_work_time[worker_id] + order_item_obj.duration <= self.data._max_working_hours:
                        candidate_workers.append(worker_id)
            if not candidate_workers:
                continue
            self.RNG.shuffle(candidate_workers)
            worker_choice = None
            worker_pos = None
            worker_route_snapshot = None
            for w_id in candidate_workers:
                route = solution.route_plan_worker[w_id]
                worker = solution.data.workers[w_id]
                pos = self.find_first_insertion_position(route, order_item_id, worker.predecessor_ids, worker.successor_ids)
                if pos is not None:
                    worker_choice = w_id
                    worker_pos = pos
                    worker_route_snapshot = list(route)
                    break
            if worker_choice is None:
                continue
            
            # --- ATTACHMENT Component (if required) ---
            attachment_info_list = []
            if order_item_obj.equipment_types:
                used_attachment_ids = set()
                for equipment_type in order_item_obj.equipment_types:
                    candidate_attachments = []
                    for attachment_id, att_route in solution.route_plan_attachment.items():
                        attachment = solution.data.attachments[int(attachment_id)]
                        if attachment.type != equipment_type:
                            continue
                        possible_ids = [oid for orders in attachment.possible_order_item_ids.values() for oid in orders]
                        if order_item_id in possible_ids:
                            candidate_attachments.append(attachment_id)
                    candidate_attachments = [att for att in candidate_attachments if att not in used_attachment_ids]
                    if not candidate_attachments:
                        candidate_attachments = []
                    if not candidate_attachments:
                        break  # This equipment occurrence cannot be assigned.
                    self.RNG.shuffle(candidate_attachments)
                    att_choice = None
                    att_pos = None
                    att_route_snapshot = None
                    for att_id in candidate_attachments:
                        route = solution.route_plan_attachment[att_id]
                        attachment = solution.data.attachments[int(att_id)]
                        pos = self.find_first_insertion_position(route, order_item_id, attachment.predecessor_ids, attachment.successor_ids)
                        if pos is not None:
                            att_choice = att_id
                            att_pos = pos
                            att_route_snapshot = list(route)
                            break
                    if att_choice is None:
                        break
                    used_attachment_ids.add(att_choice)
                    attachment_info_list.append((att_choice, att_pos, att_route_snapshot))
                if len(attachment_info_list) != len(order_item_obj.equipment_types):
                    continue
            
            # --- Build the InsertShiftMove ---
            move = InsertShiftMove(
                machine_choice,
                worker_choice,
                machine_route_snapshot,
                worker_route_snapshot,
                machine_pos,
                worker_pos,
                order_item_id,
                dynamic_percentage=solution.dynamic_percentage_order.get(order_item_id, 0),
                attachment_information=attachment_info_list if order_item_obj.equipment_types else None
            )

            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                return move

        return None
                                        

    def EvaluateMove(self, move:InsertShiftMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_insert_shift_delta(move))

    
    def sort_move_solutions(self):

        # Sort with highest Delta[0] first, if equal sort with lowest Delta[1] first
        self.MoveSolutions.sort(key=lambda move: (move.Delta[0], move.Delta[1]), reverse=False)


    def constructCompleteRoutes(self, move:InsertShiftMove, solution:Solution) -> dict: 
        ''' Constructs the comlete Route from the Move'''
        
        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

        machine_route_plan[move.MachineID] = move.MachineRoute
        worker_route_plan[move.WorkerID] = move.WorkerRoute
        
        for index in range(move.NumberOfAttachments):
            attachment_route_plan[getattr(move, f"AttachmentID_{index}")] = getattr(move, f"AttachmentRoute_{index}")

        return worker_route_plan, machine_route_plan, attachment_route_plan
    
    
        
class SwapShiftExternalMove(BaseMove):
    
    def __init__(self, machine_info_intern ,machine_id, worker_id, machine_route, worker_route, machine_index, worker_index, order_item_id_int, order_item_id_ext, dynamic_percentage_int, dynamic_percentage_ext, attachment_information_int=None, attachment_information_ext=None):
        
        self.OrderItemIDInt = order_item_id_int
        self.OrderItemIDExt = order_item_id_ext


        self.WorkerID = worker_id
        
        self.WorkerRoute = list(worker_route)

        self.WorkerRouteIndex = worker_index

        self.WorkerRoute.insert(self.WorkerRouteIndex, self.OrderItemIDExt)
        self.WorkerRoute.remove(self.OrderItemIDInt)



        self.DynamicPercentageInt = dynamic_percentage_int
        self.DynamicPercentageExt = dynamic_percentage_ext



        self.MachineIDExt = machine_id
        self.MachineIDInt = next(iter(machine_info_intern.keys()))

        if self.MachineIDExt == self.MachineIDInt:
            self.SameMachine = True
            self.MachineRoute = list(machine_route)
            self.MachineRouteIndex = machine_info_intern[self.MachineIDInt][0]

            self.MachineRoute.insert(self.MachineRouteIndex, self.OrderItemIDExt)
            self.MachineRoute.remove(self.OrderItemIDInt)



        else:
            self.SameMachine = False
            self.MachineRouteExt = list(machine_route)
            self.MachineRouteInt = list(machine_info_intern[self.MachineIDInt][1])

            self.MachineRouteIndexExt = machine_index
            self.MachineRouteIndexInt = machine_info_intern[self.MachineIDInt][0]

            self.MachineRouteExt.insert(self.MachineRouteIndexExt, self.OrderItemIDExt)

            self.MachineRouteInt.remove(self.OrderItemIDInt)


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
            for worker_id, worker_route in solution.route_plan_worker.items():
                
                # Continue to next worker if current worker is not part of the solution
                if len(worker_route) == 0:
                    continue

                worker = solution.data.workers[worker_id]

                # Continue to next worker if order_item cannot be processed by current worker
                worker_possible_order_item_ids = [order_item_ids for orders in worker.possible_order_item_ids.values() for order_item_ids in orders]
                if order_item_id_ext not in worker_possible_order_item_ids:
                    continue

                # Find the position of the order_item in the machine route
                for worker_index, order_item_id_int in enumerate(worker_route):

                    
                    
                    # If both order items collide check the following conditions
                    if order_item_id_ext not in worker.predecessor_ids[order_item_id_int] and order_item_id_ext not in worker.successor_ids[order_item_id_int]:
                        # Check the time
                        if solution.worker_work_time[worker_id] + solution.data.order_items[order_item_id_ext].duration - solution.data.order_items[order_item_id_int].duration > self.data._max_working_hours:
                            continue

                        if len(worker_route) == 1:
                            machine_info_int, machine_info_ext = self.find_machine_routes(solution, order_item_id_int, order_item_id_ext)
                            attachment_info_int, attachment_info_ext = self.find_attachment_routes(solution, order_item_id_ext, order_item_id_int)
                            if machine_info_int is not None and machine_info_ext is not None:
                                order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                for machine_id, machine_index_and_route in machine_info_ext.items():

                                    if attachment_info_int == True and attachment_info_ext == True:
                                        self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext]))
                                    elif attachment_info_ext == True and attachment_info_int:
                                        self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int))
                                    elif attachment_info_int and attachment_info_ext:
                                        for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                            if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                continue
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info))
                            break

                        # Check for the first order item in the machine route
                        elif worker_index == 0:
                            # If order_item_id_ext collides with order_item_id_machine and order_item_id_ext is a predecessor of the successor of order_item_id_machine, it can be inserted in the position of order_item_id_machine
                            if order_item_id_ext in worker.predecessor_ids[worker_route[worker_index + 1]]:
                                machine_info_int, machine_info_ext = self.find_machine_routes(solution, order_item_id_int, order_item_id_ext)
                                attachment_info_int, attachment_info_ext = self.find_attachment_routes(solution, order_item_id_ext, order_item_id_int)
                                if machine_info_int is not None and machine_info_ext is not None:
                                    order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                    order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                    for machine_id, machine_index_and_route in machine_info_ext.items():

                                        if attachment_info_int == True and attachment_info_ext == True:
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext]))
                                        elif attachment_info_ext == True and attachment_info_int:
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int))
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info))
                                break

                        # Check for order_items from the second until the second last order item in the machine route
                        elif len(worker_route) > worker_index + 1:
                            # If order_item_id_ext collides with order_item_id_machine and order_item_id_ext is a predecessor of the successor of order_item_id_machine, it can be inserted in the position of order_item_id_machine
                            if order_item_id_ext in worker.predecessor_ids[worker_route[worker_index + 1]] and order_item_id_ext in worker.successor_ids[worker_route[worker_index - 1]]:
                                machine_info_int, machine_info_ext = self.find_machine_routes(solution, order_item_id_int, order_item_id_ext)
                                attachment_info_int, attachment_info_ext = self.find_attachment_routes(solution, order_item_id_ext, order_item_id_int)
                                if machine_info_int is not None and machine_info_ext is not None:
                                    order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                    order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                    for machine_id, machine_index_and_route in machine_info_ext.items():

                                        if attachment_info_int == True and attachment_info_ext == True:
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext]))
                                        elif attachment_info_ext == True and attachment_info_int:
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int))
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info))
                                break


                        # Check for the last order item in the machine route
                        elif len(worker_route) == worker_index + 1:
                            # If order_item_id_ext collides with order_item_id_machine and order_item_id_ext is a successor of the predecessor of order_item_id_machine, it can be inserted in the position of order_item_id_machine
                            if order_item_id_ext in worker.successor_ids[worker_route[worker_index - 1]]:
                                machine_info_int, machine_info_ext = self.find_machine_routes(solution, order_item_id_int, order_item_id_ext)
                                attachment_info_int, attachment_info_ext = self.find_attachment_routes(solution, order_item_id_ext, order_item_id_int)
                                if machine_info_int is not None and machine_info_ext is not None:
                                    order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                    order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                    for machine_id, machine_index_and_route in machine_info_ext.items():

                                        if attachment_info_int == True and attachment_info_ext == True:
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext]))
                                        elif attachment_info_ext == True and attachment_info_int:
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int))
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info))

                                break               


    
    def find_machine_routes(self, solution: Solution, order_item_id_int: int, order_item_id_ext: int) -> tuple:
        """
        Finds candidate machine routes to reflect the swap (or insertion) of an external order item
        in place of an internal order item.
        
        Returns two dictionaries:
        - machine_info_int: for each machine route in which the internal order item appears,
            a tuple (index, route_snapshot) is stored.
        - machine_info_ext: for each machine that can process the external order item, a tuple 
            (insertion_index, route_snapshot) is stored, representing the first valid insertion position.
        
        If no valid insertion position for the external order item is found, returns (False, False).
        """
        #order_item_ext_obj = solution.data.order_items[order_item_id_ext]
        #order_item_int_obj = solution.data.order_items[order_item_id_int]
        
        machine_info_int = dict()
        machine_info_ext = dict()
        
        # Search all machine routes for the internal order item.
        for machine_id, machine_route in solution.route_plan_machine.items():
            if order_item_id_int in machine_route:
                machine_info_int[machine_id] = [machine_route.index(order_item_id_int), list(machine_route)]
        
        # Search for candidate insertion positions for the external order item in machine routes.
        possible_positions = []
        for machine_id, machine_route in solution.route_plan_machine.items():
            machine = solution.data.machines[machine_id]
            # Build a flattened list of possible order item IDs for this machine.
            possible_ids = [oid for orders in machine.possible_order_item_ids.values() for oid in orders]
            if order_item_id_ext not in possible_ids:
                continue
            
            # If the machine route is empty, the order item can be inserted at position 0.
            if len(machine_route) == 0:
                possible_positions.append((machine_id, 0, list(machine_route)))
            else:
                # Scan the machine route linearly to find the first valid insertion position.
                for i, current_item in enumerate(machine_route):
                    if order_item_id_ext not in machine.predecessor_ids.get(current_item, []) and order_item_id_ext not in machine.successor_ids.get(current_item, []):
                        break

                    # If order_item_id_ext is acceptable as a predecessor for the element at position i.
                    if order_item_id_ext in machine.predecessor_ids.get(current_item, []):
                        possible_positions.append((machine_id, i, list(machine_route)))
                        break
                # Also, check if insertion at the end is valid (i.e. order_item_id_ext is acceptable as a successor of the last element).
                if order_item_id_ext in machine.successor_ids.get(machine_route[-1], []):
                    possible_positions.append((machine_id, len(machine_route), list(machine_route)))
        
        if not possible_positions:
            return None, None
        
        # Build machine_info_ext: each candidate is stored under its machine_id.
        # (If es mehrere Kandidaten pro Maschine gibt, kannst du diese Liste auch als Value speichern.)
        for (mid, pos, snapshot) in possible_positions:
            machine_info_ext[mid] = (pos, snapshot)
        
        return machine_info_int, machine_info_ext



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
                        break

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
    

    def MakeOneMove(self, solution: Solution, not_used_shifts=None) -> BaseMove:
        """
        Chooses a random valid "Swap Shift (external)" move.

        - Randomly selects an order item from unused shifts.
        - Randomly selects a worker with a valid route.
        - Randomly selects a machine that can process the swap.
        - Randomly selects valid attachment swaps (if required).
        """

        max_attempts = 100
        attempts = 0
        self.Moves.clear()

        if not_used_shifts is None:
            unused_order_item_ids = solution.not_started_order_item_ids
        else:
            unused_order_item_ids = not_used_shifts

        if not unused_order_item_ids:
            return None  # No unused order items available

        while attempts < max_attempts:
            attempts += 1
            order_item_id_ext = self.RNG.choice(unused_order_item_ids)
            order_item_ext_obj = solution.data.order_items[order_item_id_ext]

            # --- WORKER Component ---
            candidate_workers = [
                worker_id for worker_id, worker_route in solution.route_plan_worker.items()
                if worker_route  # Worker must have at least one order
            ]
            
            if not candidate_workers:
                continue  # No valid workers

            self.RNG.shuffle(candidate_workers)  # Zufällige Reihenfolge der Worker
            
            for worker_id in candidate_workers:
                worker_route = solution.route_plan_worker[worker_id]
                worker = solution.data.workers[worker_id]

                worker_possible_order_item_ids = [order_item_ids for orders in worker.possible_order_item_ids.values() for order_item_ids in orders]
                
                if order_item_id_ext not in worker_possible_order_item_ids:
                    continue # Worker cannot process the order item

                for worker_index, order_item_id_int in enumerate(worker_route):


                    if order_item_id_ext not in worker.predecessor_ids[order_item_id_int] and order_item_id_ext not in worker.successor_ids[order_item_id_int]:
                        if solution.worker_work_time[worker_id] + solution.data.order_items[order_item_id_ext].duration - solution.data.order_items[order_item_id_int].duration > self.data._max_working_hours:
                            continue

                        if len(worker_route) == 1:
                            machine_info_int, machine_info_ext = self.find_single_machine_route(solution, order_item_id_int, order_item_id_ext)
                            attachment_info_int, attachment_info_ext = self.find_single_attachment_route(solution, order_item_id_ext, order_item_id_int)
                            if machine_info_int is not None and machine_info_ext is not None:
                                order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                for machine_id, machine_index_and_route in machine_info_ext.items():

                                    if attachment_info_int == True and attachment_info_ext == True:
                                        move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext])
                                        if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                            return move
                                    elif attachment_info_ext == True and attachment_info_int:
                                        move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int)
                                        if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                            return move
                                    elif attachment_info_int and attachment_info_ext:
                                        for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                            if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                continue
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info)
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                            

                        elif worker_index == 0:
                            if order_item_id_ext in worker.predecessor_ids[worker_route[worker_index + 1]]:
                                machine_info_int, machine_info_ext = self.find_single_machine_route(solution, order_item_id_int, order_item_id_ext)
                                attachment_info_int, attachment_info_ext = self.find_single_attachment_route(solution, order_item_id_ext, order_item_id_int)
                                if machine_info_int is not None and machine_info_ext is not None:
                                    order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                    order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                    for machine_id, machine_index_and_route in machine_info_ext.items():

                                        if attachment_info_int == True and attachment_info_ext == True:
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext])
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                        elif attachment_info_ext == True and attachment_info_int:
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int)
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info)
                                                if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                    return move
                                                
                        
                        elif len(worker_route) > worker_index + 1:
                            if order_item_id_ext in worker.predecessor_ids[worker_route[worker_index + 1]] and order_item_id_ext in worker.successor_ids[worker_route[worker_index - 1]]:
                                machine_info_int, machine_info_ext = self.find_single_machine_route(solution, order_item_id_int, order_item_id_ext)
                                attachment_info_int, attachment_info_ext = self.find_single_attachment_route(solution, order_item_id_ext, order_item_id_int)
                                if machine_info_int is not None and machine_info_ext is not None:
                                    order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                    order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                    for machine_id, machine_index_and_route in machine_info_ext.items():

                                        if attachment_info_int == True and attachment_info_ext == True:
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext])
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                        elif attachment_info_ext == True and attachment_info_int:
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int)
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info)
                                                if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                    return move
                                                
                        
                        elif len(worker_route) == worker_index + 1:
                            if order_item_id_ext in worker.successor_ids[worker_route[worker_index - 1]]:
                                machine_info_int, machine_info_ext = self.find_single_machine_route(solution, order_item_id_int, order_item_id_ext)
                                attachment_info_int, attachment_info_ext = self.find_single_attachment_route(solution, order_item_id_ext, order_item_id_int)
                                if machine_info_int is not None and machine_info_ext is not None:
                                    order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                    order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                    for machine_id, machine_index_and_route in machine_info_ext.items():

                                        if attachment_info_int == True and attachment_info_ext == True:
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext])
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                        elif attachment_info_ext == True and attachment_info_int:
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int)
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int = attachment_info_int, attachment_information_ext = attachment_info)
                                                if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                    return move
                                                
        return None  # No valid move found
    
                                                
                        





    def find_single_machine_route(self, solution: Solution, order_item_id_int: int, order_item_id_ext: int) -> tuple:

        machine_info_int = dict()
        machine_info_ext = dict()
        
        # Search all machine routes for the internal order item.
        for machine_id, machine_route in solution.route_plan_machine.items():
            if order_item_id_int in machine_route:
                machine_info_int[machine_id] = [machine_route.index(order_item_id_int), list(machine_route)]
        

        machine_ids = list(solution.route_plan_machine.keys())
        self.RNG.shuffle(machine_ids)

        for machine_id in machine_ids:
            machine_route = solution.route_plan_machine[machine_id]
            machine = solution.data.machines[machine_id]
            # Build a flattened list of possible order item IDs for this machine.
            possible_ids = [oid for orders in machine.possible_order_item_ids.values() for oid in orders]
            if order_item_id_ext not in possible_ids:
                continue
            
            # If the machine route is empty, the order item can be inserted at position 0.
            if len(machine_route) == 0:
                machine_info_ext[machine_id] = (0, list(machine_route))
                return machine_info_int, machine_info_ext
            else:
                # Scan the machine route linearly to find the first valid insertion position.
                for i, current_item in enumerate(machine_route):
                    if order_item_id_ext not in machine.predecessor_ids.get(current_item, []) and order_item_id_ext not in machine.successor_ids.get(current_item, []):
                        break

                    # If order_item_id_ext is acceptable as a predecessor for the element at position i.
                    if order_item_id_ext in machine.predecessor_ids.get(current_item, []):
                        machine_info_ext[machine_id] = (i, list(machine_route))
                        return machine_info_int, machine_info_ext
                # Also, check if insertion at the end is valid (i.e. order_item_id_ext is acceptable as a successor of the last element).
                if order_item_id_ext in machine.successor_ids.get(machine_route[-1], []):
                    machine_info_ext[machine_id] = (len(machine_route), list(machine_route))
                    return machine_info_int, machine_info_ext
        
        if not machine_info_ext:
            return None, None
        

    def find_single_attachment_route(self, solution: Solution, order_item_id_ext: int, order_item_id_int: int) -> dict:
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

            attachment_ids = list(solution.route_plan_attachment.keys())
            self.RNG.shuffle(attachment_ids)

            break_flag = False

            for attachment_id in attachment_ids:
                if break_flag:
                    break

                attachment_route = solution.route_plan_attachment[attachment_id]
                attachment = solution.data.attachments[attachment_id]

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
                    break
                
                # If the order_item_int is in the attachment route, the order_item_ext can be inserted at the same position if it is a predecessor or successor of the order_item_int
                if order_item_id_int in attachment_route:
                    index = attachment_route.index(order_item_id_int)
                    pred_id = attachment_route[index - 1] if index > 0 else None
                    succ_id = attachment_route[index + 1] if index < len(attachment_route) - 1 else None

                    if order_item_id_ext in attachment.predecessor_ids.get(pred_id, []) and order_item_id_ext in attachment.successor_ids.get(succ_id, []):
                        possible_positions_for_type.append((attachment_id, index, list(attachment_route)))
                        break


                # Otherwise, find a valid insertion position based on predecessor/successor relationships
                for order_item_id_attachment in attachment_route:

                    pred = attachment.predecessor_ids.get(order_item_id_attachment, [])
                    succ = attachment.successor_ids.get(order_item_id_attachment, [])
                    # If the order item is neither a predecessor nor a successor, skip this element
                    if order_item_id_ext not in pred and order_item_id_ext not in succ:
                        break_flag = True
                        break

                    # If the order item is a predecessor, it can be inserted before the current item
                    if order_item_id_ext in pred:
                        pos = attachment_route.index(order_item_id_attachment)
                        possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                        break_flag = True
                        break

                    # If it is a successor of the last element, insert at the end
                    if attachment_route.index(order_item_id_attachment) == len(attachment_route) - 1:
                        if order_item_id_ext in succ:
                            pos = attachment_route.index(order_item_id_attachment) + 1
                            possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                            break_flag = True
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
        self.MoveSolutions.sort(key=lambda move: (move.Delta[0], move.Delta[1]), reverse=False)

    
    def constructCompleteRoutes(self, move:SwapShiftExternalMove, solution:Solution) -> dict:
        
        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

        #print("\n")

        worker_route_plan[move.WorkerID] = move.WorkerRoute

        if not move.SameMachine:
            machine_route_plan[move.MachineIDInt] = move.MachineRouteInt
            machine_route_plan[move.MachineIDExt] = move.MachineRouteExt

        else:
            machine_route_plan[move.MachineIDExt] = move.MachineRoute


        

        for index in range(move.NumberOfAttachmentsInt):
            attachment_route_plan[getattr(move, f"AttachmentIDInt_{index}")] = getattr(move, f"AttachmentRouteInt_{index}")

        for index in range(move.NumberOfAttachmentsExt):
            attachment_route_plan[getattr(move, f"AttachmentIDExt_{index}")] = getattr(move, f"AttachmentRouteExt_{index}")


        return worker_route_plan, machine_route_plan, attachment_route_plan
    

    def MakeBestMove(self) -> BaseMove:
        
        # Sorting will be handled by the child classes
        self.sort_move_solutions()
        
        for move_solution in self.MoveSolutions:
            if self.WorkerRouteFeasibilityCheck(move_solution.WorkerID, move_solution.WorkerRoute):
                if move_solution.Delta[0] < 0:
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

        #print(f"\nInitial Worker Route: \n{bestNeighborhoodSolution.route_plan_worker}")

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

            
            else:
                #print(f"\nNo better solution found in iteration {iterator}")
                hasSolutionImproved = False

            feasbile = bestNeighborhoodSolution.feasibility_check()
            if not feasbile:
                raise KeyError(f"Feasibility Check failed in iteration {iterator}")

            iterator += 1

            #print(f"\nBest Current Solution: \n{bestNeighborhoodSolution}")

        #print(f"\nBest Worker Route: \n{bestNeighborhoodSolution.route_plan_worker}")

        return bestNeighborhoodSolution
    
    def SingleMove(self, solution: Solution) -> BaseMove:
        """ Generate a single move for the given solution. """
        

        self.Update()
        
        move = self.MakeOneMove(solution)

        if move:
            self.EvaluateMove(move)
            return move
        else:
            pass
            #print(f'No moves found in SingleMove() for neighborhood {self.Type}.')



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


    def __str__(self):
        return f'Attachment Route 1: {self.AttachmentRoute1}\nAttachment Route 2: {self.AttachmentRoute2} \n Attachment Route Index 1: {self.AttachmentRouteIndex1} \n Attachment Route Index 2: {self.AttachmentRouteIndex2} \n Order Item ID 1: {self.OrderItemID1} \n Order Item ID 2: {self.OrderItemID2} \n Attachment ID 1: {self.AttachmentID1} \n Attachment ID 2: {self.AttachmentID2}'

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

    def MakeOneMove(self, solution: Solution) -> BaseMove:
        """
        Chooses a random valid swap move for attachments using self.RNG.
        
        Procedure:
        1. Randomly select an attachment (attachment_id_1) from solution.route_plan_attachment
            that has at least one order item.
        2. Retrieve its equipment type.
        3. Randomly select attachment_id_2 from those attachments that are:
            - Different from attachment_id_1,
            - Have a non-empty route, and
            - Have the same equipment type.
        4. Build candidate dictionaries for potential swap positions:
            - attachment_1_order_item_positions: for order items from attachment_route_2 that can be inserted in attachment_route_1.
            - attachment_2_order_item_positions: for order items from attachment_route_1 that can be inserted in attachment_route_2.
            - same_position_attachment_route_1 and same_position_attachment_route_2: for cases where the insertion would be at the same position.
        5. Generate swap moves (covering several cases) using the candidate positions.
        6. If any valid move is found, return one randomly using self.RNG.choice;
            otherwise, return None after max_attempts.
        """
        max_attempts = 100
        attachment_ids = list(solution.route_plan_attachment.keys())
        attempts = 0
        self.Moves.clear()  # Clear any previously stored moves

        while attempts < max_attempts:
            attempts += 1

            # Randomly select attachment_id_1 (must have a non-empty route)
            attachment_id_1 = self.RNG.choice(attachment_ids)
            attachment_route_1 = solution.route_plan_attachment[attachment_id_1]
            if len(attachment_route_1) == 0:
                continue

            # Retrieve the equipment type of attachment_id_1.
            att_type = solution.data.attachments[attachment_id_1].type

            # Filter candidate attachments for attachment_id_2:
            # They must be different from attachment_id_1, have a non-empty route, and the same equipment type.
            possible_attachment_2 = [aid for aid in attachment_ids 
                                    if aid != attachment_id_1 
                                    and len(solution.route_plan_attachment[aid]) > 0 
                                    and solution.data.attachments[aid].type == att_type]
            if not possible_attachment_2:
                continue
            attachment_id_2 = self.RNG.choice(possible_attachment_2)
            attachment_route_2 = solution.route_plan_attachment[attachment_id_2]

            # Retrieve attachment objects.
            attachment_1 = solution.data.attachments[attachment_id_1]
            attachment_2 = solution.data.attachments[attachment_id_2]

            # Dictionaries for candidate positions:
            attachment_1_order_item_positions = {}  # For order items from attachment_route_2 to insert in attachment_route_1.
            attachment_2_order_item_positions = {}  # For order items from attachment_route_1 to insert in attachment_route_2.
            same_position_attachment_route_1 = {}   # For swaps where an order item from attachment_route_2 is inserted at the same position in attachment_route_1.
            same_position_attachment_route_2 = {}   # For swaps where an order item from attachment_route_1 is inserted at the same position in attachment_route_2.

            # For each order item in attachment_route_1: determine candidate insertion in attachment_route_2.
            for order_item_id_1 in attachment_route_1:
                # Create a flattened list of possible order item IDs for attachment 2.
                possible_ids_2 = [oid for orders in attachment_2.possible_order_item_ids.values() for oid in orders]
                if order_item_id_1 not in possible_ids_2:
                    continue
                else:
                    for index, order_item_id_2 in enumerate(attachment_route_2):
                        # If both order items "collide": order_item_id_1 is not in the predecessor nor successor lists of order_item_id_2.
                        if order_item_id_1 not in attachment_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in attachment_2.successor_ids[order_item_id_2]:
                            if len(attachment_route_2) > index + 1:
                                if order_item_id_1 in attachment_2.predecessor_ids[attachment_route_2[index + 1]]:
                                    same_position_attachment_route_2[order_item_id_1] = [index, order_item_id_2, attachment_route_1.index(order_item_id_1)]
                                    break
                            elif len(attachment_route_2) == index + 1:
                                if order_item_id_1 in attachment_2.successor_ids.get(order_item_id_2, []):
                                    same_position_attachment_route_2[order_item_id_1] = [index, order_item_id_2, attachment_route_1.index(order_item_id_1)]
                                    break
                            break
                        # If order_item_id_1 is a predecessor of order_item_id_2, record the insertion position.
                        if order_item_id_1 in attachment_2.predecessor_ids[order_item_id_2]:
                            attachment_2_order_item_positions[order_item_id_1] = [index, attachment_route_1.index(order_item_id_1)]
                            break
                        # If at the end of attachment_route_2 and order_item_id_1 is a successor, insert at the end.
                        if index == len(attachment_route_2) - 1:
                            if order_item_id_1 in attachment_2.successor_ids[order_item_id_2]:
                                attachment_2_order_item_positions[order_item_id_1] = [index + 1, attachment_route_1.index(order_item_id_1)]
                                break

            # For each order item in attachment_route_2: determine candidate insertion in attachment_route_1.
            for order_item_id_2 in attachment_route_2:
                possible_ids_1 = [oid for orders in attachment_1.possible_order_item_ids.values() for oid in orders]
                if order_item_id_2 not in possible_ids_1:
                    continue
                else:
                    for index, order_item_id_1 in enumerate(attachment_route_1):
                        if order_item_id_2 not in attachment_1.predecessor_ids[order_item_id_1] and order_item_id_2 not in attachment_1.successor_ids[order_item_id_1]:
                            if len(attachment_route_1) > index + 1:
                                if order_item_id_2 in attachment_1.predecessor_ids[attachment_route_1[index + 1]]:
                                    same_position_attachment_route_1[order_item_id_2] = [index, order_item_id_1, attachment_route_2.index(order_item_id_2)]
                                    break
                            elif len(attachment_route_1) == index + 1:
                                if order_item_id_2 in attachment_1.successor_ids.get(order_item_id_1, []):
                                    same_position_attachment_route_1[order_item_id_2] = [index, order_item_id_1, attachment_route_2.index(order_item_id_2)]
                                    break
                            break
                        if order_item_id_2 in attachment_1.predecessor_ids[order_item_id_1]:
                            attachment_1_order_item_positions[order_item_id_2] = [index, attachment_route_2.index(order_item_id_2)]
                            break
                        if index == len(attachment_route_1) - 1:
                            if order_item_id_2 in attachment_1.successor_ids[order_item_id_1]:
                                attachment_1_order_item_positions[order_item_id_2] = [index + 1, attachment_route_2.index(order_item_id_2)]
                                break

            valid_moves = []
            
            # Case 1: Swap moves where both order items are inserted at different positions.
            for order_item_id_2, pos_info_1 in attachment_1_order_item_positions.items():
                for order_item_id_1, pos_info_2 in attachment_2_order_item_positions.items():
                    move = SwapShiftAttachmentMove(
                        attachment_id_1, attachment_id_2,
                        attachment_route_1, attachment_route_2,
                        pos_info_1[0], pos_info_2[0],
                        order_item_id_1, order_item_id_2,
                        pos_info_2[1], pos_info_1[1]
                    )
                    valid_moves.append(move)
            
            # Case 2: Swap moves where both order items go into the same position.
            for order_item_id_2, pos_info_1 in same_position_attachment_route_1.items():
                for order_item_id_1, pos_info_2 in same_position_attachment_route_2.items():
                    if order_item_id_2 == pos_info_2[1] and order_item_id_1 == pos_info_1[1]:
                        move = SwapShiftAttachmentMove(
                            attachment_id_1, attachment_id_2,
                            attachment_route_1, attachment_route_2,
                            pos_info_1[0], pos_info_2[0],
                            order_item_id_1, order_item_id_2,
                            pos_info_2[2], pos_info_1[2]
                        )
                        valid_moves.append(move)
            
            # Case 3: Swap moves where one order item is inserted at the same position and the other at a different position.
            for order_item_id_2, pos_info_1 in same_position_attachment_route_1.items():
                for order_item_id_1, pos_info_2 in attachment_2_order_item_positions.items():
                    if order_item_id_1 == pos_info_1[1]:
                        move = SwapShiftAttachmentMove(
                            attachment_id_1, attachment_id_2,
                            attachment_route_1, attachment_route_2,
                            pos_info_1[0], pos_info_2[0],
                            order_item_id_1, order_item_id_2,
                            pos_info_2[1], pos_info_1[2]
                        )
                        valid_moves.append(move)
            
            # Case 4: The other way around.
            for order_item_id_1, pos_info_2 in same_position_attachment_route_2.items():
                for order_item_id_2, pos_info_1 in attachment_1_order_item_positions.items():
                    if order_item_id_2 == pos_info_2[1]:
                        move = SwapShiftAttachmentMove(
                            attachment_id_1, attachment_id_2,
                            attachment_route_1, attachment_route_2,
                            pos_info_1[0], pos_info_2[0],
                            order_item_id_1, order_item_id_2,
                            pos_info_2[2], pos_info_1[1]
                        )
                        valid_moves.append(move)

            if valid_moves:
                return self.RNG.choice(valid_moves)
            
        return None



    def EvaluateMove(self, move: SwapShiftAttachmentMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_swap_shift_attachment_delta(move))


    def sort_move_solutions(self):

        # Sort with smallest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    
    def constructCompleteRoutes(self, move:SwapShiftAttachmentMove, solution:Solution) -> dict:

        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

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


    def MakeOneMove(self, solution: Solution) -> BaseMove:
        """
        Chooses a random valid attachment move using self.RNG.
        
        Procedure:
        1. Randomly select an attachment (attachment_id_1) from solution.route_plan_attachment
            that has at least one order item.
        2. Retrieve its equipment type.
        3. Randomly select a second attachment (attachment_id_2) from only those attachments
            that have the same equipment type and are different from attachment_id_1.
        4. For each order item in attachment_route_1:
            - Check if the order item is in the list of possible order items for attachment 2.
            - Skip the order item if it is already in attachment 2's route.
            - Determine a valid insertion position in attachment 2's route based on
                predecessor/successor constraints:
                    * If attachment 2 has no order items, the order item can be inserted at position 0.
                    * Otherwise, if the order item is a predecessor of an order item in attachment 2's route,
                    it can be inserted before it.
                    * Or, if the order item is a successor of the last order item, it can be inserted at the end.
        5. For each valid insertion, create a ReplaceShiftAttachmentMove and add it to a list of valid moves.
        6. If valid moves exist, return one randomly using self.RNG.choice.
        7. If no valid move is found after max_attempts, return None.
        """
        max_attempts = 100
        attachment_ids = list(solution.route_plan_attachment.keys())
        attempts = 0
        # Clear any previously stored moves
        self.Moves.clear()
        
        while attempts < max_attempts:
            attempts += 1
            
            # Randomly select attachment_id_1 (must have at least one order item)
            attachment_id_1 = self.RNG.choice(attachment_ids)
            attachment_route_1 = solution.route_plan_attachment[attachment_id_1]
            if len(attachment_route_1) == 0:
                continue
            
            # Get the equipment type of attachment_id_1
            attachment_type = solution.data.attachments[attachment_id_1].type
            
            # Randomly select attachment_id_2 from those with the same equipment type and not equal to attachment_id_1
            possible_attachment_2 = [aid for aid in attachment_ids 
                                    if aid != attachment_id_1 and solution.data.attachments[aid].type == attachment_type]
            if not possible_attachment_2:
                continue
            attachment_id_2 = self.RNG.choice(possible_attachment_2)
            attachment_route_2 = solution.route_plan_attachment[attachment_id_2]
            
            # Get attachment objects
            attachment_1_obj = solution.data.attachments[attachment_id_1]
            attachment_2_obj = solution.data.attachments[attachment_id_2]
            
            valid_moves = []
            
            # Iterate over each order item in attachment_route_1
            for order_item_id in attachment_route_1:
                # Create a flattened list of possible order item IDs for attachment 2
                attachment_2_possible_order_item_ids = [
                    oid for orders in attachment_2_obj.possible_order_item_ids.values() for oid in orders
                ]
                # Skip if the order item is not possible for attachment 2
                if order_item_id not in attachment_2_possible_order_item_ids:
                    continue
                
                # Skip if the order item is already in attachment_route_2
                if order_item_id in attachment_route_2:
                    continue
                
                insertion_position = None
                # If attachment 2 has no order items, insert at position 0
                if len(attachment_route_2) == 0:
                    insertion_position = [0, attachment_route_1.index(order_item_id)]
                else:
                    # Determine a valid insertion position in attachment_route_2
                    for order_item_id_2 in attachment_route_2:
                        # If the order item is neither in the predecessor nor in the successor lists for order_item_id_2,
                        # then insertion relative to this order item is not possible – break out.
                        if order_item_id not in attachment_2_obj.predecessor_ids[order_item_id_2] and \
                        order_item_id not in attachment_2_obj.successor_ids[order_item_id_2]:
                            insertion_position = None
                            break
                        # If order_item_id is a predecessor of order_item_id_2, it can be inserted before it.
                        if order_item_id in attachment_2_obj.predecessor_ids[order_item_id_2]:
                            insertion_position = [attachment_route_2.index(order_item_id_2), attachment_route_1.index(order_item_id)]
                            break
                        # If we are at the last order item in attachment_route_2 and order_item_id is a successor,
                        # then it can be inserted at the end.
                        if attachment_route_2.index(order_item_id_2) == len(attachment_route_2) - 1:
                            if order_item_id in attachment_2_obj.successor_ids[order_item_id_2]:
                                insertion_position = [attachment_route_2.index(order_item_id_2) + 1, attachment_route_1.index(order_item_id)]
                                break
                
                # If a valid insertion position was found, create the move.
                if insertion_position is not None:
                    move = ReplaceShiftAttachmentMove(
                        attachment_id_1,
                        attachment_id_2,
                        attachment_route_1,
                        attachment_route_2,
                        insertion_position[0],  # insertion index in attachment_route_2
                        insertion_position[1],  # reference index in attachment_route_1
                        order_item_id
                    )
                    valid_moves.append(move)
            
            # If any valid moves have been found for the chosen attachment pair, return one randomly using self.RNG.
            if valid_moves:
                return self.RNG.choice(valid_moves)
        
        # If no valid move is found after max_attempts, return None.
        return None

            
    def EvaluateMove(self, move: ReplaceShiftAttachmentMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_replace_shift_attachment_delta(move))

    def sort_move_solutions(self):
            
            # Sort with lowest Delta first
            self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)


    def constructCompleteRoutes(self, move:ReplaceShiftAttachmentMove, solution:Solution) -> dict:
        ''' Constructs the comlete Route from the Move'''
        
        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

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


    def MakeOneMove(self, solution: Solution) -> BaseMove:
        """
        Chooses a random valid machine move using self.RNG.

        Procedure:
        1. Randomly select a machine (machine_id_1) from solution.route_plan_machine that has at least one order item.
        2. Retrieve the equipment type of machine_id_1.
        3. Randomly select machine_id_2 from those machines that have the same type as machine_id_1 and are different from machine_id_1.
        4. For each order item in machine_route_1, check if it is contained in the list of possible order items for machine_id_2.
            - If machine_id_2 has no order items, the order item can be inserted at position 0.
            - Otherwise, determine a valid insertion position in machine_route_2's route based on predecessor/successor constraints.
        5. For each valid insertion, create a ReplaceShiftMachineMove (including the corresponding worker_id from solution.route_plan_worker)
            and add it to a list of valid moves.
        6. If valid moves exist, return one randomly using self.RNG.choice.
        7. If no valid move is found after max_attempts, return None.
        """
        max_attempts = 100
        machine_ids = list(solution.route_plan_machine.keys())
        attempts = 0
        # Clear previous moves
        self.Moves.clear()
        
        while attempts < max_attempts:
            attempts += 1
            
            # Randomly select machine_id_1 (must have at least one order item)
            machine_id_1 = self.RNG.choice(machine_ids)
            machine_route_1 = solution.route_plan_machine[machine_id_1]
            if len(machine_route_1) == 0:
                continue
            
            # Get the equipment type of machine_id_1
            machine_type = solution.data.machines[machine_id_1].type
            
            # Randomly select machine_id_2 from those machines that have the same type as machine_id_1
            possible_machine_2 = [mid for mid in machine_ids 
                                if mid != machine_id_1 and solution.data.machines[mid].type == machine_type]
            if not possible_machine_2:
                continue
            machine_id_2 = self.RNG.choice(possible_machine_2)
            machine_route_2 = solution.route_plan_machine[machine_id_2]
            machine_2 = solution.data.machines[machine_id_2]
            
            valid_moves = []
            
            # Iterate over each order item in machine_route_1
            for order_item_id in machine_route_1:
                # Create a flattened list of possible order item IDs for machine_2
                machine_2_possible_order_item_ids = [
                    oid for orders in machine_2.possible_order_item_ids.values() for oid in orders
                ]
                # Skip if the order item is not possible for machine_2
                if order_item_id not in machine_2_possible_order_item_ids:
                    continue
                
                insertion_position = None
                # If machine_2 has no order items, we can insert at position 0
                if len(machine_route_2) == 0:
                    insertion_position = [0, machine_route_1.index(order_item_id)]
                else:
                    # Determine a valid insertion position in machine_route_2
                    for order_item_id_2 in machine_route_2:
                        # If the order item is neither in the predecessor nor in the successor lists for order_item_id_2,
                        # then insertion is not possible relative to this order item – break out of the loop.
                        if order_item_id not in machine_2.predecessor_ids[order_item_id_2] and \
                        order_item_id not in machine_2.successor_ids[order_item_id_2]:
                            insertion_position = None
                            break
                        # If order_item_id is a predecessor of order_item_id_2, it can be inserted before it.
                        if order_item_id in machine_2.predecessor_ids[order_item_id_2]:
                            insertion_position = [machine_route_2.index(order_item_id_2), machine_route_1.index(order_item_id)]
                            break
                        # If we are at the last order item in machine_route_2 and order_item_id is a successor,
                        # then it can be inserted at the end.
                        if machine_route_2.index(order_item_id_2) == len(machine_route_2) - 1:
                            if order_item_id in machine_2.successor_ids[order_item_id_2]:
                                insertion_position = [machine_route_2.index(order_item_id_2) + 1, machine_route_1.index(order_item_id)]
                                break
                
                # If a valid insertion position was found, create the move.
                if insertion_position is not None:
                    # Find the corresponding worker_id in whose route the order item appears
                    worker_id = [wid for wid, route in solution.route_plan_worker.items() if order_item_id in route][0]
                    move = ReplaceShiftMachineMove(
                        machine_id_1, 
                        machine_id_2, 
                        machine_route_1, 
                        machine_route_2,
                        insertion_position[0],  # insertion index in machine_route_2
                        insertion_position[1],  # reference index in machine_route_1
                        order_item_id, 
                        worker_id
                    )
                    valid_moves.append(move)
            
            # If any valid moves have been found for the chosen pair, return one randomly using self.RNG.
            if valid_moves:
                return self.RNG.choice(valid_moves)
        
        # If no valid move is found after max_attempts, return None.
        return None




    def EvaluateMove(self, move: ReplaceShiftMachineMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_replace_shift_machine_delta(move))


    def sort_move_solutions(self):
        
        # Sort with lowest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)


    def constructCompleteRoutes(self, move: ReplaceShiftMachineMove, solution: Solution) -> dict:

        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

        machine_route_plan[move.MachineID1] = move.MachineRoute1
        machine_route_plan[move.MachineID2] = move.MachineRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan


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
    
    
    def MakeOneMove(self, solution: Solution) -> BaseMove:
        """
        Chooses a random valid swap move for machines using self.RNG.

        Procedure:
        1. Randomly select a machine (machine_id_1) from solution.route_plan_machine that has at least one order item.
        2. Retrieve the equipment type of machine_id_1.
        3. Randomly select machine_id_2 from those machines that:
            - Have the same type as machine_id_1,
            - Are different from machine_id_1, and
            - Have a non-empty route.
        4. For each order item in machine_route_1, determine candidate insertion positions in machine_route_2 based on predecessor/successor constraints.
        5. Similarly, determine candidate insertion positions for order items in machine_route_2 relative to machine_route_1.
        6. Generate swap moves (covering various cases) using the candidate positions.
        7. If at least one valid move is found, return one randomly using self.RNG.choice; otherwise, return None after max_attempts.
        """
        max_attempts = 100
        machine_ids = list(solution.route_plan_machine.keys())
        attempts = 0
        self.Moves.clear()  # Clear any previously stored moves

        while attempts < max_attempts:
            attempts += 1

            # Randomly select machine_id_1; must have a non-empty route.
            machine_id_1 = self.RNG.choice(machine_ids)
            machine_route_1 = solution.route_plan_machine[machine_id_1]
            if len(machine_route_1) == 0:
                continue

            # Retrieve machine type of machine_id_1.
            machine_type = solution.data.machines[machine_id_1].type

            # Filter candidate machines for machine_id_2: must have the same type, be different, and have a non-empty route.
            possible_machine_2 = [mid for mid in machine_ids 
                                if mid != machine_id_1 and 
                                solution.data.machines[mid].type == machine_type and 
                                len(solution.route_plan_machine[mid]) > 0]
            if not possible_machine_2:
                continue
            machine_id_2 = self.RNG.choice(possible_machine_2)
            machine_route_2 = solution.route_plan_machine[machine_id_2]

            # Retrieve machine objects.
            machine_1 = solution.data.machines[machine_id_1]
            machine_2 = solution.data.machines[machine_id_2]

            # Dictionaries for candidate positions:
            machine_2_order_item_positions = {}  # For order items from machine_route_1 to insert into machine_route_2.
            machine_1_order_item_positions = {}  # For order items from machine_route_2 to insert into machine_route_1.
            same_position_machine_route_1 = {}   # For swaps where an order item from machine_route_2 can be inserted at the same position in machine_route_1.
            same_position_machine_route_2 = {}   # For swaps where an order item from machine_route_1 can be inserted at the same position in machine_route_2.

            # For each order item in machine_route_1: determine candidate insertion in machine_route_2.
            for order_item_id_1 in machine_route_1:
                # Flatten the possible order item IDs for machine 2.
                machine_2_possible_order_item_ids = [oid for orders in machine_2.possible_order_item_ids.values() for oid in orders]
                if order_item_id_1 not in machine_2_possible_order_item_ids:
                    continue
                else:
                    for index, order_item_id_2 in enumerate(machine_route_2):
                        # Case: order_item_id_1 "collides" with order_item_id_2
                        if order_item_id_1 not in machine_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in machine_2.successor_ids[order_item_id_2]:
                            if len(machine_route_2) > index + 1:
                                if order_item_id_1 in machine_2.predecessor_ids[machine_route_2[index + 1]]:
                                    same_position_machine_route_2[order_item_id_1] = [index, order_item_id_2, machine_route_1.index(order_item_id_1)]
                                    break
                            elif len(machine_route_2) == index + 1:
                                if order_item_id_1 in machine_2.successor_ids.get(order_item_id_2, []):
                                    same_position_machine_route_2[order_item_id_1] = [index, order_item_id_2, machine_route_1.index(order_item_id_1)]
                                    break
                            break
                        # If order_item_id_1 is a predecessor of order_item_id_2, record its insertion position.
                        if order_item_id_1 in machine_2.predecessor_ids[order_item_id_2]:
                            machine_2_order_item_positions[order_item_id_1] = [index, machine_route_1.index(order_item_id_1)]
                            break
                        # If at the end of machine_route_2 and order_item_id_1 is a successor, insert at the end.
                        if index == len(machine_route_2) - 1:
                            if order_item_id_1 in machine_2.successor_ids[order_item_id_2]:
                                machine_2_order_item_positions[order_item_id_1] = [index + 1, machine_route_1.index(order_item_id_1)]
                                break

            # For each order item in machine_route_2: determine candidate insertion in machine_route_1.
            for order_item_id_2 in machine_route_2:
                machine_1_possible_order_item_ids = [oid for orders in machine_1.possible_order_item_ids.values() for oid in orders]
                if order_item_id_2 not in machine_1_possible_order_item_ids:
                    continue
                else:
                    for index, order_item_id_1 in enumerate(machine_route_1):
                        if order_item_id_2 not in machine_1.predecessor_ids[order_item_id_1] and order_item_id_2 not in machine_1.successor_ids[order_item_id_1]:
                            if len(machine_route_1) > index + 1:
                                if order_item_id_2 in machine_1.predecessor_ids[machine_route_1[index + 1]]:
                                    same_position_machine_route_1[order_item_id_2] = [index, order_item_id_1, machine_route_2.index(order_item_id_2)]
                                    break
                            elif len(machine_route_1) == index + 1:
                                if order_item_id_2 in machine_1.successor_ids.get(order_item_id_1, []):
                                    same_position_machine_route_1[order_item_id_2] = [index, order_item_id_1, machine_route_2.index(order_item_id_2)]
                                    break
                            break
                        if order_item_id_2 in machine_1.predecessor_ids[order_item_id_1]:
                            machine_1_order_item_positions[order_item_id_2] = [index, machine_route_2.index(order_item_id_2)]
                            break
                        if index == len(machine_route_1) - 1:
                            if order_item_id_2 in machine_1.successor_ids[order_item_id_1]:
                                machine_1_order_item_positions[order_item_id_2] = [index + 1, machine_route_2.index(order_item_id_2)]
                                break

            valid_moves = []
            
            # Case 1: Swap moves where order items are inserted at different positions.
            for order_item_id_2, pos_info_1 in machine_1_order_item_positions.items():
                for order_item_id_1, pos_info_2 in machine_2_order_item_positions.items():
                    # Determine the associated worker IDs for each order item via solution.route_plan_worker.
                    worker_id_1 = [wid for wid, route in solution.route_plan_worker.items() if order_item_id_1 in route][0]
                    worker_id_2 = [wid for wid, route in solution.route_plan_worker.items() if order_item_id_2 in route][0]
                    move = SwapShiftMachineMove(
                        machine_id_1, machine_id_2,
                        machine_route_1, machine_route_2,
                        pos_info_1[0], pos_info_2[0],
                        order_item_id_1, order_item_id_2,
                        worker_id_1, worker_id_2,
                        pos_info_2[1], pos_info_1[1]
                    )
                    valid_moves.append(move)
            
            # Case 2: Swap moves where both order items go into the same position.
            for order_item_id_2, pos_info_1 in same_position_machine_route_1.items():
                for order_item_id_1, pos_info_2 in same_position_machine_route_2.items():
                    if order_item_id_2 == pos_info_2[1] and order_item_id_1 == pos_info_1[1]:
                        worker_id_1 = [wid for wid, route in solution.route_plan_worker.items() if order_item_id_1 in route][0]
                        worker_id_2 = [wid for wid, route in solution.route_plan_worker.items() if order_item_id_2 in route][0]
                        move = SwapShiftMachineMove(
                            machine_id_1, machine_id_2,
                            machine_route_1, machine_route_2,
                            pos_info_1[0], pos_info_2[0],
                            order_item_id_1, order_item_id_2,
                            worker_id_1, worker_id_2,
                            pos_info_2[2], pos_info_1[2]
                        )
                        valid_moves.append(move)
            
            # Case 3: Swap moves where one order item is inserted at the same position and the other at a different position.
            for order_item_id_2, pos_info_1 in same_position_machine_route_1.items():
                for order_item_id_1, pos_info_2 in machine_2_order_item_positions.items():
                    if order_item_id_1 == pos_info_1[1]:
                        worker_id_1 = [wid for wid, route in solution.route_plan_worker.items() if order_item_id_1 in route][0]
                        worker_id_2 = [wid for wid, route in solution.route_plan_worker.items() if order_item_id_2 in route][0]
                        move = SwapShiftMachineMove(
                            machine_id_1, machine_id_2,
                            machine_route_1, machine_route_2,
                            pos_info_1[0], pos_info_2[0],
                            order_item_id_1, order_item_id_2,
                            worker_id_1, worker_id_2,
                            pos_info_2[1], pos_info_1[2]
                        )
                        valid_moves.append(move)
            
            # Case 4: The other way around.
            for order_item_id_1, pos_info_2 in same_position_machine_route_2.items():
                for order_item_id_2, pos_info_1 in machine_1_order_item_positions.items():
                    if order_item_id_2 == pos_info_2[1]:
                        worker_id_1 = [wid for wid, route in solution.route_plan_worker.items() if order_item_id_1 in route][0]
                        worker_id_2 = [wid for wid, route in solution.route_plan_worker.items() if order_item_id_2 in route][0]
                        move = SwapShiftMachineMove(
                            machine_id_1, machine_id_2,
                            machine_route_1, machine_route_2,
                            pos_info_1[0], pos_info_2[0],
                            order_item_id_1, order_item_id_2,
                            worker_id_1, worker_id_2,
                            pos_info_2[2], pos_info_1[1]
                        )
                        valid_moves.append(move)
            
            if valid_moves:
                return self.RNG.choice(valid_moves)
            
        return None

    def EvaluateMove(self, move: SwapShiftMachineMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_swap_shift_machine_delta(move))

    
    def sort_move_solutions(self):

        # Sort with highest Delta first, if equal sort with lowest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    
    def constructCompleteRoutes(self, move:SwapShiftMachineMove, solution:Solution) -> dict:

        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

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
                        # Check if the move is feasible for both workers
                        if self.WorkerRouteFeasibilityCheck(move.WorkerID1, move.WorkerRoute1) and self.WorkerRouteFeasibilityCheck(move.WorkerID2, move.WorkerRoute2):
                            self.Moves.append(move)

            # If we have found any valid moves for the chosen pair, select one randomly
            if self.Moves:
                return self.RNG.choice(self.Moves)

        # If no valid move is found after max_attempts, return None
        return None
    


    def EvaluateMove(self, move: ReplaceShiftWorkerMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_replace_shift_worker_delta(move))


    def sort_move_solutions(self):
        
        # Sort with lowest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    
    def constructCompleteRoutes(self, move:ReplaceShiftWorkerMove, solution:Solution) -> dict:

        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

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


    def MakeOneMove(self, solution: Solution) -> BaseMove:
        """
        Chooses a random valid swap move for workers using self.RNG.
        
        Procedure:
        1. Randomly select a pair of workers (worker_id_1 and worker_id_2) with non-empty routes.
        2. For the selected pair, build dictionaries of potential swap positions:
            - worker_2_order_item_positions: for order items from worker_route_1 that can be inserted into worker_route_2.
            - worker_1_order_item_positions: for order items from worker_route_2 that can be inserted into worker_route_1.
            - same_position_work_route_1 and same_position_work_route_2: for swaps where the insertion would be at the same position.
        3. For each candidate swap, check the maximum working hours constraint for both workers.
        4. Create a SwapShiftWorkerMove for each valid swap candidate and collect them.
        5. If at least one valid swap move is found, return one randomly using self.RNG.choice.
        6. If no valid move is found after a maximum number of attempts, return None.
        """
        max_attempts = 100
        worker_ids = list(solution.route_plan_worker.keys())
        attempts = 0
        self.Moves.clear()  # Clear any previously stored moves

        while attempts < max_attempts:
            attempts += 1

            # Randomly select two distinct workers with non-empty routes.
            worker_id_1 = self.RNG.choice(worker_ids)
            worker_route_1 = solution.route_plan_worker[worker_id_1]
            if len(worker_route_1) == 0:
                continue

            possible_worker_2 = [wid for wid in worker_ids if wid != worker_id_1 and len(solution.route_plan_worker[wid]) > 0]
            if not possible_worker_2:
                continue
            worker_id_2 = self.RNG.choice(possible_worker_2)
            worker_route_2 = solution.route_plan_worker[worker_id_2]

            # Retrieve worker objects
            worker_1 = solution.data.workers[worker_id_1]
            worker_2 = solution.data.workers[worker_id_2]

            # Dictionaries to collect potential swap positions.
            worker_1_order_item_positions = {}   # For order items from worker_route_2 that can be inserted in worker_route_1.
            worker_2_order_item_positions = {}   # For order items from worker_route_1 that can be inserted in worker_route_2.
            same_position_work_route_1 = {}        # For swaps where the order item from worker_route_2 can be inserted at the same position in worker_route_1.
            same_position_work_route_2 = {}        # For swaps where the order item from worker_route_1 can be inserted at the same position in worker_route_2.

            # For each order item in worker_route_1: determine if it can be inserted into worker_route_2.
            for order_item_id_1 in worker_route_1:
                # Get list of possible order item IDs for worker 2 (flattened)
                worker_2_possible_order_item_ids = [oid for orders in worker_2.possible_order_item_ids.values() for oid in orders]
                if order_item_id_1 not in worker_2_possible_order_item_ids:
                    continue

                # Examine positions in worker_route_2
                for index, order_item_id_2 in enumerate(worker_route_2):
                    # If order_item_id_1 does not appear in either predecessor or successor lists of order_item_id_2,
                    # then a swap relative to this order item may be possible using a "same position" strategy.
                    if order_item_id_1 not in worker_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in worker_2.successor_ids[order_item_id_2]:
                        if len(worker_route_2) > index + 1:
                            if order_item_id_1 in worker_2.predecessor_ids[worker_route_2[index + 1]]:
                                same_position_work_route_2[order_item_id_1] = [index, order_item_id_2]
                                break
                        elif len(worker_route_2) == index + 1:
                            # Using get() in case there is no predecessor list for index-1
                            if order_item_id_1 in worker_2.successor_ids.get(order_item_id_2, []):
                                same_position_work_route_2[order_item_id_1] = [index, order_item_id_2]
                                break
                        break
                    # Otherwise, if order_item_id_1 is a predecessor of order_item_id_2, record the insertion position.
                    if order_item_id_1 in worker_2.predecessor_ids[order_item_id_2]:
                        worker_2_order_item_positions[order_item_id_1] = index
                        break
                    # If at the end of worker_route_2 and order_item_id_1 is a successor, it can be inserted at the end.
                    if index == len(worker_route_2) - 1:
                        if order_item_id_1 in worker_2.successor_ids[order_item_id_2]:
                            worker_2_order_item_positions[order_item_id_1] = index + 1
                            break

            # For each order item in worker_route_2: determine if it can be inserted into worker_route_1.
            for order_item_id_2 in worker_route_2:
                worker_1_possible_order_item_ids = [oid for orders in worker_1.possible_order_item_ids.values() for oid in orders]
                if order_item_id_2 not in worker_1_possible_order_item_ids:
                    continue
                for index, order_item_id_1 in enumerate(worker_route_1):
                    if order_item_id_2 not in worker_1.predecessor_ids[order_item_id_1] and order_item_id_2 not in worker_1.successor_ids[order_item_id_1]:
                        if len(worker_route_1) > index + 1:
                            if order_item_id_2 in worker_1.predecessor_ids[worker_route_1[index + 1]]:
                                same_position_work_route_1[order_item_id_2] = [index, order_item_id_1]
                                break
                        elif len(worker_route_1) == index + 1:
                            if order_item_id_2 in worker_1.successor_ids.get(order_item_id_1, []):
                                same_position_work_route_1[order_item_id_2] = [index, order_item_id_1]
                                break
                        break
                    if order_item_id_2 in worker_1.predecessor_ids[order_item_id_1]:
                        worker_1_order_item_positions[order_item_id_2] = index
                        break
                    if index == len(worker_route_1) - 1:
                        if order_item_id_2 in worker_1.successor_ids[order_item_id_1]:
                            worker_1_order_item_positions[order_item_id_2] = index + 1
                            break

            # Now generate swap moves based on the gathered positions.
            valid_moves = []
            # Case 1: Swap moves where order items move into different positions in the other worker's route.
            for order_item_id_2, pos_1 in worker_1_order_item_positions.items():
                for order_item_id_1, pos_2 in worker_2_order_item_positions.items():
                    # Check maximum working hours constraints for both workers.
                    if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                        continue
                    if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                        continue
                    # Determine the associated machine IDs for each order item.
                    machine_id_1 = [mid for mid, route in solution.route_plan_machine.items() if order_item_id_1 in route][0]
                    machine_id_2 = [mid for mid, route in solution.route_plan_machine.items() if order_item_id_2 in route][0]
                    move = SwapShiftWorkerMove(
                        worker_id_1, worker_id_2,
                        worker_route_1, worker_route_2,
                        pos_1, pos_2,
                        order_item_id_1, order_item_id_2,
                        machine_id_1, machine_id_2
                    )
                    valid_moves.append(move)
            # Case 2: Swap moves where both order items go into the same position.
            for order_item_id_2, pos_info1 in same_position_work_route_1.items():
                for order_item_id_1, pos_info2 in same_position_work_route_2.items():
                    if order_item_id_2 == pos_info2[1] and order_item_id_1 == pos_info1[1]:
                        if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                            continue
                        if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                            continue
                        machine_id_1 = [mid for mid, route in solution.route_plan_machine.items() if order_item_id_1 in route][0]
                        machine_id_2 = [mid for mid, route in solution.route_plan_machine.items() if order_item_id_2 in route][0]
                        move = SwapShiftWorkerMove(
                            worker_id_1, worker_id_2,
                            worker_route_1, worker_route_2,
                            pos_info1[0], pos_info2[0],
                            order_item_id_1, order_item_id_2,
                            machine_id_1, machine_id_2
                        )
                        valid_moves.append(move)
            # Case 3: Swap moves where one order item moves to the same position and the other to a different position.
            for order_item_id_2, pos_info1 in same_position_work_route_1.items():
                for order_item_id_1, pos_2 in worker_2_order_item_positions.items():
                    if order_item_id_1 == pos_info1[1]:
                        if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                            continue
                        if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                            continue
                        machine_id_1 = [mid for mid, route in solution.route_plan_machine.items() if order_item_id_1 in route][0]
                        machine_id_2 = [mid for mid, route in solution.route_plan_machine.items() if order_item_id_2 in route][0]
                        move = SwapShiftWorkerMove(
                            worker_id_1, worker_id_2,
                            worker_route_1, worker_route_2,
                            pos_info1[0], pos_2,
                            order_item_id_1, order_item_id_2,
                            machine_id_1, machine_id_2
                        )
                        valid_moves.append(move)
            # Case 4: The other way around.
            for order_item_id_1, pos_info2 in same_position_work_route_2.items():
                for order_item_id_2, pos_1 in worker_1_order_item_positions.items():
                    if order_item_id_2 == pos_info2[1]:
                        if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                            continue
                        if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                            continue
                        machine_id_1 = [mid for mid, route in solution.route_plan_machine.items() if order_item_id_1 in route][0]
                        machine_id_2 = [mid for mid, route in solution.route_plan_machine.items() if order_item_id_2 in route][0]
                        move = SwapShiftWorkerMove(
                            worker_id_1, worker_id_2,
                            worker_route_1, worker_route_2,
                            pos_1, pos_info2[0],
                            order_item_id_1, order_item_id_2,
                            machine_id_1, machine_id_2
                        )
                        valid_moves.append(move)

            if valid_moves:
                move = self.RNG.choice(valid_moves)
                if self.WorkerRouteFeasibilityCheck(move.WorkerID1, move.WorkerRoute1) and self.WorkerRouteFeasibilityCheck(move.WorkerID2, move.WorkerRoute2):
                    return move

        return None
    

    def EvaluateMove(self, move: SwapShiftWorkerMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.evaluationLogic.calculate_swap_shift_worker_delta(move))


    def sort_move_solutions(self):
        
        # Sort with lowest Delta first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    
    def constructCompleteRoutes(self, move:SwapShiftWorkerMove, solution:Solution) -> dict:

        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

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