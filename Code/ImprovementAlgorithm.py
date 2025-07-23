"""
===============================================================================
                              IMPROVEMENT ALGORITHM MODULE
===============================================================================

This module provides a comprehensive framework for improvement algorithms in the 
OptRail railroad construction scheduling optimization system. It implements various 
metaheuristic approaches including local search, simulated annealing variants, 
and multi-objective optimization strategies for solving complex railroad 
construction scheduling problems.

CORE FUNCTIONALITY:
------------------
1. Base Algorithm Framework
   - Common interface for all improvement algorithms
   - Neighborhood management and factory pattern implementation
   - Solution evaluation and move acceptance logic
   - Multi-threaded and parallel processing support

2. Local Search Optimization
   - Iterative improvement with variable neighborhood descent
   - Best improvement and first improvement strategies
   - Sequential exploration of multiple neighborhood types

3. Simulated Annealing Variants
   - Building Simulated Annealing: Focus on fully staffed solutions
   - Pareto Simulated Annealing: Multi-objective optimization with agents
   - Dominance-Based Simulated Annealing: Pareto dominance energy calculation
   - Two-Phase Simulated Annealing: Combined objective-focused and dominance-based

4. Multi-Objective Optimization
   - Pareto front maintenance and management
   - Adaptive weight adjustment strategies
   - Dominance relationship evaluation
   - Non-dominated solution filtering

5. Parallel Processing Support
   - Thread-based parallel agent execution
   - Process-based parallel optimization runs
   - Efficient solution space exploration
   - Scalable multi-core utilization

"""

from Code.Neighborhood import *
import math
from copy import deepcopy
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from joblib import Parallel, delayed
import pandas as pd
import copy
import cProfile
import pstats
import os
from pathlib import Path
import time


class ImprovementAlgorithm:
    """
    Base class for several types of improvement algorithms including local search,
    simulated annealing variants, and multi-objective optimization approaches.
    Provides common functionality for neighborhood management and solution evaluation.
    """

    def __init__(self, inputData:InputData, neighborhoodEvaluationStrategy:str = 'BestImprovement', neighborhoodTypes:list[str] = ['Insert_Shift']):
        # Core data and evaluation components
        self.InputData = inputData
        self.EvaluationLogic = {}
        self.SolutionPool = {}
        self.RNG = {}

        # Algorithm configuration parameters
        self.NeighborhoodEvaluationStrategy = neighborhoodEvaluationStrategy  # Strategy for evaluating neighborhood moves
        self.NeighborhoodTypes = neighborhoodTypes  # List of neighborhood types to use
        self.Neighborhoods = {}  # Dictionary storing initialized neighborhood objects

    def Initialize(self, evaluationLogic:EvaluationLogic, paretoSolutions:ParetoSolutions, rng) -> None:
        """
        Initializes the improvement algorithm with essential components.
        
        Args:
            evaluationLogic: Logic for evaluating solutions and calculating delta values
            paretoSolutions: Manager for Pareto front in multi-objective optimization
            rng: Random number generator for stochastic operations
        """
        self.EvaluationLogic = evaluationLogic
        self.ParetoSolutions = paretoSolutions
        self.RNG = rng

    def CreateNeighborhood(self, neighborhoodType:str, local_rng=None):
        """
        Factory method to create neighborhood objects based on specified type.
        Creates different types of neighborhoods for various optimization moves.
        
        Args:
            neighborhoodType: Type of neighborhood to create (e.g., 'Insert_Shift', 'Swap_Shift_Worker')
            local_rng: Optional local random number generator for parallel processing
            
        Returns:
            Neighborhood object of the specified type
        """
        
        # Create neighborhoods for different types of optimization moves
        if neighborhoodType == 'Insert_Shift':
            return InsertShiftNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        
        elif neighborhoodType == 'Swap_Shift_Worker':
            if local_rng is not None:
                return SwapShiftWorkerNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, local_rng)
            return SwapShiftWorkerNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        
        elif neighborhoodType == 'Replace_Shift_Worker':
            if local_rng is not None:
                return ReplaceShiftWorkerNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, local_rng)
            return ReplaceShiftWorkerNeighborhood(self.InputData , self.EvaluationLogic, self.SolutionPool, self.RNG)
        
        elif neighborhoodType == 'Replace_Shift_Machine':
            if local_rng is not None:
                return ReplaceShiftMachineNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, local_rng)
            return ReplaceShiftMachineNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        
        elif neighborhoodType == 'Swap_Shift_Machine':
            if local_rng is not None:
                return SwapShiftMachineNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, local_rng)
            return SwapShiftMachineNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        
        elif neighborhoodType == 'Swap_Shift_External':
            return SwapShiftExternalNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        
        elif neighborhoodType == 'Replace_Shift_Attachment':
            if local_rng is not None:
                return ReplaceShiftAttachmentNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, local_rng)
            return ReplaceShiftAttachmentNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        
        elif neighborhoodType == 'Swap_Shift_Attachment':
            if local_rng is not None:
                return SwapShiftAttachmentNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, local_rng)
            return SwapShiftAttachmentNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        
        else:
            raise Exception(f"Neighborhood type {neighborhoodType} not defined.")


    def InitializeNeighborhoods(self, neighborhoodtypes=None, neighborhoods_dict=None) -> None:
        """
        Creates and initializes multiple neighborhood objects for optimization.
        
        Args:
            neighborhoodtypes: List of neighborhood types to initialize (defaults to self.NeighborhoodTypes)
            neighborhoods_dict: Dictionary to store neighborhoods (defaults to self.Neighborhoods)
        """
        
        # Use default values if parameters not provided
        if neighborhoodtypes is None:
            neighborhoodtypes = self.NeighborhoodTypes

        if neighborhoods_dict is None:
            neighborhoods_dict = self.Neighborhoods

        # Create neighborhood objects for each specified type
        for neighborhoodType in neighborhoodtypes:
            neighborhood = self.CreateNeighborhood(neighborhoodType)
            neighborhoods_dict[neighborhoodType] = neighborhood




