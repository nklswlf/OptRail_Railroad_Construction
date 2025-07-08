from Code.InputData import InputData
from Code.ConstructiveHeuristic import *
from Code.ImprovementAlgorithm import *
from Code.EvaluationLogic import *
import time
from Code.MIP_UB import *
import numpy
import os
import json

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

        print("\nImprovement Phase with", self.InputData.algo, "started...")

        algorithm.Initialize(self.EvaluationLogic, self.ParetoSolutions, self.RNG)
        algorithm.Run(startSolution)



    
#####################################################################################################################################################################################
   
    
    def RunBound(self, UB_technique):
        ''' Run the bound phase and return the solution'''

        start_time = time.time()

        self.BoundPhase(UB_technique)

        bound_time = time.time() - start_time

        return bound_time


    
    def RunConstructive(self, UB_technique, greedy_technique):
        ''' Run the constructive heuristic and return the solution'''

        self.BoundPhase(UB_technique)

        start_time = time.time()

        startSolution = self.ConstructionPhase(greedy_technique)

        greedy_time = time.time() - start_time


        return startSolution, greedy_time



    def RunBuilding(self, UB_technique, greedy_technique, building_algorithm):
        ''' Run the building phase and return the solution'''
        
        start_time = time.time()
        self.BoundPhase(UB_technique)
        bound_time = time.time() - start_time
        print("Bound Time:", bound_time)

        start_time = time.time()
        startSolution = self.ConstructionPhase(greedy_technique)
        greedy_time = time.time() - start_time
        print("Greedy Time:", greedy_time)

        start_time = time.time()
        staffed_solution = self.BuildingPhase(startSolution, building_algorithm)
        building_time = time.time() - start_time
        print("Building Time:", building_time)

        return staffed_solution, building_time




    def Run(self, UB_technique, greedy_technique, building_algorithm, improvement_algorithm):
        ''' Run the algorithm and return the solution'''

        start_time = time.time()

        self.BoundPhase(UB_technique)
        
        bound_time = time.time() - start_time

        startSolution = self.ConstructionPhase(greedy_technique)

        greedy_time = time.time() - start_time - bound_time

        staffed_solution = self.BuildingPhase(startSolution, building_algorithm)

        building_time = time.time() - start_time - bound_time - greedy_time

        self.ImprovementPhase(staffed_solution, improvement_algorithm)


        output_file = os.path.join(self.InputData.solutions_path, "pareto_solutions.json")

        solutions_data = {}
        for idx, solution in enumerate(self.ParetoSolutions.ParetoFront):
            solutions_data[idx + 1] = {
            "worker_route_plan": getattr(solution, "route_plan_worker", None),
            "attachment_route_plan": getattr(solution, "route_plan_attachment", None),
            "machine_route_plan": getattr(solution, "route_plan_machine", None),
            "Orders": getattr(solution, "number_of_finished_orders", None),
            "Order Items": getattr(solution, "number_of_finished_order_items", None),
            "Driver Violation": getattr(solution, "driver_violation", None),
            "Commute Distance": round(getattr(solution, "total_commute_distance", 0), 2) if hasattr(solution, "total_commute_distance") else None,
            "Transport Machines": round(getattr(solution, "total_transport_distance", 0), 2) if hasattr(solution, "total_transport_distance") else None,
            "Transport Attachments": round(getattr(solution, "total_transport_distance_attachments", 0), 2) if hasattr(solution, "total_transport_distance_attachments") else None,
            "Machines": getattr(solution, "number_of_machines", None),
            "Workers": getattr(solution, "number_of_workers", None),
            "Attachments": getattr(solution, "number_of_attachments", None)
            }

        with open(output_file, "w") as f:
            json.dump(solutions_data, f, indent=2)



        improvement_time = time.time() - start_time - bound_time - greedy_time - building_time

        total_time = time.time() - start_time

        times = {   "Bound Time": bound_time,
                    "Greedy Time": greedy_time,
                    "Building Time": building_time,
                    "Improvement Time": improvement_time,
                    "Total Time": total_time}

        return times



