from InputData import InputData
from ConstructiveHeuristic import *
from ImprovementAlgorithm import *
from EvaluationLogic import *
import time
from MIP_Upper_Bound import *

class Solver:
    ''' Orchestrates all single pieces to form one strong algorithm to solve flowshop problems
    '''
    def __init__(self, inputData:InputData, seed:int):
        self.InputData = inputData
        self.Seed = seed
        self.RNG = numpy.random.default_rng(self.Seed)
        self.EvaluationLogic = EvaluationLogic(inputData)
        self.ParetoSolutions = ParetoSolutions(inputData, self.RNG)
        self.runTime = {}
        
        self.ConstructiveHeuristic = ConstructiveHeuristics(paretoSolutions=self.ParetoSolutions, evaluationLogic=self.EvaluationLogic)

    

    def ConstructionPhase(self, order_item_attractiveness_technique, machine_attractiveness_technique) -> Solution:
        ''' Find one start solution by using the chosen constructive heuristic'''

        starttime = time.time()
        start_solutuion = self.ConstructiveHeuristic.Run(self.InputData, order_item_attractiveness_technique, machine_attractiveness_technique)
        print("Constructive solution found:")
        print(start_solutuion)

        endtime = time.time()
        self.RunTime = endtime - starttime


        return start_solutuion


    def ImprovementPhase(self, startSolution:Solution, algorithm:ImprovementAlgorithm) -> Solution:
        ''' Start the improvement phase by choosing a algorithm'''

        algorithm.Initialize(self.EvaluationLogic, self.ParetoSolutions, self.RNG)
        bestSolution = algorithm.Run(startSolution)

        return bestSolution
    
    def UpperBound(self):
        ''' Calculate the upper bound for the problem instance'''

        optimizer = UpperBound(self.InputData, "both")
        site_fulfillment = optimizer.execute()
        self.InputData.site_fulfillment = int(site_fulfillment)

        self.InputData.reduce_input_data(self.InputData.site_fulfillment)
        
        print(f"Upper Bound = {round(site_fulfillment, 2)}")



    def RunAlgorithm(self, order_item_attractiveness_technique, machine_attractiveness_technique, algorithm:ImprovementAlgorithm):
        ''' Run local search with chosen algorithm and neighborhoods'''

        starttime = time.time()

        self.UpperBound()

        startSolution = self.ConstructionPhase(order_item_attractiveness_technique, machine_attractiveness_technique)

        self.ImprovementPhase(startSolution, algorithm)


        endtime = time.time()
        self.RunTime = endtime - starttime

        print("Total run time algorithm: ", round(self.RunTime, 2), " seconds")

