"""
===============================================================================
                              NEIGHBORHOOD MODULE
===============================================================================

Neighborhood Search Operations for Railroad Construction Optimization

This module implements a comprehensive framework of neighborhood search algorithms and move operations
for local search optimization of railroad construction scheduling problems. It provides systematic
exploration of solution spaces through various move types, constraint validation, and multi-objective
optimization capabilities for complex resource allocation scenarios.

Core Architecture:
- BaseMove: Abstract base class for all solution modification operations
- BaseNeighborhood: Framework for systematic neighborhood exploration with feasibility checking
- OutputNeighborhood: Specialized neighborhood for output-based solution improvements
- TimeNeighborhood: Base class for time-based multi-worker neighborhood operations

Move Types and Neighborhoods:

Insertion Operations:
- InsertShiftMove/InsertShiftNeighborhood: Insert unscheduled order items into existing routes
  with precedence constraint satisfaction and resource compatibility checking

External Swap Operations:
- SwapShiftExternalMove/SwapShiftExternalNeighborhood: Exchange scheduled order items with 
  unscheduled alternatives to improve solution quality

Resource-Specific Neighborhoods:
- ReplaceShiftAttachmentMove/ReplaceShiftAttachmentNeighborhood: Move order items between different attachments
- SwapShiftAttachmentMove/SwapShiftAttachmentNeighborhood: Exchange order items between attachment routes
- ReplaceShiftMachineMove/ReplaceShiftMachineNeighborhood: Transfer order items between machines
- SwapShiftMachineMove/SwapShiftMachineNeighborhood: Exchange order items between machine routes
- ReplaceShiftWorkerMove/ReplaceShiftWorkerNeighborhood: Move order items between worker schedules
- SwapShiftWorkerMove/SwapShiftWorkerNeighborhood: Exchange order items between worker routes

Search Strategies:
- Best Improvement: Evaluate all moves and select optimal improvement
- First Improvement: Accept first feasible improving move for faster convergence
- Stochastic Sampling: Random move generation for large neighborhoods an simulated annealing

Constraint Validation:
- Worker Regulations: Night shift limits, maximum working hours, shift frequency constraints
- Precedence Relationships: Task ordering requirements across all resource types
- Resource Compatibility: Machine capabilities, worker skills, attachment type matching
- Equipment Requirements: Multi-attachment allocation with conflict resolution


Dependencies:
- Code.OutputData: Solution representation, route plans, and data structures
- Code.EvaluationLogic: Multi-objective solution quality assessment and delta calculations
- Code.InputData: Problem instance data with orders, resources, and constraints
- itertools, numpy: Combinatorial operations and numerical computations for move generation
- concurrent.futures: Parallel evaluation capabilities for large neighborhood exploration
- copy: Deep copying for solution state management during move evaluation
"""

from Code.OutputData import Solution
from Code.OutputData import *
import itertools        
from Code.EvaluationLogic import EvaluationLogic
import concurrent.futures  # For parallelism
from copy import deepcopy
from itertools import chain
import itertools
import numpy as np
from collections import defaultdict
from itertools import permutations
from itertools import combinations


class BaseMove:
    """
    Abstract base class representing a local search move operation.
    
    A move represents a specific modification to a solution that can be
    evaluated for improvement. This includes the delta (change in objective)
    and detailed information about the move's impact on solution quality.
    """

    def __init__(self):
        """Initialize move with empty delta information."""
        self.Delta = None  # Overall change in objective value

    def setDelta(self, delta_tuple):
        """
        Set the delta (change in objective) for this move.
        
        Args:
            delta_tuple (tuple): Contains (delta_value, delta_details)
                                delta_value: Overall change in objective
                                delta_details: Detailed breakdown of changes
        """
        self.Delta = delta_tuple[0]           # Total objective change
        self.DeltaDetails = delta_tuple[1]    # Detailed component changes


