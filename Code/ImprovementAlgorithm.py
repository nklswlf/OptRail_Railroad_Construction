from Neighborhood import *
import math
from copy import deepcopy
import numpy as np
import time

class ImprovementAlgorithm:
    """ Base class for several types of improvement algorithms. """ 

    def __init__(self, inputData:InputData, neighborhoodEvaluationStrategy:str = 'BestImprovement', neighborhoodTypes:list[str] = ['Insert_Site']):
        self.InputData = inputData

        self.EvaluationLogic = {}
        self.SolutionPool = {}
        self.RNG = {}

        self.NeighborhoodEvaluationStrategy = neighborhoodEvaluationStrategy
        self.NeighborhoodTypes = neighborhoodTypes
        self.Neighborhoods = {}

    def Initialize(self, evaluationLogic:EvaluationLogic, solutionPool:SolutionPool, rng = None) -> None:
        ''' Initializes empty variables'''

        self.EvaluationLogic = evaluationLogic
        self.SolutionPool = solutionPool
        self.RNG = rng

    def CreateNeighborhood(self, neighborhoodType:str): #-> BaseNeighborhood:
        """ Creates a new neighborhood based on the current best Solution and the chosen neighborhood type.
            Similar to the so-called factory concept in software design. """
        
        ### NEEDS TO BE ADJUSTED FOR ORIENTEERING PROBLEMLocalSearch

        if neighborhoodType == 'Insert_Site':
            return InsertSiteNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'SwapInterRoute':
            return SwapInterRouteNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'TwoEdgeExchange':
            return TwoEdgeExchangeNeighborhood(self.InputData , self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'Insert':
            return InsertNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'ReplaceProfit':
            return ReplaceProfitNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
        elif neighborhoodType == 'ReplaceDelta':
            return ReplaceDeltaNeighborhood(self.InputData, self.EvaluationLogic, self.SolutionPool, self.RNG)
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
    
    def __init__(self, inputData:InputData, neighborhoodEvaluationStrategy:str = 'BestImprovement', neighborhoodTypes:list[str] = ['Insert_Site']):
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

        print("Worker Route Plan before Destroy:")
        for worker, route in solution.route_plan_worker.items():
            print(f"Worker {worker}: {route}")
        
        print("Machine Route Plan before Destroy:")
        for machine, route in solution.route_plan_machine.items():
            print(f"Machine {machine}: {route}")



        for order in semifinished_orders:
            for order_item_id in order.order_item_ids:
                for worker, route in route_plan_worker.items():
                    if order_item_id in route:
                        route.remove(order_item_id)
                for machine, route in route_plan_machine.items():
                    if order_item_id in route:
                        route.remove(order_item_id)


        destroyed_solution = Solution(route_plan_worker, route_plan_machine, self.InputData)


        print("Worker Route Plan after Destroy:")
        for worker, route in destroyed_solution.route_plan_worker.items():
            print(f"Worker {worker}: {route}")
        
        print("Machine Route Plan after Destroy:")
        for machine, route in destroyed_solution.route_plan_machine.items():
            print(f"Machine {machine}: {route}")
        

        if destroyed_solution.feasibility_check():
            print("Solution is feasible after Destroy")
        else:
            print("Solution is not feasible after Destroy")

        




        return destroyed_solution





class IterativeImprovement(ImprovementAlgorithm):
    """ Iterative improvement algorithm through sequential variable neighborhood descent. 
        Local Search with itereative steps through many different neighborhoods.
    """

    def __init__(self,  inputData:InputData, neighborhoodEvaluationStrategy:str = 'BestImprovement', neighborhoodTypes:list[str] = ['SwapWaiting']):
        super().__init__(inputData, neighborhoodEvaluationStrategy, neighborhoodTypes)

    def Run(self, solution:Solution) -> Solution:
        ''' Run local search with given solutions and iterate through all given neighborhood types'''

        self.InitializeNeighborhoods()    

        # According to "Hansen et al. (2017): Variable neighorhood search", this is equivalent to the 
        # sequential variable neighborhood descent with a pipe neighborhood change step.

        usedTypes = []
        #profit_over_time = {}
        #profit_over_time[0] = 0, solution.TotalProfit
        start_time = time.time()
        used_time = 0

        for neighborhoodType in self.NeighborhoodTypes:
            usedTypes.append(neighborhoodType)
            print(f'\nRunning neighborhood {neighborhoodType}')
            neighborhood = self.Neighborhoods[neighborhoodType]
            used_time = time.time() - start_time
            iteration = len(usedTypes)
            #profit_over_time[iteration] = used_time, solution.TotalProfit

            solution = neighborhood.LocalSearch(self.NeighborhoodEvaluationStrategy, solution)
            print(f'Best solution after {usedTypes}: {solution}')
        
        return solution#, profit_over_time



class IteratedLocalSearch(ImprovementAlgorithm):
    """ Iterative local search with perturbation to escape local optima.
        Local Search with iterative steps through many different neighborhoods.
    """

    def __init__(self, inputData: InputData, maxRunTime:int, sublists_to_modify:int,consecutive_to_remove:int, threshold1:int = 2,
                    neighborhoodEvaluationStrategyDelta: str = 'BestImprovement',
                    neighborhoodEvaluationStrategyProfit: str = 'BestImprovement',
                      neighborhoodTypesDelta: list[str] = ['SwapWaiting'],
                      neighborhoodTypesProfit: list[str] = ['SwapWaiting']):
        super().__init__(inputData)

        self.maxRunTime = maxRunTime
        #self.jobsToRemove = jobs_to_remove 
        self.sublists_to_modify = sublists_to_modify
        self.consecutive_to_remove = consecutive_to_remove
        self.NeighborhoodEvaluationStrategyDelta = neighborhoodEvaluationStrategyDelta
        self.NeighborhoodEvaluationStrategyProfit = neighborhoodEvaluationStrategyProfit
        self.NeighborhoodTypesDelta = neighborhoodTypesDelta
        self.NeighborhoodTypesProfit = neighborhoodTypesProfit
        self.NeighborhoodTypes = neighborhoodTypesDelta + neighborhoodTypesProfit
        self.Threshold1 = threshold1
        self.DeltaNeighborhoods = {}
        self.ProfitNeighborhoods = {}

    def Run(self, currentSolution: Solution) -> Solution:
        ''' Run local search with given solutions and iterate through all given neighborhood types '''

        self.InitializeNeighborhoods(neighborhoodtypes = self.NeighborhoodTypesDelta, neighborhoods_dict = self.DeltaNeighborhoods)
        self.InitializeNeighborhoods(neighborhoodtypes = self.NeighborhoodTypesProfit, neighborhoods_dict = self.ProfitNeighborhoods)
        
        
        startTime = time.time()
        usedTime = 0

        #profit_over_time = {}
        #profit_over_time[0] = 0, currentSolution.TotalProfit


        print('\nStarting Iterated Local Search')
        print(f'\n Running initial local search')

        for delta_neighbor_name, delta_neighbor in self.DeltaNeighborhoods.items():
            print(f'\nRunning local search for {delta_neighbor_name} neighborhood')
            currentSolution = delta_neighbor.LocalSearch('BestImprovement', currentSolution)

        for profit_neighbor_name,profit_neighbor in self.ProfitNeighborhoods.items():
            print(f'\nRunning local search for {profit_neighbor_name} neighborhood')
            currentSolution = profit_neighbor.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)


        iteration = 1
        iterationsWithoutImprovement = 0
        bestIteration = 'initial local search'
        bestSolution = self.SolutionPool.GetHighestProfitSolution()

        while self.maxRunTime > usedTime:
            print(f'\nStarting iteration {iteration}')
            print(f' Running perturbation')
            currentSolution = self.Perturbation(currentSolution)
            print(f' Solution after perturbation in iteration {iteration}: \n {currentSolution}')
            
            print(f'\n Running local search after perturbation')
            
            for profit_neighbor_name,profit_neighbor in self.ProfitNeighborhoods.items():
                print(f'\nRunning local search for {profit_neighbor_name} neighborhood')
                currentSolution = profit_neighbor.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)

            for delta_neighbor_name, delta_neighbor in self.DeltaNeighborhoods.items():
                print(f'\nRunning local search for {delta_neighbor_name} neighborhood')
                currentSolution = delta_neighbor.LocalSearch(self.NeighborhoodEvaluationStrategyDelta, currentSolution)

            for profit_neighbor_name,profit_neighbor in self.ProfitNeighborhoods.items():
                print(f'\nRunning local search for {profit_neighbor_name} neighborhood')
                currentSolution = profit_neighbor.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)

            print(f' Solution after local search in iteration {iteration}:\n {currentSolution}')

            
            if currentSolution.TotalProfit > bestSolution.TotalProfit:
                iterationsWithoutImprovement = 0
                bestIteration = iteration
            else:
                iterationsWithoutImprovement += 1

            bestSolution = self.SolutionPool.GetHighestProfitSolution()

            print(f'\n Overall best solution found in iteration {bestIteration}: \n {bestSolution}')

            print(f' Iterations without improvement: {iterationsWithoutImprovement}')
            
            if iterationsWithoutImprovement == self.Threshold1:
                print(f"The threshold of {self.Threshold1} iterations without improvement has been reached.")
                currentSolution = bestSolution
                iterationsWithoutImprovement = 0
            
            usedTime = time.time() - startTime

            #profit_over_time[iteration] = usedTime, bestSolution.TotalProfit

            iteration += 1

        print(f'\n Iterated Local Search finished after {iteration} iterations and {usedTime} seconds')
        bestSolution = self.SolutionPool.GetHighestProfitSolution()

        return bestSolution#, profit_over_time
    
    def Perturbation(self, solution: Solution) -> Solution:
        ''' Perturbation to escape local optima '''

        types = ['shake']
        # choose destuction based on probabilities
        destructions = ['big', 'small']
        # choose destruction based on probabilities
        probability_destruction = [0.05, 0.95]
        destruction = self.RNG.choice(destructions, p=probability_destruction)

        if destruction == 'big':
            #jobs_to_remove = int(self.jobsToRemove * 3)
            
            consective_to_remove = int(self.consecutive_to_remove * 2)
            sublists_to_modify = int(self.sublists_to_modify * 2)

        elif destruction == 'small':
            #jobs_to_remove = self.jobsToRemove

            consective_to_remove = self.consecutive_to_remove
            sublists_to_modify = self.sublists_to_modify

        ''''
        print(f'\n Perturbation types: {types}')
        print(f' Perturbation type this iteration: {type}')
        
        if type == 'remove': # Random removal of jobs
            valid_elements = [(key, sublist_idx, item_idx, item) 
                            for key, sublists in solution.RoutePlan.items()
                            for sublist_idx, sublist in enumerate(sublists) 
                            for item_idx, item in enumerate(sublist) 
                            if item <= 1000]

            newRoutePlan = deepcopy(solution.RoutePlan)
            if len(valid_elements) >= jobs_to_remove:
                to_remove = self.RNG.choice(valid_elements, jobs_to_remove, replace = False)
                for key, sublist_idx, item_idx, item in to_remove:
                    newRoutePlan[key][sublist_idx].remove(item)
            else:
                print('RoutePlan is faulty')

            currentSolution = Solution(newRoutePlan, self.InputData)
            self.EvaluationLogic.evaluateSolution(currentSolution)


        elif type == 'shake': # random removal of consectitive jobs
        '''
            
        newRoutePlan = deepcopy(solution.RoutePlan)

        all_sublists = [(key, sublist) for key, sublists in newRoutePlan.items() for sublist in sublists]
        indices = self.RNG.choice(len(all_sublists), min(sublists_to_modify, len(all_sublists)), replace=False)
        selected_sublists = [all_sublists[i] for i in indices]  # Select sublists using the chosen indices

        for key, sublist in selected_sublists:
            valid_positions = [i for i in range(len(sublist) - consective_to_remove + 1)
                                if all(sublist[i + j] <= 1000 for j in range(consective_to_remove))]

            if valid_positions:
                start_pos = self.RNG.choice(a = valid_positions, replace = False)
                del sublist[start_pos:start_pos + consective_to_remove]
            else:
                # Wenn es keine gültigen Positionen gibt, entferne einfach alle Elemente <= 1000
                sublist[:] = [item for item in sublist if item > 1000]


        currentSolution = Solution(newRoutePlan, self.InputData)
        self.EvaluationLogic.evaluateSolution(currentSolution)
        

        return currentSolution
    


