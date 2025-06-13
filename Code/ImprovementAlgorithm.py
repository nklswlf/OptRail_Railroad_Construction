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
    """ Base class for several types of improvement algorithms. """ 

    def __init__(self, inputData:InputData, neighborhoodEvaluationStrategy:str = 'BestImprovement', neighborhoodTypes:list[str] = ['Insert_Shift']):
        self.InputData = inputData

        self.EvaluationLogic = {}
        self.SolutionPool = {}
        self.RNG = {}

        self.NeighborhoodEvaluationStrategy = neighborhoodEvaluationStrategy
        self.NeighborhoodTypes = neighborhoodTypes
        self.Neighborhoods = {}

    def Initialize(self, evaluationLogic:EvaluationLogic, paretoSolutions:ParetoSolutions, rng) -> None:
        ''' Initializes empty variables'''

        self.EvaluationLogic = evaluationLogic
        self.ParetoSolutions = paretoSolutions
        self.RNG = rng

    def CreateNeighborhood(self, neighborhoodType:str, local_rng=None):
        """ Creates a new neighborhood based on the current best Solution and the chosen neighborhood type.
            Similar to the so-called factory concept in software design. """
        
        ### NEEDS TO BE ADJUSTED FOR ORIENTEERING PROBLEMLocalSearch

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
        ''' Create several neighborhoods for every neighborhood in the list neighborhoodTypes'''
        
        # If no neighborhood types are passed, default to self.NeighborhoodTypes
        if neighborhoodtypes is None:
            neighborhoodtypes = self.NeighborhoodTypes

        # If no neighborhoods dict is passed, default to self.Neighborhoods
        if neighborhoods_dict is None:
            neighborhoods_dict = self.Neighborhoods

        # Iterate over the neighborhood types and create neighborhoods
        for neighborhoodType in neighborhoodtypes:
            neighborhood = self.CreateNeighborhood(neighborhoodType)
            neighborhoods_dict[neighborhoodType] = neighborhood




class IterativeImprovement(ImprovementAlgorithm):
    """ Iterative improvement algorithm through sequential variable neighborhood descent. 
        Local Search with itereative steps through many different neighborhoods.
    """

    def __init__(self,  inputData:InputData, neighborhoodEvaluationStrategy:str = 'BestImprovement', neighborhoodTypes:list[str] = ['Swap']):
        super().__init__(inputData, neighborhoodEvaluationStrategy, neighborhoodTypes)

    def Run(self, solution:Solution) -> Solution:
        ''' Run local search with given solutions and iterate through all given neighborhood types'''

        self.InitializeNeighborhoods()


        print(f'\nInitial solution: \n{solution}')


        for neighborhoodType in self.NeighborhoodTypes:

            print(f'\nRunning neighborhood {neighborhoodType}')
            neighborhood = self.Neighborhoods[neighborhoodType]


            solution = neighborhood.LocalSearch(self.NeighborhoodEvaluationStrategy, solution)

            feasible = solution.feasibility_check()

            print(f"Attachment Route Plan: {solution.route_plan_attachment}")

            if not feasible:
                raise Exception(f'Solution is not feasible after neighborhood {neighborhoodType}')

            
            print(f'\nBest (feasible) solution after {neighborhoodType}: \n{solution}')

        
        return solution