class BaseNeighborhood:
    """
    Abstract base class for neighborhood search operations.
    
    This class provides the framework for implementing various neighborhood
    structures in local search algorithms. It handles move discovery,
    evaluation, and selection while maintaining feasibility constraints.
    
    The neighborhood search supports both best improvement and first improvement
    strategies for exploring the solution space efficiently.
    """

    def __init__(self, data: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        """
        Initialize neighborhood search with problem data and evaluation components.
        
        Args:
            data: Input problem data containing orders, workers, machines, etc.
            evaluationLogic: Component for evaluating solution quality
            paretoSolutions: Container for maintaining Pareto-optimal solutions
            rng: Random number generator for stochastic operations
        """
        self.data = data                           # Problem instance data
        self.evaluationLogic = evaluationLogic     # Solution evaluation component
        self.ParetoSolutions = paretoSolutions     # Pareto solution storage
        self.RNG = rng                            # Random number generator

        # Storage for discovered moves and their evaluations
        self.Moves = []                           # List of discovered moves
        self.MoveSolutions = []                   # List of evaluated moves
        self.type = 'None'                        # Neighborhood type identifier

    def DiscoverMoves(self) -> None:
        """
        Find all possible moves for this neighborhood structure.
        
        This method must be implemented by subclasses to define the specific
        move generation logic for each neighborhood type. The discovered moves
        should be stored in self.Moves and typically shuffled for randomization.
        """
        raise Exception('DiscoverMoves() is not implemented for the abstract BaseNeighborhood class.')

    def EvaluateMoves(self, evaluationStrategy: str) -> None:
        """
        Evaluate discovered moves using the specified strategy.
        
        Args:
            evaluationStrategy: Strategy for move evaluation
                              - 'BestImprovement': Evaluate all moves, select best
                              - 'FirstImprovement': Stop at first improving move
        """
        if evaluationStrategy == 'BestImprovement':
            self.EvaluateMovesBestImprovement()
        elif evaluationStrategy == 'FirstImprovement':
            self.EvaluateMovesFirstImprovement()
        else:
            raise Exception(f'Evaluation strategy {evaluationStrategy} not implemented.')

    def EvaluateMove(self, move: BaseMove) -> None:
        """
        Calculate the objective change for a specific move.
        
        This method must be implemented by subclasses to define how moves
        are evaluated in terms of solution quality changes.
        
        Args:
            move: The move to evaluate
        """
        raise Exception('EvaluateMove() is not implemented for the abstract BaseNeighborhood class.')

    def EvaluateMovesBestImprovement(self) -> None:
        """
        Evaluate all discovered moves for best improvement strategy.
        
        This method evaluates every move in self.Moves and stores the results
        in self.MoveSolutions for later selection of the best move.
        """
        for move in self.Moves:
            self.EvaluateMove(move)              # Calculate move's impact
            self.MoveSolutions.append(move)      # Store evaluated move

    def EvaluateMovesFirstImprovement(self) -> None:
        """
        Evaluate moves until first improvement is found.
        
        This method must be implemented by subclasses to define the specific
        logic for first improvement evaluation in each neighborhood type.
        """
        raise Exception('EvaluateMovesFirstImprovement() is not implemented for the abstract BaseNeighborhood class.')

    def MakeBestMove(self) -> BaseMove:
        """
        Select and return the best move from evaluated candidates.
        
        This method must be implemented by subclasses to define the selection
        criteria for choosing the best move from self.MoveSolutions.
        
        Returns:
            BaseMove: The best move found, or None if no improving move exists
        """
        raise Exception('MakeBestMove() is not implemented for the abstract BaseNeighborhood class.')
    
    def Update(self) -> None:
        """
        Reset neighborhood state for next iteration.
        
        Clears all discovered moves and evaluated solutions to prepare
        for the next round of neighborhood exploration.
        """
        self.Moves.clear()                        # Clear discovered moves
        self.MoveSolutions.clear()                # Clear evaluated moves

    def WorkerRouteFeasibilityCheck(self, worker_id, worker_route: list) -> bool:
        """
        Check if a worker route satisfies all safety and regulatory constraints.
        
        This method validates that the proposed worker schedule complies with
        occupational safety regulations including night shift limits and
        maximum shifts within time periods.
        
        Args:
            worker_id: ID of the worker to check
            worker_route: Ordered list of order item IDs assigned to worker
            
        Returns:
            bool: True if route is feasible, False otherwise
        """
        worker = self.data.workers[worker_id]

        # Check maximum consecutive night shifts constraint
        night_shifts = 0
        for order_item_id in worker_route:
            if order_item_id in worker.night_shift_ids:
                night_shifts += 1                 # Increment consecutive night shifts
            else:
                night_shifts = 0                  # Reset counter for day shift
            
            # Violation: too many consecutive night shifts
            if night_shifts > self.data._max_consecutive_night_shifts:
                return False
        
        # Check maximum shifts in time period constraint
        order_items = [self.data.order_items[order_item_id] for order_item_id in worker_route]
        for i, order_item_i in enumerate(order_items):
            # Define time window starting from this order item
            window_start = order_item_i.start_time.date()
            window_end = window_start + self.data._time_period_for_max_shifts
            shift_count = 0
            
            # Count shifts within the time window
            for order_item_j in order_items:
                if window_start <= order_item_j.start_time.date() < window_end:
                    shift_count += 1
            
            # Violation: too many shifts in time period
            if shift_count > self.data._max_shifts_in_time_period:
                return False

        return True  # All constraints satisfied


class OutputNeighborhood(BaseNeighborhood):
    """
    Specialized neighborhood class for output-based solution improvements.
    
    This class extends BaseNeighborhood to provide specific functionality
    for neighborhoods that focus on improving solution outputs such as
    completion times, resource utilization, or cost metrics.
    
    It includes implementation of move evaluation and selection strategies
    tailored for output optimization scenarios.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        """
        Initialize output-focused neighborhood with problem data.
        
        Args:
            inputData: Problem instance data
            evaluationLogic: Solution evaluation component
            paretoSolutions: Pareto solution management
            rng: Random number generator
        """
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

    def EvaluateMove(self, move: BaseMove) -> None:
        """
        Evaluate a move for output-based improvements.
        
        This method must be implemented by subclasses to define specific
        evaluation logic for different types of output improvements.
        
        Args:
            move: The move to evaluate
        """
        raise Exception('EvaluateMove() is not implemented for the abstract OutputNeighborhood class.')

    def MakeBestMove(self) -> BaseMove:
        """
        Select the best feasible move from evaluated candidates.
        
        This method sorts the evaluated moves according to the specific
        criteria defined by subclasses and returns the first feasible move
        that satisfies all worker safety constraints.
        
        Returns:
            BaseMove: Best feasible move, or None if no feasible moves exist
        """
        # Sort moves according to subclass-specific criteria
        self.sort_move_solutions()
        
        # Return first feasible move from sorted list
        for move_solution in self.MoveSolutions:
            if self.WorkerRouteFeasibilityCheck(move_solution.WorkerID, move_solution.WorkerRoute):
                return move_solution
                    
        return None  # No feasible moves found

    def sort_move_solutions(self):
        """
        Sort move solutions according to neighborhood-specific criteria.
        
        This method must be implemented by subclasses to define the sorting
        logic appropriate for each specific neighborhood type.
        """
        raise NotImplementedError('sort_move_solutions() must be implemented in the child class')
            
    def EvaluateMovesFirstImprovement(self) -> None:
        """
        Evaluate moves using first improvement strategy.
        
        This method evaluates moves sequentially until it finds the first
        feasible improving move, then stops the evaluation process.
        """
        for move in self.Moves:
            self.EvaluateMove(move)

            # Check feasibility before accepting the move
            if self.WorkerRouteFeasibilityCheck(move.RouteDayCohort):
                self.MoveSolutions.append(move)
                return None  # Found first feasible improving move
        
        return None  # No feasible improving moves found

    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> None:
        """
        Perform iterative local search to improve the given solution.
        
        This method implements a hill-climbing local search algorithm that
        repeatedly explores the neighborhood, evaluates moves, and applies
        the best improvement until no further improvements are possible.
        
        Args:
            neighborhoodEvaluationStrategy: Strategy for evaluating moves
                                          ('BestImprovement' or 'FirstImprovement')
            solution: Starting solution for local search
            
        Returns:
            Solution: Best solution found during local search
        """
        hasSolutionImproved = True
        bestNeighborhoodSolution = deepcopy(solution)

        iterator = 1
        while hasSolutionImproved:
            
            # Reset neighborhood state for new iteration
            self.Update() 
            self.DiscoverMoves(bestNeighborhoodSolution)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()

            if bestNeighborhoodMove is not None:
                
                print(f"\nIteration: {iterator}")
                print(bestNeighborhoodSolution)

                # Construct complete solution from the best move
                worker_route, machine_route, attachement_route = self.constructCompleteRoutes(bestNeighborhoodMove, bestNeighborhoodSolution)
                bestNeighborhoodSolution = Solution(worker_route, machine_route, attachement_route, self.data)
                self.evaluationLogic.evaluate(bestNeighborhoodSolution)

                # Denormalize delta details for display
                denorm = {}
                for detail, value in bestNeighborhoodMove.DeltaDetails.items():
                    if detail == 'attachment_distance':
                        denorm[detail] = value * (self.data.max_transport_distance - self.data.min_transport_distance) + self.data.min_transport_distance
                    elif detail == 'commute_distance':
                        denorm[detail] = value * (self.data.max_work_distance - self.data.min_work_distance) + self.data.min_work_distance
                    elif detail == 'transport_distance':
                        denorm[detail] = value * (self.data.max_transport_distance - self.data.min_transport_distance) + self.data.min_transport_distance
                    else:
                        denorm[detail] = value

                # Display improvement details
                for detail, value in denorm.items():
                    print(f"{detail}: {value}")

            else:
                # No improving move found - local optimum reached
                hasSolutionImproved = False

            iterator += 1

        return bestNeighborhoodSolution
    
    def SingleMove(self, solution: Solution) -> BaseMove:
        """
        Generate a single move for the given solution.
        
        This method creates and evaluates a single move from the neighborhood
        without exploring all possible moves. Useful for stochastic sampling
        of the neighborhood space.
        
        Args:
            solution: Current solution to generate move from
            
        Returns:
            BaseMove: Single evaluated move, or None if no moves found
        """
        # Reset neighborhood state
        self.Update()
        
        # Generate a single move
        move = self.MakeOneMove(solution)

        if move:
            self.EvaluateMove(move)
            return move
        else:
            # No moves found in current neighborhood
            return None


class InsertShiftMove(BaseMove):
    """
    Represents an insertion move for order items in the solution.
    
    This move type inserts an order item at specific positions in machine,
    worker, and attachment routes. It represents the fundamental operation
    of adding a new order item to the current schedule.
    
    The move maintains information about the insertion positions and
    handles the dynamic allocation of attachment resources.
    """

    def __init__(self, machine_id, worker_id, machine_route, worker_route, machine_route_index, worker_route_index, order_item_id, dynamic_percentage, attachment_information=None):
        """
        Initialize an insert shift move.
        
        Args:
            machine_id: ID of machine for the order item
            worker_id: ID of worker for the order item
            machine_route: Current machine route
            worker_route: Current worker route
            machine_route_index: Insertion position in machine route
            worker_route_index: Insertion position in worker route
            order_item_id: Order item to be inserted
            dynamic_percentage: Dynamic resource allocation percentage
            attachment_information: List of (attachment_id, index, route) tuples
        """
        # Copy routes to avoid modifying original solutions
        self.MachineRoute = list(machine_route)
        self.WorkerRoute = list(worker_route)

        # Store insertion positions
        self.MachineRouteIndex = machine_route_index
        self.WorkerRouteIndex = worker_route_index

        # Store move details
        self.OrderItemID = order_item_id
        self.MachineID = machine_id
        self.WorkerID = worker_id

        # Insert order item at specified positions
        self.MachineRoute.insert(self.MachineRouteIndex, self.OrderItemID)
        self.WorkerRoute.insert(self.WorkerRouteIndex, self.OrderItemID)

        # Store dynamic allocation percentage
        self.DynamicPercentage = dynamic_percentage

        # Handle attachment information if provided
        if attachment_information is not None:
            index = 0
            for attachment_id, attachment_index, attachment_route in attachment_information:
                # Dynamically create attachment route attributes
                setattr(self, f"AttachmentRoute_{index}", list(attachment_route))
                setattr(self, f"AttachmentRouteIndex_{index}", attachment_index)
                setattr(self, f"AttachmentID_{index}", attachment_id)
                
                # Insert order item into attachment route
                route = getattr(self, f"AttachmentRoute_{index}")
                route.insert(attachment_index, self.OrderItemID)
                
                index += 1

            self.NumberOfAttachments = index
        else:
            self.NumberOfAttachments = 0

    def __str__(self):
        """String representation of the move for debugging and logging."""
        return f"Machine: {self.MachineID} \nMachine Route: {self.MachineRoute} \nMachine Route Index: {self.MachineRouteIndex} \nWorker: {self.WorkerID} \nWorker Route: {self.WorkerRoute} \nWorker Route Index: {self.WorkerRouteIndex} \nOrder Item ID: {self.OrderItemID} \nDynamic Percentage: {self.DynamicPercentage} \nNumber of Attachments: {self.NumberOfAttachments}"


class InsertShiftNeighborhood(OutputNeighborhood):
    """
    Neighborhood for insertion and shift moves of order items.
    
    This neighborhood explores moves where unscheduled order items are
    inserted into existing routes at feasible positions. It considers
    precedence constraints, machine capabilities, and worker skills
    when generating possible insertion positions.
    
    The neighborhood systematically explores all valid insertion points
    for each unscheduled order item across all compatible resources.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        """
        Initialize insertion neighborhood with problem data.
        
        Args:
            inputData: Problem instance data
            evaluationLogic: Solution evaluation component
            paretoSolutions: Pareto solution management
            rng: Random number generator
        """
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)
        self.Type = 'Insert_Shift'

    def DiscoverMoves(self, solution: Solution, not_used_shifts=None):
        """
        Generate all valid insertion moves for unscheduled order items.
        
        This method systematically explores insertion positions for each
        unscheduled order item, considering precedence constraints and
        resource compatibility.
        
        Args:
            solution: Current solution to explore
            not_used_shifts: Optional list of specific order items to consider
        """
        # Get unscheduled order items
        if not_used_shifts is None:
            unused_order_item_ids = solution.not_started_order_item_ids
        
        for order_item_id in unused_order_item_ids:

            # Storage for valid insertion positions
            order_item_position_machine_route = dict()  # Maps machine_id to [position, route]
            order_item_position_worker_route = dict()   # Maps worker_id to [position, route]
            possible_attachment_positions = dict()      # Maps attachment tuple to position info

            # Find valid machine insertion positions
            for machine_id, machine_route in solution.route_plan_machine.items():
                machine = solution.data.machines[machine_id]

                # Check if machine can process this order item
                machine_possible_order_item_ids = [order_item_ids for orders in machine.possible_order_item_ids.values() for order_item_ids in orders]
                if order_item_id not in machine_possible_order_item_ids:
                    continue

                # Handle empty machine route - can insert at position 0
                if len(machine_route) == 0:
                    order_item_position_machine_route[machine_id] = [0, list(machine_route)]
                    continue

                # Find valid insertion position based on precedence constraints
                for order_item_id_machine in machine_route:
                    # Check if order_item can be inserted relative to current item
                    if order_item_id not in machine.predecessor_ids[order_item_id_machine] and order_item_id not in machine.successor_ids[order_item_id_machine]:
                        break

                    # Insert before current item if order_item is its predecessor
                    if order_item_id in machine.predecessor_ids[order_item_id_machine]:
                        order_item_position_machine_route[machine_id] = [machine_route.index(order_item_id_machine), list(machine_route)]
                        break
                    
                    # Insert at end if order_item is successor of last item
                    if len(machine_route) == machine_route.index(order_item_id_machine) + 1:
                        if order_item_id in machine.successor_ids[order_item_id_machine]:
                            order_item_position_machine_route[machine_id] = [machine_route.index(order_item_id_machine) + 1, list(machine_route)]
                            break

            # Find valid worker insertion positions
            for worker_id, worker_route in solution.route_plan_worker.items():
                worker = solution.data.workers[worker_id]

                # Check if worker can process this order item
                worker_possible_order_item_ids = [order_item_ids for orders in worker.possible_order_item_ids.values() for order_item_ids in orders]
                if order_item_id not in worker_possible_order_item_ids:
                    continue
                
                # Skip if adding this order would exceed maximum working hours
                if solution.worker_work_time[worker_id] + solution.data.order_items[order_item_id].duration > self.data._max_working_hours:
                    continue
  
                # Handle empty worker route - can insert at position 0
                if len(worker_route) == 0:
                    order_item_position_worker_route[worker_id] = [0, list(worker_route)]
                    continue
                
                # Find valid insertion position based on precedence constraints
                for order_item_id_worker in worker_route:
                    # Check if order_item can be inserted relative to current item
                    if order_item_id not in worker.predecessor_ids[order_item_id_worker] and order_item_id not in worker.successor_ids[order_item_id_worker]:
                        break

                    # Insert before current item if order_item is its predecessor
                    if order_item_id in worker.predecessor_ids[order_item_id_worker]:
                        order_item_position_worker_route[worker_id] = [worker_route.index(order_item_id_worker), list(worker_route)]
                        break
                    
                    # Insert at end if order_item is successor of last item
                    if len(worker_route) == worker_route.index(order_item_id_worker) + 1:
                        if order_item_id in worker.successor_ids[order_item_id_worker]:
                            order_item_position_worker_route[worker_id] = [worker_route.index(order_item_id_worker) + 1, list(worker_route)]
                            break

            # Find valid attachment insertion positions if required
            order_item_obj = solution.data.order_items[order_item_id]
            
            if order_item_obj.equipment_types:
                # Collect possible insertion positions for each required equipment
                positions_for_each_occurrence = []
                for equipment_type in order_item_obj.equipment_types:
                    possible_positions_for_type = []
                    for attachment_id, attachment_route in solution.route_plan_attachment.items():
                        attachment = solution.data.attachments[int(attachment_id)]

                        # Check if attachment can handle this equipment type
                        if equipment_type != attachment.type:
                            continue

                        # Check if attachment can process this order item
                        attachment_possible_order_item_ids = [oid for orders in attachment.possible_order_item_ids.values() for oid in orders]
                        if order_item_id not in attachment_possible_order_item_ids:
                            continue

                        # Handle empty attachment route
                        if len(attachment_route) == 0:
                            possible_positions_for_type.append((attachment_id, 0, list(attachment_route)))
                            continue

                        # Find valid insertion position based on precedence constraints
                        for order_item_id_attachment in attachment_route:
                            pred = attachment.predecessor_ids.get(order_item_id_attachment, [])
                            succ = attachment.successor_ids.get(order_item_id_attachment, [])
                            
                            # Skip if order item cannot be inserted relative to current item
                            if order_item_id not in pred and order_item_id not in succ:
                                break

                            # Insert before current item if order_item is its predecessor
                            if order_item_id in pred:
                                pos = attachment_route.index(order_item_id_attachment)
                                possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                                break

                            # Insert at end if order_item is successor of last item
                            if attachment_route.index(order_item_id_attachment) == len(attachment_route) - 1:
                                if order_item_id in succ:
                                    pos = attachment_route.index(order_item_id_attachment) + 1
                                    possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                                    break

                    positions_for_each_occurrence.append(possible_positions_for_type)

                # Generate all valid attachment combinations
                attachment_insertion_combinations = list(itertools.product(*positions_for_each_occurrence))
                
                # Store valid combinations (no duplicate attachments)
                for combo in attachment_insertion_combinations:
                    attachment_ids_tuple = tuple(pos[0] for pos in combo)
                    # Skip combinations with duplicate attachment usage
                    if len(set(attachment_ids_tuple)) < len(attachment_ids_tuple):
                        continue
                    possible_attachment_positions[attachment_ids_tuple] = combo

            # Get order number for dynamic percentage lookup
            order = [order.order_number for order in solution.data.orders if order_item_id in order.order_item_ids][0]

            # Generate moves for all valid machine-worker-attachment combinations
            for machine_id, machine_index_and_route in order_item_position_machine_route.items():
                for worker_id, worker_index_and_route in order_item_position_worker_route.items():
                    if order_item_obj.equipment_types:
                        # Create moves with attachment information
                        for attachment_ids_tuple, attachment_info in possible_attachment_positions.items():
                            self.Moves.append(InsertShiftMove(
                                machine_id,
                                worker_id,
                                machine_index_and_route[1],  # machine route snapshot
                                worker_index_and_route[1],   # worker route snapshot
                                machine_index_and_route[0],  # machine insertion index
                                worker_index_and_route[0],   # worker insertion index
                                order_item_id,
                                dynamic_percentage=solution.dynamic_percentage_order[order],
                                attachment_information=attachment_info
                            ))
                    else:
                        # Create moves without attachment requirements
                        self.Moves.append(InsertShiftMove(
                            machine_id,
                            worker_id,
                            machine_index_and_route[1],
                            worker_index_and_route[1],
                            machine_index_and_route[0],
                            worker_index_and_route[0],
                            order_item_id,
                            dynamic_percentage=solution.dynamic_percentage_order[order]
                        ))

    def find_first_insertion_position(self, route, order_item_id, predecessor_ids, successor_ids):
        """
        Find the first valid insertion position in a route based on precedence constraints.
        
        This method scans the route linearly and returns the first position where
        the order item can be validly inserted while respecting predecessor and
        successor relationships.
        
        Args:
            route: Current route to search for insertion position
            order_item_id: Order item to be inserted
            predecessor_ids: Dictionary mapping items to their valid predecessors
            successor_ids: Dictionary mapping items to their valid successors
            
        Returns:
            int: First valid insertion position, or None if no valid position found
        """
        # Empty route allows insertion at position 0
        if not route:
            return 0
            
        # Check each position in the route
        for pos in range(len(route)):
            # Skip if order item cannot be related to current route item
            if order_item_id not in predecessor_ids.get(route[pos], []) and order_item_id not in successor_ids.get(route[pos], []):
                return None
                
            # Insert before current item if order_item is its predecessor
            if order_item_id in predecessor_ids.get(route[pos], []):
                return pos
                
        # Check if can insert at end of route
        if order_item_id in successor_ids.get(route[-1], []):
            return len(route)
        return None

    def MakeOneMove(self, solution: Solution, not_used_shifts=None) -> BaseMove:
        """
        Generate a single random valid insertion move using cascading selection.
        
        This method implements a stochastic approach to move generation by:
        1. Randomly selecting an unused order item
        2. Finding compatible machine, worker, and attachment resources
        3. Using linear scanning to find first valid insertion positions
        4. Ensuring no resource conflicts (e.g., duplicate attachment usage)
        
        Args:
            solution: Current solution to generate move from
            not_used_shifts: Optional list of specific order items to consider
            
        Returns:
            InsertShiftMove: Single valid move, or None if no feasible moves exist
        """
        attempts = 0
        self.Moves.clear()
        
        # Get order items to consider
        if not_used_shifts is None:
            unused_order_item_ids = solution.not_started_order_item_ids
        else:
            unused_order_item_ids = not_used_shifts

        if not unused_order_item_ids:
            return None
        
        # Shuffle order item candidates for randomness
        order_item_candidates = list(unused_order_item_ids)
        self.RNG.shuffle(order_item_candidates)

        for order_item_id in order_item_candidates:
            attempts += 1
            order_item_id = self.RNG.choice(unused_order_item_ids)
            order_item_obj = solution.data.order_items[order_item_id]
            
            # Find compatible machines and select first valid insertion position
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
            
            # Find compatible workers considering working hour constraints
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
            
            # Handle attachment requirements if any
            attachment_info_list = []
            if order_item_obj.equipment_types:
                used_attachment_ids = set()
                for equipment_type in order_item_obj.equipment_types:
                    # Find attachments of matching type
                    candidate_attachments = []
                    for attachment_id, att_route in solution.route_plan_attachment.items():
                        attachment = solution.data.attachments[int(attachment_id)]
                        if attachment.type != equipment_type:
                            continue
                        possible_ids = [oid for orders in attachment.possible_order_item_ids.values() for oid in orders]
                        if order_item_id in possible_ids:
                            candidate_attachments.append(attachment_id)
                            
                    # Filter out already used attachments
                    candidate_attachments = [att for att in candidate_attachments if att not in used_attachment_ids]
                    if not candidate_attachments:
                        break  # Cannot assign this equipment requirement
                        
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
                    
                # Check if all equipment requirements were satisfied
                if len(attachment_info_list) != len(order_item_obj.equipment_types):
                    continue
            
            # Create the insertion move
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

            # Verify worker route feasibility before returning
            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                return move

        return None

    def EvaluateMove(self, move: InsertShiftMove) -> None:
        """
        Evaluate the impact of an insertion move on solution quality.
        
        This method calculates the delta (change) in objective function values
        that would result from applying the given insertion move.
        
        Args:
            move: The insertion move to evaluate
        """
        # Calculate and store the delta impact of this move
        move.setDelta(self.evaluationLogic.calculate_insert_shift_delta(move))

    def sort_move_solutions(self):
        """
        Sort evaluated moves by solution quality improvement.
        
        Sorts moves in ascending order of delta values, prioritizing moves
        that provide the best improvement in the primary objective.
        """
        # Sort by delta values: primary objective first, secondary if tied
        self.MoveSolutions.sort(key=lambda move: (move.Delta[0], move.Delta[1]), reverse=False)

    def constructCompleteRoutes(self, move: InsertShiftMove, solution: Solution) -> tuple:
        """
        Construct complete route plans from an insertion move.
        
        This method takes a move and constructs the complete worker, machine,
        and attachment route plans that would result from applying the move
        to the current solution.
        
        Args:
            move: The insertion move to apply
            solution: Current solution to modify
            
        Returns:
            tuple: (worker_route_plan, machine_route_plan, attachment_route_plan)
        """
        # Copy current route plans to avoid modifying original solution
        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

        # Apply move modifications
        machine_route_plan[move.MachineID] = move.MachineRoute
        worker_route_plan[move.WorkerID] = move.WorkerRoute
        
        # Update attachment routes if any
        for index in range(move.NumberOfAttachments):
            attachment_route_plan[getattr(move, f"AttachmentID_{index}")] = getattr(move, f"AttachmentRoute_{index}")

        return worker_route_plan, machine_route_plan, attachment_route_plan


class SwapShiftExternalMove(BaseMove):
    """
    Represents a swap move between an order item in the current solution and an external (unscheduled) order item.
    
    This move type exchanges a scheduled order item with an unscheduled one, potentially improving
    solution quality by replacing less optimal assignments with better alternatives.
    
    The move handles complex resource reassignment including machines, workers, and attachments,
    and manages both same-machine and different-machine scenarios.
    """
    
    def __init__(self, machine_info_intern, machine_id, worker_id, machine_route, worker_route, machine_index, worker_index, order_item_id_int, order_item_id_ext, dynamic_percentage_int, dynamic_percentage_ext, attachment_information_int=None, attachment_information_ext=None):
        """
        Initialize an external swap move.
        
        Args:
            machine_info_intern: Information about the internal order item's machine assignment
            machine_id: Machine ID for the external order item
            worker_id: Worker ID for both order items
            machine_route: Machine route for external order item
            worker_route: Worker route containing internal order item
            machine_index: Insertion index for external order item in machine route
            worker_index: Position of internal order item in worker route
            order_item_id_int: Internal (currently scheduled) order item ID
            order_item_id_ext: External (unscheduled) order item ID
            dynamic_percentage_int: Dynamic allocation percentage for internal order
            dynamic_percentage_ext: Dynamic allocation percentage for external order
            attachment_information_int: Attachment info for internal order item
            attachment_information_ext: Attachment info for external order item
        """
        # Store order item identifiers
        self.OrderItemIDInt = order_item_id_int
        self.OrderItemIDExt = order_item_id_ext

        # Worker route modifications
        self.WorkerID = worker_id
        self.WorkerRoute = list(worker_route)
        self.WorkerRouteIndex = worker_index

        # Replace internal order item with external one in worker route
        self.WorkerRoute.insert(self.WorkerRouteIndex, self.OrderItemIDExt)
        self.WorkerRoute.remove(self.OrderItemIDInt)

        # Store dynamic allocation percentages
        self.DynamicPercentageInt = dynamic_percentage_int
        self.DynamicPercentageExt = dynamic_percentage_ext

        # Machine assignment handling
        self.MachineIDExt = machine_id
        self.MachineIDInt = next(iter(machine_info_intern.keys()))

        # Handle same machine vs. different machine scenarios
        if self.MachineIDExt == self.MachineIDInt:
            # Same machine: simple replacement
            self.SameMachine = True
            self.MachineRoute = list(machine_route)
            self.MachineRouteIndex = machine_info_intern[self.MachineIDInt][0]

            self.MachineRoute.insert(self.MachineRouteIndex, self.OrderItemIDExt)
            self.MachineRoute.remove(self.OrderItemIDInt)

        else:
            # Different machines: separate route handling
            self.SameMachine = False
            self.MachineRouteExt = list(machine_route)
            self.MachineRouteInt = list(machine_info_intern[self.MachineIDInt][1])

            self.MachineRouteIndexExt = machine_index
            self.MachineRouteIndexInt = machine_info_intern[self.MachineIDInt][0]

            # Add external order item to external machine route
            self.MachineRouteExt.insert(self.MachineRouteIndexExt, self.OrderItemIDExt)
            # Remove internal order item from internal machine route
            self.MachineRouteInt.remove(self.OrderItemIDInt)

        # Handle external attachment information
        if attachment_information_ext is not None:
            index = 0
            for attachment_id, attachment_index, attachment_route in attachment_information_ext:
                # Create dynamic attachment route attributes
                setattr(self, f"AttachmentRouteExt_{index}", list(attachment_route))
                setattr(self, f"AttachmentRouteIndexExt_{index}", attachment_index)
                setattr(self, f"AttachmentIDExt_{index}", attachment_id)
                
                # Insert external order item into attachment route
                route = getattr(self, f"AttachmentRouteExt_{index}")
                route.insert(attachment_index, self.OrderItemIDExt)
                
                index += 1

            self.NumberOfAttachmentsExt = index
        else:
            self.NumberOfAttachmentsExt = 0

        # Handle internal attachment information
        if attachment_information_int is not None:
            index = 0
            for attachment_id, attachment_index_route in attachment_information_int.items():
                setattr(self, f"AttachmentRouteInt_{index}", list(attachment_index_route[1]))
                setattr(self, f"AttachmentRouteIndexInt_{index}", attachment_index_route[0])
                setattr(self, f"AttachmentIDInt_{index}", attachment_id)

                # Remove internal order item from attachment route
                route = getattr(self, f"AttachmentRouteInt_{index}")
                route.remove(self.OrderItemIDInt)
                
                index += 1

            self.NumberOfAttachmentsInt = index
        else:
            self.NumberOfAttachmentsInt = 0


