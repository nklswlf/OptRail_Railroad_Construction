from Neighborhood import *
import math
from copy import deepcopy
import numpy as np
import time
from concurrent.futures import ProcessPoolExecutor
import pandas as pd


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

    def CreateNeighborhood(self, neighborhoodType:str): #-> BaseNeighborhood:
        """ Creates a new neighborhood based on the current best Solution and the chosen neighborhood type.
            Similar to the so-called factory concept in software design. """
        
        ### NEEDS TO BE ADJUSTED FOR ORIENTEERING PROBLEMLocalSearch

        if neighborhoodType == 'Insert_Shift':
            return InsertShiftNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'Swap_Shift_Worker':
            return SwapShiftWorkerNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'Replace_Shift_Worker':
            return ReplaceShiftWorkerNeighborhood(self.InputData , self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'Replace_Shift_Machine':
            return ReplaceShiftMachineNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'Swap_Shift_Machine':
            return SwapShiftMachineNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'Swap_Shift_External':
            return SwapShiftExternalNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'Replace_Shift_Attachment':
            return ReplaceShiftAttachmentNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'Swap_Shift_Attachment':
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



class RepairAlgorithm(ImprovementAlgorithm):
    """ Repair algorithm to fix incomplete solutions. """
    
    def __init__(self, inputData:InputData, neighborhoodEvaluationStrategy:str = 'BestImprovement', neighborhoodTypes:list[str] = ['Insert_Shift']):
        super().__init__(inputData, neighborhoodEvaluationStrategy, neighborhoodTypes)

    def Run(self, solution:Solution) -> Solution:
        ''' Run local search with given solutions and iterate through all given neighborhood types'''

        self.InitializeNeighborhoods()

        self.GetOrderItemsToRearrange(solution)
        print("Order and Order Items to rearrange: ", self.orders_to_rearrange)

        destroyed_solution = self.Destroy(solution)

        for neighborhoodType in self.NeighborhoodTypes:
            print(f'\nRunning neighborhood {neighborhoodType}')
            neighborhood = self.Neighborhoods[neighborhoodType]

            repaired_solution = neighborhood.LocalSearch(self.NeighborhoodEvaluationStrategy, solution)
            print(f'Best solution: {repaired_solution}')

        
        return repaired_solution
    

    def GetOrderItemsToRearrange(self, solution:Solution) -> list[int]:
        ''' Get all order items of semi-finished orders from the solution'''

        self.orders_to_rearrange = dict()

        for order in solution.semifinished_orders:
            self.orders_to_rearrange[order.order_number] = order.order_item_ids

    

    def Destroy(self, solution:Solution) -> Solution:
        ''' Delete order items of semi-finished orders from the solution'''

        route_plan_worker = deepcopy(solution.route_plan_worker)
        route_plan_machine = deepcopy(solution.route_plan_machine)
        semifinished_orders = deepcopy(solution.semifinished_orders)

        """
        print("Worker Route Plan before Destroy:")
        for worker, route in solution.route_plan_worker.items():
            print(f"Worker {worker}: {route}")
        
        print("Machine Route Plan before Destroy:")
        for machine, route in solution.route_plan_machine.items():
            print(f"Machine {machine}: {route}")
        """


        for order in semifinished_orders:
            for order_item_id in order.order_item_ids:
                for worker, route in route_plan_worker.items():
                    if order_item_id in route:
                        route.remove(order_item_id)
                for machine, route in route_plan_machine.items():
                    if order_item_id in route:
                        route.remove(order_item_id)


        destroyed_solution = Solution(route_plan_worker, route_plan_machine, self.InputData)

        """
        print("Worker Route Plan after Destroy:")
        for worker, route in destroyed_solution.route_plan_worker.items():
            print(f"Worker {worker}: {route}")
        
        print("Machine Route Plan after Destroy:")
        for machine, route in destroyed_solution.route_plan_machine.items():
            print(f"Machine {machine}: {route}")
        """
        

        if destroyed_solution.feasibility_check():
            print("Solution is feasible after Destroy")
            self.EvaluationLogic.evaluate(destroyed_solution)
            print(f"Solution after Destroy: {destroyed_solution}")
        else:
            print("Solution is not feasible after Destroy")

        




        return destroyed_solution



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




class ParetoSimulatedAnnealing(ImprovementAlgorithm):
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

        self.SizeStartPopulation = 5
        self.WeightAlpha = 1.1


        self.NeighborhoodTypes = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}



    def MutateSolution(self, solution: Solution) -> None:
        ''' Mutate the solution by applying multiple moves on a copy of the original '''

        random_number_of_moves = self.RNG.integers(10, 50)
        current_solution = deepcopy(solution)

        for _ in range(random_number_of_moves):
            move = None
            attempts = 0
            while move is None and attempts < 10:
                random_type = self.RNG.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                try:
                    move = neighborhood.SingleMove(current_solution)
                except KeyError:
                    move = None
                attempts += 1

            if move is None:
                continue

            worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, current_solution)
            current_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
            self.EvaluationLogic.evaluate(current_solution)

        self.ParetoSolutions.UpdateParetoFront(current_solution)

    
    def update_weights(self, x, population, objectives):
        """
        Berechnet dynamische Gewichtung der Ziele basierend auf Dominanz-Relationen
        """

        # Mapping für interne Attributnamen in Solution
        attr_mapping = {
            'commute_distance': 'total_commute_distance',
            'transport_distance': 'total_transport_distance',
            'attachment_distance': 'total_attachment_distance',
            'worker_count': 'number_of_workers',
            'machine_count': 'number_of_machines',
            'attachment_count': 'number_of_attachments',
            'driver_violation': 'driver_violation'
        }

        def dominates(a, b):
            better_in_at_least_one = False
            for obj in objectives:
                if a[obj] > b[obj]:
                    return False
                if a[obj] < b[obj]:
                    better_in_at_least_one = True
            return better_in_at_least_one

        def distance(a, b):
            return sum(abs(a[obj] - b[obj]) for obj in objectives)

        # Aktuelle Lösung
        x_values = {
            obj: getattr(x, attr_mapping.get(obj, obj), 0)
            for obj in objectives
        }

        candidates = []
        for x_ in population:
            if x_ == x:
                continue
            x__values = {
                obj: getattr(x_, attr_mapping.get(obj, obj), 0)
                for obj in objectives
            }
            if not dominates(x_values, x__values):
                candidates.append((x_, distance(x_values, x__values)))

        if not candidates:
            weights = weights = {obj: self.RNG.random() for obj in objectives}
        else:
            x_prime, _ = min(candidates, key=lambda tup: tup[1])
            x_prime_values = {
                obj: getattr(x_prime, attr_mapping.get(obj, obj), 0)
                for obj in objectives
            }

            weights = {}
            for obj in objectives:
                if x_values[obj] > x_prime_values[obj]:
                    weights[obj] = self.WeightAlpha
                elif x_values[obj] < x_prime_values[obj]:
                    weights[obj] = 1 / self.WeightAlpha
                else:
                    weights[obj] = 1.0

        # Normalisierung
        total = sum(weights.values())
        normalized_weights = {k: v / total for k, v in weights.items()}
        return normalized_weights



    def PSA(self, local_solution: Solution, local_pareto_front: list) -> list[Solution]:
        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData)
        local_pareto_solutions.ParetoFront = local_pareto_front

        while current_temperature > self.MinTemperature:
            for i in range(self.MaxIterations):
                random_type = self.RNG.choice(list(self.NeighborhoodTypes.keys()))
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(local_solution)

                if move is None:
                    continue

                objectives = self.NeighborhoodTypes[random_type]
                weights = self.update_weights(local_solution, local_pareto_solutions.ParetoFront, objectives)

                value = sum(weights[obj] * move.DeltaDetails[obj] for obj in objectives)

                if value > 0:
                    prob = math.exp(-value * self.ScalingEnergy / current_temperature)
                    if self.RNG.random() > prob:
                        continue

                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, local_solution)
                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)
                local_pareto_solutions.UpdateParetoFront(local_solution)

            current_temperature *= self.CoolingRate

        return local_pareto_solutions.ParetoFront




    def Run(self, solution: Solution) -> Solution:
        ''' Run simulated annealing algorithm with given solutions and parameters '''

        start_time = time.time()

        self.InitializeNeighborhoods(list(self.NeighborhoodTypes.keys()))

        while len(self.ParetoSolutions.ParetoFront) < self.SizeStartPopulation:
            self.MutateSolution(solution)
        print(f"Initial Solution Pool:")
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()
        

        if len(self.ParetoSolutions.ParetoFront) != self.SizeStartPopulation:
            raise Exception(f"Not enough solutions in Pareto Front: {len(self.ParetoSolutions.ParetoFront)}")

        tasks = []
        with ProcessPoolExecutor() as executor:
            for solution in self.ParetoSolutions.ParetoFront:
                local_solution = deepcopy(solution)
                local_pareto_front = deepcopy(self.ParetoSolutions.ParetoFront)
                tasks.append(executor.submit(self.PSA, local_solution, local_pareto_front))
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

        algo_time = time.time() - start_time

        return algo_time


        