class BuildingSimulatedAnnealing(ImprovementAlgorithm):
    """ Simulated Annealing algorithm to find a fully staffed solution. """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 fallback_threshold:int,
                 scaling_energy:int):
        super().__init__(inputData)

        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.FallbackThreshold = fallback_threshold # Currently not used
        self.ScalingEnergy = scaling_energy

        self.DistanceTypes = {  'Swap_Shift_External': ['commute_distance', 'transport_distance', 'attachment_distance'],
                                'Replace_Shift_Worker': ['commute_distance'],
                                'Replace_Shift_Machine': ['transport_distance'],
                                'Replace_Shift_Attachment': ['attachment_distance'],
                                'Swap_Shift_Worker': ['commute_distance'],
                                'Swap_Shift_Machine': ['transport_distance'],
                                'Swap_Shift_Attachment': ['attachment_distance'],
                                'Insert_Shift': None}
        

        self.FulfillmentType = 'Insert_Shift'


    def Run(self, solution:Solution) -> Solution:
        ''' Run simulated annealing algorithm with given solutions and parameters'''
        
        current_temperature = self.StartTemperature
        self.InitializeNeighborhoods(list(self.DistanceTypes.keys()) + [self.FulfillmentType])


        while current_temperature > self.MinTemperature:

            print(f"\nSolution order item count: {solution.number_of_finished_order_items}")
            print(f"Solution distances: {solution.total_distance}")
            best_distance = solution.total_distance
            fallback_counter = 0

            for i in range(self.MaxIterations):

                # Check if solution is fully staffed
                if solution.total_dynamic_percentage == self.InputData.site_fulfillment:
                    print("\nFound fully staffed solution:")
                    print(solution)
                    #self.ParetoSolutions.SetReferencePoint(solution)
                    return solution

                # Randomly select a neighborhood type and create a move
                random_type = self.RNG.choice(list(self.DistanceTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(solution)
                objective = self.DistanceTypes[random_type]

                if move is None:
                    continue

                
                if objective is not None:
                    value = 0
                    for obj in objective:
                        value += move.DeltaDetails[obj]
                else:
                    value = -1

                if value <= 0:
                    pass
                elif value > 0:
                    prob = math.exp(-value * self.ScalingEnergy / current_temperature)
                    random_number = self.RNG.random()

                    if prob < random_number:
                        continue

                
                # Rethink this solution creation strategy: Compare to IM Challenge --> Changing the solution in place instead of creating a new one
                # Evaluate distances and dynamic percentage ONLY maybe
                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, solution)
                solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(solution)



            
            # Update the temperature
            current_temperature *= self.CoolingRate

        if solution.total_dynamic_percentage != self.InputData.site_fulfillment:
            raise Exception(f"Solution is not fully staffed after simulated annealing: {solution.total_dynamic_percentage} != {self.InputData.site_fulfillment}")




class ParetoSimulatedAnnealing(ImprovementAlgorithm):
    """ Simulated Annealing algorithm with individual agents to move in the solution space."""

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 fallback_threshold:int,
                 scaling_energy:int,
                 weight_alpha:float,
                 max_single_move_tries:int,
                 start_size_population:int):
        super().__init__(inputData)

        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.FallbackThreshold = 0 # Currently not used
        self.ScalingEnergy = scaling_energy

        self.MaxSingleMoveTries = max_single_move_tries
        self.SizeStartPopulation = start_size_population
        self.WeightAlpha = weight_alpha


        self.NeighborhoodTypes = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}
        
        self.objectives = ['driver_violation', 'commute_distance', 'transport_distance', 'attachment_distance', 'worker_count', 'machine_count', 'attachment_count']



    def MutateSolution(self, solution: Solution) -> None:
        ''' Mutate the solution by applying multiple moves on a copy of the original '''

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
 

    def normalize_objectives(self, population, objectives, attr_mapping):
        min_vals = {}
        max_vals = {}
        for obj in objectives:
            values = [getattr(sol, attr_mapping.get(obj, obj), 0) for sol in population]
            min_vals[obj] = min(values)
            max_vals[obj] = max(values)
        return min_vals, max_vals

    def get_normalized_values(self, solution, objectives, attr_mapping, min_vals, max_vals):
        norm_values = {}
        for obj in objectives:
            raw = getattr(solution, attr_mapping.get(obj, obj), 0)
            range_ = max_vals[obj] - min_vals[obj]
            norm_values[obj] = (raw - min_vals[obj]) / range_ if range_ > 0 else 0.0
        return norm_values


    def update_weights(self, x, population, objectives, previous_weights, local_rng):
        ''' Update weights for the objectives based on the current solution and the population '''

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
            better_in_a = False
            better_in_b = False
            for obj in objectives:
                if a[obj] < b[obj]:
                    better_in_a = True
                elif a[obj] > b[obj]:
                    better_in_b = True

            # non-dominating == True
            return better_in_a and better_in_b

        def distance(a, b):
            return sum(abs(a[obj] - b[obj]) for obj in objectives)

        min_vals, max_vals = self.normalize_objectives(population + [x], objectives, attr_mapping)
        x_values = self.get_normalized_values(x, objectives, attr_mapping, min_vals, max_vals)

        candidates = []
        for x_ in population:
            if x_ == x:
                continue
            x__values = self.get_normalized_values(x_, objectives, attr_mapping, min_vals, max_vals)
            if non_dominating(x_values, x__values):
                candidates.append((x_, distance(x_values, x__values)))

        if not candidates:
            weights = {obj: local_rng.random() for obj in objectives}
        else:
            x_prime, _ = min(candidates, key=lambda tup: tup[1])
            x_prime_values = self.get_normalized_values(x_prime, objectives, attr_mapping, min_vals, max_vals)

            weights = {}
            for obj in objectives:
                if x_values[obj] >= x_prime_values[obj]:
                    weights[obj] = self.WeightAlpha * previous_weights[obj]
                elif x_values[obj] < x_prime_values[obj]:
                    weights[obj] = previous_weights[obj] / self.WeightAlpha
                else:
                    raise Exception(f"Objective {obj} not defined.")
                    weights[obj] = 1.0

        for obj in self.objectives:
            if obj not in weights:
                weights[obj] = previous_weights[obj] * self.WeightAlpha
    
        # Normalisierung
        total = sum(weights.values())
        normalized_weights = {k: v / total for k, v in weights.items()}

        #print(f"Normalized weights: {normalized_weights}")


        return normalized_weights



    def psa_iteration(self, info: dict, T: float, S_snapshot: list):
        x = info["solution"]
        weights_dict = info["weights"]
        seed = info["seed"]
        same_seed = info["same seed"]
        agent_id = info["id"]
        local_rng = np.random.default_rng(seed)
        #local_same_rng = np.random.default_rng(same_seed)

        profiled = info.get("profiled", False)

        # Wenn profiled==False → einmalig Profiling aktivieren
        #if not profiled:
        #    profiler = cProfile.Profile()
        #    profiler.enable()
        #else:
        #    profiler = None


        move = None
        tries = 0
        while move is None and tries < self.MaxSingleMoveTries:
            n_type = local_rng.choice(list(self.NeighborhoodTypes.keys()))
            neighborhood = self.CreateNeighborhood(n_type, local_rng)
            move = neighborhood.SingleMove(x, self.MaxSingleMoveTries, local_rng)
            tries += 1

        objectives = self.NeighborhoodTypes[n_type]
        weights = self.update_weights(x, S_snapshot, objectives, weights_dict, local_rng)
        delta = sum(weights[obj] * move.DeltaDetails[obj] for obj in objectives)

        if delta > 0:
            p = math.exp(-delta * self.ScalingEnergy / T)
            if local_rng.random() > p:

                return {
                        "solution": x,
                        "new_solution": None,
                        "weights": weights,
                        "seed": seed + 1,
                        "same seed": same_seed + 1,
                        "id": agent_id
                    }

        w, m, a = neighborhood.constructCompleteRoutes(move, x)
        x_new = Solution(w, m, a, self.InputData)
        self.EvaluationLogic.evaluate(x_new)

        # Falls Profiling aktiviert war
        #if profiler is not None:
        #    profiler.disable()
        #    Path("Profiler/PSA/Agents").mkdir(parents=True, exist_ok=True)
        #    profile_path = Path(f"Profiler/PSA/Agents/agent_{agent_id}.prof")

        #    if profile_path.exists():
        #        existing_stats = pstats.Stats(str(profile_path))
        #        new_stats = pstats.Stats(profiler)
        #        existing_stats.add(new_stats)
        #        existing_stats.dump_stats(str(profile_path))
        #    else:
        #        profiler.dump_stats(str(profile_path))



        return {
                    "solution": x,
                    "new_solution": x_new,
                    "weights": weights,
                    "seed": seed + 1,
                    "same seed": same_seed + 1,
                    "id": agent_id,
                    "profiled": True  # <- hinzugefügt
                }

    def Run(self, solution: Solution) -> Solution:
        #profiler = cProfile.Profile()
        #profiler.enable()
        ''' Run simulated annealing algorithm with given solutions and parameters '''
        self.InitializeNeighborhoods(list(self.NeighborhoodTypes.keys()))
        self.ParetoSolutions.UpdateParetoFront(solution)
        

        while len(self.ParetoSolutions.ParetoFront) < self.SizeStartPopulation:
            self.MutateSolution(solution)
        print(f"Initial Solution Pool:")
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()

        current_temperature = self.StartTemperature

        S_info = []
        same_seed = self.RNG.integers(0, 1_000_000)
        for i, x in enumerate(self.ParetoSolutions.ParetoFront):
            x.id = i
            weights = {obj: self.RNG.random() for obj in self.objectives}
            seed = self.RNG.integers(0, 1_000_000)

            S_info.append({
                "solution": deepcopy(x),
                "weights": weights,
                "seed": seed,
                "same seed": same_seed,
                "id": i,
                "profiled": False  # <- hinzugefügt
            })
        with ThreadPoolExecutor(max_workers=self.SizeStartPopulation) as executor:
            while current_temperature > self.MinTemperature:
                
                for i in range(self.MaxIterations):
                    tasks = []

                    
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

                    
                    new_S_info = results

                    for info in new_S_info:
                        if info["new_solution"] is not None:
                            self.ParetoSolutions.UpdateParetoFront(info["new_solution"])
                            info["solution"] = info["new_solution"]

                    S_info = new_S_info

    
                current_temperature *= self.CoolingRate


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
    """ Simulated Annealing algorithm with dominance based energy. """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 fallback_threshold:int,
                 scaling_energy:int,
                 max_single_move_tries:int,
                 parallel_runs:int):
        super().__init__(inputData)

        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.FallbackThreshold = 0 # Currently not used
        self.ScalingEnergy = None # Currently not used
        self.MaxSingleMoveTries = max_single_move_tries
        self.ParallelRuns = parallel_runs

        self.max_traversal_moves = 1
        self.max_location_moves = 4
        self.fallback_strategy = None # Currently not used # 'random' or 'best'


        self.NeighborhoodTypes = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}

        self.None_Move_Counter = {}
        self.Move_Counter = {}
        for neighborhoodType in self.NeighborhoodTypes:
            self.None_Move_Counter[neighborhoodType] = 0
            self.Move_Counter[neighborhoodType] = 0
            


    def MutateSolution(self, solution: Solution) -> None:
        ''' Mutate the solution by applying multiple moves on a copy of the original '''

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

    def log(self, text: str):
        with open(self.log_path, "a") as f:
            f.write(text + "\n")

 
    def multiple_moves(self, solution:Solution, move_type:str, local_rng):

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

        for _ in range(random_number_of_moves):
            move = None
            while move is None:
                random_type = local_rng.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                self.Move_Counter[random_type] += 1

                move = neighborhood.SingleMove(current_solution, self.MaxSingleMoveTries, local_rng)

                if move is None:
                    self.None_Move_Counter[random_type] += 1
    

            for obj, details in move.DeltaDetails.items():
                if obj not in delta_details:
                    delta_details[obj] = 0
                delta_details[obj] += details
                objectives.add(obj)


            worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, current_solution)
            current_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
            self.EvaluationLogic.calculate_worker_count_and_utilization_time(current_solution)



        
        return delta_details,objectives, worker_route_plan, machine_route_plan, attachment_route_plan
    

    def unnormalize_value(self, value:float, objective:str) -> float:

        ''' Unnormalize the value based on the objective type '''

        if objective == 'transport_distance' or objective == 'attachment_distance':
            return value * (self.InputData.max_transport_distance - self.InputData.min_transport_distance) + self.InputData.min_transport_distance
        elif objective == 'commute_distance':
            return value * (self.InputData.max_work_distance + self.InputData.min_work_distance) + self.InputData.min_work_distance
        elif objective == 'driver_violation' or objective == 'attachment_count' or objective == 'worker_count' or objective == 'machine_count':
            return value
   

        
        raise Exception(f"Objective {objective} not defined.")

    
    def DBSA(self, local_solution:Solution, local_pareto_front: list = None, seed = None) -> list[Solution]:
        #profiler = cProfile.Profile()
        #profiler.enable()
        ''' Run simulated annealing algorithm with given solutions and parameters'''
        ''' Simulated annealing algorithm with energy dominance neighborhood'''
        #profiler = cProfile.Profile()
        #profiler.enable()

        local_rng = np.random.default_rng(seed)

        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData,  local_rng)
        local_pareto_solutions.ParetoFront = local_pareto_front

        current_temperature = self.StartTemperature

        fallback_counter = 0

        while current_temperature > self.MinTemperature:

            for i in range(self.MaxIterations):

                neighborhoodType = local_rng.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[neighborhoodType]
                objectives = self.NeighborhoodTypes[neighborhoodType]

                move_type = local_rng.choice(['traversal', 'location'])
    
                delta_details, objectives, worker_route_plan, machine_route_plan, attachment_route_plan = self.multiple_moves(local_solution, move_type, local_rng)
 
            
                # Alle Ziele initial aus der aktuellen Lösung übernehmen
                objective_dict = {
                    "driver_violation": local_solution.driver_violation,
                    "commute_distance": local_solution.total_commute_distance,
                    "transport_distance": local_solution.total_transport_distance,
                    "attachment_distance": local_solution.total_transport_distance_attachments,
                    "worker_count": local_solution.number_of_workers,
                    "machine_count": local_solution.number_of_machines,
                    "attachment_count": local_solution.number_of_attachments
                }

                # Die betroffenen Ziele aktualisieren
                for objective in objectives:
                    unnormalized_value = self.unnormalize_value(delta_details[objective], objective)
                    objective_dict[objective] += unnormalized_value
           
                # Possible to combine objectives to 3 main topics: distance, ressource count, violation

                dominating_count_current, interpolated_points = local_pareto_solutions.CountDominatingSolutions(local_solution, objective_dict_point=objective_dict)
                dominating_count_new, _ = local_pareto_solutions.CountDominatingSolutions(objective_dict, interpolated_points=interpolated_points, solution_point=local_solution)

                if local_solution in local_pareto_solutions.ParetoFront:
                    lenght = len(local_pareto_solutions.ParetoFront) + len(interpolated_points) + 1
                else:
                    lenght = len(local_pareto_solutions.ParetoFront) + len(interpolated_points) + 2

                overall_difference = (dominating_count_new - dominating_count_current) #/ lenght


                if overall_difference <= 0:
                    prob = 1.0
                else:
                    prob =  math.exp(-overall_difference / current_temperature)


                random_number = local_rng.random()

                
                if prob < random_number:
                    continue

                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)

                if dominating_count_new == 0:
                    added = local_pareto_solutions.UpdateParetoFront(local_solution)
                    if not added:
                        fallback_counter += 1
                    else:
                        fallback_counter = 0
                else:
                    fallback_counter += 1

                if fallback_counter >= self.FallbackThreshold:
                    if self.fallback_strategy == 'random':
                        # Select a random solution from the Pareto front
                        local_solution = local_rng.choice(local_pareto_solutions.ParetoFront)
                    elif self.fallback_strategy == 'best':
                        # Select the best solution from the Pareto front
                        local_solution = local_pareto_solutions.SelectRandomBestSolution()


            current_temperature *= self.CoolingRate

        #profiler.disable()
        #Path("Profiler/DBSA/Agents").mkdir(parents=True, exist_ok=True)
        #profile_path = Path(f"Profiler/DBSA/Agents/agent_{os.getpid()}.prof")

        # Profil anhängen oder neu speichern
        #if profile_path.exists():
        #    existing = pstats.Stats(str(profile_path))
        #    new = pstats.Stats(profiler)
        #    existing.add(new)
        #    existing.dump_stats(str(profile_path))
        #else:
        #    profiler.dump_stats(str(profile_path))

        return local_pareto_solutions.ParetoFront
        
    def _dbsa_with_counts(self, solution: Solution, pareto_front: list, seed) -> tuple[list[Solution], dict, dict]:
        """
        Wrapper to run DBSA in-process and capture the Move counters.
        Returns: (pareto_front, Move_Counter copy, None_Move_Counter copy)
        """
        result_front = self.DBSA(solution, pareto_front, seed)
        # copy counters to send back to the parent
        mov = self.Move_Counter.copy()
        none = self.None_Move_Counter.copy()

        return result_front, mov, none

    def Run(self, solution: Solution) -> Solution:
        #profiler = cProfile.Profile()
        #profiler.enable()
        ''' Run simulated annealing algorithm with given solutions and parameters '''
        self.InitializeNeighborhoods(list(self.NeighborhoodTypes.keys()))
        self.ParetoSolutions.UpdateParetoFront(solution)

        while len(self.ParetoSolutions.ParetoFront) < self.ParallelRuns:
            self.MutateSolution(solution)
        print(f"Initial Solution Pool:")
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()

        if len(self.ParetoSolutions.ParetoFront) != self.ParallelRuns:
            raise Exception(f"Not enough solutions in Pareto Front: {len(self.ParetoSolutions.ParetoFront)}")

        # ===== parallel execution with counter aggregation =====
        tasks = []
        with ProcessPoolExecutor() as executor:
            for sol in self.ParetoSolutions.ParetoFront:
                local_solution = sol.clone()
                seed = self.RNG.integers(0, 1_000_000)
                self.EvaluationLogic.evaluate(local_solution)
                local_pareto_front = [s for s in self.ParetoSolutions.ParetoFront if s != local_solution]
                for s in local_pareto_front:
                    self.EvaluationLogic.evaluate(s)
                # submit wrapper that returns both front and counters
                tasks.append(
                    executor.submit(self._dbsa_with_counts, local_solution, local_pareto_front, seed)
                )

        combined_solutions = []
        # collect results and sum up counters
        for result_front, mov_counts, none_counts in [t.result() for t in tasks]:
            combined_solutions.extend(result_front)
            for nt, c in mov_counts.items():
                self.Move_Counter[nt] += c
            for nt, c in none_counts.items():
                self.None_Move_Counter[nt] += c
        results = combined_solutions

        # update Pareto front
        self.ParetoSolutions.ParetoFront = results
        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()

        # final logging of None vs Move counters
        for nt, count in self.None_Move_Counter.items():
            print(f"Neighborhood {nt} had {count}/{self.Move_Counter[nt]} None Moves.")

        for solution_check in self.ParetoSolutions.ParetoFront:
            feasible = solution_check.feasibility_check()
            if not feasible:
                raise Exception('Solution is not feasible after dominance based simulated annealing')

        print("\nPareto Front after Dominance Based Energy Improvement:")
        self.ParetoSolutions.ShowFront()
        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)
        #self.ParetoSolutions.CalculateParetoFrontMetrics()

        # Kombinierte Agentenprofile erzeugen
        #combined_stats = None
        #profile_files = list(Path("Profiler/DBSA/Agents").glob("agent_*.prof"))
        #for file in profile_files:
        #    stats = pstats.Stats(str(file))
        #    if combined_stats is None:
        #        combined_stats = stats
        #    else:
        #        combined_stats.add(stats)

        #with open("Profiler/DBSA/combined_agents.txt", "w") as f:
        #    combined_stats.stream = f
        #    combined_stats.strip_dirs().sort_stats("cumulative").print_stats(50)

        # Nach Zusammenfassung: alle Einzelprofile löschen
        #for file in profile_files:
        #    os.remove(file)



        #profiler.disable()
        #Path("Profiler/DBSA").mkdir(parents=True, exist_ok=True)
        #with open("Profiler/DBSA/run_profile.txt", "w") as f:
        #    ps = pstats.Stats(profiler, stream=f)
        #    ps.strip_dirs().sort_stats("cumulative").print_stats(50)

        
            





