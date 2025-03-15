from InputData import *
from OutputData import *
from ConstructiveHeuristic import *
from ImprovementAlgorithm import *
from EvaluationLogic import *

import random
import time

class Solver:
    ''' Orchestrates all single pieces to form one strong algorithm to solve flowshop problems
    '''
    def __init__(self, inputData:InputData, seed:int):
        self.InputData = inputData
        self.Seed = seed
        self.RNG = numpy.random.default_rng(self.Seed)
        self.EvaluationLogic = EvaluationLogic(inputData)
        self.ParetoSolutions = ParetoSolutions(inputData)
        self.runTime = {}
        
        self.ConstructiveHeuristic = ConstructiveHeuristics(paretoSolutions=self.ParetoSolutions, evaluationLogic=self.EvaluationLogic)

    

    def ConstructionPhase(self, order_item_attractiveness_technique, machine_attractiveness_technique) -> Solution:
        ''' Find one start solution by using the chosen constructive heuristic'''

        starttime = time.time()
        start_solutuion = self.ConstructiveHeuristic.Run(self.InputData, order_item_attractiveness_technique, machine_attractiveness_technique)
        print("Constructive solution found.")
        print(start_solutuion)

        endtime = time.time()
        self.RunTime = endtime - starttime

        return start_solutuion



    def ImprovementPhase(self, startSolution:Solution, algorithm:ImprovementAlgorithm) -> Solution:
        ''' Start the improvement phase by choosing a algorithm'''

        algorithm.Initialize(self.EvaluationLogic, self.ParetoSolutions, self.RNG)
        bestSolution = algorithm.Run(startSolution)

        return bestSolution



    def RunAlgorithm(self, order_item_attractiveness_technique, machine_attractiveness_technique, algorithm:ImprovementAlgorithm):
        ''' Run local search with chosen algorithm and neighborhoods'''

        starttime = time.time()
        startSolution = self.ConstructionPhase(order_item_attractiveness_technique, machine_attractiveness_technique)
        self.ParetoSolutions.UpdateParetoFront(startSolution)

        bestSolution = self.ImprovementPhase(startSolution, algorithm)


        print("Best found Solution.")
        print(bestSolution)

        endtime = time.time()
        self.RunTime = endtime - starttime