class SwapShiftExternalNeighborhood(OutputNeighborhood):
    """
    Neighborhood for swapping scheduled order items with unscheduled external ones.
    
    This neighborhood explores moves where currently scheduled order items are
    replaced with unscheduled alternatives that might provide better solution
    quality. It handles complex resource constraints including machine compatibility,
    worker skills, attachment requirements, and precedence relationships.
    
    The neighborhood systematically evaluates all feasible swaps between internal
    and external order items while maintaining solution feasibility.
    """
    
    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        """
        Initialize external swap neighborhood.
        
        Args:
            inputData: Problem instance data
            evaluationLogic: Solution evaluation component
            paretoSolutions: Pareto solution management
            rng: Random number generator
        """
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)
        self.Type = 'Swap_Shift_External'

    def DiscoverMoves(self, solution: Solution, not_used_shifts=None):
        """
        Generate all valid external swap moves for the current solution.
        
        This method systematically explores swaps between scheduled and unscheduled
        order items, considering worker compatibility, working hour constraints,
        precedence relationships, and resource availability.
        
        Args:
            solution: Current solution to explore
            not_used_shifts: Optional list of specific unscheduled order items to consider
        """
        # Get unscheduled order items to consider
        if not_used_shifts is None:
            unused_order_item_ids = solution.not_started_order_item_ids

        # Explore swaps for each unscheduled order item
        for order_item_id_ext in unused_order_item_ids:
            for worker_id, worker_route in solution.route_plan_worker.items():
                
                # Skip workers not involved in current solution
                if len(worker_route) == 0:
                    continue

                worker = solution.data.workers[worker_id]

                # Check if worker can process the external order item
                worker_possible_order_item_ids = [order_item_ids for orders in worker.possible_order_item_ids.values() for order_item_ids in orders]
                if order_item_id_ext not in worker_possible_order_item_ids:
                    continue

                # Evaluate each position in worker route for potential swaps
                for worker_index, order_item_id_int in enumerate(worker_route):
                    
                    # Check precedence compatibility for the swap
                    if order_item_id_ext not in worker.predecessor_ids[order_item_id_int] and order_item_id_ext not in worker.successor_ids[order_item_id_int]:
                        # Verify working hour constraints after swap
                        if solution.worker_work_time[worker_id] + solution.data.order_items[order_item_id_ext].duration - solution.data.order_items[order_item_id_int].duration > self.data._max_working_hours:
                            continue

                        # Handle single-item worker route case
                        if len(worker_route) == 1:
                            machine_info_int, machine_info_ext = self.find_machine_routes(solution, order_item_id_int, order_item_id_ext)
                            attachment_info_int, attachment_info_ext = self.find_attachment_routes(solution, order_item_id_ext, order_item_id_int)
                            if machine_info_int is not None and machine_info_ext is not None:
                                # Get order numbers for dynamic percentage lookup
                                order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                
                                # Generate moves for all valid machine combinations
                                for machine_id, machine_index_and_route in machine_info_ext.items():
                                    if attachment_info_int == True and attachment_info_ext == True:
                                        self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext]))
                                    elif attachment_info_ext == True and attachment_info_int:
                                        self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int))
                                    elif attachment_info_int and attachment_info_ext:
                                        for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                            # Avoid attachment conflicts
                                            if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                continue
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int, attachment_information_ext=attachment_info))
                            break

                        # Handle first position in worker route
                        elif worker_index == 0:
                            # Check if external order can be predecessor of next item
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
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int))
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int, attachment_information_ext=attachment_info))
                                break

                        # Handle middle positions in worker route
                        elif len(worker_route) > worker_index + 1:
                            # Check if external order fits between predecessor and successor
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
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int))
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int, attachment_information_ext=attachment_info))
                                break

                        # Handle last position in worker route
                        elif len(worker_route) == worker_index + 1:
                            # Check if external order can be successor of previous item
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
                                            self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int))
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                self.Moves.append(SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int, attachment_information_ext=attachment_info))
                                break

    def find_machine_routes(self, solution: Solution, order_item_id_int: int, order_item_id_ext: int) -> tuple:
        """
        Find valid machine routes for swapping internal and external order items.
        
        This method identifies machine assignments for both the internal (currently scheduled)
        and external (unscheduled) order items, considering machine capabilities and
        precedence constraints.
        
        Args:
            solution: Current solution
            order_item_id_int: Internal order item to be removed
            order_item_id_ext: External order item to be inserted
            
        Returns:
            tuple: (machine_info_int, machine_info_ext) containing machine assignment information
        """
        machine_info_int = dict()
        machine_info_ext = dict()
        
        # Find all machines currently processing the internal order item
        for machine_id, machine_route in solution.route_plan_machine.items():
            if order_item_id_int in machine_route:
                machine_info_int[machine_id] = [machine_route.index(order_item_id_int), list(machine_route)]
        
        # Find valid insertion positions for external order item
        possible_positions = []
        for machine_id, machine_route in solution.route_plan_machine.items():
            machine = solution.data.machines[machine_id]
            
            # Check if machine can process the external order item
            possible_ids = [oid for orders in machine.possible_order_item_ids.values() for oid in orders]
            if order_item_id_ext not in possible_ids:
                continue
            
            # Handle empty machine route
            if len(machine_route) == 0:
                possible_positions.append((machine_id, 0, list(machine_route)))
            else:
                # Find first valid insertion position based on precedence constraints
                for i, current_item in enumerate(machine_route):
                    if order_item_id_ext not in machine.predecessor_ids.get(current_item, []) and order_item_id_ext not in machine.successor_ids.get(current_item, []):
                        break

                    # Insert before current item if external order is its predecessor
                    if order_item_id_ext in machine.predecessor_ids.get(current_item, []):
                        possible_positions.append((machine_id, i, list(machine_route)))
                        break
                        
                # Check if can insert at end of route
                if order_item_id_ext in machine.successor_ids.get(machine_route[-1], []):
                    possible_positions.append((machine_id, len(machine_route), list(machine_route)))
        
        # Return None if no valid positions found
        if not possible_positions:
            return None, None
        
        # Build machine info dictionary for external order item
        for (mid, pos, snapshot) in possible_positions:
            machine_info_ext[mid] = (pos, snapshot)
        
        return machine_info_int, machine_info_ext

    def find_attachment_routes(self, solution: Solution, order_item_id_ext: int, order_item_id_int: int) -> tuple:
        """
        Find valid attachment routes for swapping internal and external order items.
        
        This method identifies attachment assignments for both order items,
        considering equipment type requirements and attachment capabilities.
        
        Args:
            solution: Current solution
            order_item_id_ext: External order item requiring attachments
            order_item_id_int: Internal order item currently using attachments
            
        Returns:
            tuple: (attachment_info_int, attachment_info_ext) containing attachment information
        """
        order_item_ext_obj = solution.data.order_items[order_item_id_ext]
        order_item_int_obj = solution.data.order_items[order_item_id_int]

        # Handle case where neither order item requires attachments
        if not order_item_ext_obj.equipment_types and not order_item_int_obj.equipment_types:
            return True, True
        
        attachment_info_int = dict()
        attachment_info_ext = dict()

        # Find current attachment assignments for internal order item
        for attachment_id, attachment_route in solution.route_plan_attachment.items():
            if order_item_id_int in attachment_route:
                attachment_info_int[attachment_id] = [attachment_route.index(order_item_id_int), list(attachment_route)]

        # Handle case where external order item doesn't require attachments
        if not order_item_ext_obj.equipment_types:
            return attachment_info_int, True

        # Find valid attachment positions for external order item
        positions_for_each_occurrence = []
        for equipment_type in order_item_ext_obj.equipment_types:
            possible_positions_for_type = []
            for attachment_id, attachment_route in solution.route_plan_attachment.items():
                attachment = solution.data.attachments[int(attachment_id)]

                # Check if attachment can handle this equipment type
                if equipment_type != attachment.type:
                    continue

                # Check if attachment can process this order item
                attachment_possible_order_item_ids = [oid for orders in attachment.possible_order_item_ids.values() for oid in orders]
                if order_item_id_ext not in attachment_possible_order_item_ids:
                    continue

                # Handle empty attachment route
                if len(attachment_route) == 0:
                    possible_positions_for_type.append((attachment_id, 0, list(attachment_route)))
                    continue
                
                # Special case: if internal order item is in this attachment route,
                # external order can potentially take its place if precedence allows
                if order_item_id_int in attachment_route:
                    index = attachment_route.index(order_item_id_int)
                    pred_id = attachment_route[index - 1] if index > 0 else None
                    succ_id = attachment_route[index + 1] if index < len(attachment_route) - 1 else None

                    # Check if external order can fit between predecessor and successor
                    if order_item_id_ext in attachment.predecessor_ids.get(pred_id, []) and order_item_id_ext in attachment.successor_ids.get(succ_id, []):
                        possible_positions_for_type.append((attachment_id, index, list(attachment_route)))
                        continue

                # Find valid insertion position based on precedence constraints
                for order_item_id_attachment in attachment_route:
                    pred = attachment.predecessor_ids.get(order_item_id_attachment, [])
                    succ = attachment.successor_ids.get(order_item_id_attachment, [])
                    
                    # Skip if external order cannot be related to current attachment item
                    if order_item_id_ext not in pred and order_item_id_ext not in succ:
                        break

                    # Insert before current item if external order is its predecessor
                    if order_item_id_ext in pred:
                        pos = attachment_route.index(order_item_id_attachment)
                        possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                        break

                    # Insert at end if external order is successor of last item
                    if attachment_route.index(order_item_id_attachment) == len(attachment_route) - 1:
                        if order_item_id_ext in succ:
                            pos = attachment_route.index(order_item_id_attachment) + 1
                            possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                            break

            positions_for_each_occurrence.append(possible_positions_for_type)

        # Generate all valid attachment combinations
        attachment_insertion_combinations = list(itertools.product(*positions_for_each_occurrence))
        
        # Store valid combinations (no duplicate attachments)
        for combo in attachment_insertion_combinations:
            attachment_ids_tuple = tuple(pos[0] for pos in combo)
            # Skip combinations with duplicate attachment usage
            if len(set(attachment_ids_tuple)) < len(attachment_ids_tuple):
                continue
            attachment_info_ext[attachment_ids_tuple] = combo

        # Return None if no valid attachment combinations found
        if not attachment_info_ext:
            return False, False

        return attachment_info_int, attachment_info_ext

    def MakeOneMove(self, solution: Solution, not_used_shifts=None) -> BaseMove:
        """
        Generate a single random external swap move using cascading selection.
        
        This method implements a stochastic approach to external swap move generation by:
        1. Randomly selecting an unscheduled order item
        2. Finding compatible workers with existing assignments
        3. Evaluating swap opportunities at each worker position
        4. Ensuring resource compatibility and constraint satisfaction
        
        Args:
            solution: Current solution to generate move from
            not_used_shifts: Optional list of specific unscheduled order items
            
        Returns:
            SwapShiftExternalMove: Single valid swap move, or None if no feasible moves exist
        """
        self.Moves.clear()

        # Get unscheduled order items to consider
        if not_used_shifts is None:
            unused_order_item_ids = solution.not_started_order_item_ids
        else:
            unused_order_item_ids = not_used_shifts

        if not unused_order_item_ids:
            return None  # No unused order items available
        
        # Shuffle order item candidates for randomness
        order_item_candidates = list(unused_order_item_ids)
        self.RNG.shuffle(order_item_candidates)

        for order_item_id_ext in order_item_candidates:

            # Find workers with non-empty routes for potential swaps
            candidate_workers = [
                worker_id for worker_id, worker_route in solution.route_plan_worker.items()
                if worker_route  # Worker must have at least one order item
            ]
            
            if not candidate_workers:
                continue  # No valid workers

            # Randomize worker selection order
            self.RNG.shuffle(candidate_workers)
            
            for worker_id in candidate_workers:
                worker_route = solution.route_plan_worker[worker_id]
                worker = solution.data.workers[worker_id]

                # Check if worker can process the external order item
                worker_possible_order_item_ids = [order_item_ids for orders in worker.possible_order_item_ids.values() for order_item_ids in orders]
                
                if order_item_id_ext not in worker_possible_order_item_ids:
                    continue  # Worker cannot process the order item

                # Evaluate each position in worker route for potential swaps
                for worker_index, order_item_id_int in enumerate(worker_route):

                    # Check precedence compatibility and working hour constraints
                    if order_item_id_ext not in worker.predecessor_ids[order_item_id_int] and order_item_id_ext not in worker.successor_ids[order_item_id_int]:
                        # Verify working hours after swap
                        if solution.worker_work_time[worker_id] + solution.data.order_items[order_item_id_ext].duration - solution.data.order_items[order_item_id_int].duration > self.data._max_working_hours:
                            continue

                        # Handle single-item worker route case
                        if len(worker_route) == 1:
                            machine_info_int, machine_info_ext = self.find_single_machine_route(solution, order_item_id_int, order_item_id_ext)
                            attachment_info_int, attachment_info_ext = self.find_single_attachment_route(solution, order_item_id_ext, order_item_id_int)
                            if machine_info_int is not None and machine_info_ext is not None:
                                # Get order numbers for dynamic percentage lookup
                                order_int = [order.order_number for order in solution.data.orders if order_item_id_int in order.order_item_ids][0]
                                order_ext = [order.order_number for order in solution.data.orders if order_item_id_ext in order.order_item_ids][0]
                                
                                # Try all valid machine combinations
                                for machine_id, machine_index_and_route in machine_info_ext.items():
                                    if attachment_info_int == True and attachment_info_ext == True:
                                        move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext])
                                        if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                            return move
                                    elif attachment_info_ext == True and attachment_info_int:
                                        move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int)
                                        if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                            return move
                                    elif attachment_info_int and attachment_info_ext:
                                        for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                            # Avoid attachment conflicts
                                            if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                continue
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int, attachment_information_ext=attachment_info)
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move

                        # Handle first position in worker route
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
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int)
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int, attachment_information_ext=attachment_info)
                                                if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                    return move

                        # Handle middle positions in worker route
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
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int)
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int, attachment_information_ext=attachment_info)
                                                if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                    return move

                        # Handle last position in worker route
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
                                            move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int)
                                            if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                return move
                                        elif attachment_info_int and attachment_info_ext:
                                            for attachment_ids_tuple, attachment_info in attachment_info_ext.items():
                                                if any(attachment_id_int == attachment_id_ext for attachment_id_ext in attachment_ids_tuple for attachment_id_int in attachment_info_int.keys()):
                                                    continue
                                                move = SwapShiftExternalMove(machine_info_int, machine_id, worker_id, machine_index_and_route[1], worker_route, machine_index_and_route[0], worker_index, order_item_id_int, order_item_id_ext, solution.dynamic_percentage_order[order_int], solution.dynamic_percentage_order[order_ext], attachment_information_int=attachment_info_int, attachment_information_ext=attachment_info)
                                                if self.WorkerRouteFeasibilityCheck(move.WorkerID, move.WorkerRoute):
                                                    return move

        return None  # No valid move found

    def find_single_machine_route(self, solution: Solution, order_item_id_int: int, order_item_id_ext: int) -> tuple:
        """
        Find a single valid machine route assignment for external swap move generation.
        
        This method randomly selects the first valid machine that can process the external
        order item, used for stochastic move generation rather than exhaustive search.
        
        Args:
            solution: Current solution
            order_item_id_int: Internal order item to locate
            order_item_id_ext: External order item to place
            
        Returns:
            tuple: (machine_info_int, machine_info_ext) for first valid assignment
        """
        machine_info_int = dict()
        machine_info_ext = dict()
        
        # Find current machine assignment for internal order item
        for machine_id, machine_route in solution.route_plan_machine.items():
            if order_item_id_int in machine_route:
                machine_info_int[machine_id] = [machine_route.index(order_item_id_int), list(machine_route)]

        # Randomly search for first valid machine for external order item
        machine_ids = list(solution.route_plan_machine.keys())
        self.RNG.shuffle(machine_ids)

        for machine_id in machine_ids:
            machine_route = solution.route_plan_machine[machine_id]
            machine = solution.data.machines[machine_id]
            
            # Check if machine can process external order item
            possible_ids = [oid for orders in machine.possible_order_item_ids.values() for oid in orders]
            if order_item_id_ext not in possible_ids:
                continue
            
            # Handle empty machine route
            if len(machine_route) == 0:
                machine_info_ext[machine_id] = (0, list(machine_route))
                return machine_info_int, machine_info_ext
            else:
                # Find first valid insertion position
                for i, current_item in enumerate(machine_route):
                    if order_item_id_ext not in machine.predecessor_ids.get(current_item, []) and order_item_id_ext not in machine.successor_ids.get(current_item, []):
                        break

                    # Insert before current item if external order is its predecessor
                    if order_item_id_ext in machine.predecessor_ids.get(current_item, []):
                        machine_info_ext[machine_id] = (i, list(machine_route))
                        return machine_info_int, machine_info_ext
                        
                # Check if can insert at end
                if order_item_id_ext in machine.successor_ids.get(machine_route[-1], []):
                    machine_info_ext[machine_id] = (len(machine_route), list(machine_route))
                    return machine_info_int, machine_info_ext
        
        # Return None if no valid assignments found
        if not machine_info_ext:
            return None, None

    def find_single_attachment_route(self, solution: Solution, order_item_id_ext: int, order_item_id_int: int) -> tuple:
        """
        Find a single valid attachment route assignment for external swap move generation.
        
        This method randomly selects the first valid attachment configuration for the
        external order item, used for stochastic move generation.
        
        Args:
            solution: Current solution
            order_item_id_ext: External order item requiring attachments
            order_item_id_int: Internal order item currently using attachments
            
        Returns:
            tuple: (attachment_info_int, attachment_info_ext) for first valid assignment
        """
        order_item_ext_obj = solution.data.order_items[order_item_id_ext]
        order_item_int_obj = solution.data.order_items[order_item_id_int]

        # Handle case where neither order item requires attachments
        if not order_item_ext_obj.equipment_types and not order_item_int_obj.equipment_types:
            return True, True
        
        attachment_info_int = dict()
        attachment_info_ext = dict()

        # Find current attachment assignments for internal order item
        for attachment_id, attachment_route in solution.route_plan_attachment.items():
            if order_item_id_int in attachment_route:
                attachment_info_int[attachment_id] = [attachment_route.index(order_item_id_int), list(attachment_route)]

        # Handle case where external order item doesn't require attachments
        if not order_item_ext_obj.equipment_types:
            return attachment_info_int, True

        # Find valid attachment positions for external order item
        positions_for_each_occurrence = []
        for equipment_type in order_item_ext_obj.equipment_types:
            possible_positions_for_type = []

            # Randomly search attachments for first valid position
            attachment_ids = list(solution.route_plan_attachment.keys())
            self.RNG.shuffle(attachment_ids)

            break_flag = False

            for attachment_id in attachment_ids:
                if break_flag:
                    break

                attachment_route = solution.route_plan_attachment[attachment_id]
                attachment = solution.data.attachments[attachment_id]

                # Check if attachment can handle this equipment type
                if equipment_type != attachment.type:
                    continue

                # Check if attachment can process this order item
                attachment_possible_order_item_ids = [oid for orders in attachment.possible_order_item_ids.values() for oid in orders]
                if order_item_id_ext not in attachment_possible_order_item_ids:
                    continue

                # Handle empty attachment route
                if len(attachment_route) == 0:
                    possible_positions_for_type.append((attachment_id, 0, list(attachment_route)))
                    break
                
                # Check if can replace internal order item at same position
                if order_item_id_int in attachment_route:
                    index = attachment_route.index(order_item_id_int)
                    pred_id = attachment_route[index - 1] if index > 0 else None
                    succ_id = attachment_route[index + 1] if index < len(attachment_route) - 1 else None

                    if order_item_id_ext in attachment.predecessor_ids.get(pred_id, []) and order_item_id_ext in attachment.successor_ids.get(succ_id, []):
                        possible_positions_for_type.append((attachment_id, index, list(attachment_route)))
                        break

                # Find valid insertion position based on precedence
                for order_item_id_attachment in attachment_route:
                    pred = attachment.predecessor_ids.get(order_item_id_attachment, [])
                    succ = attachment.successor_ids.get(order_item_id_attachment, [])
                    
                    # Skip if external order cannot be related to current attachment item
                    if order_item_id_ext not in pred and order_item_id_ext not in succ:
                        break_flag = True
                        break

                    # Insert before current item if external order is its predecessor
                    if order_item_id_ext in pred:
                        pos = attachment_route.index(order_item_id_attachment)
                        possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                        break_flag = True
                        break

                    # Insert at end if external order is successor of last item
                    if attachment_route.index(order_item_id_attachment) == len(attachment_route) - 1:
                        if order_item_id_ext in succ:
                            pos = attachment_route.index(order_item_id_attachment) + 1
                            possible_positions_for_type.append((attachment_id, pos, list(attachment_route)))
                            break_flag = True
                            break

            positions_for_each_occurrence.append(possible_positions_for_type)

        # Generate valid attachment combinations
        attachment_insertion_combinations = list(itertools.product(*positions_for_each_occurrence))
        
        # Store valid combinations (no duplicate attachments)
        for combo in attachment_insertion_combinations:
            attachment_ids_tuple = tuple(pos[0] for pos in combo)
            # Skip combinations with duplicate attachment usage
            if len(set(attachment_ids_tuple)) < len(attachment_ids_tuple):
                continue
            attachment_info_ext[attachment_ids_tuple] = combo

        # Return None if no valid combinations found
        if not attachment_info_ext:
            return False, False

        return attachment_info_int, attachment_info_ext

    def EvaluateMove(self, move: SwapShiftExternalMove) -> None:
        """
        Evaluate the impact of an external swap move on solution quality.
        
        This method calculates the delta (change) in objective function values
        that would result from applying the given external swap move.
        
        Args:
            move: The external swap move to evaluate
        """
        # Calculate and store the delta impact of this move
        move.setDelta(self.evaluationLogic.calculate_swap_shift_external_delta(move))

    def sort_move_solutions(self):
        """
        Sort evaluated moves by solution quality improvement.
        
        Sorts moves in ascending order of delta values, prioritizing moves
        that provide the best improvement in the primary objective.
        """
        # Sort by delta values: primary objective first, secondary if tied
        self.MoveSolutions.sort(key=lambda move: (move.Delta[0], move.Delta[1]), reverse=False)

    def constructCompleteRoutes(self, move: SwapShiftExternalMove, solution: Solution) -> tuple:
        """
        Construct complete route plans from an external swap move.
        
        This method builds the complete worker, machine, and attachment route plans
        that would result from applying the external swap move to the current solution.
        
        Args:
            move: The external swap move to apply
            solution: Current solution to modify
            
        Returns:
            tuple: (worker_route_plan, machine_route_plan, attachment_route_plan)
        """
        # Copy current route plans to avoid modifying original solution
        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

        # Apply worker route changes
        worker_route_plan[move.WorkerID] = move.WorkerRoute

        # Apply machine route changes based on same/different machine scenarios
        if not move.SameMachine:
            # Different machines: update both internal and external machine routes
            machine_route_plan[move.MachineIDInt] = move.MachineRouteInt
            machine_route_plan[move.MachineIDExt] = move.MachineRouteExt
        else:
            # Same machine: update single machine route
            machine_route_plan[move.MachineIDExt] = move.MachineRoute

        # Apply attachment route changes for internal order item
        for index in range(move.NumberOfAttachmentsInt):
            attachment_route_plan[getattr(move, f"AttachmentIDInt_{index}")] = getattr(move, f"AttachmentRouteInt_{index}")

        # Apply attachment route changes for external order item
        for index in range(move.NumberOfAttachmentsExt):
            attachment_route_plan[getattr(move, f"AttachmentIDExt_{index}")] = getattr(move, f"AttachmentRouteExt_{index}")

        return worker_route_plan, machine_route_plan, attachment_route_plan

    def MakeBestMove(self) -> BaseMove:
        """
        Select the best feasible external swap move from evaluated candidates.
        
        This method sorts the evaluated moves and returns the first feasible move
        that provides an improvement (negative delta).
        
        Returns:
            SwapShiftExternalMove: Best improving feasible move, or None if none exist
        """
        # Sort moves according to quality improvement
        self.sort_move_solutions()
        
        # Return first feasible improving move
        for move_solution in self.MoveSolutions:
            if self.WorkerRouteFeasibilityCheck(move_solution.WorkerID, move_solution.WorkerRoute):
                if move_solution.Delta[0] < 0:  # Only accept improving moves
                    return move_solution
                    
        return None  # No feasible improving moves found