class TwoPhaseSimulatedAnnealing(ImprovementAlgorithm):
    """  """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 fallback_threshold:int,
                 scaling_energy:int,
                 max_single_move_tries:int,
                 parallel_runs:int):
        super().__init__(inputData)

        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.FallbackThreshold = 0 # Currently not used
        self.ScalingEnergy = scaling_energy

        self.MaxSingleMoveTries = max_single_move_tries
        self.ParallelRuns = parallel_runs
        


        self.NeighborhoodTypes = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}
        
        self.objectives = ['driver_violation', 'commute_distance', 'transport_distance', 'attachment_distance', 'worker_count', 'machine_count', 'attachment_count']


        self.max_traversal_moves = 1
        self.max_location_moves = 4


    def MutateSolution(self, solution: Solution) -> None:
        ''' Mutate the solution by applying multiple moves on a copy of the original '''

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
        ''' Run first phase of simulated annealing algorithm with given solutions and parameters'''

        local_rng = np.random.default_rng(seed)

        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData,  local_rng)
        local_pareto_solutions.ParetoFront = local_pareto_front

        current_temperature = self.StartTemperature

        # Only choose a neighborhoodType that includes the focused_objective
        valid_types = [nt for nt, objs in self.NeighborhoodTypes.items() if focused_objective in objs]
        if not valid_types:
            raise Exception(f"No neighborhood type contains the focused objective: {focused_objective}")

        while current_temperature > self.MinTemperature:

            for i in range(self.MaxIterations):

                
                neighborhoodType = local_rng.choice(valid_types)
                objectives = self.NeighborhoodTypes[neighborhoodType]

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

                # Assign weights: focused objective gets 0.7, rest share 0.3 equally
                weights = {}
                num_other_objs = len(objectives) - 1
                for obj in objectives:
                    if obj == focused_objective:
                        weights[obj] = 0.7
                    else:
                        weights[obj] = 0.3 / num_other_objs if num_other_objs > 0 else 0.0

                delta = sum(move.DeltaDetails[obj] * weights[obj] for obj in objectives)


                if delta <= 0:
                    prob = 1.0
                else:
                    prob =  math.exp(-delta * self.ScalingEnergy / current_temperature)


                random_number = local_rng.random()

                
                if prob < random_number:
                    continue

                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, local_solution)
                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)

                local_pareto_solutions.UpdateParetoFront(local_solution)


            current_temperature *= self.CoolingRate


        return local_pareto_solutions.ParetoFront
    

    def unnormalize_value(self, value:float, objective:str) -> float:

        ''' Unnormalize the value based on the objective type '''

        if objective == 'transport_distance' or objective == 'attachment_distance':
            return value * (self.InputData.max_transport_distance - self.InputData.min_transport_distance) + self.InputData.min_transport_distance
        elif objective == 'commute_distance':
            return value * (self.InputData.max_work_distance + self.InputData.min_work_distance) + self.InputData.min_work_distance
        elif objective == 'driver_violation' or objective == 'attachment_count' or objective == 'worker_count' or objective == 'machine_count':
            return value
    
    def multiple_moves(self, solution:Solution, move_type:str, local_rng):

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

        for _ in range(random_number_of_moves):
            move = None
            while move is None:
                random_type = local_rng.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
            
                move = neighborhood.SingleMove(current_solution, self.MaxSingleMoveTries, local_rng)


    

            for obj, details in move.DeltaDetails.items():
                if obj not in delta_details:
                    delta_details[obj] = 0
                delta_details[obj] += details
                objectives.add(obj)


            worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, current_solution)
            current_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
            self.EvaluationLogic.calculate_worker_count_and_utilization_time(current_solution)



        
        return delta_details,objectives, worker_route_plan, machine_route_plan, attachment_route_plan
    
    def second_phase(self, local_solution:Solution, local_pareto_front: list = None, seed = None) -> list[Solution]:
        ''' Run simulated annealing algorithm with given solutions and parameters'''

        local_rng = np.random.default_rng(seed)

        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData,  local_rng)
        local_pareto_solutions.ParetoFront = local_pareto_front

        current_temperature = self.StartTemperature


        while current_temperature > self.MinTemperature:

            for i in range(self.MaxIterations):

                move_type = local_rng.choice(['traversal', 'location'])
    
                delta_details, objectives, worker_route_plan, machine_route_plan, attachment_route_plan = self.multiple_moves(local_solution, move_type, local_rng)
 
            
                # Alle Ziele initial aus der aktuellen Lösung übernehmen
                objective_dict = {
                    "driver_violation": local_solution.driver_violation,
                    "commute_distance": local_solution.total_commute_distance,
                    "transport_distance": local_solution.total_transport_distance,
                    "attachment_distance": local_solution.total_transport_distance_attachments,
                    "worker_count": local_solution.number_of_workers,
                    "machine_count": local_solution.number_of_machines,
                    "attachment_count": local_solution.number_of_attachments
                }

                # Die betroffenen Ziele aktualisieren
                for objective in objectives:
                    unnormalized_value = self.unnormalize_value(delta_details[objective], objective)
                    objective_dict[objective] += unnormalized_value
           
                # Possible to combine objectives to 3 main topics: distance, ressource count, violation

                dominating_count_current, interpolated_points = local_pareto_solutions.CountDominatingSolutions(local_solution, objective_dict_point=objective_dict)
                dominating_count_new, _ = local_pareto_solutions.CountDominatingSolutions(objective_dict, interpolated_points=interpolated_points, solution_point=local_solution)


                overall_difference = (dominating_count_new - dominating_count_current) #/ lenght


                if overall_difference <= 0:
                    prob = 1.0
                else:
                    prob =  math.exp(-overall_difference / current_temperature)


                random_number = local_rng.random()

                
                if prob < random_number:
                    continue

                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)

                if dominating_count_new == 0:
                    local_pareto_solutions.UpdateParetoFront(local_solution)


            current_temperature *= self.CoolingRate


        return local_pareto_solutions.ParetoFront


    def Run(self, solution:Solution) -> Solution:
        ''' Run simulated annealing algorithm with given solutions and parameters'''

        # Initialize Model
        self.InitializeNeighborhoods(list(self.NeighborhoodTypes.keys()))
        self.ParetoSolutions.UpdateParetoFront(solution)

        # Mutate the initial solution to create a starting population
        while len(self.ParetoSolutions.ParetoFront) < len(self.objectives):
            self.MutateSolution(solution)
        print(f"Initial Solution Pool:")
        self.ParetoSolutions.ShowFront()


        # First Phase
        tasks = []
        with ProcessPoolExecutor() as executor:
            for i,sol in enumerate(self.ParetoSolutions.ParetoFront):
                local_solution = sol.clone()
                seed = self.RNG.integers(0, 1_000_000)
                self.EvaluationLogic.evaluate(local_solution)
                local_pareto_front = [s for s in self.ParetoSolutions.ParetoFront if s != local_solution]
                for s in local_pareto_front:
                    self.EvaluationLogic.evaluate(s)
                tasks.append(
                    executor.submit(self.first_phase, local_solution, local_pareto_front, seed, self.objectives[i])
                )

        combined_solutions = []
        for result_front in [t.result() for t in tasks]:
            combined_solutions.extend(result_front)
        results = combined_solutions

        self.ParetoSolutions.ParetoFront = results
        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()
        print("\nPareto Front after First Phase:")
        self.ParetoSolutions.ShowFront()

        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)


        # Second Phase
        tasks = []
        with ProcessPoolExecutor() as executor:
            for i in range(self.ParallelRuns):
                local_solution = self.RNG.choice(self.ParetoSolutions.ParetoFront).clone()
                seed = self.RNG.integers(0, 1_000_000)
                self.EvaluationLogic.evaluate(local_solution)
                local_pareto_front = [s for s in self.ParetoSolutions.ParetoFront if s != local_solution]
                tasks.append(
                    executor.submit(self.second_phase, local_solution, local_pareto_front, seed)
                )
        
        
        combined_solutions = []
        for result_front in [t.result() for t in tasks]:
            combined_solutions.extend(result_front)
        self.ParetoSolutions.ParetoFront = combined_solutions
        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()

        for solution_check in self.ParetoSolutions.ParetoFront:
            feasible = solution_check.feasibility_check()
            if not feasible:
                raise Exception('Solution is not feasible after two phase simulated annealing')

        print("\nPareto Front after Second Phase:")
        self.ParetoSolutions.ShowFront()
        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)

        

        










