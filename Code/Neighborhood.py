from OutputData import Solution
from OutputData import *
import itertools        
from EvaluationLogic import EvaluationLogic
import concurrent.futures  # For parallelism
from copy import deepcopy
from itertools import chain


class BaseMove:

    def __init__(self):
        self.Delta = None

    def setDelta(self,delta:float) -> None: 
        ''' Set the Delta of the Move'''
        self.Delta = delta



class BaseNeighborhood:

    def __init__(self, data: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng=None):
        self.data = data
        self.evaluationLogic = evaluationLogic
        self.solutionPool = solutionPool
        self.rng = rng

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

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

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

                worker_route, machine_route = self.constructCompleteRoutes(bestNeighborhoodMove, bestNeighborhoodSolution)
                bestNeighborhoodSolution = Solution(worker_route, machine_route, self.data)
                self.evaluationLogic.evaluate(bestNeighborhoodSolution)

                self.solutionPool.AddSolution(bestNeighborhoodSolution)

                #print(f"Best Neighborhood Solution: \n{bestNeighborhoodSolution}")

            else:
                print(f"\nNo better solution found in iteration {iterator}")
                hasSolutionImproved = False

            iterator += 1

        return bestNeighborhoodSolution
    


class InsertShiftMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """

    def __init__(self, machine_id, worker_id, machine_route, worker_route, machine_route_index, worker_route_index, order_item_id):


        self.MachineRoute = list(machine_route)
        self.WorkerRoute = list(worker_route)

        self.MachineRouteIndex = machine_route_index
        self.WorkerRouteIndex = worker_route_index

        self.OrderItemID = order_item_id
        
        self.MachineID = machine_id
        self.WorkerID = worker_id

        

        self.MachineRoute.insert(self.MachineRouteIndex, self.OrderItemID)
        self.WorkerRoute.insert(self.WorkerRouteIndex, self.OrderItemID)

        #print(f"Machine ID: {self.MachineID}")
        #print(f"Machine Route: {self.MachineRoute}")
        #print(f"Worker ID: {self.WorkerID}")
        #print(f"Worker Route: {self.WorkerRoute}")
    


class InsertShiftNeighborhood(OutputNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData:InputData, evaluationLogic:EvaluationLogic, solutionPool:SolutionPool, rng):
        super().__init__(inputData,  evaluationLogic, solutionPool, rng)

        self.Type = 'Insert_Shift'


    def DiscoverMoves(self, solution:Solution, not_used_shifts = None):
        """ Generate all $n choose 2$ moves and shuffle them """

        if not_used_shifts is None:
            unused_order_item_ids = solution.not_started_order_item_ids

        
        for order_item_id in unused_order_item_ids:

            # Dictionary to store information about the position of the order_item in machine routes
            order_item_position_machine_route = dict()
            order_item_position_worker_route = dict()

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


    

            for machine_id, machine_route_and_index in order_item_position_machine_route.items():
                for worker_id, worker_route_and_index in order_item_position_worker_route.items():
                    self.Moves.append(InsertShiftMove(machine_id, worker_id, machine_route_and_index[1], worker_route_and_index[1], machine_route_and_index[0], worker_route_and_index[0], order_item_id))


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

        machine_route_plan[move.MachineID] = move.MachineRoute
        worker_route_plan[move.WorkerID] = move.WorkerRoute

        return worker_route_plan, machine_route_plan

        




class TimeNeighborhood(BaseNeighborhood):

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

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

                worker_route, machine_route = self.constructCompleteRoutes(bestNeighborhoodMove, bestNeighborhoodSolution)
                bestNeighborhoodSolution = Solution(worker_route, machine_route, self.data)
                self.evaluationLogic.evaluate(bestNeighborhoodSolution)

                self.solutionPool.AddSolution(bestNeighborhoodSolution)

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

            print(f"\nBest Current Solution: \n{bestNeighborhoodSolution}")

        print(f"\nBest Worker Route: \n{bestNeighborhoodSolution.route_plan_worker}")

        return bestNeighborhoodSolution


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

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

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

        worker_route_plan[move.WorkerID1] = move.WorkerRoute1
        worker_route_plan[move.WorkerID2] = move.WorkerRoute2

        return worker_route_plan, machine_route_plan



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

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

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
                if len(worker_route_1) == 0 or len(worker_route_2) == 0:
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
                                worker_2_order_item_positions[order_item_id_1] = worker_route_2.index(order_item_id_2)
                                break

                            # If order_item_id_1 is a successor of the last order_item in the worker route of worker 2, it can be inserted at the end of the worker route
                            if len(worker_route_2) == worker_route_2.index(order_item_id_2) + 1:
                                if order_item_id_1 in worker_2.successor_ids[order_item_id_2]:
                                    worker_2_order_item_positions[order_item_id_1] = worker_route_2.index(order_item_id_2) + 1
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
                                worker_1_order_item_positions[order_item_id_2] = worker_route_1.index(order_item_id_1)
                                break

                            # If order_item_id_2 is a successor of the last order_item in the worker route of worker 1, it can be inserted at the end of the worker route
                            if len(worker_route_1) == worker_route_1.index(order_item_id_1) + 1:
                                if order_item_id_2 in worker_1.successor_ids[order_item_id_1]:
                                    worker_1_order_item_positions[order_item_id_2] = worker_route_1.index(order_item_id_1) + 1
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
                '''
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
                '''

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

        worker_route_plan[move.WorkerID1] = move.WorkerRoute1
        worker_route_plan[move.WorkerID2] = move.WorkerRoute2

        return worker_route_plan, machine_route_plan






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