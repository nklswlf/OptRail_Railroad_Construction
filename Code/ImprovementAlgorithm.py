from Neighborhood import *
import math
from copy import deepcopy
import numpy as np
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




class SimulatedAnnealingLocalSearch(ImprovementAlgorithm):
    """ Simulated Annealing algorithm with perturbation to escape local optima. """

    def __init__(self, inputData:InputData,
                 start_temp:int,
                 min_temp:int,
                 cooling_rate:float,
                 max_iterations:int,
                 neighborhoodTypesSA:list[str] = ['Swap'],
                neighborhoodTypesLS:list[str] = ['Insert']):
        super().__init__(inputData)

        self.StartTemperature = start_temp
        self.MinTemperature = min_temp
        self.CoolingRate = cooling_rate
        self.MaxIterations = max_iterations
        self.NeighborhoodTypes = neighborhoodTypesSA
        self.NeighborhoodTypesLS = neighborhoodTypesLS


    
    def Run(self, solution:Solution) -> Solution:
        ''' Run simulated annealing algorithm with given solutions and parameters'''

        self.InitializeNeighborhoods()

        print(f'\nInitial solution: \n{solution}')

        local_search_on = False
        if local_search_on:
            local_search = IterativeImprovement(self.InputData, self.NeighborhoodEvaluationStrategy, self.NeighborhoodTypesLS)
            local_search.Initialize(self.EvaluationLogic, self.ParetoSolutions, self.RNG)

        currentSolution = deepcopy(solution)

        print(f"Attachment Route Plan: {currentSolution.route_plan_attachment}")


        currentTemperature = self.StartTemperature

        count = dict()
        count['dominates'] = 0
        count['dominated'] = 0
        count['non-dominated'] = 0
        count['none'] = 0
        count['number_accepted'] = 0

        fallback_counter = 0
        fallback = True
        fallbacks = 0

        energy_strategy = 'deltas'

        while currentTemperature > self.MinTemperature:
            
            if local_search_on:
                currentSolution = local_search.Run(deepcopy(currentSolution))

            for i in range(self.MaxIterations):

                neighborhoodType = self.RNG.choice(self.NeighborhoodTypes)
                neighborhood = self.Neighborhoods[neighborhoodType]

                move = neighborhood.SingleMove(currentSolution)

                if move is None:
                    count['none'] += 1
                    continue
                
                print(f"Move Delta Details: {move.DeltaDetails}")
                #values = list(move.DeltaDetails.values())
                value = move.DeltaDetails["driver_violation"]

                if value < 0:
                    count['dominates'] += 1
                    pass
                elif value > 0:
                    count['dominated'] += 1
                    prob = math.exp(-value * 30/ currentTemperature)
                    random_number = self.RNG.random()
                    print(f"Comparison: {random_number} <=> {prob}")

                    if prob < random_number:
                        continue
                    else:
                        count['number_accepted'] += 1


                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, currentSolution)
                currentSolution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(currentSolution)
                print(f"New solution: {currentSolution}")
                feasible = currentSolution.feasibility_check()
                if not feasible:
                    raise Exception(f"Solution is not feasible after neighborhood {neighborhoodType}")
                
                added = self.ParetoSolutions.UpdateParetoFront(currentSolution)

                if not added:
                    fallback_counter += 1
                    if fallback_counter % 10 == 0 and fallback:
                        print("Fallback")
                        fallbacks += 1
                        self.ParetoSolutions.SortParetoFront()


                        currentSolution = self.ParetoSolutions.ParetoFront[0]

            currentTemperature *= self.CoolingRate

        print(f"Number of dominates: {count['dominates']}")
        print(f"Number of dominated: {count['dominated']}")
        print(f"Number of non-dominated: {count['non-dominated']}")
        print(f"Number of accepted: {count['number_accepted']}")
        print(f"Number of none: {count['none']}")


                

        return self.ParetoSolutions.ShowFront()
    



'''

                all_less_equal_zero = all(v <= 0 for v in values)
                all_greater_equal_zero = all(v >= 0 for v in values)

                any_less_than_zero = any(v < 0 for v in values)
                any_greater_than_zero = any(v > 0 for v in values)

                if all_less_equal_zero and any_less_than_zero:
                    count['dominates'] += 1
                    print("dominates")
                elif all_greater_equal_zero and any_greater_than_zero:
                    count['dominated'] += 1
                    print("dominated")

                    
                    if energy_strategy == 'deltas':
                        overall_delta = 0
                        for v in values:
                            if v > 0:
                                overall_delta += v

                        prob =  math.exp(-overall_delta / currentTemperature)
                        random_number = self.RNG.random()
                        print(f"Comparison: {random_number} <=> {prob}")

                        if prob < random_number:
                            print("Random number is greater than probability")
                            continue

                    elif energy_strategy == 'pareto':
                        overall_difference = 0
                        dominating_count_current = self.ParetoSolutions.CountDominatingSolutions(currentSolution)

                        worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, currentSolution)
                        new_solution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                        self.EvaluationLogic.evaluate(new_solution)
                        dominating_count_new = self.ParetoSolutions.CountDominatingSolutions(new_solution)

                        overall_difference = dominating_count_new - dominating_count_current

                        prob =  math.exp(-overall_difference / currentTemperature)
                        random_number = self.RNG.random()
                        print(f"Comparison: {random_number} <=> {prob}")

                        if prob < random_number:
                            print("Random number is greater than probability")
                            continue

                    
                else:
                    count['non-dominated'] += 1
                    print(f"Delta: {move.Delta}")
                    print("non-dominated")

  
                worker_route_plan, machine_route_plan, attachment_route_plan = neighborhood.constructCompleteRoutes(move, currentSolution)
                currentSolution = Solution(worker_route_plan, machine_route_plan, attachment_route_plan, self.InputData)
                self.EvaluationLogic.evaluate(currentSolution)
                print(f"New solution: {currentSolution}")
                feasible = currentSolution.feasibility_check()
                if not feasible:
                    raise Exception(f"Solution is not feasible after neighborhood {neighborhoodType}")
                
                added = self.ParetoSolutions.UpdateParetoFront(currentSolution)


                if not added:
                    fallback_counter += 1
                    if fallback_counter % 10 == 0 and fallback:
                        print("Fallback")
                        fallbacks += 1
                        #self.ParetoSolutions.PurgeParetoFront()


                        currentSolution = self.RNG.choice(self.ParetoSolutions.ParetoFront)

                print(f"Lenght of Pareto Front: {len(self.ParetoSolutions.ParetoFront)}")
                if energy_strategy == 'deltas':
                    if len(self.ParetoSolutions.ParetoFront) > 2000:
                        energy_strategy = 'pareto'


            currentTemperature *= self.CoolingRate

        print(f"Number of dominates: {count['dominates']}")
        print(f"Number of dominated: {count['dominated']}")
        print(f"Number of non-dominated: {count['non-dominated']}")
        print(f"Number of none: {count['none']}")
        print(f"Number of fallbacks: {fallbacks}")
        self.ParetoSolutions.PurgeParetoFront()
        print(f"Number of Pareto solutions: {len(self.ParetoSolutions.ParetoFront)}")
        '''