class ParetoSimulatedAnnealing_archive_setter(ImprovementAlgorithm):
    """ Simulated Annealing algorithm to find a fully staffed solution. """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 fallback_threshold:int,
                 scaling_energy:int,
                 weight_alpha:float,
                 max_single_move_tries:int,
                 start_size_population:int):
        super().__init__(inputData)

        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.FallbackThreshold = fallback_threshold # Currently not used
        self.ScalingEnergy = scaling_energy

        self.MaxSingleMoveTries = max_single_move_tries
        self.SizeStartPopulation = start_size_population
        self.WeightAlpha = weight_alpha


        self.NeighborhoodTypes = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}
        
        self.PreviousWeight = {  'driver_violation': 1.0,
                                'commute_distance': 1.0,
                                'transport_distance': 1.0,
                                'attachment_distance': 1.0,
                                'worker_count': 1.0,
                                'machine_count': 1.0,
                                'attachment_count': 1.0}
        
        self.objectives = ['driver_violation', 'commute_distance', 'transport_distance', 'attachment_distance', 'worker_count', 'machine_count', 'attachment_count']


    def MutateSolution(self, solution: Solution) -> None:
        ''' Mutate the solution by applying multiple moves on a copy of the original '''

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
 

    def normalize_objectives(self, population, objectives, attr_mapping):
        min_vals = {}
        max_vals = {}
        for obj in objectives:
            values = [getattr(sol, attr_mapping.get(obj, obj), 0) for sol in population]
            min_vals[obj] = min(values)
            max_vals[obj] = max(values)
        return min_vals, max_vals

    def get_normalized_values(self, solution, objectives, attr_mapping, min_vals, max_vals):
        norm_values = {}
        for obj in objectives:
            raw = getattr(solution, attr_mapping.get(obj, obj), 0)
            range_ = max_vals[obj] - min_vals[obj]
            norm_values[obj] = (raw - min_vals[obj]) / range_ if range_ > 0 else 0.0
        return norm_values


    def update_weights(self, x, population, objectives, local_rng):
        ''' Update weights for the objectives based on the current solution and the population '''

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
            better_in_a = False
            better_in_b = False
            for obj in objectives:
                if a[obj] < b[obj]:
                    better_in_a = True
                elif a[obj] > b[obj]:
                    better_in_b = True

            # non-dominating == True
            return better_in_a and better_in_b

        def distance(a, b):
            return sum(abs(a[obj] - b[obj]) for obj in objectives)

        min_vals, max_vals = self.normalize_objectives(population + [x], objectives, attr_mapping)
        x_values = self.get_normalized_values(x, objectives, attr_mapping, min_vals, max_vals)

        candidates = []
        for x_ in population:
            if x_ == x:
                continue
            x__values = self.get_normalized_values(x_, objectives, attr_mapping, min_vals, max_vals)
            if non_dominating(x_values, x__values):
                candidates.append((x_, distance(x_values, x__values)))

        if not candidates:
            weights = {obj: local_rng.random() for obj in objectives}
        else:
            x_prime, _ = min(candidates, key=lambda tup: tup[1])
            x_prime_values = self.get_normalized_values(x_prime, objectives, attr_mapping, min_vals, max_vals)

            weights = {}
            for obj in objectives:
                if x_values[obj] >= x_prime_values[obj]:
                    weights[obj] = self.WeightAlpha * self.PreviousWeight[obj]
                elif x_values[obj] < x_prime_values[obj]:
                    weights[obj] = self.PreviousWeight[obj] / self.WeightAlpha
                else:
                    raise Exception(f"Objective {obj} not defined.")
                    weights[obj] = 1.0

        for obj in self.objectives:
            if obj not in weights:
                weights[obj] = self.PreviousWeight[obj] * self.WeightAlpha
    
        # Normalisierung
        total = sum(weights.values())
        normalized_weights = {k: v / total for k, v in weights.items()}

        # Update previous weights
        for obj in objectives:
            self.PreviousWeight[obj] = normalized_weights[obj]

        return normalized_weights

    def PSA(self, local_solution: Solution, local_pareto_front: list, seed: int) -> list[Solution]:
        profiler = cProfile.Profile()
        profiler.enable()

        local_rng = np.random.default_rng(seed)

        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData)
        local_pareto_solutions.ParetoFront = local_pareto_front

        while current_temperature > self.MinTemperature:
            for i in range(self.MaxIterations):
                
                move = None
                while move is None:
                    random_type = local_rng.choice(list(self.NeighborhoodTypes.keys()))
                    neighborhood = self.Neighborhoods[random_type]
                    move = neighborhood.SingleMove(local_solution, self.MaxSingleMoveTries)

                objectives = self.NeighborhoodTypes[random_type]
                weights = self.update_weights(local_solution, local_pareto_solutions.ParetoFront, objectives, local_rng)

                value = sum(weights[obj] * move.DeltaDetails[obj] for obj in objectives)
                
                if value >= 0:
                    prob = math.exp(-value * self.ScalingEnergy / current_temperature)
                    if local_rng.random() > prob:
                        continue

                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, local_solution)
                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)
                local_pareto_solutions.UpdateParetoFront(local_solution)

            current_temperature *= self.CoolingRate

        (Path("Profiler") / "PSA").mkdir(parents=True, exist_ok=True)
        profile_path_txt = Path("Profiler") / "PSA" / f"psa_profile_{os.getpid()}.txt"
        with open(profile_path_txt, "w") as f:
            ps = pstats.Stats(profiler, stream=f)
            ps.sort_stats("cumulative").print_stats()

        return local_pareto_solutions.ParetoFront

    def Run(self, solution: Solution) -> Solution:
        ''' Run simulated annealing algorithm with given solutions and parameters '''


        self.InitializeNeighborhoods(list(self.NeighborhoodTypes.keys()))

        self.ParetoSolutions.UpdateParetoFront(solution)

        while len(self.ParetoSolutions.ParetoFront) < self.SizeStartPopulation:
            self.MutateSolution(solution)
        print(f"Initial Solution Pool:")
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()
        

        if len(self.ParetoSolutions.ParetoFront) != self.SizeStartPopulation:
            raise Exception(f"Not enough solutions in Pareto Front: {len(self.ParetoSolutions.ParetoFront)}")

        tasks = []
        seeds = [self.RNG.integers(0, 1_000_000) for _ in range(len(self.ParetoSolutions.ParetoFront))]
        with ProcessPoolExecutor() as executor:
            for solution in self.ParetoSolutions.ParetoFront:
                local_solution = solution.clone()
                self.EvaluationLogic.evaluate(local_solution)
                local_pareto_front = [sol for sol in self.ParetoSolutions.ParetoFront if sol != local_solution]
                for sol in local_pareto_front:
                    self.EvaluationLogic.evaluate(sol)
                tasks.append(executor.submit(self.PSA, local_solution, local_pareto_front, seeds.pop(0)))
            results: list[list[Solution]] = [task.result() for task in tasks]


        combined_solutions = [sol for sublist in results for sol in sublist]

        self.ParetoSolutions.ParetoFront = combined_solutions
        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()

        for solution in self.ParetoSolutions.ParetoFront:
            feasible = solution.feasibility_check()
            if not feasible:
                raise Exception('Solution is not feasible after pareto simulated annealing')

        print("\nFinal Pareto Front:")
        self.ParetoSolutions.ShowFront()
        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)
        #self.ParetoSolutions.CalculateParetoFrontMetrics()