class IterativeImprovement(ImprovementAlgorithm):
    """
    Iterative improvement algorithm implementing sequential variable neighborhood descent.
    Performs local search by systematically exploring different neighborhood types
    to find better solutions through iterative optimization steps.
    """

    def __init__(self,  inputData:InputData, neighborhoodEvaluationStrategy:str = 'BestImprovement', neighborhoodTypes:list[str] = ['Swap']):
        super().__init__(inputData, neighborhoodEvaluationStrategy, neighborhoodTypes)

    def Run(self, solution:Solution) -> Solution:
        """
        Executes local search with iterative improvement through multiple neighborhood types.
        
        Args:
            solution: Initial solution to improve
            
        Returns:
            Improved solution after exploring all neighborhood types
        """
        # Initialize all neighborhood objects for optimization
        self.InitializeNeighborhoods()

        print(f'\nInitial solution: \n{solution}')

        # Iterate through each neighborhood type sequentially
        for neighborhoodType in self.NeighborhoodTypes:

            print(f'\nRunning neighborhood {neighborhoodType}')
            neighborhood = self.Neighborhoods[neighborhoodType]

            # Perform local search in current neighborhood
            solution = neighborhood.LocalSearch(self.NeighborhoodEvaluationStrategy, solution)

            # Verify solution feasibility after neighborhood exploration
            feasible = solution.feasibility_check()

            print(f"Attachment Route Plan: {solution.route_plan_attachment}")

            if not feasible:
                raise Exception(f'Solution is not feasible after neighborhood {neighborhoodType}')

            print(f'\nBest (feasible) solution after {neighborhoodType}: \n{solution}')

        return solution