class TimeNeighborhood(BaseNeighborhood):
    """
    Base class for time-based neighborhood operations that involve multiple workers.
    
    This neighborhood class extends BaseNeighborhood to handle moves that affect
    multiple workers simultaneously, such as worker swaps or task reassignments.
    It provides specialized feasibility checking and move evaluation for scenarios
    where time constraints and worker coordination are critical.
    
    The class includes enhanced local search capabilities with detailed progress
    tracking and feasibility validation.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        """
        Initialize time-based neighborhood with problem data.
        
        Args:
            inputData: Problem instance data
            evaluationLogic: Solution evaluation component
            paretoSolutions: Pareto solution management
            rng: Random number generator
        """
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)

    def EvaluateMove(self, move: BaseMove) -> None:
        """
        Evaluate a move for time-based improvements.
        
        This method must be implemented by subclasses to define specific
        evaluation logic for different types of time-based improvements.
        
        Args:
            move: The move to evaluate
        """
        raise Exception('EvaluateMove() is not implemented for the abstract TimeNeighborhood class.')

    def MakeBestMove(self) -> BaseMove:
        """
        Select the best feasible move from evaluated candidates.
        
        This method sorts the evaluated moves and returns the first feasible move
        that satisfies worker safety constraints for all affected workers.
        
        Returns:
            BaseMove: Best feasible move, or None if no feasible moves exist
        """
        # Sort moves according to subclass-specific criteria
        self.sort_move_solutions()
        
        # Return first feasible move from sorted list
        for move_solution in self.MoveSolutions:
            if self.WorkerRouteFeasibilityCheck(move_solution.WorkerID1, move_solution.WorkerRoute1) and self.WorkerRouteFeasibilityCheck(move_solution.WorkerID2, move_solution.WorkerRoute2):
                return move_solution
                    
        return None  # No feasible moves found

    def sort_move_solutions(self):
        """
        Sort move solutions according to neighborhood-specific criteria.
        
        This method must be implemented by subclasses to define the sorting
        logic appropriate for each specific neighborhood type.
        """
        raise NotImplementedError('sort_move_solutions() must be implemented in the child class')

    def EvaluateMovesFirstImprovement(self) -> None:
        """
        Evaluate moves using first improvement strategy.
        
        This method evaluates moves sequentially until it finds the first
        feasible improving move, then stops the evaluation process.
        """
        for move in self.Moves:
            self.EvaluateMove(move)

            # Check feasibility before accepting the move
            if self.WorkerRouteFeasibilityCheck(move.RouteDayCohort):
                self.MoveSolutions.append(move)
                return None  # Found first feasible improving move
        
        return None  # No feasible improving moves found

    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> Solution:
        """
        Perform iterative local search with enhanced progress tracking.
        
        This method implements a hill-climbing local search algorithm specifically
        designed for time-based neighborhoods, with detailed progress reporting
        and feasibility validation at each iteration.
        
        Args:
            neighborhoodEvaluationStrategy: Strategy for evaluating moves
                                          ('BestImprovement' or 'FirstImprovement')
            solution: Starting solution for local search
            
        Returns:
            Solution: Best solution found during local search
        """
        hasSolutionImproved = True
        bestNeighborhoodSolution = deepcopy(solution)

        iterator = 1
        while hasSolutionImproved:
            print(f"Solution: {bestNeighborhoodSolution}")
            
            # Reset neighborhood state for new iteration
            self.Update() 
            self.DiscoverMoves(bestNeighborhoodSolution)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()

            if bestNeighborhoodMove is not None and bestNeighborhoodMove.Delta < 0:
                print(f"\nIteration: {iterator}")

                # Construct complete solution from the best move
                worker_route, machine_route, attachement_route = self.constructCompleteRoutes(bestNeighborhoodMove, bestNeighborhoodSolution)
                bestNeighborhoodSolution = Solution(worker_route, machine_route, attachement_route, self.data)
                self.evaluationLogic.evaluate(bestNeighborhoodSolution)

                # Denormalize delta details for display
                denorm = {}
                for detail, value in bestNeighborhoodMove.DeltaDetails.items():
                    if detail == 'attachment_distance':
                        denorm[detail] = value * (self.data.max_transport_distance - self.data.min_transport_distance) + self.data.min_transport_distance
                    elif detail == 'commute_distance':
                        denorm[detail] = value * (self.data.max_work_distance - self.data.min_work_distance) + self.data.min_work_distance
                    elif detail == 'transport_distance':
                        denorm[detail] = value * (self.data.max_transport_distance - self.data.min_transport_distance) + self.data.min_transport_distance
                    else:
                        denorm[detail] = value

                # Display improvement details
                for detail, value in denorm.items():
                    print(f"{detail}: {value}")

            else:
                # No improving move found - local optimum reached
                hasSolutionImproved = False

            # Validate solution feasibility
            feasible = bestNeighborhoodSolution.feasibility_check()
            if not feasible:
                raise KeyError(f"Feasibility Check failed in iteration {iterator}")

            iterator += 1

        return bestNeighborhoodSolution
    
    def SingleMove(self, solution: Solution, max_attempts: int = 100, local_rng=None) -> BaseMove:
        """
        Generate a single move for the given solution with optional custom RNG.
        
        This method creates and evaluates a single move from the neighborhood
        without exploring all possible moves. Supports custom random number
        generator for deterministic testing or specific sampling strategies.
        
        Args:
            solution: Current solution to generate move from
            max_attempts: Maximum attempts to find a valid move
            local_rng: Optional custom random number generator
            
        Returns:
            BaseMove: Single evaluated move, or None if no moves found
        """
        # Reset neighborhood state
        self.Update()
        
        # Generate a single move with appropriate RNG
        if local_rng is not None:
            move = self.MakeOneMove(solution, max_attempts, local_rng)
        else:
            move = self.MakeOneMove(solution, max_attempts)

        if move:
            self.EvaluateMove(move)
            return move
        else:
            # No moves found in current neighborhood
            pass


class ReplaceShiftAttachmentMove(BaseMove):
    """
    Represents a move that replaces an attachment assignment for an order item.
    
    This move type changes the attachment used for a specific order item
    while keeping the same worker and machine assignments. It explores
    alternative attachment allocations that might improve solution quality.
    """
    
    def __init__(self, attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_2, attachment_route_index_1, order_item_id):
        """
        Initialize the attachment replacement move.
        
        Args:
            attachment_id_1: ID of source attachment (currently serving order item)
            attachment_id_2: ID of target attachment (to receive order item)
            attachment_route_1: Current route of source attachment
            attachment_route_2: Current route of target attachment
            attachment_route_index_2: Insert position in target attachment route
            attachment_route_index_1: Remove position in source attachment route
            order_item_id: ID of order item being reassigned
        """
        # Copy original routes to avoid side effects
        self.AttachmentRoute1 = list(attachment_route_1)
        self.AttachmentRoute2 = list(attachment_route_2)

        # Store position indices for the move
        self.AttachmentRouteIndex1 = attachment_route_index_1
        self.AttachmentRouteIndex2 = attachment_route_index_2

        # Store order item and attachment IDs
        self.OrderItemID = order_item_id
        self.AttachmentID1 = attachment_id_1
        self.AttachmentID2 = attachment_id_2

        # Apply the move operations
        self.AttachmentRoute2.insert(self.AttachmentRouteIndex2, self.OrderItemID)  # Insert into target
        self.AttachmentRoute1.remove(self.OrderItemID)  # Remove from source


class ReplaceShiftAttachmentNeighborhood(TimeNeighborhood):
    """
    Neighborhood for attachment replacement moves between order items.
    
    This neighborhood explores moves that reassign order items from one
    attachment to another attachment of the same equipment type. It's useful
    for balancing attachment workloads and resolving attachment conflicts.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)
        self.Type = 'Replace_Shift_Attachment'

    def MakeBestMove(self) -> BaseMove:
        """
        Return the first move solution from the sorted list.
        
        Since attachment replacement moves are generally conservative,
        we accept the first feasible move without strict improvement criteria.
        
        Returns:
            ReplaceShiftAttachmentMove: First move in the sorted list, or None
        """
        # Sort moves according to quality criteria
        self.sort_move_solutions()
        
        # Return first move if any exist
        for move_solution in self.MoveSolutions:
            return move_solution
                    
        return None

    def DiscoverMoves(self, solution: Solution):
        """
        Generate all possible attachment replacement moves.
        
        This method finds all valid reassignments of order items between
        attachments of the same equipment type, considering precedence
        constraints and attachment availability.
        
        Args:
            solution: Current solution to analyze for moves
        """
        # Examine all attachment pairs for potential moves
        for attachment_id_1, attachment_route_1 in solution.route_plan_attachment.items():
            for attachment_id_2, attachment_route_2 in solution.route_plan_attachment.items():
                attachment_2_order_item_positions = {}

                # Skip empty source attachments (no order items to move)
                if len(attachment_route_1) == 0:
                    break
                
                # Get attachment objects for type checking
                attachment_1_obj = solution.data.attachments[attachment_id_1]
                attachment_2_obj = solution.data.attachments[attachment_id_2]

                # Only consider attachments of the same equipment type
                if attachment_1_obj.type != attachment_2_obj.type:
                    continue

                # Skip self-assignment (same attachment)
                if attachment_id_1 == attachment_id_2:
                    continue
                else:
                    attachment_2 = solution.data.attachments[attachment_id_2]

                    # Check each order item in source attachment for reassignment
                    for order_item_id_1 in attachment_route_1:
                        # Verify target attachment can handle this order item
                        attachment_2_possible_order_item_ids = [order_item_ids for orders in attachment_2.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_1 not in attachment_2_possible_order_item_ids:
                            continue

                        # Skip if order item already exists in target attachment
                        # (prevents duplicate assignments of same order item)
                        if order_item_id_1 in attachment_route_2:
                            continue

                        # Handle empty target attachment (insert at beginning)
                        if len(attachment_route_2) == 0:
                            attachment_2_order_item_positions[order_item_id_1] = [0, attachment_route_1.index(order_item_id_1)]
                            continue

                        # Find valid insertion positions based on precedence constraints
                        for order_item_id_2 in attachment_route_2:
                            # Check if order items have conflicting precedence relationships
                            if order_item_id_1 not in attachment_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in attachment_2.successor_ids[order_item_id_2]:
                                break

                            # Insert before order_item_id_2 if precedence allows
                            if order_item_id_1 in attachment_2.predecessor_ids[order_item_id_2]:
                                attachment_2_order_item_positions[order_item_id_1] = [attachment_route_2.index(order_item_id_2), attachment_route_1.index(order_item_id_1)]
                                break
                            
                            # Insert at end if order_item_id_1 is successor of last item
                            if len(attachment_route_2) == attachment_route_2.index(order_item_id_2) + 1:
                                if order_item_id_1 in attachment_2.successor_ids[order_item_id_2]:
                                    attachment_2_order_item_positions[order_item_id_1] = [attachment_route_2.index(order_item_id_2) + 1, attachment_route_1.index(order_item_id_1)]
                                    break

                # Create moves for all valid position assignments
                for order_item_id, attachment_route_index_2_1 in attachment_2_order_item_positions.items():
                    self.Moves.append(ReplaceShiftAttachmentMove(attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_2_1[0], attachment_route_index_2_1[1], order_item_id))

    def MakeOneMove(self, solution: Solution, max_attempts: int = 100, local_rng=None) -> BaseMove:
        """
        Generate a single random attachment replacement move.
        
        This method creates one random move by selecting source and target
        attachments and finding a valid order item reassignment between them.
        
        Procedure:
        1. Randomly select a source attachment with at least one order item
        2. Find target attachments with the same equipment type
        3. Randomly select a target attachment
        4. Choose a random order item from source that can be reassigned
        5. Find a valid insertion position in the target attachment
        
        Args:
            solution: Current solution
            max_attempts: Maximum number of attempts to find a valid move
            local_rng: Optional custom random number generator
            
        Returns:
            ReplaceShiftAttachmentMove: Random valid move, or None if none found
        """
        # Use appropriate random number generator
        rng = local_rng if local_rng is not None else self.RNG
        
        # Get all attachment IDs from the solution
        attachment_ids = list(solution.route_plan_attachment.keys())
 
        # Clear previous moves
        self.Moves.clear()
        attempts = 0

        # Group attachments by type for efficient pairing
        type_to_ids = defaultdict(list)
        for aid in attachment_ids:
            atype = solution.data.attachments[aid].type
            type_to_ids[atype].append(aid)

        # Generate all valid attachment pairs (same type, different ID)
        attachment_pairs = [
            (a1, a2)
            for ids in type_to_ids.values()
            for a1 in ids
            for a2 in ids
            if a1 != a2
        ]
        
        # Shuffle pairs for random selection order
        if local_rng is not None:
            local_rng.shuffle(attachment_pairs)
        else:
            self.RNG.shuffle(attachment_pairs)
  
        # Try each attachment pair until a valid move is found
        for attachment_id_1, attachment_id_2 in attachment_pairs:          
            attempts += 1
            if attempts > max_attempts:
                break
 
            # Get source attachment route (must have order items)
            attachment_route_1 = solution.route_plan_attachment[attachment_id_1]
            if len(attachment_route_1) == 0:
                continue

            # Get target attachment route and objects
            attachment_route_2 = solution.route_plan_attachment[attachment_id_2]
            attachment_1_obj = solution.data.attachments[attachment_id_1]
            attachment_2_obj = solution.data.attachments[attachment_id_2]
            
            valid_moves = []
            
            # Check each order item in source attachment for reassignment
            for order_item_id in attachment_route_1:
                # Verify target attachment can handle this order item
                attachment_2_possible_order_item_ids = [
                    oid for orders in attachment_2_obj.possible_order_item_ids.values() for oid in orders
                ]
                if order_item_id not in attachment_2_possible_order_item_ids:
                    continue
                
                # Skip if order item already exists in target attachment
                if order_item_id in attachment_route_2:
                    continue
                
                insertion_position = None
                
                # Handle empty target attachment
                if len(attachment_route_2) == 0:
                    insertion_position = [0, attachment_route_1.index(order_item_id)]
                else:
                    # Find valid insertion position based on precedence constraints
                    for order_item_id_2 in attachment_route_2:
                        # Check precedence compatibility
                        if order_item_id not in attachment_2_obj.predecessor_ids[order_item_id_2] and \
                        order_item_id not in attachment_2_obj.successor_ids[order_item_id_2]:
                            insertion_position = None
                            break
                            
                        # Insert before if predecessor relationship exists
                        if order_item_id in attachment_2_obj.predecessor_ids[order_item_id_2]:
                            insertion_position = [attachment_route_2.index(order_item_id_2), attachment_route_1.index(order_item_id)]
                            break
                            
                        # Insert at end if successor of last item
                        if attachment_route_2.index(order_item_id_2) == len(attachment_route_2) - 1:
                            if order_item_id in attachment_2_obj.successor_ids[order_item_id_2]:
                                insertion_position = [attachment_route_2.index(order_item_id_2) + 1, attachment_route_1.index(order_item_id)]
                                break
                
                # Create move if valid insertion position found
                if insertion_position is not None:
                    move = ReplaceShiftAttachmentMove(
                        attachment_id_1,
                        attachment_id_2,
                        attachment_route_1,
                        attachment_route_2,
                        insertion_position[0],  # insertion index in target route
                        insertion_position[1],  # reference index in source route
                        order_item_id
                    )
                    valid_moves.append(move)
            
            # Return random move from valid moves if any exist
            if valid_moves:
                if local_rng is not None:
                    return local_rng.choice(valid_moves)
                else:
                    return self.RNG.choice(valid_moves)
        
        # No valid move found after all attempts
        return None

    def EvaluateMove(self, move: ReplaceShiftAttachmentMove) -> None:
        """
        Evaluate the impact of an attachment replacement move.
        
        This method calculates the delta (change in objective value) that would
        result from applying the given attachment replacement move.
        
        Args:
            move: The attachment replacement move to evaluate
        """
        # Calculate and store the delta impact of this move
        move.setDelta(self.evaluationLogic.calculate_replace_shift_attachment_delta(move))

    def sort_move_solutions(self):
        """
        Sort evaluated moves by objective improvement.
        
        Sorts moves in ascending order of delta values to prioritize
        moves with the best (most negative) improvement.
        """
        # Sort by delta values: lowest (best improvement) first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    def constructCompleteRoutes(self, move: ReplaceShiftAttachmentMove, solution: Solution) -> tuple:
        """
        Construct complete route plans from an attachment replacement move.
        
        This method builds the complete worker, machine, and attachment route plans
        that would result from applying the attachment replacement move.
        
        Args:
            move: The attachment replacement move to apply
            solution: Current solution to modify
            
        Returns:
            tuple: (worker_route_plan, machine_route_plan, attachment_route_plan)
        """
        # Copy current route plans to avoid modifying original solution
        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

        # Apply attachment route changes from the move
        attachment_route_plan[move.AttachmentID1] = move.AttachmentRoute1
        attachment_route_plan[move.AttachmentID2] = move.AttachmentRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan


class SwapShiftAttachmentMove(BaseMove):
    """
    Represents a move that swaps order items between two attachments.
    
    This move type exchanges order items between two attachments of the same
    equipment type, potentially improving resource utilization and reducing
    conflicts in attachment scheduling.
    """
                    
    def __init__(self, attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_index_1, attachment_index_2, order_item_id_1, order_item_id_2, taken_index_1, taken_index_2):
        """
        Initialize the attachment swap move.
        
        Args:
            attachment_id_1: ID of first attachment
            attachment_id_2: ID of second attachment  
            attachment_route_1: Current route of first attachment
            attachment_route_2: Current route of second attachment
            attachment_index_1: Insert position for order_item_2 in route 1
            attachment_index_2: Insert position for order_item_1 in route 2
            order_item_id_1: Order item from attachment 1 to swap
            order_item_id_2: Order item from attachment 2 to swap
            taken_index_1: Original position of order_item_1 in route 1
            taken_index_2: Original position of order_item_2 in route 2
        """
        # Copy original routes to preserve state
        self.AttachmentRoute1 = list(attachment_route_1)
        self.AttachmentRoute2 = list(attachment_route_2)
        
        # Store original routes for reference
        self.AttachmentRoute1Original = list(attachment_route_1)
        self.AttachmentRoute2Original = list(attachment_route_2)

        # Store original positions of items being swapped
        self.AttachmentRouteTakenIndex1 = taken_index_1
        self.AttachmentRouteTakenIndex2 = taken_index_2

        # Store insert positions for swapped items
        self.AttachmentRouteIndex1 = attachment_index_1
        self.AttachmentRouteIndex2 = attachment_index_2

        # Store order item and attachment IDs
        self.OrderItemID1 = order_item_id_1
        self.OrderItemID2 = order_item_id_2
        self.AttachmentID1 = attachment_id_1
        self.AttachmentID2 = attachment_id_2

        # Apply the swap operations
        self.AttachmentRoute1.insert(self.AttachmentRouteIndex1, self.OrderItemID2)  # Insert item 2 into route 1
        self.AttachmentRoute2.insert(self.AttachmentRouteIndex2, self.OrderItemID1)  # Insert item 1 into route 2
        
        self.AttachmentRoute1.remove(self.OrderItemID1)  # Remove original item 1 from route 1
        self.AttachmentRoute2.remove(self.OrderItemID2)  # Remove original item 2 from route 2

    def __str__(self):
        """String representation of the attachment swap move for debugging."""
        return f'Attachment Route 1: {self.AttachmentRoute1}\nAttachment Route 2: {self.AttachmentRoute2} \n Attachment Route Index 1: {self.AttachmentRouteIndex1} \n Attachment Route Index 2: {self.AttachmentRouteIndex2} \n Order Item ID 1: {self.OrderItemID1} \n Order Item ID 2: {self.OrderItemID2} \n Attachment ID 1: {self.AttachmentID1} \n Attachment ID 2: {self.AttachmentID2}'


class SwapShiftAttachmentNeighborhood(TimeNeighborhood):
    """
    Neighborhood for attachment swap moves between order items.
    
    This neighborhood explores moves that swap order items between two
    attachments of the same equipment type. These swaps can help balance
    workloads and resolve scheduling conflicts by redistributing tasks
    between compatible attachments.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)
        self.Type = 'Swap_Shift_Attachment'

    def MakeBestMove(self) -> BaseMove:
        """
        Return the first move solution from the sorted list.
        
        Since attachment swap moves are exploratory, we accept the first
        feasible move without strict improvement criteria.
        
        Returns:
            SwapShiftAttachmentMove: First move in the sorted list, or None
        """
        # Sort moves according to quality criteria
        self.sort_move_solutions()
        
        # Return first move if any exist
        for move_solution in self.MoveSolutions:
            return move_solution
                    
        return None

    def DiscoverMoves(self, solution: Solution):
        """
        Generate all possible attachment swap moves.
        
        This method finds all valid swaps of order items between attachments
        of the same equipment type, considering precedence constraints and
        attachment compatibility for both order items.
        
        Args:
            solution: Current solution to analyze for moves
        """
        # Examine all attachment pairs for potential swaps
        for attachment_id_1, attachment_route_1 in solution.route_plan_attachment.items():
            for attachment_id_2, attachment_route_2 in solution.route_plan_attachment.items():
                # Track valid positions for swapping order items
                attachment_1_order_item_positions = {}
                attachment_2_order_item_positions = {}
                same_position_attachment_route_1 = {}
                same_position_attachment_route_2 = {}

                # Skip if either attachment route is empty
                if len(attachment_route_1) == 0:
                    break
                if len(attachment_route_2) == 0:
                    continue

                # Skip self-swapping (same attachment)
                if attachment_id_1 == attachment_id_2:
                    continue
                else:
                    # Get attachment objects for type checking
                    attachment_1 = solution.data.attachments[attachment_id_1]
                    attachment_2 = solution.data.attachments[attachment_id_2]

                    # Only consider attachments of the same equipment type
                    if attachment_1.type != attachment_2.type:
                        continue

                    # Check each order item in attachment 1 for swap potential
                    for order_item_id_1 in attachment_route_1:
                        # Verify attachment 2 can handle order_item_1
                        attachment_2_possible_order_item_ids = [order_item_ids for orders in attachment_2.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_1 not in attachment_2_possible_order_item_ids:
                            continue
                        else:
                            # Find valid insertion positions for order_item_1 in attachment 2
                            for index, order_item_id_2 in enumerate(attachment_route_2):
                                # Check precedence compatibility for insertion
                                if order_item_id_1 not in attachment_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in attachment_2.successor_ids[order_item_id_2]:
                                    # Handle precedence conflicts with position replacement
                                    # Check for order_items until the second last order item in the attachment route
                                    if len(attachment_route_2) > index + 1:
                                        # If order_item_id_1 collides with order_item_id_2 but is a predecessor of the next item,
                                        # it can replace order_item_id_2 in its position
                                        if order_item_id_1 in attachment_2.predecessor_ids[attachment_route_2[index + 1]]:
                                            same_position_attachment_route_2[order_item_id_1] = [index, order_item_id_2, attachment_route_1.index(order_item_id_1)]
                                            break
                                    # Check for the last order item in the attachment route of attachment 2
                                    elif len(attachment_route_2) == index + 1:
                                        # If order_item_id_1 collides with the last item but has valid successor relationship,
                                        # it can replace that item
                                        if order_item_id_1 in attachment_2.successor_ids.get(index - 1, []):
                                            same_position_attachment_route_2[order_item_id_1] = [index, order_item_id_2, attachment_route_1.index(order_item_id_1)]
                                            break
                                    break

                                # Standard insertion based on precedence relationships
                                # If order_item_id_1 is a predecessor of order_item_id_2, insert before it
                                if order_item_id_1 in attachment_2.predecessor_ids[order_item_id_2]:
                                    attachment_2_order_item_positions[order_item_id_1] = [index, attachment_route_1.index(order_item_id_1)]
                                    break

                                # If order_item_id_1 is a successor of the last order_item, insert at the end
                                if len(attachment_route_2) == index + 1:
                                    if order_item_id_1 in attachment_2.successor_ids[order_item_id_2]:
                                        attachment_2_order_item_positions[order_item_id_1] = [index + 1, attachment_route_1.index(order_item_id_1)]
                                        break

                    # Check each order item in attachment 2 for insertion in attachment 1
                    for order_item_id_2 in attachment_route_2:
                        # Verify attachment 1 can handle order_item_2
                        attachment_1_possible_order_item_ids = [order_item_ids for orders in attachment_1.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_2 not in attachment_1_possible_order_item_ids:
                            continue
                        else:
                            # Find valid insertion positions for order_item_2 in attachment 1
                            for index, order_item_id_1 in enumerate(attachment_route_1):
                                # Check precedence compatibility for insertion
                                if order_item_id_2 not in attachment_1.predecessor_ids[order_item_id_1] and order_item_id_2 not in attachment_1.successor_ids[order_item_id_1]:
                                    # Handle precedence conflicts with position replacement
                                    # Check for order_items until the second last order item in the attachment route
                                    if len(attachment_route_1) > index + 1:
                                        # If order_item_id_2 collides with order_item_id_1 but is a predecessor of the next item,
                                        # it can replace order_item_id_1 in its position
                                        if order_item_id_2 in attachment_1.predecessor_ids[attachment_route_1[index + 1]]:
                                            same_position_attachment_route_1[order_item_id_2] = [index, order_item_id_1, attachment_route_2.index(order_item_id_2)]
                                            break
                                    # Check for the last order item in the attachment route of attachment 1
                                    elif len(attachment_route_1) == index + 1:
                                        # If order_item_id_2 collides with the last item but has valid successor relationship,
                                        # it can replace that item
                                        if order_item_id_2 in attachment_1.successor_ids.get(index - 1, []):
                                            same_position_attachment_route_1[order_item_id_2] = [index, order_item_id_1, attachment_route_2.index(order_item_id_2)]
                                            break
                                    break

                                # Standard insertion based on precedence relationships
                                # If order_item_id_2 is a predecessor of order_item_id_1, insert before it
                                if order_item_id_2 in attachment_1.predecessor_ids[order_item_id_1]:
                                    attachment_1_order_item_positions[order_item_id_2] = [index, attachment_route_2.index(order_item_id_2)]
                                    break

                                # If order_item_id_2 is a successor of the last order_item, insert at the end
                                if len(attachment_route_1) == index + 1:
                                    if order_item_id_2 in attachment_1.successor_ids[order_item_id_1]:
                                        attachment_1_order_item_positions[order_item_id_2] = [index + 1, attachment_route_2.index(order_item_id_2)]
                                        break
                    
                    # Create swap moves based on identified valid positions
                    # Swaps where both order items go into different positions
                    for order_item_id_2, attachment_route_index_1_taken_index_2 in attachment_1_order_item_positions.items():
                        for order_item_id_1, attachment_route_index_2_taken_index_1 in attachment_2_order_item_positions.items():
                            self.Moves.append(SwapShiftAttachmentMove(attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_1_taken_index_2[0], attachment_route_index_2_taken_index_1[0], order_item_id_1, order_item_id_2, attachment_route_index_2_taken_index_1[1], attachment_route_index_1_taken_index_2[1]))
                    
                    # Swaps where both order items go into the same position (replace each other)
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
                    
                    # The reverse case: one order item replaces another in same position
                    for order_item_id_1, attachment_route_index_2_and_order_item_id_2_and_taken_index_1 in same_position_attachment_route_2.items():
                        for order_item_id_2, attachment_route_index_1_taken_index_2 in attachment_1_order_item_positions.items():
                            if order_item_id_2 == attachment_route_index_2_and_order_item_id_2_and_taken_index_1[1]:
                                self.Moves.append(SwapShiftAttachmentMove(attachment_id_1, attachment_id_2, attachment_route_1, attachment_route_2, attachment_route_index_1_taken_index_2[0], attachment_route_index_2_and_order_item_id_2_and_taken_index_1[0], order_item_id_1, order_item_id_2, attachment_route_index_2_and_order_item_id_2_and_taken_index_1[2], attachment_route_index_1_taken_index_2[1]))

    def MakeOneMove(self, solution: Solution, max_attempts: int = 100, local_rng=None) -> BaseMove:
        """
        Generate a single random attachment swap move.
        
        This method creates one random swap move by selecting compatible
        attachments and finding valid order item exchanges between them.
        
        Procedure:
        1. Randomly select two attachments with non-empty routes and same equipment type
        2. Build candidate dictionaries for potential swap positions considering precedence
        3. Generate possible swap moves covering different position scenarios
        4. Return one random move if any valid moves are found
        
        Args:
            solution: Current solution
            max_attempts: Maximum number of attempts to find a valid move
            local_rng: Optional custom random number generator
            
        Returns:
            SwapShiftAttachmentMove: Random valid swap move, or None if none found
        """
        # Use appropriate random number generator
        rng = local_rng if local_rng is not None else self.RNG
        
        # Clear any previously stored moves
        self.Moves.clear()
        attempts = 0

        # Get attachments with non-empty routes
        attachment_ids = [aid for aid, route in solution.route_plan_attachment.items() if route]

        # Generate pairs of attachments with same equipment type
        attachment_pairs = [
            (id1, id2)
            for i, id1 in enumerate(attachment_ids)
            for id2 in attachment_ids[i+1:]
            if solution.data.attachments[id1].type == solution.data.attachments[id2].type
        ]

        # Shuffle pairs for random selection order
        rng.shuffle(attachment_pairs)

        # Try each attachment pair until a valid move is found
        for attachment_id_1, attachment_id_2 in attachment_pairs:
            attempts += 1
            if attempts > max_attempts:
                break

            # Get attachment routes and objects
            attachment_route_1 = solution.route_plan_attachment[attachment_id_1]
            attachment_route_2 = solution.route_plan_attachment[attachment_id_2]
            attachment_1 = solution.data.attachments[attachment_id_1]
            attachment_2 = solution.data.attachments[attachment_id_2]

            # Initialize candidate position dictionaries
            attachment_1_order_item_positions = {}  # For order items from route_2 to insert in route_1
            attachment_2_order_item_positions = {}  # For order items from route_1 to insert in route_2
            same_position_attachment_route_1 = {}   # For position replacement swaps in route_1
            same_position_attachment_route_2 = {}   # For position replacement swaps in route_2

            # Analyze insertion possibilities for order items from attachment_1 to attachment_2
            for order_item_id_1 in attachment_route_1:
                # Check if attachment_2 can handle this order item
                possible_ids_2 = [oid for orders in attachment_2.possible_order_item_ids.values() for oid in orders]
                if order_item_id_1 not in possible_ids_2:
                    continue
                else:
                    # Find valid insertion positions in attachment_2
                    for index, order_item_id_2 in enumerate(attachment_route_2):
                        # Handle precedence conflicts and position assignments
                        if order_item_id_1 not in attachment_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in attachment_2.successor_ids[order_item_id_2]:
                            # Check for replacement opportunities with adjacent items
                            if len(attachment_route_2) > index + 1:
                                if order_item_id_1 in attachment_2.predecessor_ids[attachment_route_2[index + 1]]:
                                    same_position_attachment_route_2[order_item_id_1] = [index, order_item_id_2, attachment_route_1.index(order_item_id_1)]
                                    break
                            elif len(attachment_route_2) == index + 1:
                                if order_item_id_1 in attachment_2.successor_ids.get(order_item_id_2, []):
                                    same_position_attachment_route_2[order_item_id_1] = [index, order_item_id_2, attachment_route_1.index(order_item_id_1)]
                                    break
                            break
                        # If order_item_id_1 is a predecessor of order_item_id_2, record the insertion position
                        if order_item_id_1 in attachment_2.predecessor_ids[order_item_id_2]:
                            attachment_2_order_item_positions[order_item_id_1] = [index, attachment_route_1.index(order_item_id_1)]
                            break
                        # If at the end of attachment_route_2 and order_item_id_1 is a successor, insert at the end
                        if index == len(attachment_route_2) - 1:
                            if order_item_id_1 in attachment_2.successor_ids[order_item_id_2]:
                                attachment_2_order_item_positions[order_item_id_1] = [index + 1, attachment_route_1.index(order_item_id_1)]
                                break

            # Analyze insertion possibilities for order items from attachment_2 to attachment_1
            for order_item_id_2 in attachment_route_2:
                # Check if attachment_1 can handle this order item
                possible_ids_1 = [oid for orders in attachment_1.possible_order_item_ids.values() for oid in orders]
                if order_item_id_2 not in possible_ids_1:
                    continue
                else:
                    # Find valid insertion positions in attachment_1
                    for index, order_item_id_1 in enumerate(attachment_route_1):
                        # Handle precedence conflicts and position assignments
                        if order_item_id_2 not in attachment_1.predecessor_ids[order_item_id_1] and order_item_id_2 not in attachment_1.successor_ids[order_item_id_1]:
                            # Check for replacement opportunities with adjacent items
                            if len(attachment_route_1) > index + 1:
                                if order_item_id_2 in attachment_1.predecessor_ids[attachment_route_1[index + 1]]:
                                    same_position_attachment_route_1[order_item_id_2] = [index, order_item_id_1, attachment_route_2.index(order_item_id_2)]
                                    break
                            elif len(attachment_route_1) == index + 1:
                                if order_item_id_2 in attachment_1.successor_ids.get(order_item_id_1, []):
                                    same_position_attachment_route_1[order_item_id_2] = [index, order_item_id_1, attachment_route_2.index(order_item_id_2)]
                                    break
                            break
                        # If order_item_id_2 is a predecessor of order_item_id_1, record the insertion position
                        if order_item_id_2 in attachment_1.predecessor_ids[order_item_id_1]:
                            attachment_1_order_item_positions[order_item_id_2] = [index, attachment_route_2.index(order_item_id_2)]
                            break
                        # If at the end of attachment_route_1 and order_item_id_2 is a successor, insert at the end
                        if index == len(attachment_route_1) - 1:
                            if order_item_id_2 in attachment_1.successor_ids[order_item_id_1]:
                                attachment_1_order_item_positions[order_item_id_2] = [index + 1, attachment_route_2.index(order_item_id_2)]
                                break

            # Generate all possible swap moves from identified positions
            valid_moves = []
            
            # Case 1: Swap moves where both order items are inserted at different positions
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
            
            # Case 2: Swap moves where both order items replace each other in same positions
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
            
            # Case 3: Mixed swaps where one item replaces and other inserts at different position
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
            
            # Case 4: Reverse mixed swaps
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

            # Return first valid move found
            if valid_moves:
                return rng.choice(valid_moves)
            
        # No valid moves found after all attempts
        return None

    def EvaluateMove(self, move: SwapShiftAttachmentMove) -> None:
        """
        Evaluate the impact of an attachment swap move.
        
        This method calculates the delta (change in objective value) that would
        result from applying the given attachment swap move.
        
        Args:
            move: The attachment swap move to evaluate
        """
        # Calculate and store the delta impact of this move
        move.setDelta(self.evaluationLogic.calculate_swap_shift_attachment_delta(move))

    def sort_move_solutions(self):
        """
        Sort evaluated moves by objective improvement.
        
        Sorts moves in ascending order of delta values to prioritize
        moves with the best (most negative) improvement.
        """
        # Sort by delta values: lowest (best improvement) first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    def constructCompleteRoutes(self, move: SwapShiftAttachmentMove, solution: Solution) -> tuple:
        """
        Construct complete route plans from an attachment swap move.
        
        This method builds the complete worker, machine, and attachment route plans
        that would result from applying the attachment swap move.
        
        Args:
            move: The attachment swap move to apply
            solution: Current solution to modify
            
        Returns:
            tuple: (worker_route_plan, machine_route_plan, attachment_route_plan)
        """
        # Copy current route plans to avoid modifying original solution
        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

        # Apply attachment route changes from the move
        attachment_route_plan[move.AttachmentID1] = move.AttachmentRoute1
        attachment_route_plan[move.AttachmentID2] = move.AttachmentRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan


class ReplaceShiftMachineMove(BaseMove):
    """
    Represents a move that replaces a machine assignment for an order item.
    
    This move type changes the machine used for a specific order item
    while keeping the same worker assignment. It explores alternative
    machine allocations that might improve solution quality.
    """
    
    def __init__(self, machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_2, machine_route_index_1, order_item_id, worker_id):
        """
        Initialize the machine replacement move.
        
        Args:
            machine_id_1: ID of source machine (currently serving order item)
            machine_id_2: ID of target machine (to receive order item)
            machine_route_1: Current route of source machine
            machine_route_2: Current route of target machine
            machine_route_index_2: Insert position in target machine route
            machine_route_index_1: Remove position in source machine route
            order_item_id: ID of order item being reassigned
            worker_id: ID of worker associated with this move
        """
        # Copy original routes to avoid side effects
        self.MachineRoute1 = list(machine_route_1)
        self.MachineRoute2 = list(machine_route_2)

        # Store position indices for the move
        self.MachineRouteIndex1 = machine_route_index_1
        self.MachineRouteIndex2 = machine_route_index_2

        # Store order item, machine, and worker IDs
        self.OrderItemID = order_item_id
        self.MachineID1 = machine_id_1
        self.MachineID2 = machine_id_2
        self.WorkerID = worker_id

        # Apply the move operations
        self.MachineRoute2.insert(self.MachineRouteIndex2, self.OrderItemID)  # Insert into target
        self.MachineRoute1.remove(self.OrderItemID)  # Remove from source


class ReplaceShiftMachineNeighborhood(TimeNeighborhood):
    """
    Neighborhood for machine replacement moves between order items.
    
    This neighborhood explores moves that reassign order items from one
    machine to another compatible machine. It's useful for balancing
    machine workloads and resolving machine conflicts.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)
        self.Type = 'Replace_Shift_Machine'

    def MakeBestMove(self) -> BaseMove:
        """
        Return the first move solution from the sorted list.
        
        Since machine replacement moves are generally conservative,
        we accept the first feasible move without strict improvement criteria.
        
        Returns:
            ReplaceShiftMachineMove: First move in the sorted list, or None
        """
        # Sort moves according to quality criteria
        self.sort_move_solutions()
        
        # Return first move if any exist
        for move_solution in self.MoveSolutions:
            return move_solution
                    
        return None

    def DiscoverMoves(self, solution: Solution):
        """
        Generate all possible machine replacement moves.
        
        This method finds all valid reassignments of order items between
        machines, considering machine compatibility and precedence constraints.
        
        Args:
            solution: Current solution to analyze for moves
        """
        # Examine all machine pairs for potential moves
        for machine_id_1, machine_route_1 in solution.route_plan_machine.items():
            for machine_id_2, machine_route_2 in solution.route_plan_machine.items():
                machine_2_order_item_positions = {}

                # Skip empty source machines (no order items to move)
                if len(machine_route_1) == 0:
                    break

                # Skip self-assignment (same machine)
                if machine_id_1 == machine_id_2:
                    continue
                else:
                    # Get target machine object for compatibility checking
                    machine_2 = solution.data.machines[machine_id_2]

                    # Check each order item in source machine for reassignment
                    for order_item_id_1 in machine_route_1:
                        # Verify target machine can handle this order item
                        machine_2_possible_order_item_ids = [order_item_ids for orders in machine_2.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_1 not in machine_2_possible_order_item_ids:
                            continue

                        # Handle empty target machine (insert at beginning)
                        if len(machine_route_2) == 0:
                            machine_2_order_item_positions[order_item_id_1] = [0, machine_route_1.index(order_item_id_1)]
                            continue

                        # Find valid insertion positions based on precedence constraints
                        for order_item_id_2 in machine_route_2:
                            # Check if order items have conflicting precedence relationships
                            if order_item_id_1 not in machine_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in machine_2.successor_ids[order_item_id_2]:
                                break

                            # Insert before order_item_id_2 if precedence allows
                            if order_item_id_1 in machine_2.predecessor_ids[order_item_id_2]:
                                machine_2_order_item_positions[order_item_id_1] = [machine_route_2.index(order_item_id_2), machine_route_1.index(order_item_id_1)]
                                break

                            # Insert at end if order_item_id_1 is successor of last item
                            if len(machine_route_2) == machine_route_2.index(order_item_id_2) + 1:
                                if order_item_id_1 in machine_2.successor_ids[order_item_id_2]:
                                    machine_2_order_item_positions[order_item_id_1] = [machine_route_2.index(order_item_id_2) + 1, machine_route_1.index(order_item_id_1)]
                                    break

                # Create moves for all valid position assignments
                for order_item_id, machine_route_index_2_1 in machine_2_order_item_positions.items():
                    # Find the worker associated with this order item
                    worker_id = [worker_id for worker_id, worker_route in solution.route_plan_worker.items() if order_item_id in worker_route][0]
                    self.Moves.append(ReplaceShiftMachineMove(machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_2_1[0], machine_route_index_2_1[1], order_item_id, worker_id))

    def MakeOneMove(self, solution: Solution, max_attempts: int = 100, local_rng=None) -> BaseMove:
        """
        Generate a single random machine replacement move.
        
        This method creates one random move by selecting source and target
        machines and finding a valid order item reassignment between them.
        
        Procedure:
        1. Randomly select two machines with compatible types
        2. Choose a random order item from source that can be reassigned
        3. Find a valid insertion position in the target machine
        4. Return the move with associated worker information
        
        Args:
            solution: Current solution
            max_attempts: Maximum number of attempts to find a valid move
            local_rng: Optional custom random number generator
            
        Returns:
            ReplaceShiftMachineMove: Random valid move, or None if none found
        """
        # Use appropriate random number generator
        rng = local_rng if local_rng is not None else self.RNG
        
        # Get all machine IDs from the solution
        machine_ids = list(solution.route_plan_machine.keys())
        
        # Clear previous moves
        self.Moves.clear()
        attempts = 0

        # Generate pairs of machines with same type but different IDs
        machine_pairs = [(m1, m2)
                        for m1 in machine_ids
                        for m2 in machine_ids
                        if m1 != m2 and solution.data.machines[m1].type == solution.data.machines[m2].type]
        
        # Shuffle pairs for random selection order
        rng.shuffle(machine_pairs)
  
        # Try each machine pair until a valid move is found
        for machine_id_1, machine_id_2 in machine_pairs:
            attempts += 1
            if attempts > max_attempts:
                break

            # Get source machine route (must have order items)
            machine_route_1 = solution.route_plan_machine[machine_id_1]
            if len(machine_route_1) == 0:
                continue
                
            # Get target machine route and object
            machine_route_2 = solution.route_plan_machine[machine_id_2]
            machine_2 = solution.data.machines[machine_id_2]
            
            valid_moves = []
            
            # Check each order item in source machine for reassignment
            for order_item_id in machine_route_1:
                # Verify target machine can handle this order item
                machine_2_possible_order_item_ids = [
                    oid for orders in machine_2.possible_order_item_ids.values() for oid in orders
                ]
                if order_item_id not in machine_2_possible_order_item_ids:
                    continue
                
                insertion_position = None
                
                # Handle empty target machine
                if len(machine_route_2) == 0:
                    insertion_position = [0, machine_route_1.index(order_item_id)]
                else:
                    # Find valid insertion position based on precedence constraints
                    for order_item_id_2 in machine_route_2:
                        # Check precedence compatibility
                        if order_item_id not in machine_2.predecessor_ids[order_item_id_2] and \
                        order_item_id not in machine_2.successor_ids[order_item_id_2]:
                            insertion_position = None
                            break
                            
                        # Insert before if predecessor relationship exists
                        if order_item_id in machine_2.predecessor_ids[order_item_id_2]:
                            insertion_position = [machine_route_2.index(order_item_id_2), machine_route_1.index(order_item_id)]
                            break
                            
                        # Insert at end if successor of last item
                        if machine_route_2.index(order_item_id_2) == len(machine_route_2) - 1:
                            if order_item_id in machine_2.successor_ids[order_item_id_2]:
                                insertion_position = [machine_route_2.index(order_item_id_2) + 1, machine_route_1.index(order_item_id)]
                                break
                
                # Create move if valid insertion position found
                if insertion_position is not None:
                    # Find the worker associated with this order item
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
            
            # Return random move from valid moves if any exist
            if valid_moves:
                return rng.choice(valid_moves)
        
        # No valid move found after all attempts
        return None

    def EvaluateMove(self, move: ReplaceShiftMachineMove) -> None:
        """
        Evaluate the impact of a machine replacement move.
        
        This method calculates the delta (change in objective value) that would
        result from applying the given machine replacement move.
        
        Args:
            move: The machine replacement move to evaluate
        """
        # Calculate and store the delta impact of this move
        move.setDelta(self.evaluationLogic.calculate_replace_shift_machine_delta(move))

    def sort_move_solutions(self):
        """
        Sort evaluated moves by objective improvement.
        
        Sorts moves in ascending order of delta values to prioritize
        moves with the best (most negative) improvement.
        """
        # Sort by delta values: lowest (best improvement) first
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    def constructCompleteRoutes(self, move: ReplaceShiftMachineMove, solution: Solution) -> tuple:
        """
        Construct complete route plans from a machine replacement move.
        
        This method builds the complete worker, machine, and attachment route plans
        that would result from applying the machine replacement move.
        
        Args:
            move: The machine replacement move to apply
            solution: Current solution to modify
            
        Returns:
            tuple: (worker_route_plan, machine_route_plan, attachment_route_plan)
        """
        # Copy current route plans to avoid modifying original solution
        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

        # Apply machine route changes from the move
        machine_route_plan[move.MachineID1] = move.MachineRoute1
        machine_route_plan[move.MachineID2] = move.MachineRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan


class SwapShiftMachineMove(BaseMove):
    """
    Represents a move that swaps order items between two machines.
    
    This move type exchanges order items between two machines of the same
    equipment type, potentially improving resource utilization and reducing
    conflicts in machine scheduling.
    """
    
    def __init__(self, machine_id_1, machine_id_2, machine_route_1, machine_route_2, machine_route_index_1, machine_route_index_2, order_item_id_1, order_item_id_2, worker_id_1, worker_id_2, taken_index_1, taken_index_2):
        """
        Initialize the machine swap move.
        
        Args:
            machine_id_1: ID of first machine
            machine_id_2: ID of second machine
            machine_route_1: Current route of first machine
            machine_route_2: Current route of second machine
            machine_route_index_1: Insert position for order_item_2 in route 1
            machine_route_index_2: Insert position for order_item_1 in route 2
            order_item_id_1: Order item from machine 1 to swap
            order_item_id_2: Order item from machine 2 to swap
            worker_id_1: Worker associated with order_item_1
            worker_id_2: Worker associated with order_item_2
            taken_index_1: Original position of order_item_1 in route 1
            taken_index_2: Original position of order_item_2 in route 2
        """
        # Copy original routes to preserve state
        self.MachineRoute1 = list(machine_route_1)
        self.MachineRoute2 = list(machine_route_2)
        
        # Store original routes for reference
        self.MachineRoute1Original = list(machine_route_1)
        self.MachineRoute2Original = list(machine_route_2)

        # Store original positions of items being swapped
        self.MachineRouteTakenIndex1 = taken_index_1
        self.MachineRouteTakenIndex2 = taken_index_2

        # Store insert positions for swapped items
        self.MachineRouteIndex1 = machine_route_index_1
        self.MachineRouteIndex2 = machine_route_index_2

        # Store order item and machine IDs
        self.OrderItemID1 = order_item_id_1
        self.OrderItemID2 = order_item_id_2
        self.MachineID1 = machine_id_1
        self.MachineID2 = machine_id_2

        # Apply the swap operations
        self.MachineRoute1.insert(self.MachineRouteIndex1, self.OrderItemID2)  # Insert item 2 into route 1
        self.MachineRoute2.insert(self.MachineRouteIndex2, self.OrderItemID1)  # Insert item 1 into route 2
        
        self.MachineRoute1.remove(self.OrderItemID1)  # Remove original item 1 from route 1
        self.MachineRoute2.remove(self.OrderItemID2)  # Remove original item 2 from route 2

        # Store worker IDs
        self.WorkerID1 = worker_id_1
        self.WorkerID2 = worker_id_2

    def __str__(self):
        """String representation of the machine swap move for debugging."""
        return f'Machine Route 1: {self.MachineRoute1}\nMachine Route 2: {self.MachineRoute2} \n Machine Route Index 1: {self.MachineRouteIndex1} \n Machine Route Index 2: {self.MachineRouteIndex2} \n Order Item ID 1: {self.OrderItemID1} \n Order Item ID 2: {self.OrderItemID2} \n Machine ID 1: {self.MachineID1} \n Machine ID 2: {self.MachineID2}'


class SwapShiftMachineNeighborhood(TimeNeighborhood):
    """
    Neighborhood for machine swap moves between order items.
    
    This neighborhood explores moves that swap order items between two
    machines of the same equipment type. These swaps can help balance
    machine workloads and resolve scheduling conflicts by redistributing
    tasks between compatible machines.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)
        self.Type = 'Swap_Shift_Machine'

    def MakeBestMove(self) -> BaseMove:
        """
        Return the first move solution from the sorted list.
        
        Since machine swap moves are exploratory, we accept the first
        feasible move without strict improvement criteria.
        
        Returns:
            SwapShiftMachineMove: First move in the sorted list, or None
        """
        # Sort moves according to quality criteria
        self.sort_move_solutions()
        
        # Return first move if any exist
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
    
    
    def MakeOneMove(self, solution: Solution, max_attempts: int = 100, local_rng = None) -> BaseMove:
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
        
        machine_ids = [mid for mid, route in solution.route_plan_machine.items() if route]

        machine_pairs = [
            (id1, id2)
            for i, id1 in enumerate(machine_ids)
            for id2 in machine_ids[i+1:]
            if solution.data.machines[id1].type == solution.data.machines[id2].type
        ]

        if local_rng is not None:
            local_rng.shuffle(machine_pairs)
        else:
            self.RNG.shuffle(machine_pairs)  # Shuffle the pairs to ensure randomness

        self.Moves.clear()  # Clear any previously stored moves
        attempts = 0

        for machine_id_1, machine_id_2 in machine_pairs:

            attempts += 1
            if attempts > max_attempts:
                break

            machine_route_1 = solution.route_plan_machine[machine_id_1]
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
                if local_rng is not None:
                    return local_rng.choice(valid_moves)
                else:
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


'''





























































































































































































































































































'''



class ReplaceShiftWorkerMove(BaseMove):
    """
    Represents a move that replaces a worker assignment for an order item.
    
    This move type changes the worker used for a specific order item
    while keeping the same machine assignment. It explores alternative
    worker allocations that might improve solution quality.
    """
    
    def __init__(self, worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index, order_item_id, machine_id):
        """
        Initialize the worker replacement move.
        
        Args:
            worker_id_1: ID of source worker (currently serving order item)
            worker_id_2: ID of target worker (to receive order item)
            worker_route_1: Current route of source worker
            worker_route_2: Current route of target worker
            worker_route_index: Insert position in target worker route
            order_item_id: ID of order item being reassigned
            machine_id: ID of machine associated with this move
        """
        # Copy original routes to avoid side effects
        self.WorkerRoute1 = list(worker_route_1)
        self.WorkerRoute2 = list(worker_route_2)

        # Store position index for the move
        self.WorkerRouteIndex = worker_route_index

        # Store order item, worker, and machine IDs
        self.OrderItemID = order_item_id
        self.WorkerID1 = worker_id_1
        self.WorkerID2 = worker_id_2
        self.MachineID = machine_id

        # Apply the move operations
        self.WorkerRoute2.insert(self.WorkerRouteIndex, self.OrderItemID)  # Insert into target
        self.WorkerRoute1.remove(self.OrderItemID)  # Remove from source


class ReplaceShiftWorkerNeighborhood(TimeNeighborhood):
    """
    Neighborhood for worker replacement moves between order items.
    
    This neighborhood explores moves that reassign order items from one
    worker to another compatible worker. It's useful for balancing
    worker workloads and resolving worker conflicts.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)
        self.Type = 'Replace_Shift_Worker'

    def DiscoverMoves(self, solution: Solution):
        """
        Generate all possible worker replacement moves.
        
        This method finds all valid reassignments of order items between
        workers, considering worker compatibility and precedence constraints.
        
        Args:
            solution: Current solution to analyze for moves
        """
        # Examine all worker pairs for potential moves
        for worker_id_1, worker_route_1 in solution.route_plan_worker.items():
            for worker_id_2, worker_route_2 in solution.route_plan_worker.items():
                worker_2_order_item_positions = {}

                # Skip empty source workers (no order items to move)
                if len(worker_route_1) == 0:
                    break

                # Skip self-assignment (same worker)
                if worker_id_1 == worker_id_2:
                    continue
                else:
                    # Get target worker object for compatibility checking
                    worker_2 = solution.data.workers[worker_id_2]

                    # Check each order item in source worker for reassignment
                    for order_item_id_1 in worker_route_1:
                        # Verify target worker can handle this order item
                        worker_2_possible_order_item_ids = [order_item_ids for orders in worker_2.possible_order_item_ids.values() for order_item_ids in orders]
                        if order_item_id_1 not in worker_2_possible_order_item_ids:
                            continue
                        # Check working hour constraints for target worker
                        if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                            continue
                        
                        # Handle empty target worker route (simple insertion at start)
                        if len(worker_route_2) == 0:
                            worker_2_order_item_positions[order_item_id_1] = 0
                            continue

                        # Find valid insertion positions based on precedence constraints
                        for order_item_id_2 in worker_route_2:
                            # Check if order items conflict (neither predecessor nor successor)
                            if order_item_id_1 not in worker_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in worker_2.successor_ids[order_item_id_2]:
                                break

                            # Insert before order_item_id_2 if it's a predecessor
                            if order_item_id_1 in worker_2.predecessor_ids[order_item_id_2]:
                                worker_2_order_item_positions[order_item_id_1] = worker_route_2.index(order_item_id_2)
                                break

                            # Insert at end if it's a successor of the last item
                            if len(worker_route_2) == worker_route_2.index(order_item_id_2) + 1:
                                if order_item_id_1 in worker_2.successor_ids[order_item_id_2]:
                                    worker_2_order_item_positions[order_item_id_1] = worker_route_2.index(order_item_id_2) + 1
                                    break

                # Create moves for all valid positions found
                for order_item_id, worker_route_index_2 in worker_2_order_item_positions.items():
                    # Find associated machine for this order item
                    machine_id = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id in machine_route][0]                 
                    self.Moves.append(ReplaceShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_2, order_item_id, machine_id))


    def MakeOneMove(self, solution: Solution, max_attempts: int = 100, local_rng = None) -> BaseMove:
        """
        Randomly selects a valid worker replacement move.
        
        This method:
        1. Randomly selects worker pairs to explore moves
        2. Validates feasibility constraints (capacity, skills, working hours)
        3. Ensures precedence constraints are satisfied
        4. Returns a feasible move or None if none found
        
        Args:
            solution: Current solution to modify
            max_attempts: Maximum attempts before giving up
            local_rng: Random number generator (optional)
            
        Returns:
            BaseMove: Valid worker replacement move or None
        """
        # Generate all possible worker pairs (excluding self-pairs)
        worker_ids = list(solution.route_plan_worker.keys())
        worker_id_pairs = [(w1, w2) for w1 in worker_ids for w2 in worker_ids if w1 != w2]

        # Randomize pair selection order
        if local_rng is not None:
            local_rng.shuffle(worker_id_pairs)
        else:
            self.RNG.shuffle(worker_id_pairs)

        # Clear previous moves and reset attempt counter
        self.Moves.clear()
        attempts = 0

        # Explore worker pairs until valid moves found or max attempts reached
        for worker_id_1, worker_id_2 in worker_id_pairs:
            attempts += 1
            if attempts > max_attempts:
                break

            # Skip workers with empty routes (no order items to move)
            if not solution.route_plan_worker[worker_id_1]:
                continue

            # Get route information for both workers
            worker_route_1 = solution.route_plan_worker[worker_id_1]
            worker_route_2 = solution.route_plan_worker[worker_id_2]
            worker_2 = solution.data.workers[worker_id_2]

            # Examine each order item in source worker for potential reassignment
            for order_item_id in worker_route_1:
                # Check if target worker can handle this order item type
                worker_2_possible_order_item_ids = [
                    oid for orders in worker_2.possible_order_item_ids.values() for oid in orders
                ]
                if order_item_id not in worker_2_possible_order_item_ids:
                    continue

                # Verify working hour constraints
                if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id].duration > self.data._max_working_hours:
                    continue

                insertion_position = None

                # Handle empty target worker route
                if not worker_route_2:
                    insertion_position = 0
                else:
                    # Find valid insertion position based on precedence constraints
                    for order_item_id_2 in worker_route_2:
                        # Check precedence compatibility
                        if order_item_id not in worker_2.predecessor_ids[order_item_id_2] and order_item_id not in worker_2.successor_ids[order_item_id_2]:
                            insertion_position = None
                            break
                        
                        # Insert before current item if it's a predecessor
                        if order_item_id in worker_2.predecessor_ids[order_item_id_2]:
                            insertion_position = worker_route_2.index(order_item_id_2)
                            break
                        
                        # Insert at end if it's a successor of the last item
                        if worker_route_2.index(order_item_id_2) == len(worker_route_2) - 1:
                            if order_item_id in worker_2.successor_ids[order_item_id_2]:
                                insertion_position = len(worker_route_2)
                                break

                # Create move if valid insertion position found
                if insertion_position is not None:
                    # Find associated machine for this order item
                    machine_id = None
                    for m_id, machine_route in solution.route_plan_machine.items():
                        if order_item_id in machine_route:
                            machine_id = m_id
                            break
                    
                    if machine_id is not None:
                        move = ReplaceShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, insertion_position, order_item_id, machine_id)
                        self.Moves.append(move)

            # Return random valid move if any found for this pair
            while self.Moves:
                if local_rng is not None:
                    move = local_rng.choice(self.Moves)
                else:
                    move = self.RNG.choice(self.Moves)
                
                # Verify move feasibility for both workers
                if self.WorkerRouteFeasibilityCheck(move.WorkerID1, move.WorkerRoute1) and self.WorkerRouteFeasibilityCheck(move.WorkerID2, move.WorkerRoute2):
                    return move
                else:
                    self.Moves.remove(move)  # Remove invalid move

        return None  # No valid move found

    def EvaluateMove(self, move: ReplaceShiftWorkerMove) -> None:
        """
        Calculate the delta (change in objective value) for the worker replacement move.
        
        Args:
            move: Worker replacement move to evaluate
        """
        # Calculate impact on solution quality
        move.setDelta(self.evaluationLogic.calculate_replace_shift_worker_delta(move))

    def sort_move_solutions(self):
        """Sort moves by delta value (best improvements first)."""
        self.MoveSolutions.sort(key=lambda move: move.Delta, reverse=False)

    def constructCompleteRoutes(self, move: ReplaceShiftWorkerMove, solution: Solution) -> dict:
        """
        Construct complete route plans after applying the worker replacement move.
        
        Args:
            move: Worker replacement move to apply
            solution: Current solution
            
        Returns:
            dict: Updated route plans for workers, machines, and attachments
        """
        # Create deep copies of current route plans
        machine_route_plan = {k: v[:] for k, v in solution.route_plan_machine.items()}
        worker_route_plan = {k: v[:] for k, v in solution.route_plan_worker.items()}
        attachment_route_plan = {k: v[:] for k, v in solution.route_plan_attachment.items()}

        # Apply the worker route changes from the move
        worker_route_plan[move.WorkerID1] = move.WorkerRoute1
        worker_route_plan[move.WorkerID2] = move.WorkerRoute2

        return worker_route_plan, machine_route_plan, attachment_route_plan