class ParetoSimulatedAnnealing_global_archive_setter(ImprovementAlgorithm):
    """ Simulated Annealing algorithm to find a fully staffed solution. """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 fallback_threshold:int,
                 scaling_energy:int,
                 weight_alpha:float,
                 max_single_move_tries:int,
                 start_size_population:int):
        super().__init__(inputData)

        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.FallbackThreshold = fallback_threshold # Currently not used
        self.ScalingEnergy = scaling_energy

        self.MaxSingleMoveTries = max_single_move_tries
        self.SizeStartPopulation = start_size_population
        self.WeightAlpha = weight_alpha


        self.NeighborhoodTypes = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}
        
        self.objectives = ['driver_violation', 'commute_distance', 'transport_distance', 'attachment_distance', 'worker_count', 'machine_count', 'attachment_count']



    def MutateSolution(self, solution: Solution) -> None:
        ''' Mutate the solution by applying multiple moves on a copy of the original '''

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
 

    def normalize_objectives(self, population, objectives, attr_mapping):
        min_vals = {}
        max_vals = {}
        for obj in objectives:
            values = [getattr(sol, attr_mapping.get(obj, obj), 0) for sol in population]
            min_vals[obj] = min(values)
            max_vals[obj] = max(values)
        return min_vals, max_vals

    def get_normalized_values(self, solution, objectives, attr_mapping, min_vals, max_vals):
        norm_values = {}
        for obj in objectives:
            raw = getattr(solution, attr_mapping.get(obj, obj), 0)
            range_ = max_vals[obj] - min_vals[obj]
            norm_values[obj] = (raw - min_vals[obj]) / range_ if range_ > 0 else 0.0
        return norm_values


    def update_weights(self, x, population, objectives, previous_weights, local_rng):
        ''' Update weights for the objectives based on the current solution and the population '''

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
            better_in_a = False
            better_in_b = False
            for obj in objectives:
                if a[obj] < b[obj]:
                    better_in_a = True
                elif a[obj] > b[obj]:
                    better_in_b = True

            # non-dominating == True
            return better_in_a and better_in_b

        def distance(a, b):
            return sum(abs(a[obj] - b[obj]) for obj in objectives)

        min_vals, max_vals = self.normalize_objectives(population + [x], objectives, attr_mapping)
        x_values = self.get_normalized_values(x, objectives, attr_mapping, min_vals, max_vals)

        candidates = []
        for x_ in population:
            if x_ == x:
                continue
            x__values = self.get_normalized_values(x_, objectives, attr_mapping, min_vals, max_vals)
            if non_dominating(x_values, x__values):
                candidates.append((x_, distance(x_values, x__values)))

        if not candidates:
            weights = {obj: local_rng.random() for obj in objectives}
        else:
            x_prime, _ = min(candidates, key=lambda tup: tup[1])
            x_prime_values = self.get_normalized_values(x_prime, objectives, attr_mapping, min_vals, max_vals)

            weights = {}
            for obj in objectives:
                if x_values[obj] >= x_prime_values[obj]:
                    weights[obj] = self.WeightAlpha * previous_weights[obj]
                elif x_values[obj] < x_prime_values[obj]:
                    weights[obj] = previous_weights[obj] / self.WeightAlpha
                else:
                    raise Exception(f"Objective {obj} not defined.")
                    weights[obj] = 1.0

        for obj in self.objectives:
            if obj not in weights:
                weights[obj] = previous_weights[obj] * self.WeightAlpha
    
        # Normalisierung
        total = sum(weights.values())
        normalized_weights = {k: v / total for k, v in weights.items()}

        #print(f"Normalized weights: {normalized_weights}")


        return normalized_weights



    def psa_iteration(self, info: dict, T: float, S_snapshot: list):
        x = info["solution"]
        weights_dict = info["weights"]
        seed = info["seed"]
        agent_id = info["id"]
        local_rng = np.random.default_rng(seed)

        identifier = getattr(x, "id", os.getpid())
        profile = cProfile.Profile()
        profile.enable()

        move = None
        tries = 0
        while move is None and tries < self.MaxSingleMoveTries:
            n_type = local_rng.choice(list(self.NeighborhoodTypes.keys()))
            neighborhood = self.CreateNeighborhood(n_type, local_rng)
            move = neighborhood.SingleMove(x, self.MaxSingleMoveTries, local_rng)
            tries += 1

        objectives = self.NeighborhoodTypes[n_type]
        weights = self.update_weights(x, S_snapshot, objectives, weights_dict, local_rng)
        delta = sum(weights[obj] * move.DeltaDetails[obj] for obj in objectives)

        if delta >= 0:
            p = math.exp(-delta * self.ScalingEnergy / T)
            if local_rng.random() > p:
                profile.disable()
                return {
                        "solution": x,
                        "new_solution": None,
                        "weights": weights,
                        "seed": seed + 1,
                        "id": agent_id
                    }

        w, m, a = neighborhood.constructCompleteRoutes(move, x)
        x_new = Solution(w, m, a, self.InputData)
        self.EvaluationLogic.evaluate(x_new)

        profile.disable()
        Path("Profiler/Agents").mkdir(parents=True, exist_ok=True)
        profile_path = Path(f"Profiler/Agents/agent_{identifier}_seed_{seed}.prof")

        # Kumulativ zusammenführen, falls Datei existiert
        if profile_path.exists():
            existing_stats = pstats.Stats(str(profile_path))
            new_stats = pstats.Stats(profile)
            existing_stats.add(new_stats)
            existing_stats.dump_stats(str(profile_path))  # Überschreiben mit kumulierter Version
        else:
            profile.dump_stats(str(profile_path))

        # Optional: zusätzlich als lesbare Textdatei
        txt_path = Path(f"Profiler/Agents/agent_{identifier}.txt")
        with open(txt_path, "w") as f:
            ps = pstats.Stats(str(profile_path), stream=f)
            ps.strip_dirs().sort_stats("cumulative").print_stats(50)

        return {
                    "solution": x,
                    "new_solution": x_new,
                    "weights": weights,
                    "seed": seed + 1,
                    "id": agent_id
                }

    def Run(self, solution: Solution) -> Solution:
        profiler = cProfile.Profile()
        profiler.enable()
        ''' Run simulated annealing algorithm with given solutions and parameters '''
        self.InitializeNeighborhoods(list(self.NeighborhoodTypes.keys()))
        self.ParetoSolutions.UpdateParetoFront(solution)
        

        while len(self.ParetoSolutions.ParetoFront) < self.SizeStartPopulation:
            self.MutateSolution(solution)
        print(f"Initial Solution Pool:")
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()

        current_temperature = self.StartTemperature

        S_info = []

        for i, x in enumerate(self.ParetoSolutions.ParetoFront):
            x.id = i
            weights = {obj: self.RNG.random() for obj in self.objectives}
            seed = self.RNG.integers(0, 1_000_000)

            S_info.append({
                "solution": deepcopy(x),
                "weights": weights,
                "seed": seed,
                "id": i
            })
        
        while current_temperature > self.MinTemperature:
            
            for i in range(self.MaxIterations):
                tasks = []

                with ThreadPoolExecutor(max_workers=self.SizeStartPopulation) as executor:
                    futures = [
                        executor.submit(
                            self.psa_iteration,
                            info,
                            current_temperature,
                            self.ParetoSolutions.ParetoFront
                        )
                        for info in S_info
                    ]
                    results = [f.result() for f in futures]
                

                new_S_info = results

                for info in new_S_info:
                    if info["new_solution"] is not None:
                        self.ParetoSolutions.UpdateParetoFront(info["new_solution"])
                        info["solution"] = info["new_solution"]

                S_info = new_S_info

            
            current_temperature *= self.CoolingRate

        print("\nFinal Pareto Approximation:")
        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()

        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)

        profiler.disable()
        Path("Profiler/Run").mkdir(parents=True, exist_ok=True)
        profile_path = Path("Profiler/Run") / "run_profile.txt"
        with open(profile_path, "w") as f:
            ps = pstats.Stats(profiler, stream=f)
            ps.strip_dirs().sort_stats("cumulative").print_stats(50)
        