class Adaptive_IteratedLocalSearch(IteratedLocalSearch):
    """ Iterative local search with perturbation to escape local optima.
        Local Search with iterative steps through many different neighborhoods.
    """

    def __init__(self, inputData: InputData, maxRunTime:int, sublists_to_modify:int,consecutive_to_remove:int, threshold1:int, score_threshold:int,
                    neighborhoodEvaluationStrategyDelta: str, neighborhoodEvaluationStrategyProfit: str, neighborhoodTypesDelta: list[str], neighborhoodTypesProfit: list[str]):
        super().__init__(inputData, maxRunTime, sublists_to_modify,consecutive_to_remove, threshold1,neighborhoodEvaluationStrategyDelta,neighborhoodEvaluationStrategyProfit,neighborhoodTypesDelta,
                         neighborhoodTypesProfit)

        self.maxRunTime = maxRunTime
        #self.jobsToRemove = jobs_to_remove 
        self.sublists_to_modify = sublists_to_modify
        self.consecutive_to_remove = consecutive_to_remove
        self.NeighborhoodEvaluationStrategyDelta = neighborhoodEvaluationStrategyDelta
        self.NeighborhoodEvaluationStrategyProfit = neighborhoodEvaluationStrategyProfit
        self.NeighborhoodTypesDelta = neighborhoodTypesDelta
        self.NeighborhoodTypesProfit = neighborhoodTypesProfit
        self.NeighborhoodTypes = neighborhoodTypesDelta + neighborhoodTypesProfit
        self.Threshold1 = threshold1
        self.ScoreThreshold = score_threshold

    def Run(self, currentSolution: Solution) -> Solution:
        ''' Run local search with given solutions and iterate through all given neighborhood types '''

        self.InitializeNeighborhoods()
        
        print('\nStarting Adaptive Iterated Local Search')

        startTime = time.time()
        usedTime = 0

        #profit_over_time = {}
        #profit_over_time[0] = 0, currentSolution.TotalProfit


        print('\nStarting Iterated Local Search')
        print(f'\n Running initial local search')

        for delta_neighbor_name, delta_neighbor in self.DeltaNeighborhoods.items():
            print(f'\nRunning local search for {delta_neighbor_name} neighborhood')
            currentSolution = delta_neighbor.LocalSearch('BestImprovement', currentSolution)

        for profit_neighbor_name,profit_neighbor in self.ProfitNeighborhoods.items():
            print(f'\nRunning local search for {profit_neighbor_name} neighborhood')
            currentSolution = profit_neighbor.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)

        iteration = 1
        iterationsWithoutImprovement = 0
        bestIteration = 'initial local search'
        bestSolution = self.SolutionPool.GetHighestProfitSolution()

        scores = [100/len(self.NeighborhoodTypesDelta)]* len(self.NeighborhoodTypesDelta)

        while self.maxRunTime > usedTime:
            
            print(f'Scores: {scores}')
            total_score = sum(scores)
            probabilities = [score / total_score for score in scores]
            neighborhoodTypeDelta = np.random.choice(self.NeighborhoodTypesDelta, p=probabilities, replace=False)

            take_first = np.random.choice([True, False], p=[0.5, 0.5])
            if take_first:
                neighborhoodTypesProfit = self.NeighborhoodTypesProfit[:1]
            else:
                neighborhoodTypesProfit = self.NeighborhoodTypesProfit


            print(f'\nStarting iteration {iteration}')
            print(f' Running perturbation')
            currentSolution = self.Perturbation(currentSolution)
            print(f' Solution after perturbation in iteration {iteration}: \n {currentSolution}')
            
            print(f'\n Running local search after perturbation')

            
            
            for neighborhoodType in neighborhoodTypesProfit:
                print(f' Running neighborhood {neighborhoodType}')
                neighboorhood = self.Neighborhoods[neighborhoodType]
                currentSolution = neighboorhood.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)
            
            
            waitingTimeBeforeDelta = currentSolution.WaitingTime

            # Delta Neighborhoods with probability weight, if waiting time diff more than 1000 then raise score
            print(f' Running neighborhood {neighborhoodTypeDelta}')
            neighboorhood = self.Neighborhoods[neighborhoodTypeDelta]
            currentSolution = neighboorhood.LocalSearch(self.NeighborhoodEvaluationStrategyDelta, currentSolution)

            waitingTimeDifference = currentSolution.WaitingTime - waitingTimeBeforeDelta

            if waitingTimeDifference > self.ScoreThreshold:
                scores[self.NeighborhoodTypesDelta.index(neighborhoodTypeDelta)] += 1

            for neighborhoodType in neighborhoodTypesProfit:
                print(f' Running neighborhood {neighborhoodType}')
                neighboorhood = self.Neighborhoods[neighborhoodType]
                currentSolution = neighboorhood.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)

            print(f' Solution after local search in iteration {iteration}:\n {currentSolution}')

            
            if currentSolution.TotalProfit > bestSolution.TotalProfit:
                iterationsWithoutImprovement = 0
                bestIteration = iteration
            else:
                iterationsWithoutImprovement += 1

            bestSolution = self.SolutionPool.GetHighestProfitSolution()

            print(f'\n Overall best solution found in iteration {bestIteration}: \n {bestSolution}')

            print(f' Iterations without improvement: {iterationsWithoutImprovement}')
            
            if iterationsWithoutImprovement == self.Threshold1:
                print(f"The threshold of {self.Threshold1} iterations without improvement has been reached.")
                currentSolution = bestSolution
                iterationsWithoutImprovement = 0

            usedTime = time.time() - startTime


            #profit_over_time[iteration] = usedTime, self.SolutionPool.GetHighestProfitSolution().TotalProfit


            iteration += 1

        print(f'\n Iterated Local Search finished after {iteration} iterations and {usedTime} seconds')
        bestSolution = self.SolutionPool.GetHighestProfitSolution()

        return bestSolution, iteration