class SwapShiftWorkerMove(BaseMove):
    """
    Represents a move that swaps order items between two workers.
    
    This move type exchanges order items between workers, which can
    help balance workloads and resolve resource conflicts while
    maintaining feasible schedules.
    """
    
    def __init__(self, worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1, 
                 worker_route_index_2, order_item_id_1, order_item_id_2, machine_id_1, machine_id_2):
        """
        Initialize the worker swap move.
        
        Args:
            worker_id_1: ID of first worker
            worker_id_2: ID of second worker
            worker_route_1: Current route of first worker
            worker_route_2: Current route of second worker
            worker_route_index_1: Position for order_item_id_2 in worker 1's route
            worker_route_index_2: Position for order_item_id_1 in worker 2's route
            order_item_id_1: Order item from worker 1
            order_item_id_2: Order item from worker 2
            machine_id_1: Machine associated with order_item_id_1
            machine_id_2: Machine associated with order_item_id_2
        """
        # Copy original routes to avoid side effects
        self.WorkerRoute1 = list(worker_route_1)
        self.WorkerRoute2 = list(worker_route_2)

        # Store insertion positions for swapped items
        self.WorkerRouteIndex1 = worker_route_index_1
        self.WorkerRouteIndex2 = worker_route_index_2

        # Store order item and worker IDs
        self.OrderItemID1 = order_item_id_1
        self.OrderItemID2 = order_item_id_2
        self.WorkerID1 = worker_id_1
        self.WorkerID2 = worker_id_2

        # Apply the swap operations
        self.WorkerRoute1.insert(self.WorkerRouteIndex1, self.OrderItemID2)  # Insert item2 into route1
        self.WorkerRoute2.insert(self.WorkerRouteIndex2, self.OrderItemID1)  # Insert item1 into route2
        self.WorkerRoute1.remove(self.OrderItemID1)  # Remove original item1
        self.WorkerRoute2.remove(self.OrderItemID2)  # Remove original item2

        # Store associated machine IDs
        self.MachineID1 = machine_id_1
        self.MachineID2 = machine_id_2
    """
    Represents a move that swaps order items between two workers.
    
    This move type exchanges order items between workers, which can
    help balance workloads and resolve resource conflicts while
    maintaining feasible schedules.
    """
    
    def __init__(self, worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1, 
                 worker_route_index_2, order_item_id_1, order_item_id_2, machine_id_1, machine_id_2):
        """
        Initialize the worker swap move.
        
        Args:
            worker_id_1: ID of first worker
            worker_id_2: ID of second worker
            worker_route_1: Current route of first worker
            worker_route_2: Current route of second worker
            worker_route_index_1: Position for order_item_id_2 in worker 1's route
            worker_route_index_2: Position for order_item_id_1 in worker 2's route
            order_item_id_1: Order item from worker 1
            order_item_id_2: Order item from worker 2
            machine_id_1: Machine associated with order_item_id_1
            machine_id_2: Machine associated with order_item_id_2
        """
        # Copy original routes to avoid side effects
        self.WorkerRoute1 = list(worker_route_1)
        self.WorkerRoute2 = list(worker_route_2)

        # Store insertion positions for swapped items
        self.WorkerRouteIndex1 = worker_route_index_1
        self.WorkerRouteIndex2 = worker_route_index_2

        # Store order item and worker IDs
        self.OrderItemID1 = order_item_id_1
        self.OrderItemID2 = order_item_id_2
        self.WorkerID1 = worker_id_1
        self.WorkerID2 = worker_id_2

        # Apply the swap operations
        self.WorkerRoute1.insert(self.WorkerRouteIndex1, self.OrderItemID2)  # Insert item2 into route1
        self.WorkerRoute2.insert(self.WorkerRouteIndex2, self.OrderItemID1)  # Insert item1 into route2
        self.WorkerRoute1.remove(self.OrderItemID1)  # Remove original item1
        self.WorkerRoute2.remove(self.OrderItemID2)  # Remove original item2

        # Store associated machine IDs
        self.MachineID1 = machine_id_1
        self.MachineID2 = machine_id_2