class BuildingSimulatedAnnealing(ImprovementAlgorithm):
    """
    Simulated Annealing algorithm specifically designed to find fully staffed solutions.
    Uses temperature-based acceptance criteria to escape local optima while building
    solutions that satisfy all staffing requirements for railroad construction projects.
    """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int):
        super().__init__(inputData)

        # Simulated annealing temperature parameters
        self.StartTemperature = start_temp  # Initial temperature for acceptance probability
        self.MinTemperature = min_temp  # Minimum temperature to stop algorithm
        self.CoolingRate = cooling_rate  # Rate at which temperature decreases

        # Iteration and optimization parameters
        self.MaxIterations = max_iterations  # Maximum iterations per temperature level
        self.ScalingEnergy = 30  # Scaling factor for energy calculations

        # Neighborhood types mapped to their objective functions for evaluation
        self.DistanceTypes = {  'Swap_Shift_External': ['commute_distance', 'transport_distance', 'attachment_distance'],
                                'Replace_Shift_Worker': ['commute_distance'],
                                'Replace_Shift_Machine': ['transport_distance'],
                                'Replace_Shift_Attachment': ['attachment_distance'],
                                'Swap_Shift_Worker': ['commute_distance'],
                                'Swap_Shift_Machine': ['transport_distance'],
                                'Swap_Shift_Attachment': ['attachment_distance'],
                                'Insert_Shift': None}
        
        self.FulfillmentType = 'Insert_Shift'  # Neighborhood type for order fulfillment


    def Run(self, solution:Solution) -> Solution:
        """
        Executes the building simulated annealing algorithm to find fully staffed solutions.
        
        Args:
            solution: Initial solution to improve
            
        Returns:
            Fully staffed solution or best solution found if full staffing not achieved
        """
        current_temperature = self.StartTemperature
        # Initialize all neighborhood types for the algorithm
        self.InitializeNeighborhoods(list(self.DistanceTypes.keys()) + [self.FulfillmentType])

        # Track best solutions found during optimization
        highest_number_of_fully_staffed_orders = 0
        highest_dynamic_percentage = 0

        # Main simulated annealing loop with temperature cooling
        while current_temperature > self.MinTemperature:
            
            # Display current solution status
            number_of_needed_orders = len(self.InputData.orders) - len(solution.not_recognized_orders)
            print(f"\nSolution order count: {solution.number_of_finished_orders} of {number_of_needed_orders} needed orders")
            self.EvaluationLogic.calculate_finished_order_items(solution)
            number_of_needed_order_items = len(self.InputData.order_items) - len(solution.not_recognized_order_item_ids)
            print(f"Solution order item count: {solution.number_of_finished_order_items} of {number_of_needed_order_items} needed order items")
            print(f"Not started order items: {solution.not_started_order_item_ids}")

            # Perform iterations at current temperature level
            for i in range(self.MaxIterations):

                # Check if solution meets full staffing requirement
                if solution.total_dynamic_percentage == self.InputData.site_fulfillment:
                    print("\nFound fully staffed solution:")
                    self.EvaluationLogic.evaluate(solution)
                    print(solution)
                    return solution

                # Randomly select neighborhood type and generate move
                random_type = self.RNG.choice(list(self.DistanceTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(solution)
                objective = self.DistanceTypes[random_type]

                if move is None:
                    continue

                # Calculate energy value based on move's impact on objectives
                if objective is not None:
                    value = 0
                    for obj in objective:
                        value += move.DeltaDetails[obj]
                else:
                    value = -1

                # Apply acceptance criteria: always accept improving moves
                if value <= 0:
                    pass
                # Use probability for worsening moves based on temperature
                elif value > 0:
                    prob = math.exp(-value * self.ScalingEnergy / current_temperature)
                    random_number = self.RNG.random()

                    if prob < random_number:
                        continue
                
                # Apply move to solution and update route plans
                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, solution)
                solution.route_plan_worker = worker_route_plan
                solution.route_plan_machine = machine_route_plan
                solution.route_plan_attachment = attachment_route_plan

                # Update solution metrics for tracking progress
                self.EvaluationLogic.categorizing_orders(solution)
                self.EvaluationLogic.calculate_dynamic_percentage_order(solution)
                self.EvaluationLogic.calculate_worker_count_and_utilization_time(solution)
                
                # Save best solution found so far
                if len(solution.finished_orders) >= highest_number_of_fully_staffed_orders:
                    if solution.total_dynamic_percentage > highest_dynamic_percentage:
                        saved_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                        highest_number_of_fully_staffed_orders = len(solution.finished_orders)
                        highest_dynamic_percentage = solution.total_dynamic_percentage

            # Cool down temperature for next iteration
            current_temperature *= self.CoolingRate

        # Handle case where full staffing was not achieved
        if solution.total_dynamic_percentage != self.InputData.site_fulfillment:
            self.EvaluationLogic.evaluate(saved_solution)

            # Find order with most missing items to remove and retry
            all_order_items = {
                item for sublist in saved_solution.route_plan_machine.values()
                for item in sublist
            }

            # Find order with the most unincluded order items
            number_of_not_included = {}
            for order in self.InputData.orders:
                if not order.status:
                    continue
                missing_count = sum(1 for item in order.order_items if item.id not in all_order_items)
                number_of_not_included[order.order_number] = missing_count

            order_id_to_delete = max(number_of_not_included, key=number_of_not_included.get)
            print(number_of_not_included)
            print(order_id_to_delete)

            # Remove problematic order and its items from solution
            self.InputData.deactivate_order(order_id_to_delete)
            order_to_delete = self.InputData.orders[order_id_to_delete]

            for order_item in order_to_delete.order_items:
                oid = order_item.id
                # Remove from worker routes
                next((v.remove(oid) for v in saved_solution.route_plan_worker.values() if oid in v), None)
                # Remove from machine routes
                next((v.remove(oid) for v in saved_solution.route_plan_machine.values() if oid in v), None)
                # Remove from attachment routes
                for v in saved_solution.route_plan_attachment.values():
                    v[:] = [x for x in v if x != oid]

            print("Retrying BuildingSimulatedAnnealing with new solution...")
            self.EvaluationLogic.evaluate(saved_solution)
            return self.Run(saved_solution)





class ParetoSimulatedAnnealing(ImprovementAlgorithm):
    """
    Multi-objective Simulated Annealing algorithm with individual agents exploring the solution space.
    Uses adaptive weight adjustment and parallel processing to maintain and improve a Pareto front
    of non-dominated solutions for multi-objective railroad construction optimization.
    """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 weight_alpha:float,
                 start_size_population:int):
        super().__init__(inputData)

        # Simulated annealing temperature parameters
        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.ScalingEnergy = 50

        # Algorithm-specific parameters
        self.MaxSingleMoveTries = 30  # Maximum attempts to find valid move
        self.SizeStartPopulation = start_size_population  # Initial population size
        self.WeightAlpha = weight_alpha  # Weight adjustment factor for objectives

        # Neighborhood types mapped to their relevant objective functions
        self.NeighborhoodTypes = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}
        
        # List of all optimization objectives
        self.objectives = ['driver_violation', 'commute_distance', 'transport_distance', 'attachment_distance', 'worker_count', 'machine_count', 'attachment_count']



    def MutateSolution(self, solution: Solution) -> None:
        """
        Creates a mutated copy of the solution by applying multiple random moves.
        Used to generate diverse solutions for the initial Pareto front population.
        
        Args:
            solution: Original solution to mutate
        """
        # Generate random number of moves to apply
        random_number_of_moves = self.RNG.integers(2, 50)
        current_solution = solution.clone()
        self.EvaluationLogic.evaluate(current_solution)

        # Apply multiple random moves to create diversity
        for _ in range(random_number_of_moves):
            move = None

            # Keep trying until a valid move is found
            while move is None:
                random_type = self.RNG.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(current_solution)

            # Apply move and create new solution
            worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, current_solution)
            current_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
            self.EvaluationLogic.evaluate(current_solution)

        # Add mutated solution to Pareto front
        self.ParetoSolutions.UpdateParetoFront(current_solution)
 
    def normalize_objectives(self, population, objectives, attr_mapping):
        """
        Normalizes objective values across the population for fair comparison.
        
        Args:
            population: List of solutions to normalize
            objectives: List of objective names
            attr_mapping: Mapping from objective names to solution attributes
            
        Returns:
            Tuple of (min_vals, max_vals) dictionaries for normalization
        """
        min_vals = {}
        max_vals = {}
        for obj in objectives:
            values = [getattr(sol, attr_mapping.get(obj, obj), 0) for sol in population]
            min_vals[obj] = min(values)
            max_vals[obj] = max(values)
        return min_vals, max_vals

    def get_normalized_values(self, solution, objectives, attr_mapping, min_vals, max_vals):
        """
        Gets normalized objective values for a specific solution.
        
        Args:
            solution: Solution to normalize
            objectives: List of objective names
            attr_mapping: Mapping from objective names to solution attributes
            min_vals: Minimum values for normalization
            max_vals: Maximum values for normalization
            
        Returns:
            Dictionary of normalized objective values
        """
        norm_values = {}
        for obj in objectives:
            raw = getattr(solution, attr_mapping.get(obj, obj), 0)
            range_ = max_vals[obj] - min_vals[obj]
            norm_values[obj] = (raw - min_vals[obj]) / range_ if range_ > 0 else 0.0
        return norm_values


    def update_weights(self, x, population, objectives, previous_weights, local_rng):
        """
        Updates objective weights based on the current solution's position relative to the population.
        Implements adaptive weight adjustment to guide search toward underexplored regions.
        
        Args:
            x: Current solution
            population: Current population of solutions
            objectives: List of objective names
            previous_weights: Previous weight configuration
            local_rng: Local random number generator
            
        Returns:
            Dictionary of updated normalized weights
        """
        # Mapping from objective names to solution attributes
        attr_mapping = {
            'commute_distance': 'total_commute_distance',
            'transport_distance': 'total_transport_distance',
            'attachment_distance': 'total_transport_distance_attachments',
            'worker_count': 'number_of_workers',
            'machine_count': 'number_of_machines',
            'attachment_count': 'number_of_attachments',
            'driver_violation': 'driver_violation'
        }

        def non_dominating(a, b):
            """Check if two solutions are non-dominating (both have advantages)"""
            better_in_a = False
            better_in_b = False
            for obj in objectives:
                if a[obj] < b[obj]:
                    better_in_a = True
                elif a[obj] > b[obj]:
                    better_in_b = True
            return better_in_a and better_in_b

        def distance(a, b):
            """Calculate Euclidean distance between two solutions in objective space"""
            return sum(abs(a[obj] - b[obj]) for obj in objectives)

        # Normalize all objective values for fair comparison
        min_vals, max_vals = self.normalize_objectives(population + [x], objectives, attr_mapping)
        x_values = self.get_normalized_values(x, objectives, attr_mapping, min_vals, max_vals)

        # Find non-dominating solutions and select closest one
        candidates = []
        for x_ in population:
            if x_ == x:
                continue
            x__values = self.get_normalized_values(x_, objectives, attr_mapping, min_vals, max_vals)
            if non_dominating(x_values, x__values):
                candidates.append((x_, distance(x_values, x__values)))

        # Update weights based on comparison with closest non-dominating solution
        if not candidates:
            # No non-dominating solutions found, use random weights
            weights = {obj: local_rng.random() for obj in objectives}
        else:
            # Select closest non-dominating solution for weight adjustment
            x_prime, _ = min(candidates, key=lambda tup: tup[1])
            x_prime_values = self.get_normalized_values(x_prime, objectives, attr_mapping, min_vals, max_vals)

            weights = {}
            for obj in objectives:
                if x_values[obj] >= x_prime_values[obj]:
                    # Current solution is worse, decrease weight
                    weights[obj] = self.WeightAlpha * previous_weights[obj]
                elif x_values[obj] < x_prime_values[obj]:
                    # Current solution is better, increase weight
                    weights[obj] = previous_weights[obj] / self.WeightAlpha
                else:
                    raise Exception(f"Objective {obj} not defined.")
                    weights[obj] = 1.0

        # Add weights for objectives not in current neighborhood
        for obj in self.objectives:
            if obj not in weights:
                weights[obj] = previous_weights[obj] * self.WeightAlpha
    
        # Normalize weights to sum to 1
        total = sum(weights.values())
        normalized_weights = {k: v / total for k, v in weights.items()}

        return normalized_weights



    def psa_iteration(self, info: dict, T: float, S_snapshot: list):
        """
        Executes a single iteration of Pareto Simulated Annealing for one agent.
        
        Args:
            info: Dictionary containing agent information (solution, weights, seeds, etc.)
            T: Current temperature
            S_snapshot: Snapshot of current population for weight updates
            
        Returns:
            Updated agent information dictionary
        """
        # Extract agent information
        x = info["solution"]
        weights_dict = info["weights"]
        seed = info["seed"]
        same_seed = info["same seed"]
        agent_id = info["id"]
        local_rng = np.random.default_rng(seed)

        profiled = info.get("profiled", False)

        # Generate neighborhood move
        move = None
        tries = 0
        while move is None and tries < self.MaxSingleMoveTries:
            n_type = local_rng.choice(list(self.NeighborhoodTypes.keys()))
            neighborhood = self.CreateNeighborhood(n_type, local_rng)
            move = neighborhood.SingleMove(x, self.MaxSingleMoveTries, local_rng)
            tries += 1

        # Get objectives for this neighborhood type and update weights
        objectives = self.NeighborhoodTypes[n_type]
        weights = self.update_weights(x, S_snapshot, objectives, weights_dict, local_rng)
        
        # Calculate weighted delta for acceptance decision
        delta = sum(weights[obj] * move.DeltaDetails[obj] for obj in objectives)

        # Apply acceptance criteria
        if delta > 0:
            p = math.exp(-delta * self.ScalingEnergy / T)
            if local_rng.random() > p:
                # Reject move, return current solution
                return {
                        "solution": x,
                        "new_solution": None,
                        "weights": weights,
                        "seed": seed + 1,
                        "same seed": same_seed + 1,
                        "id": agent_id
                    }

        # Accept move, construct new solution
        w, m, a = neighborhood.constructCompleteRoutes(move, x)
        x_new = Solution(w, m, a, self.InputData)
        self.EvaluationLogic.evaluate(x_new)

        return {
                    "solution": x,
                    "new_solution": x_new,
                    "weights": weights,
                    "seed": seed + 1,
                    "same seed": same_seed + 1,
                    "id": agent_id,
                    "profiled": True
                }





    def Run(self, solution: Solution) -> Solution:
        """
        Executes the Pareto Simulated Annealing algorithm with multiple agents.
        
        Args:
            solution: Initial solution to start optimization
            
        Returns:
            Final Pareto front
        """
        # Initialize neighborhoods and start with given solution
        self.InitializeNeighborhoods(list(self.NeighborhoodTypes.keys()))
        self.ParetoSolutions.UpdateParetoFront(solution)
        
        # Build initial population through mutation
        while len(self.ParetoSolutions.ParetoFront) < self.SizeStartPopulation:
            self.MutateSolution(solution)
        print(f"Initial Solution Pool:")
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()

        current_temperature = self.StartTemperature

        # Initialize agent information for parallel processing
        S_info = []
        same_seed = self.RNG.integers(0, 1_000_000)
        for i, x in enumerate(self.ParetoSolutions.ParetoFront):
            x.id = i
            # Initialize random weights for each objective
            weights = {obj: self.RNG.random() for obj in self.objectives}
            seed = self.RNG.integers(0, 1_000_000)

            S_info.append({
                "solution": deepcopy(x),
                "weights": weights,
                "seed": seed,
                "same seed": same_seed,
                "id": i,
                "profiled": False
            })

        # Main optimization loop with parallel agent processing
        with ThreadPoolExecutor(max_workers=self.SizeStartPopulation) as executor:
            while current_temperature > self.MinTemperature:
                
                # Execute iterations at current temperature
                for i in range(self.MaxIterations):
                    # Submit parallel tasks for all agents
                    futures = [
                        executor.submit(
                            self.psa_iteration,
                            info,
                            current_temperature,
                            [s["solution"] for s in S_info]
                        )
                        for info in S_info
                    ]
                    results = [f.result() for f in futures]

                    # Update agent information and Pareto front
                    new_S_info = results

                    for info in new_S_info:
                        if info["new_solution"] is not None:
                            # Add new solution to Pareto front
                            self.ParetoSolutions.UpdateParetoFront(info["new_solution"])
                            info["solution"] = info["new_solution"]

                    S_info = new_S_info

                # Cool down temperature
                current_temperature *= self.CoolingRate

        # Verify feasibility of final solutions
        for solution in self.ParetoSolutions.ParetoFront:
            feasible = solution.feasibility_check()
            if not feasible:
                raise Exception('Solution is not feasible after pareto simulated annealing')

        print("\nFinal Pareto Approximation:")
        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()

        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)

        #profiler.disable()
        #Path("Profiler/PSA").mkdir(parents=True, exist_ok=True)
        #profile_path = Path("Profiler/PSA") / "run_profile.txt"

        #with open(profile_path, "w") as f:
        #    ps = pstats.Stats(profiler, stream=f)
        #    ps.strip_dirs().sort_stats("cumulative").print_stats(50)

        #combined_stats = None
        #profile_files = list(Path("Profiler/PSA/Agents").glob("agent_*.prof"))

        #for file in profile_files:
        #    stats = pstats.Stats(str(file))
        #    if combined_stats is None:
        #        combined_stats = stats
        #    else:
        #        combined_stats.add(stats)

        #with open("Profiler/PSA/combined_agents.txt", "w") as f:
        #    combined_stats.stream = f
        #    combined_stats.strip_dirs().sort_stats("cumulative").print_stats(50)

        # Nach Zusammenfassung: alle Einzelprofile löschen
       # for file in profile_files:
         #   os.remove(file)

        