class SAILS(IteratedLocalSearch):
    """ A combination of Simulated Annealing and Iterative local search.."""

    def __init__(self, inputData: InputData, 
                 maxRunTime: int,  # Add the missing parameter 
                 sublists_to_modify: int,  # Add the missing parameter
                 consecutive_to_remove: int,  # Add the missing parameter
                 start_temperature: int,
                 min_temperature: float,
                 temp_decrease_factor: float,
                 maxInnerLoop: int,
                 maxIterationsWithoutImprovement: int,
                 neighborhoodEvaluationStrategyDelta: str = 'BestImprovement',
                 neighborhoodEvaluationStrategyProfit: str = 'BestImprovement',
                 neighborhoodTypesDelta: list[str] = ['SwapWaiting'],
                 neighborhoodTypesProfit: list[str] = ['SwapWaiting']):
        super().__init__(inputData, maxRunTime, sublists_to_modify,consecutive_to_remove)

        self.startTemperature = start_temperature
        self.tempDecreaseFactor = temp_decrease_factor
        self.minTemp = min_temperature
        self.maxInnerLoop = maxInnerLoop
        self.maxIterationsWithoutImprovement = maxIterationsWithoutImprovement
        self.NeighborhoodEvaluationStrategyDelta = neighborhoodEvaluationStrategyDelta
        self.NeighborhoodEvaluationStrategyProfit = neighborhoodEvaluationStrategyProfit
        self.NeighborhoodTypesDelta = neighborhoodTypesDelta
        self.NeighborhoodTypesProfit = neighborhoodTypesProfit
        self.NeighborhoodTypes = neighborhoodTypesDelta + neighborhoodTypesProfit
        self.DeltaNeighborhoods = {}
        self.ProfitNeighborhoods = {}



    def Run(self, solution: Solution) -> Solution:

        self.InitializeNeighborhoods(neighborhoodtypes = self.NeighborhoodTypesDelta, neighborhoods_dict = self.DeltaNeighborhoods)
        self.InitializeNeighborhoods(neighborhoodtypes = self.NeighborhoodTypesProfit, neighborhoods_dict = self.ProfitNeighborhoods)
        
        print('\nStarting SAILS (Simualted Annealing Iterated Local Search)')
        print(f'\n Running initial local search')

        startTime = time.time()
        usedTime = 0

        #profit_over_time = {}
        #profit_over_time[0] = 0, solution.TotalProfit
        
        
        for delta_neighbor_name, delta_neighbor in self.DeltaNeighborhoods.items():
            print(f'\nRunning local search for {delta_neighbor_name} neighborhood')
            solution = delta_neighbor.LocalSearch('BestImprovement', solution)

        for profit_neighbor_name,profit_neighbor in self.ProfitNeighborhoods.items():
            print(f'\nRunning local search for {profit_neighbor_name} neighborhood')
            solution = profit_neighbor.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, solution)

        currentSolution = solution
        lineSolution = solution
        print(f' Solution after initial local search:\n {currentSolution}')

        iteration = 1
        iterationsWithoutImprovement = 0
        bestIteration = 'initial local search'
        bestSolution = self.SolutionPool.GetHighestProfitSolution()

        temperature = self.startTemperature
        

        while self.maxRunTime  > usedTime:
            print(f'\nStarting iteration {iteration}')

            innerLoop = 1
            while innerLoop < self.maxInnerLoop:

                print(f'\n Iteration.InnerLoop {iteration}.{innerLoop}')
                print(f' Running perturbation')
                currentSolution = self.Perturbation(currentSolution)
                print(f' Solution after perturbation in iteration {iteration}.{innerLoop}: \n {currentSolution}')
                
                print(f'\n Running local search after perturbation')

                for profit_neighbor_name,profit_neighbor in self.ProfitNeighborhoods.items():
                    print(f'\nRunning local search for {profit_neighbor_name} neighborhood')
                    currentSolution = profit_neighbor.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)

                for delta_neighbor_name, delta_neighbor in self.DeltaNeighborhoods.items():
                    print(f'\nRunning local search for {delta_neighbor_name} neighborhood')
                    currentSolution = delta_neighbor.LocalSearch(self.NeighborhoodEvaluationStrategyDelta, currentSolution)

                for profit_neighbor_name,profit_neighbor in self.ProfitNeighborhoods.items():
                    print(f'\nRunning local search for {profit_neighbor_name} neighborhood')
                    currentSolution = profit_neighbor.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)

                print(f' Solution after local search in iteration {iteration}.{innerLoop}:\n {currentSolution}')

                if currentSolution.TotalProfit > lineSolution.TotalProfit:
                    lineSolution = currentSolution
                    if currentSolution.TotalProfit > bestSolution.TotalProfit:
                        bestSolution = deepcopy(currentSolution)
                        iterationsWithoutImprovement = 0
                        bestIteration = iteration
                    else:
                        iterationsWithoutImprovement += 1
                else:
                    random_number = self.RNG.random()
                    if random_number < math.exp((currentSolution.TotalProfit - lineSolution.TotalProfit) / (temperature)):
                        lineSolution = currentSolution   
                    else:
                        currentSolution = lineSolution

                    iterationsWithoutImprovement += 1
                
                innerLoop += 1

                if iterationsWithoutImprovement >= self.maxIterationsWithoutImprovement:
                    print(f"The limit of {self.maxIterationsWithoutImprovement} iterations without improvement has been reached.")
                    currentSolution = bestSolution
                    lineSolution = currentSolution
                    iterationsWithoutImprovement = 0

            bestSolution = self.SolutionPool.GetHighestProfitSolution()

            print(f'\n Overall best solution found in iteration {bestIteration}: \n {bestSolution}')

            print(f' Iterations without improvement: {iterationsWithoutImprovement}')
            
            temperature = temperature * self.tempDecreaseFactor

            usedTime = time.time() - startTime

            iteration += 1

            #profit_over_time[iteration] = usedTime, bestSolution.TotalProfit

        print(f'\n SAILS finished after {iteration} iterations and {usedTime} seconds')
        bestSolution = self.SolutionPool.GetHighestProfitSolution()

        return bestSolution#, profit_over_time