class SwapShiftWorkerNeighborhood(TimeNeighborhood):
    """
    Neighborhood for worker swap moves between order items.
    
    This neighborhood explores moves that exchange order items between
    different workers. It helps redistribute workload and resolve
    scheduling conflicts through worker reassignment.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, paretoSolutions: ParetoSolutions, rng):
        super().__init__(inputData, evaluationLogic, paretoSolutions, rng)
        self.Type = 'Swap_Shift_Worker'

    def DiscoverMoves(self, solution: Solution):
        """
        Generate all possible worker swap moves.
        
        This method finds all valid exchanges of order items between
        workers, considering compatibility and precedence constraints.
        
        Args:
            solution: Current solution to analyze for moves
        """
        # Examine all worker pairs for potential swaps
        for worker_id_1, worker_route_1 in solution.route_plan_worker.items():
            for worker_id_2, worker_route_2 in solution.route_plan_worker.items():
                # Track valid positions for order items in each worker's route
                worker_1_order_item_positions = {}
                worker_2_order_item_positions = {}
                same_position_work_route_1 = {}
                same_position_work_route_2 = {}

                # Skip empty worker routes (need items to swap)
                if len(worker_route_1) == 0:
                    break
                if len(worker_route_2) == 0:
                    continue

                # Skip self-swap (same worker)
                if worker_id_1 == worker_id_2:
                    continue
                else:
                    # Get worker objects for compatibility checking
                    worker_1 = solution.data.workers[worker_id_1]
                    worker_2 = solution.data.workers[worker_id_2]

                # Check feasibility of moving order items from worker 1 to worker 2
                for order_item_id_1 in worker_route_1:
                    # Verify worker 2 can handle this order item type
                    worker_2_possible_order_item_ids = [order_item_ids for orders in worker_2.possible_order_item_ids.values() for order_item_ids in orders]
                    if order_item_id_1 not in worker_2_possible_order_item_ids:
                        continue
                    else:                        
                        # Find valid insertion positions in worker 2's route
                        for index, order_item_id_2 in enumerate(worker_route_2):
                            # Handle precedence conflicts between order items
                            if order_item_id_1 not in worker_2.predecessor_ids[order_item_id_2] and order_item_id_1 not in worker_2.successor_ids[order_item_id_2]:
                                
                                # Check non-last positions (can look ahead)
                                if len(worker_route_2) > index + 1:
                                    # Can insert at current position if it's a predecessor of next item
                                    if order_item_id_1 in worker_2.predecessor_ids[worker_route_2[index + 1]]:
                                        same_position_work_route_2[order_item_id_1] = [index, order_item_id_2]
                                        break
                                # Check last position
                                elif len(worker_route_2) == index + 1:
                                    # Can insert at current position if it's a successor of previous item
                                    if order_item_id_1 in worker_2.successor_ids.get(index - 1, []):
                                        same_position_work_route_2[order_item_id_1] = [index, order_item_id_2]
                                        break
                                break

                            # Standard insertion based on precedence relationships
                            if order_item_id_1 in worker_2.predecessor_ids[order_item_id_2]:
                                worker_2_order_item_positions[order_item_id_1] = index
                                break

                            # Insert at end if it's a successor of the last item
                            if len(worker_route_2) == index + 1:
                                if order_item_id_1 in worker_2.successor_ids[order_item_id_2]:
                                    worker_2_order_item_positions[order_item_id_1] = index + 1
                                    break

                # Check feasibility of moving order items from worker 2 to worker 1
                for order_item_id_2 in worker_route_2:
                    # Verify worker 1 can handle this order item type
                    worker_1_possible_order_item_ids = [order_item_ids for orders in worker_1.possible_order_item_ids.values() for order_item_ids in orders]
                    if order_item_id_2 not in worker_1_possible_order_item_ids:
                        continue
                    else:
                        # Find valid insertion positions in worker 1's route
                        for index, order_item_id_1 in enumerate(worker_route_1):
                            # Handle precedence conflicts between order items
                            if order_item_id_2 not in worker_1.predecessor_ids[order_item_id_1] and order_item_id_2 not in worker_1.successor_ids[order_item_id_1]:
                                
                                # Check non-last positions (can look ahead)
                                if len(worker_route_1) > index + 1:
                                    # Can insert at current position if it's a predecessor of next item
                                    if order_item_id_2 in worker_1.predecessor_ids[worker_route_1[index + 1]]:
                                        same_position_work_route_1[order_item_id_2] = [index, order_item_id_1]
                                        break
                                # Check last position
                                elif len(worker_route_1) == index + 1:
                                    # Can insert at current position if it's a successor of previous item
                                    if order_item_id_2 in worker_1.successor_ids.get(index - 1, []):
                                        same_position_work_route_1[order_item_id_2] = [index, order_item_id_1]
                                        break
                                break

                            # Standard insertion based on precedence relationships
                            if order_item_id_2 in worker_1.predecessor_ids[order_item_id_1]:
                                worker_1_order_item_positions[order_item_id_2] = index
                                break

                            # Insert at end if it's a successor of the last item
                            if len(worker_route_1) == index + 1:
                                if order_item_id_2 in worker_1.successor_ids[order_item_id_1]:
                                    worker_1_order_item_positions[order_item_id_2] = index + 1
                                    break

                # Generate swaps where order items go to different positions in other routes
                for order_item_id_2, worker_route_index_1 in worker_1_order_item_positions.items():
                    for order_item_id_1, worker_route_index_2 in worker_2_order_item_positions.items():
                        # Verify working hour constraints after swap
                        if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                            continue
                        if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                            continue
                        
                        # Find associated machines for both order items
                        machine_id_1 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_1 in machine_route][0]
                        machine_id_2 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_2 in machine_route][0]
                        self.Moves.append(SwapShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1, worker_route_index_2, order_item_id_1, order_item_id_2, machine_id_1, machine_id_2))

                # Generate swaps where both order items go to same position (replacement swaps)
                for order_item_id_2, worker_route_index_1_and_order_item_id_1 in same_position_work_route_1.items():
                    for order_item_id_1, worker_route_index_2_and_order_item_id_2 in same_position_work_route_2.items():
                        # Verify that this is a valid position swap (items match positions)
                        if order_item_id_2 == worker_route_index_2_and_order_item_id_2[1] and order_item_id_1 == worker_route_index_1_and_order_item_id_1[1]:
                            # Check working hour constraints for both workers
                            if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                                continue
                            if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                                continue
                            
                            # Find associated machines and create move
                            machine_id_1 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_1 in machine_route][0]
                            machine_id_2 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_2 in machine_route][0]
                            self.Moves.append(SwapShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1_and_order_item_id_1[0], worker_route_index_2_and_order_item_id_2[0], order_item_id_1, order_item_id_2, machine_id_1, machine_id_2))
                
                # Generate mixed swaps (one item at same position, other at different position)
                for order_item_id_2, worker_route_index_1_and_order_item_id_1 in same_position_work_route_1.items():
                    for order_item_id_1, worker_route_index_2 in worker_2_order_item_positions.items():
                        # Ensure items match for valid swap
                        if order_item_id_1 == worker_route_index_1_and_order_item_id_1[1]:
                            # Verify working hour constraints
                            if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                                continue
                            if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                                continue
                            
                            # Find machines and create move
                            machine_id_1 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_1 in machine_route][0]
                            machine_id_2 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_2 in machine_route][0]
                            self.Moves.append(SwapShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1_and_order_item_id_1[0], worker_route_index_2, order_item_id_1, order_item_id_2, machine_id_1, machine_id_2))

                # Generate reverse mixed swaps
                for order_item_id_1, worker_route_index_2_and_order_item_id_2 in same_position_work_route_2.items():
                    for order_item_id_2, worker_route_index_1 in worker_1_order_item_positions.items():
                        # Ensure items match for valid swap
                        if order_item_id_2 == worker_route_index_2_and_order_item_id_2[1]:
                            # Verify working hour constraints
                            if solution.worker_work_time[worker_id_1] + solution.data.order_items[order_item_id_2].duration - solution.data.order_items[order_item_id_1].duration > self.data._max_working_hours:
                                continue
                            if solution.worker_work_time[worker_id_2] + solution.data.order_items[order_item_id_1].duration - solution.data.order_items[order_item_id_2].duration > self.data._max_working_hours:
                                continue
                            
                            # Find machines and create move
                            machine_id_1 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_1 in machine_route][0]
                            machine_id_2 = [machine_id for machine_id, machine_route in solution.route_plan_machine.items() if order_item_id_2 in machine_route][0]
                            self.Moves.append(SwapShiftWorkerMove(worker_id_1, worker_id_2, worker_route_1, worker_route_2, worker_route_index_1, worker_route_index_2_and_order_item_id_2[0], order_item_id_1, order_item_id_2, machine_id_1, machine_id_2))

    def MakeOneMove(self, solution: Solution, max_attempts: int = 100, local_rng = None) -> BaseMove:
        """
        Randomly selects a valid worker swap move.
        
        This method:
        1. Randomly selects worker pairs with non-empty routes
        2. Identifies potential swap positions based on precedence constraints
        3. Validates working hour constraints for both workers
        4. Returns a feasible swap move or None if none found
        
        Args:
            solution: Current solution to modify
            max_attempts: Maximum attempts before giving up
            local_rng: Random number generator (optional)
            
        Returns:
            BaseMove: Valid worker swap move or None
        """
        # Get workers with non-empty routes
        worker_ids = [wid for wid, route in solution.route_plan_worker.items() if route]
        self.Moves.clear()
        attempts = 0

        # Generate and randomize worker pairs
        worker_id_pairs = list(combinations(worker_ids, 2))
        if local_rng is not None:
            local_rng.shuffle(worker_id_pairs)
        else:
            self.RNG.shuffle(worker_id_pairs)

        # Explore worker pairs for valid swaps
        for worker_id_1, worker_id_2 in worker_id_pairs:
            attempts += 1
            if attempts > max_attempts:
                break

            # Get route and worker information
            worker_route_1 = solution.route_plan_worker[worker_id_1]
            worker_route_2 = solution.route_plan_worker[worker_id_2]
            worker_1 = solution.data.workers[worker_id_1]
            worker_2 = solution.data.workers[worker_id_2]

            # Track potential insertion positions for swaps
            worker_1_order_item_positions = {}  # Items from route_2 to route_1
            worker_2_order_item_positions = {}  # Items from route_1 to route_2
            same_position_work_route_1 = {}     # Same position swaps in route_1
            same_position_work_route_2 = {}     # Same position swaps in route_2

            # Analyze feasibility of moving items from worker_1 to worker_2
            for order_item_id_1 in worker_route_1:
                # Check if worker_2 can handle this order item type
                worker_2_possible_order_item_ids = [oid for orders in worker_2.possible_order_item_ids.values() for oid in orders]
                if order_item_id_1 not in worker_2_possible_order_item_ids:
                    continue

                # Find valid insertion positions in worker_2's route
                for index, order_item_id_2 in enumerate(worker_route_2):
                    # Handle precedence conflicts with same-position strategy
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

            while valid_moves != []:
                if local_rng is not None:
                    move = local_rng.choice(valid_moves)
                else:
                    move = self.RNG.choice(valid_moves)
                if self.WorkerRouteFeasibilityCheck(move.WorkerID1, move.WorkerRoute1) and self.WorkerRouteFeasibilityCheck(move.WorkerID2, move.WorkerRoute2):
                    return move
                else:
                    valid_moves.remove(move)

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



