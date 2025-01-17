
from OutputData import *
from InputData import *
from EvaluationLogic import *

class ConstructiveHeuristics:
    ''' Class for creating objects to run different constructive heuristics'''

    def __init__(self,  solutionPool:SolutionPool, evaluationLogic:EvaluationLogic):

        self.EvaluationLogic = evaluationLogic
        self._SolutionPool = solutionPool


    

    def Greedy(self, inputdata:InputData):
        
        print("Greedy")
        # Create a new solution
        