class Adaptive_SAILS(IteratedLocalSearch):
    """ A combination of Simulated Annealing and Iterative local search.."""

    def __init__(self, inputData: InputData, 
                 maxRunTime: int,  # Add the missing parameter
                 sublists_to_modify: int,  # Add the missing parameter
                 consecutive_to_remove: int,  # Add the missing parameter
                 start_temperature: int,
                 min_temperature: float,
                 temp_decrease_factor: float,
                 maxInnerLoop: int,
                 maxIterationsWithoutImprovement: int,
                 score_threshold: int = 1000,
                 neighborhoodEvaluationStrategyDelta: str = 'BestImprovement',
                 neighborhoodEvaluationStrategyProfit: str = 'BestImprovement',
                 neighborhoodTypesDelta: list[str] = ['SwapWaiting'],
                 neighborhoodTypesProfit: list[str] = ['SwapWaiting']):
        super().__init__(inputData, maxRunTime, sublists_to_modify,consecutive_to_remove)

        self.startTemperature = start_temperature
        self.tempDecreaseFactor = temp_decrease_factor
        self.minTemp = min_temperature
        self.maxInnerLoop = maxInnerLoop
        self.maxIterationsWithoutImprovement = maxIterationsWithoutImprovement
        self.ScoreThreshold = score_threshold
        self.NeighborhoodEvaluationStrategyDelta = neighborhoodEvaluationStrategyDelta
        self.NeighborhoodEvaluationStrategyProfit = neighborhoodEvaluationStrategyProfit
        self.NeighborhoodTypesDelta = neighborhoodTypesDelta
        self.NeighborhoodTypesProfit = neighborhoodTypesProfit
        self.NeighborhoodTypes = neighborhoodTypesDelta + neighborhoodTypesProfit


    def Run(self, solution: Solution) -> Solution:

        self.InitializeNeighborhoods()
        
        print('\nStarting Adaptive SAILS (Simualted Annealing Iterated Local Search)')
        print(f'\n Running initial local search')

        startTime = time.time()
        usedTime = 0

        #profit_over_time = {}
        #profit_over_time[0] = 0, solution.TotalProfit

        for neighborhoodType in self.NeighborhoodTypesDelta + self.NeighborhoodTypesProfit:    
            print(f' Running neighborhood {neighborhoodType}')
            neighboorhood = self.Neighborhoods[neighborhoodType]
            solution = neighboorhood.LocalSearch('BestImprovement', solution)
            print(f'Best solution after {neighborhoodType}: {solution}')

        currentSolution = solution
        lineSolution = solution
        print(f' Solution after initial local search:\n {currentSolution}')

        iteration = 1
        iterationsWithoutImprovement = 0
        bestIteration = 'initial local search'
        bestSolution = self.SolutionPool.GetHighestProfitSolution()

        temperature = self.startTemperature
        
        
        scores = [100/len(self.NeighborhoodTypesDelta)]* len(self.NeighborhoodTypesDelta)

        while self.maxRunTime  > usedTime:
            print(f'\nStarting iteration {iteration}')

            innerLoop = 1
            while innerLoop < self.maxInnerLoop:

                print(f'Scores: {scores}')
                total_score = sum(scores)
                probabilities = [score / total_score for score in scores]
                neighborhoodTypeDelta = np.random.choice(self.NeighborhoodTypesDelta, p=probabilities, replace=False)


                take_first = np.random.choice([True, False], p=[0.5, 0.5])
                if take_first:
                    neighborhoodTypesProfit = self.NeighborhoodTypesProfit[:1]
                else:
                    neighborhoodTypesProfit = self.NeighborhoodTypesProfit



                print(f'\n Iteration.InnerLoop {iteration}.{innerLoop}')
                print(f' Running perturbation')
                currentSolution = self.Perturbation(currentSolution)
                print(f' Solution after perturbation in iteration {iteration}.{innerLoop}: \n {currentSolution}')
                
                print(f'\n Running local search after perturbation')

                # Only Insert or Insert and ReplaceProfit 50/50% chance
                for neighborhoodType in neighborhoodTypesProfit:
                    print(f' Running neighborhood {neighborhoodType}')
                    neighboorhood = self.Neighborhoods[neighborhoodType]
                    currentSolution = neighboorhood.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)

                waitingTimeBeforeDelta = currentSolution.WaitingTime

                # Delta Neighborhoods with probability weight, if waiting time diff more than 1000 then raise score
                print(f' Running neighborhood {neighborhoodTypeDelta}')
                neighboorhood = self.Neighborhoods[neighborhoodTypeDelta]
                currentSolution = neighboorhood.LocalSearch(self.NeighborhoodEvaluationStrategyDelta, currentSolution)

                waitingTimeDifference = currentSolution.WaitingTime - waitingTimeBeforeDelta

                if waitingTimeDifference > self.ScoreThreshold:
                    scores[self.NeighborhoodTypesDelta.index(neighborhoodTypeDelta)] += 1


                # Only Insert or Insert and ReplaceProfit 50/50% chance
                for neighborhoodType in neighborhoodTypesProfit:
                    print(f' Running neighborhood {neighborhoodType}')
                    neighboorhood = self.Neighborhoods[neighborhoodType]
                    currentSolution = neighboorhood.LocalSearch(self.NeighborhoodEvaluationStrategyProfit, currentSolution)

                print(f' Solution after local search in iteration {iteration}.{innerLoop}:\n {currentSolution}')

                if currentSolution.TotalProfit > lineSolution.TotalProfit:
                    lineSolution = currentSolution
                    if currentSolution.TotalProfit > bestSolution.TotalProfit:
                        bestSolution = deepcopy(currentSolution)
                        iterationsWithoutImprovement = 0
                        bestIteration = iteration
                    else:
                        iterationsWithoutImprovement += 1
                else:
                    random_number = self.RNG.random()
                    if random_number < math.exp((currentSolution.TotalProfit - lineSolution.TotalProfit) / (temperature)):
                        lineSolution = currentSolution   
                    else:
                        currentSolution = lineSolution

                    iterationsWithoutImprovement += 1
                
                innerLoop += 1

                if iterationsWithoutImprovement >= self.maxIterationsWithoutImprovement:
                    print(f"The limit of {self.maxIterationsWithoutImprovement} iterations without improvement has been reached.")
                    currentSolution = bestSolution
                    lineSolution = currentSolution
                    iterationsWithoutImprovement = 0

            bestSolution = self.SolutionPool.GetHighestProfitSolution()

            print(f'\n Overall best solution found in iteration {bestIteration}: \n {bestSolution}')

            print(f' Iterations without improvement: {iterationsWithoutImprovement}')
            
            temperature = temperature * self.tempDecreaseFactor

            usedTime = time.time() - startTime

            #profit_over_time[iteration] = usedTime, self.SolutionPool.GetHighestProfitSolution().TotalProfit

            iteration += 1

        print(f'\n SAILS finished after {iteration} iterations and {usedTime} seconds')
        bestSolution = self.SolutionPool.GetHighestProfitSolution()

        return bestSolution, iteration