class DominanceBasedSimulatedAnnealing(ImprovementAlgorithm):
    """
    Simulated Annealing algorithm using dominance-based energy calculation.
    Uses Pareto dominance relationships to guide the search process,
    accepting moves based on how they affect the solution's dominance status.
    """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int):
        super().__init__(inputData)

        # Simulated annealing parameters
        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.MaxSingleMoveTries = 30
        self.ParallelRuns = 0 # Not used in this implementation --> currently single agent optimization

        # Move configuration parameters
        self.max_traversal_moves = 1  # Maximum moves for traversal operations
        self.max_location_moves = 4  # Maximum moves for location operations

        # Neighborhood types with their corresponding objectives
        self.NeighborhoodTypes = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}

        # Counters for tracking move success rates
        self.None_Move_Counter = {}  # Count of failed move attempts
        self.Move_Counter = {}  # Count of total move attempts
        for neighborhoodType in self.NeighborhoodTypes:
            self.None_Move_Counter[neighborhoodType] = 0
            self.Move_Counter[neighborhoodType] = 0
            


    def MutateSolution(self, solution: Solution) -> None:
        """
        Creates a mutated copy of the solution by applying multiple random moves.
        Used to generate initial population diversity.
        
        Args:
            solution: Original solution to mutate
        """
        # Apply random number of mutations
        random_number_of_moves = self.RNG.integers(2, 50)
        current_solution = solution.clone()
        self.EvaluationLogic.evaluate(current_solution)

        for _ in range(random_number_of_moves):
            move = None

            # Find valid move
            while move is None:
                random_type = self.RNG.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(current_solution)

            # Apply move to create new solution
            worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, current_solution)
            current_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
            self.EvaluationLogic.evaluate(current_solution)

        # Add to Pareto front
        self.ParetoSolutions.UpdateParetoFront(current_solution)

    def log(self, text: str):
        """
        Logs text to the algorithm's log file.
        
        Args:
            text: Text to write to log file
        """
        with open(self.log_path, "a") as f:
            f.write(text + "\n")
 
    def multiple_moves(self, solution:Solution, move_type:str, local_rng):
        """
        Applies multiple moves of specified type to the solution.
        
        Args:
            solution: Solution to modify
            move_type: Type of moves ('traversal' or 'location')
            local_rng: Local random number generator
            
        Returns:
            Tuple of (delta_details, objectives, worker_routes, machine_routes, attachment_routes)
        """
        # Configure move count based on type
        if move_type == 'traversal':
            possible_moves = list(range(1, self.max_traversal_moves + 1))
            move_probs = [1.0 / len(possible_moves)] * len(possible_moves)
        elif move_type == 'location':
            possible_moves = list(range(self.max_traversal_moves+1, self.max_location_moves + 1))
            move_probs = [1.0 / len(possible_moves)] * len(possible_moves)

        # Select number of moves to apply
        random_number_of_moves = local_rng.choice(possible_moves, p=move_probs)

        current_solution = solution.clone()
        self.EvaluationLogic.evaluate(current_solution)
        delta_details = dict()  # Accumulated delta values
        objectives = set()  # Set of affected objectives

        # Apply multiple moves and accumulate their effects
        for _ in range(random_number_of_moves):
            move = None
            while move is None:
                random_type = local_rng.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                self.Move_Counter[random_type] += 1

                move = neighborhood.SingleMove(current_solution, self.MaxSingleMoveTries, local_rng)

                if move is None:
                    self.None_Move_Counter[random_type] += 1

            # Accumulate delta values for all objectives
            for obj, details in move.DeltaDetails.items():
                if obj not in delta_details:
                    delta_details[obj] = 0
                delta_details[obj] += details
                objectives.add(obj)

            # Apply move to solution
            worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, current_solution)
            current_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
            self.EvaluationLogic.calculate_worker_count_and_utilization_time(current_solution)

        return delta_details, objectives, worker_route_plan, machine_route_plan, attachment_route_plan
    

    def unnormalize_value(self, value:float, objective:str) -> float:
        """
        Converts normalized objective value back to original scale.
        
        Args:
            value: Normalized value to convert
            objective: Name of the objective
            
        Returns:
            Unnormalized value in original scale
        """
        if objective == 'transport_distance' or objective == 'attachment_distance':
            return value * (self.InputData.max_transport_distance - self.InputData.min_transport_distance) + self.InputData.min_transport_distance
        elif objective == 'commute_distance':
            return value * (self.InputData.max_work_distance + self.InputData.min_work_distance) + self.InputData.min_work_distance
        elif objective == 'driver_violation' or objective == 'attachment_count' or objective == 'worker_count' or objective == 'machine_count':
            return value
        
        raise Exception(f"Objective {objective} not defined.")

    
    def DBSA(self, local_solution:Solution, local_pareto_front: list = None, seed = None) -> list[Solution]:
        """
        Executes the Dominance-Based Simulated Annealing algorithm.
        Uses dominance relationships to calculate energy and guide the search.
        
        Args:
            local_solution: Starting solution for this run
            local_pareto_front: Current Pareto front for comparison
            seed: Random seed for reproducibility
            
        Returns:
            List of solutions in the local Pareto front
        """
        local_rng = np.random.default_rng(seed)

        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData, local_rng)
        local_pareto_solutions.ParetoFront = local_pareto_front


        # Main simulated annealing loop
        while current_temperature > self.MinTemperature:

            for i in range(self.MaxIterations):
                # Select random neighborhood and move type
                neighborhoodType = local_rng.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[neighborhoodType]
                objectives = self.NeighborhoodTypes[neighborhoodType]

                move_type = local_rng.choice(['traversal', 'location'])
    
                # Apply multiple moves and get combined effect
                delta_details, objectives, worker_route_plan, machine_route_plan, attachment_route_plan = self.multiple_moves(local_solution, move_type, local_rng)
 
                # Create objective dictionary with current solution values
                objective_dict = {
                    "driver_violation": local_solution.driver_violation,
                    "commute_distance": local_solution.total_commute_distance,
                    "transport_distance": local_solution.total_transport_distance,
                    "attachment_distance": local_solution.total_transport_distance_attachments,
                    "worker_count": local_solution.number_of_workers,
                    "machine_count": local_solution.number_of_machines,
                    "attachment_count": local_solution.number_of_attachments
                }

                # Update affected objectives with delta values
                for objective in objectives:
                    unnormalized_value = self.unnormalize_value(delta_details[objective], objective)
                    objective_dict[objective] += unnormalized_value
           
                # Calculate dominance counts for energy calculation
                dominating_count_current, interpolated_points = local_pareto_solutions.CountDominatingSolutions(local_solution, objective_dict_point=objective_dict)
                dominating_count_new, _ = local_pareto_solutions.CountDominatingSolutions(objective_dict, interpolated_points=interpolated_points, solution_point=local_solution)

                # Calculate energy difference based on dominance change
                overall_difference = (dominating_count_new - dominating_count_current)

                # Apply acceptance criteria based on dominance energy
                if overall_difference <= 0:
                    prob = 1.0  # Always accept non-worsening moves
                else:
                    prob = math.exp(-overall_difference / current_temperature)

                random_number = local_rng.random()

                if prob < random_number:
                    continue  # Reject move

                # Accept move and create new solution
                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)

                # Update Pareto front if solution is non-dominated
                if dominating_count_new == 0:
                    added = local_pareto_solutions.UpdateParetoFront(local_solution)


            # Cool down temperature
            current_temperature *= self.CoolingRate

        return local_pareto_solutions.ParetoFront
        
    def _dbsa_with_counts(self, solution: Solution, pareto_front: list, seed) -> tuple[list[Solution], dict, dict]:
        """
        Wrapper function to run DBSA and capture move counters for parallel processing.
        
        Args:
            solution: Solution to optimize
            pareto_front: Current Pareto front
            seed: Random seed
            
        Returns:
            Tuple of (pareto_front, move_counter_copy, none_move_counter_copy)
        """
        result_front = self.DBSA(solution, pareto_front, seed)
        # Copy counters to send back to parent process
        mov = self.Move_Counter.copy()
        none = self.None_Move_Counter.copy()

        return result_front, mov, none

    def Run(self, solution: Solution) -> Solution:
        """
        Executes the Dominance-Based Simulated Annealing algorithm.
        
        Args:
            solution: Initial solution to optimize
            
        Returns:
            Final Pareto front
        """
        # Initialize neighborhoods and Pareto front
        self.InitializeNeighborhoods(list(self.NeighborhoodTypes.keys()))
        self.ParetoSolutions.UpdateParetoFront(solution)

        multiprocessing = False
        
        if multiprocessing:
            # Generate initial population for parallel processing
            while len(self.ParetoSolutions.ParetoFront) < self.ParallelRuns:
                self.MutateSolution(solution)
            print(f"Initial Solution Pool:")
            self.ParetoSolutions.SortParetoFront()
            self.ParetoSolutions.ShowFront()

            if len(self.ParetoSolutions.ParetoFront) != self.ParallelRuns:
                raise Exception(f"Not enough solutions in Pareto Front: {len(self.ParetoSolutions.ParetoFront)}")

            # Execute parallel DBSA with counter aggregation
            tasks = []
            with ProcessPoolExecutor() as executor:
                for sol in self.ParetoSolutions.ParetoFront:
                    local_solution = sol.clone()
                    seed = self.RNG.integers(0, 1_000_000)
                    self.EvaluationLogic.evaluate(local_solution)
                    local_pareto_front = [s for s in self.ParetoSolutions.ParetoFront if s != local_solution]
                    for s in local_pareto_front:
                        self.EvaluationLogic.evaluate(s)
                    # Submit wrapper that returns both front and counters
                    tasks.append(
                        executor.submit(self._dbsa_with_counts, local_solution, local_pareto_front, seed)
                    )

            combined_solutions = []
            # Collect results and aggregate counters
            for result_front, mov_counts, none_counts in [t.result() for t in tasks]:
                combined_solutions.extend(result_front)
                for nt, c in mov_counts.items():
                    self.Move_Counter[nt] += c
                for nt, c in none_counts.items():
                    self.None_Move_Counter[nt] += c
            results = combined_solutions

            # Update Pareto front with all results
            self.ParetoSolutions.ParetoFront = results

        else:
            # Single-threaded execution
            print(f"Initial Solution:")
            self.ParetoSolutions.ShowFront()
            local_solution = solution
            seed = self.RNG.integers(0, 1_000_000)
            local_pareto_front = [s for s in self.ParetoSolutions.ParetoFront]

            result_front = self.DBSA(local_solution, local_pareto_front, seed)
            self.ParetoSolutions.ParetoFront = result_front

        # Clean up and finalize Pareto front
        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()

        # Log move statistics
        for nt, count in self.None_Move_Counter.items():
            print(f"Neighborhood {nt} had {count}/{self.Move_Counter[nt]} None Moves.")

        # Verify solution feasibility
        for solution_check in self.ParetoSolutions.ParetoFront:
            feasible = solution_check.feasibility_check()
            if not feasible:
                raise Exception('Solution is not feasible after dominance based simulated annealing')

        print("\nPareto Front after Dominance Based Energy Improvement:")
        self.ParetoSolutions.ShowFront()
        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)

        
            