class DominanceBasedSimulatedAnnealing(ImprovementAlgorithm):
    """ Simulated Annealing algorithm with dominance based energy. """

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

    

        


class TwoPhaseSimulatedAnnealing(ImprovementAlgorithm):
    """ Simulated Annealing algorithm with perturbation to escape local optima. """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 fallback_threshold:int,
                 scaling_energy:int,
                 max_building_iterations_without_improvement:int = None,
                 neighborhoodTypes:list[str] = None,
                 energyDominanceNeighborhoods:dict[str, list[str]] = None,
                 buildingTypesObjectives:dict[str, list[str]] = None,
                 improveTypesObjectives:dict[str, list[str]] = None,
                 improveIndividualStrategy:str = None):
        super().__init__(inputData)

        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.FallbackThreshold = fallback_threshold
        self.ScalingEnergy = scaling_energy
        self.NeighborhoodTypes = neighborhoodTypes
        self.BuildingTypesObjectives = buildingTypesObjectives
        self.ImproveTypesObjectives = improveTypesObjectives
        self.ImproveIndividualStrategy = improveIndividualStrategy
        self.EnergyDominanceNeighborhoods = energyDominanceNeighborhoods
        self.MaxBuildingIterationsWithoutImprovement = max_building_iterations_without_improvement
        self.DontChangeBackInOrder = set()
        self.BuildingIteration = 0


    

    def ImproveIndividuals(self, solution:Solution, objective:str) -> ParetoSolutions:
        ''' Improve individuals with simulated annealing algorithm'''

        current_temperature = self.StartTemperature
        local_solution = deepcopy(solution)
        local_pareto_solutions = ParetoSolutions(self.InputData)
        fallback_counter = 0

        while current_temperature > self.MinTemperature:

            for i in range(self.MaxIterations):

                types = self.ImproveTypesObjectives[objective]
                random_type = self.RNG.choice(types)
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(local_solution)

                if move is None:
                    continue

                value = move.DeltaDetails[objective]

                if value <= 0:
                    pass
                elif value > 0:
                    prob = math.exp(-value * self.ScalingEnergy / current_temperature)
                    random_number = self.RNG.random()

                    if prob < random_number:
                        # Rethink structure of the code and Simulated Annealing
                        # max iterations without improvement should be place here somewhere
                        continue

                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, local_solution)
                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)

                added = local_pareto_solutions.UpdateParetoFront(local_solution)

                if not added:
                    fallback_counter += 1
                    # Adjust Fallback to break criteria (max iterations without improvement)
                    if fallback_counter >= self.FallbackThreshold:
                        local_pareto_solutions.SortParetoFront(objective)
                        local_solution = local_pareto_solutions.ParetoFront[0]
                else:
                    fallback_counter = 0


            current_temperature *= self.CoolingRate

            # Introduce a perturbation to escape local optima!!!

        return local_pareto_solutions


    def ParallelImproveIndividuals(self, solution: Solution) -> None:
        ''' Improve individuals with simulated annealing algorithm in parallel'''

        print("\nStarting Parallel Improvement of individual objectives...")

        tasks = []
        with ProcessPoolExecutor() as executor:
            for obj in self.ImproveTypesObjectives.keys():
                local_solution = deepcopy(solution)
                tasks.append(executor.submit(self.ImproveIndividuals, local_solution, obj))

            results = [task.result() for task in tasks]

        combined_pareto_front = []
        for local_pareto in results:
            combined_pareto_front.extend(local_pareto.ParetoFront)

        self.ParetoSolutions.ParetoFront = combined_pareto_front
        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()
        print("\nPareto Front after Parallel Improvement:")
        self.ParetoSolutions.ShowFront()

        # Add an analysis of the Pareto Front to see the improvement up till now


    def SuccessiveImproveIndividuals(self, solution:Solution) -> None:

        ''' Improve individuals with simulated annealing algorithm in successive order'''

        print("\nStarting Successive Improvement of individual objectives...")

        for objective in self.ImproveTypesObjectives.keys():
            local_pareto_solutions = self.ImproveIndividuals(solution, objective)
            self.ParetoSolutions.ParetoFront.extend(local_pareto_solutions.ParetoFront)


        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()
        print("\nPareto Front after Successive Improvement:")
        self.ParetoSolutions.ShowFront()



    def DominanceBasedEnergyImprovement(self, solution:Solution) -> None:

        ''' Simulated annealing algorithm with energy dominance neighborhood'''

        print("\nStarting Dominance Based Energy Improvement...")
        
        fallback_counter = 0
        current_temperature = self.StartTemperature

        while current_temperature > self.MinTemperature:

            for i in range(self.MaxIterations):

                dominating_count_current = self.ParetoSolutions.CountDominatingSolutions(solution)

                neighborhoodType = self.RNG.choice(list(self.EnergyDominanceNeighborhoods.keys()))
                neighborhood = self.Neighborhoods[neighborhoodType]
                objectives = self.EnergyDominanceNeighborhoods[neighborhoodType]

                move = neighborhood.SingleMove(solution)

                if move is None:
                    continue

                not_involved_objectives = ['driver_violation', 'commute_distance', 'transport_distance', 'attachment_distance', 'machine_count', 'worker_count', 'attachment_count']
                objective_dict = dict()
                for objective in objectives:
                    value = move.DeltaDetails[objective]
                    not_involved_objectives.remove(objective)

                    if objective == 'driver_violation':
                        objective_dict[objective] = solution.driver_violation - value
                    elif objective == 'commute_distance':
                        objective_dict[objective] = solution.total_commute_distance - value
                    elif objective == 'transport_distance':
                        objective_dict[objective] = solution.total_transport_distance - value
                    elif objective == 'attachment_distance':
                        objective_dict[objective] = solution.total_attachment_distance - value
                    elif objective == 'machine_count':
                        objective_dict[objective] = solution.number_of_machines - value
                    elif objective == 'worker_count':
                        objective_dict[objective] = solution.number_of_workers - value
                    elif objective == 'attachment_count':
                        objective_dict[objective] = solution.number_of_attachments - value
                
                for objective in not_involved_objectives:

                    if objective == 'driver_violation':
                        objective_dict[objective] = solution.driver_violation
                    elif objective == 'commute_distance':
                        objective_dict[objective] = solution.total_commute_distance
                    elif objective == 'transport_distance':
                        objective_dict[objective] = solution.total_transport_distance
                    elif objective == 'attachment_distance':
                        objective_dict[objective] = solution.total_attachment_distance
                    elif objective == 'machine_count':
                        objective_dict[objective] = solution.number_of_machines
                    elif objective == 'worker_count':
                        objective_dict[objective] = solution.number_of_workers
                    elif objective == 'attachment_count':
                        objective_dict[objective] = solution.number_of_attachments

                # Possible to combine objectives to 3 main topics: distance, ressource count, violation

                dominating_count_new = self.ParetoSolutions.CountDominatingSolutions(objective_dict)

                overall_difference = dominating_count_new - dominating_count_current
                
                if overall_difference <= 0:
                    pass
                elif overall_difference > 0:
                        
                        prob =  math.exp(-overall_difference * self.ScalingEnergy / current_temperature)
                        random_number = self.RNG.random()
                        if prob < random_number:
                            continue


                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, solution)
                solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(solution)

                added = self.ParetoSolutions.UpdateParetoFront(solution)

                if not added:
                    fallback_counter += 1
                    if fallback_counter >= self.FallbackThreshold:
                        solution = self.ParetoSolutions.SelectRandomBestSolution()
                else:
                    fallback_counter = 0

            current_temperature *= self.CoolingRate

        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()
        print("\nPareto Front after Dominance Based Energy Improvement:")
        self.ParetoSolutions.ShowFront()



    

    
    def Run(self, solution:Solution) -> Solution:
        ''' Run simulated annealing algorithm with given solutions and parameters'''

        # Initialize Model
        self.InitializeNeighborhoods()
        currentSolution = deepcopy(solution)


        self.ParetoSolutions.SetReferencePoint(currentSolution)

        current_time = time.time()
        # Improving each individual objective and keeping Pareto front
        if self.ImproveIndividualStrategy == 'parallel':
            self.ParallelImproveIndividuals(currentSolution)
        elif self.ImproveIndividualStrategy == 'successive':
            self.SuccessiveImproveIndividuals(currentSolution)
        
            
        hv_sqrt, hv_log = self.ParetoSolutions.CalculateHypervolume()
        print(f"\nHypervolume squareroot of Pareto Front after individual {self.ImproveIndividualStrategy} improvement: {round(hv_sqrt, 2)}")
        print(f"\nHypervolume log of Pareto Front after individual {self.ImproveIndividualStrategy} improvement: {round(hv_log, 2)}")

        self.IndividualPhaseTime = time.time() - current_time
        print(f"\nIndividual Phase finished after: {round(self.IndividualPhaseTime, 2)} seconds")

        # Show individual best solutions for each objective
        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)

        current_time = time.time()
        # Using dominace based energy for simulated annealing
        solution = self.ParetoSolutions.SelectRandomBestSolution()
        self.DominanceBasedEnergyImprovement(solution)
        
        hv_sqrt, hv_log = self.ParetoSolutions.CalculateHypervolume()
        print(f"\nHypervolume squareroot of Pareto Front after dominance based energy improvement: {round(hv_sqrt, 2)}")
        print(f"\nHypervolume log of Pareto Front after dominance based energy improvement: {round(hv_log, 2)}")
        
        self.DominanceBasedEnergyImprovementTime = time.time() - current_time
        print(f"\nDominance Based Energy Improvement finished after: {round(self.DominanceBasedEnergyImprovementTime, 2)} seconds")
        
        current_time = time.time()
        for solution in self.ParetoSolutions.ParetoFront:
            feasible = solution.feasibility_check()
            if not feasible:
                raise Exception('Solution is not feasible after pareto simulated annealing')

        self.FeasibilityCheckTime = time.time() - current_time

        # Show individual best solutions for each objective
        self.ParetoSolutions.SelectRandomBestSolution(all_values=True)

        return self.BuildingPhaseTime, self.IndividualPhaseTime, self.DominanceBasedEnergyImprovementTime, self.FeasibilityCheckTime

        







