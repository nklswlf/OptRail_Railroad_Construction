from InputData import InputData
from ConstructiveHeuristic import *
from ImprovementAlgorithm import *
from EvaluationLogic import *
import time
from MIP_UB import *

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
        print("Constructive solution found after:", round(time.time() - starttime, 2), "seconds")
        print(start_solutuion)

        endtime = time.time()
        self.ConstructionTime = endtime - starttime


        return start_solutuion


    def ImprovementPhase(self, startSolution:Solution, algorithm:ImprovementAlgorithm) -> Solution:
        ''' Start the improvement phase by choosing a algorithm'''

        print("\nImprovement Phase started...")
        start_time = time.time()

        algorithm.Initialize(self.EvaluationLogic, self.ParetoSolutions, self.RNG)
        bestSolution = algorithm.Run(startSolution)

        print("\nImprovement Phase finished after:", round(time.time() - start_time, 2), "seconds")

        return bestSolution
    
    def UpperBound(self, UB_technique):
        ''' Calculate the upper bound for the problem instance'''

        print("\nCalculating Upper Bound...")

        start_time = time.time()
        optimizer = UpperBound(self.InputData, bound_technique=UB_technique)
        site_fulfillment = optimizer.execute()
        self.InputData.site_fulfillment = int(site_fulfillment[0])

        
        self.InputData.reduce_input_data(self.InputData.site_fulfillment)

        if self.InputData.instance == "a20_o236_m12_an106_ar24":
            self.InputData.deactivate_order(8)
            self.InputData.activate_order(11)

        for order in self.InputData.orders:
            if order.status == False:
                print("Order", order.order_number, "is not planned.")
        
        self.UpperBoundTime = time.time() - start_time
        print("\nUpper Bound calculated after:", round(self.UpperBoundTime, 2), "seconds")
        print(f"UB = {round(site_fulfillment[0], 2)}")

    
    def RunConstructive(self, UB_technique, order_item_attractiveness_technique, machine_attractiveness_technique):
        ''' Run the constructive heuristic and return the solution'''

        self.UpperBound(UB_technique)

        starttime = time.time()

        startSolution = self.ConstructionPhase(order_item_attractiveness_technique, machine_attractiveness_technique)

        endtime = time.time()
        self.RunTime = endtime - starttime

        return startSolution, self.UpperBoundTime, self.ConstructionTime, self.RunTime




    def RunAlgorithm(self, UB_technique, order_item_attractiveness_technique, machine_attractiveness_technique, algorithm:ImprovementAlgorithm):
        ''' Run local search with chosen algorithm and neighborhoods'''

        self.UpperBound(UB_technique)

        starttime = time.time()

        startSolution = self.ConstructionPhase(order_item_attractiveness_technique, machine_attractiveness_technique)

        building_time, individual_time, dominance_time, feasibility_check_time = self.ImprovementPhase(startSolution, algorithm)

        endtime = time.time()
        self.RunTime = endtime - starttime

        return self.UpperBoundTime, self.ConstructionTime, building_time, individual_time, dominance_time, feasibility_check_time, self.RunTime

