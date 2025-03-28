from Neighborhood import *
import math
from copy import deepcopy
import numpy as np
import time
from concurrent.futures import ProcessPoolExecutor


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




class ParetoSimulatedAnnealing(ImprovementAlgorithm):
    """ Simulated Annealing algorithm with perturbation to escape local optima. """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 fallback_threshold:int,
                 scaling_energy:int,
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
        
        self.DontChangeBackInOrder = set()


    def BuildingPhase(self, solution:Solution) -> Solution:

        fallback_counter = 0
        current_temperature = self.StartTemperature
        local_pareto_solutions = ParetoSolutions(self.InputData)

        while current_temperature > self.MinTemperature:

            for i in range(self.MaxIterations):

                if solution.total_dynamic_percentage == self.InputData.site_fulfillment:
                    self.ParetoSolutions.ParetoFront.append(solution)
                    self.ParetoSolutions.ShowFront()
                    return solution, True


                random_objective = self.RNG.choice(list(self.BuildingTypesObjectives.keys()))
                types = self.BuildingTypesObjectives[random_objective]
                random_type = self.RNG.choice(types)
                neighborhood = self.Neighborhoods[random_type]
                move = neighborhood.SingleMove(solution)

                if move is None:
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
                print(f"New solution: {solution}")
                print(f"Unfinished Order Items {solution.not_started_order_item_ids}")
                print(f"Worker Route Plan: {solution.route_plan_worker}")

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
        local_pareto_solutions.UpdateParetoFront(solution)
        local_pareto_solutions.ShowFront()
        return solution, False
    
        # Introduce a perturbation to escape local optima!!!


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
                        continue

                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, local_solution)
                local_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(local_solution)

                added = local_pareto_solutions.UpdateParetoFront(local_solution)

                if not added:
                    fallback_counter += 1
                    if fallback_counter >= self.FallbackThreshold:
                        local_pareto_solutions.SortParetoFront(objective)
                        local_solution = local_pareto_solutions.ParetoFront[0]
                else:
                    fallback_counter = 0


            current_temperature *= self.CoolingRate

            # Introduce a perturbation to escape local optima!!!

        return local_pareto_solutions


    def ParallelImproveIndividuals(self, solution: Solution) -> None:
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
        self.ParetoSolutions.ShowFront()


    def SuccessiveImproveIndividuals(self, solution:Solution) -> None:

        for objective in self.ImproveTypesObjectives.keys():
            local_pareto_solutions = self.ImproveIndividuals(solution, objective)
            self.ParetoSolutions.ParetoFront.extend(local_pareto_solutions.ParetoFront)


        self.ParetoSolutions.PurgeParetoFront()
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()



    def DominanceBasedEnergyImprovement(self, solution:Solution) -> None:
        
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
        self.ParetoSolutions.ShowFront()


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

            print(f"Chosen Order: {chosen_order.order_number}")
            print(f"Chosen Order Item IDs: {chosen_order_item_ids}")

         
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

                for order in usable_orders:
                    print(f"Usable Order: {order.order_number}")

                if usable_orders != []:
                    new_order = min(usable_orders, key=lambda order: len(order.order_item_ids))
                    self.InputData.activate_order(new_order.order_number)
                else:
                    raise Exception("No usable order to add")
                
                for order in self.InputData.orders:
                    print(f"Order {order.order_number} Status: {order.status}")


            self.DontChangeBackInOrder.add(chosen_order.order_number)
            new_solution = Solution(new_route_plan_worker, new_route_plan_machine, new_route_plan_attachment, self.InputData)
            self.EvaluationLogic.evaluate(new_solution)

            return new_solution


        raise Exception("No order to delete")
    
        




    
    def Run(self, solution:Solution) -> Solution:
        ''' Run simulated annealing algorithm with given solutions and parameters'''

        # Initialize Model
        self.InitializeNeighborhoods()
        currentSolution = deepcopy(solution)

        # Building up after the initial solution
        Found = False
        exchange_tries = 0
        while not Found:
            currentSolution, Found = self.BuildingPhase(currentSolution)

            if not Found:
                if exchange_tries < 2: # Change: LOOP could HAPPEN
                    print(f"Current Solution: {currentSolution}")
                    print(f"Unfinished Order Items {currentSolution.not_started_order_item_ids}")
                    for order in self.InputData.orders:
                        print(f"Order {order.order_number} Status: {order.status}")
                    currentSolution = self.EditSites(currentSolution, True)
                    print("EDITED")
                    print(f"Edited Solution: {currentSolution}")
                    print(f"Unfinished Order Items {currentSolution.not_started_order_item_ids}")
                    for order in self.InputData.orders:
                        print(f"Order {order.order_number} Status: {order.status}")
                    feasible = currentSolution.feasibility_check()
                    if not feasible:
                        raise Exception('Solution is not feasible after adding site')
                    exchange_tries += 1
                else:
                    currentSolution = self.EditSites(currentSolution, False)



        # Improving each individual objective and keeping Pareto front
        if self.ImproveIndividualStrategy == 'parallel':
            self.ParallelImproveIndividuals(currentSolution)
        elif self.ImproveIndividualStrategy == 'successive':
            self.SuccessiveImproveIndividuals(currentSolution)

        # Using dominace based energy for simulated annealing
        solution = self.ParetoSolutions.SelectRandomBestSolution()
        self.DominanceBasedEnergyImprovement(solution)

        for solution in self.ParetoSolutions.ParetoFront:
            feasible = solution.feasibility_check()
            if not feasible:
                raise Exception('Solution is not feasible after pareto simulated annealing')


        # Visualize individual best solutions for each objective
        best_solution_set = self.ParetoSolutions.SelectRandomBestSolution(all_values=True)

        self.ParetoSolutions.ParetoFront = []

        for solution in best_solution_set:
            self.ParetoSolutions.ParetoFront.append(solution)
        self.ParetoSolutions.SortParetoFront()
        self.ParetoSolutions.ShowFront()