class SimulatedAnnealingLocalSearch(ImprovementAlgorithm):
    """ Simulated Annealing algorithm with perturbation to escape local optima. """

    def __init__(self, inputData: InputData,
                 start_temperature:int,
                 min_temperature:float,
                 temp_decrease_factor:float,
                 maxRunTime:int,
                 maxRandomMoves:int,
                 neighborhoodTypesDelta: list[str] = ['SwapIntraRoute','TwoEdgeExchange','SwapInterRoute',"ReplaceDelta"],
                 neighborhoodTypesProfit: list[str] = ['Insert','ReplaceProfit']):
        super().__init__(inputData)

        self.neighborhoodTypesDelta = neighborhoodTypesDelta
        self.neighborhoodTypesProfit = neighborhoodTypesProfit
        self.maxRunTime = maxRunTime
        self.startTemperature = start_temperature
        self.tempDecreaseFactor = temp_decrease_factor
        self.minTemp = min_temperature
        self.DeltaNeighborhoods = {}
        self.ProfitNeighborhoods = {}
        self.MaxRandomMoves = maxRandomMoves

    def Run(self, currentSolution: Solution) -> Solution:

        self.InitializeNeighborhoods(neighborhoodtypes = self.neighborhoodTypesDelta, neighborhoods_dict = self.DeltaNeighborhoods)
        self.InitializeNeighborhoods(neighborhoodtypes = self.neighborhoodTypesProfit, neighborhoods_dict = self.ProfitNeighborhoods)

        print('\nStarting Simulated Annealing Local Search Procedure')

        startTime = time.time()
        usedTime = 0

        bestLoop = 0
        temperature = self.startTemperature
        iteration = 1

        probabilities = [1/len(self.DeltaNeighborhoods) for i in range(len(self.DeltaNeighborhoods))]

        #profit_over_time = {}
        #profit_over_time[0] = 0, currentSolution.TotalProfit

        while self.maxRunTime > usedTime:
            
            #Update at beginning and before every iteration of Local Improvement
            bestSolutionWaitingTime = currentSolution.WaitingTime
            
            print(f'\nStarting iteration {iteration}')

            #SA mit Delta Nachbarschaften --> Wartezeit als Kriterium
            innerLoop = 0
            bestLoop = 0
                        
            print(f'\nRunning Simulated Annealing for Delta neighborhoods')
            temperature = self.startTemperature

            while temperature > self.minTemp:
          
                delta_neighborhood = self.RNG.choice(list(self.DeltaNeighborhoods.values()), p = probabilities)

                move = delta_neighborhood.SingleMove(currentSolution, self.MaxRandomMoves)

                if move is not None: #Break MakeOneMove, when Iterations is about 10000
                    if move.Delta < 0:
                        completeRouteplan = delta_neighborhood.constructCompleteRoute(move,currentSolution)
                        
                        currentSolution.setRoutePlan(completeRouteplan, self.InputData)
                        if delta_neighborhood.Type == "ReplaceDelta":
                            currentSolution.remove_unused_Task(move.UnusedTask)
                        self.EvaluationLogic.evaluateSolution(currentSolution)
                
                        if currentSolution.WaitingTime > bestSolutionWaitingTime:
                            
                            #Create Best Known Solution
                            bestLoop = innerLoop
                            bestKnownSolution = Solution(deepcopy(completeRouteplan), self.InputData)
                            self.EvaluationLogic.evaluateSolution(bestKnownSolution) #Evaluate Sol
                            #self.SolutionPool.AddSolution(bestKnownSolution)
                            #Schauen ob die vorhergehenden Lösungen gleich bleiben -> Debug Modus 
                            bestSolutionWaitingTime = bestKnownSolution.WaitingTime
                    else:
                        random_number = self.RNG.random()
                        if random_number < math.exp(-move.Delta / (temperature)):
                            completeRouteplan = delta_neighborhood.constructCompleteRoute(move,currentSolution)
                            currentSolution.setRoutePlan(completeRouteplan, self.InputData)
                            if delta_neighborhood.Type == "ReplaceDelta":
                                currentSolution.remove_unused_Task(move.UnusedTask)
                            self.EvaluationLogic.evaluateSolution(currentSolution)
                

                temperature = temperature * self.tempDecreaseFactor

                innerLoop += 1


            #Overwrite before Local Search
            if bestLoop > 0:
                currentSolution = bestKnownSolution

                #print(f'\n Time needed to find simulated annealing solution: {round(usedTime,2)} seconds')
                print(f' Best solution after inner loop {bestLoop}/{innerLoop}, {bestKnownSolution}')
                
            else: 
                #print(f'\n Time needed to find simulated annealing solution: {round(usedTime,2)} seconds')
                print(f' Best solution after inner loop {bestLoop}/{innerLoop}, {currentSolution}')


            for profit_neighbor_name,profit_neighbor in self.ProfitNeighborhoods.items():

                print(f'\nRunning local search for {profit_neighbor_name} neighborhood')
                currentSolution = profit_neighbor.LocalSearch('BestImprovement', currentSolution)
            
                #print(f'\n Time to find local search solution: {round(usedTime,2)} seconds')
                print(f' Best solution after local search: {currentSolution}')
                

            usedTime = time.time() - startTime

            #profit_over_time[iteration] = usedTime, self.SolutionPool.GetHighestProfitSolution().TotalProfit
 
            iteration += 1



        print(f'Number of total iterations: {iteration}')
        return self.SolutionPool.GetHighestProfitSolution()#, profit_over_time