class TwoPhaseSimulatedAnnealing(ImprovementAlgorithm):
    """
    Two-Phase Simulated Annealing algorithm combining objective-focused optimization
    with dominance-based multi-objective search. First phase focuses on individual
    objectives, second phase uses dominance relationships for overall optimization.
    """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations_first:int,
                 max_iterations_second:int):
        super().__init__(inputData)

        # Temperature and cooling parameters
        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        
        # Phase-specific iteration limits
        self.MaxIterationsFirstPhase = max_iterations_first
        self.MaxIterationsSecondPhase = max_iterations_second
        
        # Algorithm parameters
        self.ScalingEnergy = 50
        self.MaxSingleMoveTries = 30
        self.ParallelRuns = 0  # Not used in this implementation --> currently single agent optimization in second phase

        # Tracking solution count over time
        self.NumberOfSolutions = {}

        # Neighborhood types with their corresponding objectives
        self.NeighborhoodTypes = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}
        
        # Complete list of optimization objectives
        self.objectives = ['driver_violation', 'commute_distance', 'transport_distance', 'attachment_distance', 'worker_count', 'machine_count', 'attachment_count']

        # Move type configuration
        self.max_traversal_moves = 1
        self.max_location_moves = 4


    def MutateSolution(self, solution: Solution) -> None:
        """
        Creates a mutated solution for population diversity.
        
        Args:
            solution: Original solution to mutate
        """
        random_number_of_moves = self.RNG.integers(2, 50)
        current_solution = solution.clone()
        self.EvaluationLogic.evaluate(current_solution)

        for _ in range(random_number_of_moves):
            move = None

            while move is None:
                random_type = self.RNG.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(current_solution)

            worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, current_solution)
            current_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
            self.EvaluationLogic.evaluate(current_solution)

        self.ParetoSolutions.UpdateParetoFront(current_solution)

    def first_phase(self, local_solution:Solution, local_pareto_front: list = None, seed = None, focused_objective: str = None) -> list[Solution]:
        """
        Executes first phase focusing on a specific objective with weighted acceptance.
        
        Args:
            local_solution: Starting solution
            local_pareto_front: Current Pareto front
            seed: Random seed for reproducibility
            focused_objective: Objective to focus optimization on
            
        Returns:
            List of solutions in local Pareto front after first phase
        """
        local_rng = np.random.default_rng(seed)

        # Track solution count over iterations
        number_of_solutions = {}
        iteration = 0
        number_of_solutions[iteration] = len(local_pareto_front)

        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData, local_rng)
        local_pareto_solutions.ParetoFront = local_pareto_front

        # Filter neighborhood types to those containing the focused objective
        valid_types = [nt for nt, objs in self.NeighborhoodTypes.items() if focused_objective in objs]
        if not valid_types:
            raise Exception(f"No neighborhood type contains the focused objective: {focused_objective}")

        while current_temperature > self.MinTemperature:

            for i in range(self.MaxIterationsFirstPhase):
                iteration += 1
                
                # Find valid move from neighborhood containing focused objective
                move = None
                tries = 0
                while move is None and tries < self.MaxSingleMoveTries:
                    n_type = local_rng.choice(valid_types)
                    neighborhood = self.CreateNeighborhood(n_type, local_rng)
                    move = neighborhood.SingleMove(local_solution, self.MaxSingleMoveTries, local_rng)
                    objectives = self.NeighborhoodTypes[n_type]
                    tries += 1
 
                if move is None:
                    continue

                # Assign higher weight to focused objective (0.7), distribute rest equally
                weights = {}
                num_other_objs = len(objectives) - 1
                for obj in objectives:
                    if obj == focused_objective:
                        weights[obj] = 0.7
                    else:
                        weights[obj] = 0.3 / num_other_objs if num_other_objs > 0 else 0.0

                # Calculate weighted delta for acceptance decision
                delta = sum(move.DeltaDetails[obj] * weights[obj] for obj in objectives)

                # Apply acceptance criteria
                if delta <= 0:
                    prob = 1.0
                else:
                    prob = math.exp(-delta * self.ScalingEnergy / current_temperature)

                random_number = local_rng.random()

                if prob < random_number:
                    continue

                # Apply move and update solution
                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, local_solution)
                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)

                # Update Pareto front and track solution count
                added = local_pareto_solutions.UpdateParetoFront(local_solution)

                if not added:
                    continue
                number_of_solutions[iteration] = len(local_pareto_solutions.ParetoFront)

            current_temperature *= self.CoolingRate

        # Save solution count progression to CSV
        df = pd.DataFrame.from_dict(number_of_solutions, orient='index', columns=['Number of Solutions'])
        df.index.name = 'Time (s)'
        df.to_csv(self.InputData.solutions_path/f'NumberOfSolutions_{focused_objective}.csv')

        return local_pareto_solutions.ParetoFront
    

    def unnormalize_value(self, value:float, objective:str) -> float:
        """
        Converts normalized objective value back to original scale.
        
        Args:
            value: Normalized value
            objective: Objective name
            
        Returns:
            Unnormalized value
        """
        if objective == 'transport_distance' or objective == 'attachment_distance':
            return value * (self.InputData.max_transport_distance - self.InputData.min_transport_distance) + self.InputData.min_transport_distance
        elif objective == 'commute_distance':
            return value * (self.InputData.max_work_distance + self.InputData.min_work_distance) + self.InputData.min_work_distance
        elif objective == 'driver_violation' or objective == 'attachment_count' or objective == 'worker_count' or objective == 'machine_count':
            return value
    
    def multiple_moves(self, solution:Solution, move_type:str, local_rng):
        """
        Applies multiple moves of specified type to solution.
        
        Args:
            solution: Solution to modify
            move_type: Type of moves ('traversal' or 'location')
            local_rng: Local random number generator
            
        Returns:
            Tuple of accumulated effects and new route plans
        """
        # Configure move count based on type
        if move_type == 'traversal':
            possible_moves = list(range(1, self.max_traversal_moves + 1))
            move_probs = [1.0 / len(possible_moves)] * len(possible_moves)
        elif move_type == 'location':
            possible_moves = list(range(self.max_traversal_moves+1, self.max_location_moves + 1))
            move_probs = [1.0 / len(possible_moves)] * len(possible_moves)

        random_number_of_moves = local_rng.choice(possible_moves, p=move_probs)

        current_solution = solution.clone()
        self.EvaluationLogic.evaluate(current_solution)
        delta_details = dict()
        objectives = set()

        # Apply multiple moves and accumulate effects
        for _ in range(random_number_of_moves):
            move = None
            while move is None:
                random_type = local_rng.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(current_solution, self.MaxSingleMoveTries, local_rng)

            # Accumulate delta values
            for obj, details in move.DeltaDetails.items():
                if obj not in delta_details:
                    delta_details[obj] = 0
                delta_details[obj] += details
                objectives.add(obj)

            # Apply move
            worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, current_solution)
            current_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
            self.EvaluationLogic.calculate_worker_count_and_utilization_time(current_solution)

        return delta_details, objectives, worker_route_plan, machine_route_plan, attachment_route_plan
    
    def second_phase(self, local_solution:Solution, local_pareto_front: list = None, seed = None) -> list[Solution]:
        """
        Executes second phase using dominance-based energy for multi-objective optimization.
        
        Args:
            local_solution: Starting solution for second phase
            local_pareto_front: Current Pareto front from first phase
            seed: Random seed for reproducibility
            
        Returns:
            List of solutions in final Pareto front
        """
        local_rng = np.random.default_rng(seed)

        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData, local_rng)
        local_pareto_solutions.ParetoFront = local_pareto_front

        # Main optimization loop
        while current_temperature > self.MinTemperature:

            for i in range(self.MaxIterationsSecondPhase):
                # Choose move type and apply multiple moves
                move_type = local_rng.choice(['traversal', 'location'])
                delta_details, objectives, worker_route_plan, machine_route_plan, attachment_route_plan = self.multiple_moves(local_solution, move_type, local_rng)
 
                # Create objective dictionary with current values
                objective_dict = {
                    "driver_violation": local_solution.driver_violation,
                    "commute_distance": local_solution.total_commute_distance,
                    "transport_distance": local_solution.total_transport_distance,
                    "attachment_distance": local_solution.total_transport_distance_attachments,
                    "worker_count": local_solution.number_of_workers,
                    "machine_count": local_solution.number_of_machines,
                    "attachment_count": local_solution.number_of_attachments
                }

                # Update affected objectives with delta values
                for objective in objectives:
                    unnormalized_value = self.unnormalize_value(delta_details[objective], objective)
                    objective_dict[objective] += unnormalized_value
           
                # Calculate dominance counts for energy
                dominating_count_current, interpolated_points = local_pareto_solutions.CountDominatingSolutions(local_solution, objective_dict_point=objective_dict)
                dominating_count_new, _ = local_pareto_solutions.CountDominatingSolutions(objective_dict, interpolated_points=interpolated_points, solution_point=local_solution)

                # Calculate energy difference based on dominance change
                overall_difference = (dominating_count_new - dominating_count_current)

                # Apply acceptance criteria
                if overall_difference <= 0:
                    prob = 1.0
                else:
                    prob = math.exp(-overall_difference / current_temperature)

                random_number = local_rng.random()

                if prob < random_number:
                    continue

                # Accept move and update solution
                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)

                # Update Pareto front if solution is non-dominated
                if dominating_count_new == 0:
                    added = local_pareto_solutions.UpdateParetoFront(local_solution)

                    if not added:
                        continue
                    # Track solution count over time
                    current_time = time.time() - self.start_time
                    self.NumberOfSolutions[current_time] = len(local_pareto_solutions.ParetoFront)

            current_temperature *= self.CoolingRate

        return local_pareto_solutions.ParetoFront


    def Run(self, solution:Solution) -> Solution:
        '''
        Executes the complete Two-Phase Simulated Annealing algorithm.
        
        Args:
            solution: Initial solution to start optimization from
            
        Returns:
            Final Pareto front after both phases
        '''
        self.start_time = time.time()
        
        # Initialize neighborhoods and add initial solution to Pareto front
        self.InitializeNeighborhoods(list(self.NeighborhoodTypes.keys()))
        self.ParetoSolutions.UpdateParetoFront(solution)

        # Track initial solution count
        self.NumberOfSolutions[0] = len(self.ParetoSolutions.ParetoFront)

        # Mutate the initial solution to create a starting population
        # Ensure we have at least one solution per objective for parallel processing
        while len(self.ParetoSolutions.ParetoFront) < len(self.objectives):
            self.MutateSolution(solution)
        print(f"Initial Solution Pool:")
        self.ParetoSolutions.ShowFront()
        
        # Record solution count after initial population creation
        current_time = time.time() - self.start_time
        self.NumberOfSolutions[current_time] = len(self.ParetoSolutions.ParetoFront)

        # FIRST PHASE: Objective-focused optimization with parallel processing
        # Each task focuses on one specific objective using weighted acceptance
        tasks = []
        with ProcessPoolExecutor() as executor:
            for i, sol in enumerate(self.ParetoSolutions.ParetoFront):
                # Clone solution for independent processing
                local_solution = sol.clone()
                seed = self.RNG.integers(0, 1_000_000)
                self.EvaluationLogic.evaluate(local_solution)
                
                # Create local Pareto front excluding current solution
                local_pareto_front = [s for s in self.ParetoSolutions.ParetoFront if s != local_solution]
                for s in local_pareto_front:
                    self.EvaluationLogic.evaluate(s)
                
                # Submit first phase task with specific objective focus
                tasks.append(
                    executor.submit(self.first_phase, local_solution, local_pareto_front, seed, self.objectives[i])
                )

        # Collect and combine results from all parallel first phase runs
        combined_solutions = []
        for result_front in [t.result() for t in tasks]:
            combined_solutions.extend(result_front)
        results = combined_solutions

        # Update Pareto front with first phase results
        self.ParetoSolutions.ParetoFront = results
        self.ParetoSolutions.PurgeParetoFront()  # Remove dominated solutions
        self.ParetoSolutions.SortParetoFront()   # Sort by objectives
        print("\nPareto Front after First Phase:")
        self.ParetoSolutions.ShowFront()

        # Select best solution and track progress
        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)
        current_time = time.time() - self.start_time
        self.NumberOfSolutions[current_time] = len(self.ParetoSolutions.ParetoFront)

        # SECOND PHASE: Dominance-based multi-objective optimization
        multiprocessing = False  # Currently disabled for second phase
        if multiprocessing:
            # Parallel execution for second phase (alternative implementation)
            tasks = []
            with ProcessPoolExecutor() as executor:
                for i in range(self.ParallelRuns):  # Run parallel second phase processes
                    # Select random solution from first phase results
                    local_solution = self.RNG.choice(self.ParetoSolutions.ParetoFront).clone()
                    seed = self.RNG.integers(0, 1_000_000)
                    self.EvaluationLogic.evaluate(local_solution)
                    local_pareto_front = [s for s in self.ParetoSolutions.ParetoFront if s != local_solution]
                    tasks.append(
                        executor.submit(self.second_phase, local_solution, local_pareto_front, seed)
                    )
            
            # Combine results from parallel second phase runs
            combined_solutions = []
            for result_front in [t.result() for t in tasks]:
                combined_solutions.extend(result_front)
            self.ParetoSolutions.ParetoFront = combined_solutions

        else:
            # Single-threaded second phase execution
            local_solution = self.RNG.choice(self.ParetoSolutions.ParetoFront).clone()
            seed = self.RNG.integers(0, 1_000_000)
            local_pareto_front = [s for s in self.ParetoSolutions.ParetoFront if s != local_solution]
            self.ParetoSolutions.ParetoFront = self.second_phase(local_solution, local_pareto_front, seed)

        # Record solution count after second phase
        current_time = time.time() - self.start_time
        self.NumberOfSolutions[current_time] = len(self.ParetoSolutions.ParetoFront)

        # Final cleanup and validation
        self.ParetoSolutions.PurgeParetoFront()  # Remove any dominated solutions
        self.ParetoSolutions.SortParetoFront()   # Sort final Pareto front

        # Verify that all final solutions are feasible
        for solution_check in self.ParetoSolutions.ParetoFront:
            feasible = solution_check.feasibility_check()
            if not feasible:
                raise Exception('Solution is not feasible after two phase simulated annealing')

        # Display final results and select best solution
        print("\nPareto Front after Second Phase:")
        self.ParetoSolutions.ShowFront()
        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)

        # Export solution count progression to CSV file
        df = pd.DataFrame.from_dict(self.NumberOfSolutions, orient='index', columns=['Number of Solutions'])
        df.index.name = 'Time (s)'
        df.to_csv(self.InputData.solutions_path/'NumberOfSolutions.csv')