'''
def BuildingPhase(self, solution:Solution) -> Solution:

        self.BuildingIteration += 1
        print(f"\nBuilding Phase Iteration {self.BuildingIteration}...")

        fallback_counter = 0
        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData)
        break_counter = 0
        break_flag = False

        while current_temperature > self.MinTemperature:

            if break_flag:
                break

            for i in range(self.MaxIterations):


                if solution.total_dynamic_percentage == self.InputData.site_fulfillment:
                    if len(local_pareto_solutions.ParetoFront) > 0:
                        print("\nLocal Pareto Front after Building Phase:")
                        local_pareto_solutions.ShowFront()
                    self.ParetoSolutions.ParetoFront.append(solution)
                    print("\nSingle Solution added to Global Pareto Front:")
                    print(solution)
                    return solution, True


                random_objective = self.RNG.choice(list(self.BuildingTypesObjectives.keys()))
                types = self.BuildingTypesObjectives[random_objective]
                random_type = self.RNG.choice(types)
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(solution)

                if move is None:
                    # Count consecutive non-moves for Insert_Shift and Swap_Shift_External
                    # Break if threshold is reached
                    if random_type in ['Insert_Shift', 'Swap_Shift_External']:
                        break_counter += 1
                    if break_counter >= self.MaxBuildingIterationsWithoutImprovement:
                        break_flag = True
                        break
                    
                    continue

                value = move.DeltaDetails[random_objective]

                if value <= 0:
                    pass
                elif value > 0:
                    prob = math.exp(-value * self.ScalingEnergy/ current_temperature)
                    random_number = self.RNG.random()

                    if prob < random_number:
                        continue

                
                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, solution)
                solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(solution)

                added = local_pareto_solutions.UpdateParetoFront(solution)

                if not added:
                    fallback_counter += 1
                    if fallback_counter >= self.FallbackThreshold:
                        local_pareto_solutions.SortParetoFront()
                        solution = local_pareto_solutions.ParetoFront[0]
                else:
                    fallback_counter = 0

            current_temperature *= self.CoolingRate

        solution = deepcopy(local_pareto_solutions.ParetoFront[0])
        #local_pareto_solutions.UpdateParetoFront(solution)
        print("\nDid not find fully staffed solution after Building Phase iteration")
        print(f"\nSingle Solution which is not fully fulfilled after Building Phase iteration:")
        print(solution)
        return solution, False
    
        # Introduce a perturbation to escape local optima!!! --> Maybe not necessary for building phase

        
            def EditSites(self, solution:Solution, add_site:bool) -> Solution:

        amount_not_started_orders = len(solution.not_started_orders)

        if amount_not_started_orders >= 1:

            chosen_order = max(solution.not_started_orders, key=lambda order: len(order.order_item_ids))
            chosen_order_item_ids = chosen_order.order_item_ids
            
            
            self.InputData.deactivate_order(chosen_order.order_number)

            new_route_plan_worker = deepcopy(solution.route_plan_worker)
            new_route_plan_machine = deepcopy(solution.route_plan_machine)
            new_route_plan_attachment = deepcopy(solution.route_plan_attachment)

            for worker, route in new_route_plan_worker.items():
                for order_item_id in chosen_order_item_ids:
                    if order_item_id in route:
                        route.remove(order_item_id)
            for machine, route in new_route_plan_machine.items():
                for order_item_id in chosen_order_item_ids:
                    if order_item_id in route:
                        route.remove(order_item_id)
            for attachment, route in new_route_plan_attachment.items():
                for order_item_id in chosen_order_item_ids:
                    if order_item_id in route:
                        route.remove(order_item_id)

            if add_site:
                usable_orders = [order for order in solution.not_recognized_orders if not order.unuseable and order.order_number not in self.DontChangeBackInOrder]

                if usable_orders:
                    new_order = min(usable_orders, key=lambda order: len(order.order_item_ids))
                    self.InputData.activate_order(new_order.order_number)
                else:
                    raise Exception("No usable order to add")

            self.DontChangeBackInOrder.add(chosen_order.order_number)
            new_solution = Solution(new_route_plan_worker, new_route_plan_machine, new_route_plan_attachment, self.InputData)
            self.EvaluationLogic.evaluate(new_solution)

            
            return new_solution
        
        amount_semifinished_orders = len(solution.semifinished_orders)

        if amount_semifinished_orders >= 1:

            chosen_order = max(solution.semifinished_orders, key=lambda order: len(order.order_item_ids))
            chosen_order_item_ids = chosen_order.order_item_ids


         
            self.InputData.deactivate_order(chosen_order.order_number)

            
            new_route_plan_worker = deepcopy(solution.route_plan_worker)
            new_route_plan_machine = deepcopy(solution.route_plan_machine)
            new_route_plan_attachment = deepcopy(solution.route_plan_attachment)

            for worker, route in new_route_plan_worker.items():
                for order_item_id in chosen_order_item_ids:
                    if order_item_id in route:
                        route.remove(order_item_id)
            for machine, route in new_route_plan_machine.items():
                for order_item_id in chosen_order_item_ids:
                    if order_item_id in route:
                        route.remove(order_item_id)
            for attachment, route in new_route_plan_attachment.items():
                for order_item_id in chosen_order_item_ids:
                    if order_item_id in route:
                        route.remove(order_item_id)

            if add_site:
                usable_orders = [order for order in solution.not_recognized_orders if not order.unuseable and order.order_number not in self.DontChangeBackInOrder]


                if usable_orders != []:
                    new_order = min(usable_orders, key=lambda order: len(order.order_item_ids))
                    self.InputData.activate_order(new_order.order_number)
                else:
                    raise Exception("No usable order to add")
                


            self.DontChangeBackInOrder.add(chosen_order.order_number)
            new_solution = Solution(new_route_plan_worker, new_route_plan_machine, new_route_plan_attachment, self.InputData)
            self.EvaluationLogic.evaluate(new_solution)

            return new_solution


        raise Exception("No order to delete")

'''