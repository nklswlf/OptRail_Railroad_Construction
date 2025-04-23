from InputData import InputData
from ConstructiveHeuristic import *
from ImprovementAlgorithm import *
from EvaluationLogic import *
import time
from MIP_UB import *
import numpy

class Solver:
    ''' Orchestrates all single pieces to form one strong algorithm to solve flowshop problems
    '''
    def __init__(self, inputData:InputData, seed:int):
        self.InputData = inputData
        self.Seed = seed
        self.RNG = numpy.random.default_rng(self.Seed)
        self.EvaluationLogic = EvaluationLogic(inputData)
        self.ParetoSolutions = ParetoSolutions(inputData, self.RNG)
        
        self.ConstructiveHeuristic = ConstructiveHeuristics(evaluationLogic=self.EvaluationLogic, rng=self.RNG)


    def BoundPhase(self, UB_technique):
        ''' Calculate the upper bound for the problem instance'''

        print("\nCalculating Upper Bound...")

        optimizer = UpperBound(self.InputData, bound_technique=UB_technique)
        best_orders = optimizer.execute()

        for order_number in best_orders:
            self.InputData.activate_order(order_number)
    

    def ConstructionPhase(self, greedy_technique) -> Solution:
        ''' Start the construction phase by choosing a constructive heuristic'''

        start_solutuion = self.ConstructiveHeuristic.Run(self.InputData, greedy_technique)

        return start_solutuion
    

    def BuildingPhase(self, startSolution:Solution, algorithm:ImprovementAlgorithm) -> Solution:
        ''' Start the building phase by choosing a algorithm'''

        print("\nBuilding Phase started...")

        algorithm.Initialize(self.EvaluationLogic, self.ParetoSolutions, self.RNG)
        staffed_solutuion = algorithm.Run(startSolution)


        return staffed_solutuion


    def ImprovementPhase(self, startSolution:Solution, algorithm:ImprovementAlgorithm) -> Solution:
        ''' Start the improvement phase by choosing a algorithm'''

        print("\nImprovement Phase started...")

        algorithm.Initialize(self.EvaluationLogic, self.ParetoSolutions, self.RNG)
        algorithm.Run(startSolution)



    
#####################################################################################################################################################################################
   
    

    
    def RunConstructive(self, UB_technique, greedy_technique):
        ''' Run the constructive heuristic and return the solution'''

        self.BoundPhase(UB_technique)

        startSolution = self.ConstructionPhase(greedy_technique)


        return startSolution



    def RunBuilding(self, UB_technique, greedy_technique, building_algorithm):
        ''' Run the building phase and return the solution'''

        self.BoundPhase(UB_technique)

        startSolution = self.ConstructionPhase(greedy_technique)

        staffed_solution = self.BuildingPhase(startSolution, building_algorithm)


        return staffed_solution




    def Run(self, UB_technique, greedy_technique, building_algorithm, improvement_algorithm):
        ''' Run the algorithm and return the solution'''

        start_time = time.time()

        self.BoundPhase(UB_technique)

        bound_time = time.time() - start_time

        startSolution = self.ConstructionPhase(greedy_technique)

        construction_time = time.time() - start_time - bound_time

        staffed_solution = self.BuildingPhase(startSolution, building_algorithm)

        building_time = time.time() - start_time - bound_time - construction_time

        self.ImprovementPhase(staffed_solution, improvement_algorithm)

        improvement_time = time.time() - start_time - bound_time - construction_time - building_time

        total_time = time.time() - start_time

        times = {   "Bound Time": bound_time,
                    "Construction Time": construction_time,
                    "Building Time": building_time,
                    "Improvement Time": improvement_time,
                    "Total Time": total_time}

        return times



