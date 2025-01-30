from OutputData import Solution
from OutputData import *
import itertools        
from EvaluationLogic import EvaluationLogic
import concurrent.futures  # For parallelism

# Dummy class to have one class where all Moves are inheriting --> Potential to implement more funtionalities here! 
class BaseMove: 
    ''' Base Move Class, that all specific Move classes can inherit from! '''

    def __init__(self):
        self.Delta = None
        self.RouteDayCohort = None
        self.Day = None
        self.Cohort = None

    def setDelta(self,delta:int) -> None: 
        ''' Set the Delta of the Move'''
        self.Delta = delta

    def setExtraTime(self,extraTime:int) -> None: 
        ''' Set the ExtraTime of the Move'''
        self.ExtraTime = extraTime

class BaseNeighborhood:
    ''' Framework for generally needed neighborhood functionalities'''

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng = None):
        self.InputData = inputData
        self.RoutePlan = None
        self.EvaluationLogic = evaluationLogic
        self.SolutionPool = solutionPool
        self.RNG = rng

        # Create empty lists for discovering different moves
        self.Moves = []
        self.MoveSolutions = []
        self.Type = 'None'

    def DiscoverMoves(self) -> None:
        ''' Find all possible moves for particular neighborhood and permutation
            And shuffles them! 
        '''
        raise Exception('DiscoverMoves() is not implemented for the abstract BaseNeighborhood class.')

    def EvaluateMoves(self, evaluationStrategy: str) -> None:
        ''' Define a strategy for the local search of the neighborhood and "activate" it'''

        if evaluationStrategy == 'BestImprovement':
            self.EvaluateMovesBestImprovement()
        elif evaluationStrategy == 'FirstImprovement':
            self.EvaluateMovesFirstImprovement()
        else:
            raise Exception(f'Evaluation strategy {evaluationStrategy} not implemented.')

    def EvaluateMove(self, move: BaseMove) -> None:
        ''' Calculates the MakeSpan of the certain move - adds to recent Solution'''
        raise Exception('EvaluateMove() is not implemented for the abstract BaseNeighborhood class.')

    def EvaluateMovesBestImprovement(self) -> None:
        """ Evaluate all moves for best improvement and adds the calculated solutions to list MoveSolutions"""
        for move in self.Moves:
            self.EvaluateMove(move)
            self.MoveSolutions.append(move)

    def EvaluateMovesFirstImprovement(self) -> None:
        """ Evaluate all moves until the first one is found that improves the best solution found so far. """
        raise Exception('EvaluateMovesFirstImprovement() is not implemented for the abstract BaseNeighborhood class.')

    def MakeBestMove(self) -> BaseMove:
        ''' Returns the best move found from the list Move Solutions'''
        raise Exception('MakeBestMove() is not implemented for the abstract BaseNeighborhood class.')

    def Update(self, new_routeplan) -> None:
        ''' Updates the actual permutation and deletes all saved Moves and Move Solutions'''
        self.Moves.clear()
        self.MoveSolutions.clear()
        self.RoutePlan = new_routeplan

    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> None:
        ''' Tries to find a better solution from the start solution by searching the neighborhod'''
        raise Exception('LocalSearch() is not implemented for the abstract BaseNeighborhood class.')
    
    def MakeOneMove(self, move: BaseMove) -> Solution:
        ''' Returns the solution of a single move'''
        raise Exception('MakeOneMove() is not implemented for the abstract BaseNeighborhood class.')

    def constructCompleteRoute(self, move:BaseMove, solution=None) -> dict: 
        ''' Constructs the comlete Route from the Move and the BaseMove'''

        adapted_Route_Plan = solution.RoutePlan if solution else self.RoutePlan

        adapted_Route_Plan[move.Day][move.Cohort] = move.RouteDayCohort

        return adapted_Route_Plan
    
    def SingleRouteFeasibilityCheck(self, route: list[int]) -> bool:
        """
        Checks the feasibility of a single route considering service times, travel distances, and main task constraints.

        Parameters:
        -----------
        route : list[int]
            A list of task IDs representing the sequence of tasks in the route. Task IDs greater than 1000 are considered main tasks.
        
        inputData : InputData
            An object containing necessary input data such as distances, task details, and constraints.

        Returns:
        --------
        bool
            Returns True if the route is feasible, otherwise returns False.
        """

        feasible = True
        serviceDuration = 0
        previousTask = 0  # Start at depot
        mainTasks = [task for task in route if task > 1000]  # Identify all main tasks in the route
        
        #Cache
        distances = self.InputData.distances
        allTasks = self.InputData.allTasks
        maxRouteDuration = self.InputData.maxRouteDuration

        if mainTasks:
            mainIndices = [i for i, task in enumerate(route) if task in mainTasks]  # Find the indices of all main tasks
            previousTask = 0  # Reset to depot at the start
            current_index = 0
            for mainIndex in mainIndices:
                tasksBeforeMain = route[:(mainIndex - current_index)]  # Get all tasks before the current main task
                mainTask = route[(mainIndex - current_index)]
                tasksAfterMain = route[(mainIndex - current_index)+1:]  # Get all tasks after the current main task

                # Process tasks before the main task
                for task in tasksBeforeMain:
                    serviceDuration += distances[previousTask][task] + allTasks[task].service_time
                    previousTask = task

                serviceDuration += distances[previousTask][mainTask]  # Add travel time to main task

                # Check if the main task can be started at the earliest start time
                if serviceDuration > allTasks[mainTask].start_time:
                    return False

                # Reset the service duration to the main task's start time and process the main task
                serviceDuration = allTasks[mainTask].start_time + allTasks[mainTask].service_time
                previousTask = mainTask

                # Process tasks after the main task
                route = tasksAfterMain
                current_index += (mainIndex + 1) 

            # Process remaining tasks after the last main task
            for task in route:
                serviceDuration += distances[previousTask][task] + allTasks[task].service_time
                previousTask = task

            serviceDuration += distances[previousTask][0]  # Add travel time to depot

            if serviceDuration > maxRouteDuration:
                return False

        else:  # Route consists of optional tasks only
            for task in route:
                serviceDuration += distances[previousTask][task] + allTasks[task].service_time
                previousTask = task

            serviceDuration += distances[previousTask][0]  # Add travel time to depot
            
            if serviceDuration > maxRouteDuration:
                return  False

        return feasible

        
    def SingleMove(self, solution: Solution, maxAttempts) -> Solution:
        ''' Overwritten to avoid comparisons of strings'''
        
        MAX_ATTEMPTS = maxAttempts  # Maximum attempts limit
        feasible = False
        attempt = 0
        move = None  # Placeholder for the move

        while not feasible and attempt < MAX_ATTEMPTS:
            move = self.MakeOneMove(solution)
            feasible = self.SingleRouteFeasibilityCheck(move.RouteDayCohort)
            attempt += 1

        # If a feasible move is found, evaluate and return it
        if feasible:
            self.EvaluateMove(move)
        
        else: 
            move = None


        return move
    
#_______________________________________________________________________________________________________________________

class ProfitNeighborhood(BaseNeighborhood):

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

    def EvaluateMove(self, move: BaseMove) -> None:
        raise Exception('EvaluateMove() is not implemented for the abstract ProfitNeighborhood class.')

    def MakeBestMove(self) -> BaseMove:
        
        # Sorting will be handled by the child classes
        self.sort_move_solutions()
        
        for move_solution in self.MoveSolutions:

            if self.SingleRouteFeasibilityCheck(move_solution.RouteDayCohort): 
                return move_solution
                    
        return None

    def sort_move_solutions(self):
        # Placeholder method to be overridden by child classes
        raise NotImplementedError('sort_move_solutions() must be implemented in the child class')
            
    def EvaluateMovesFirstImprovement(self) -> None:
        """ Evaluate all moves until the first one is found that improves the best solution found so far. """

        for move in self.Moves:
            self.EvaluateMove(move)

            ### NEED OF FEASIBILITY CHECK!! 
            if self.SingleRouteFeasibilityCheck(move.RouteDayCohort):
                self.MoveSolutions.append(move)
                return None
        
        ### Return None, if no feasible moves found! 
        return None 

    def LocalSearch(self, neighborhoodEvaluationStrategy:str, solution:Solution) -> None:
        ''' Tries to find a better solution from the start solution by searching the neighborhod'''

        hasSolutionImproved = True
        bestNeighborhoodSolution = Solution(solution.RoutePlan, self.InputData)
        self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

        while hasSolutionImproved:
            
            # Sets Algorithm back!
            self.Update(bestNeighborhoodSolution.RoutePlan) 
            self.DiscoverMoves(bestNeighborhoodSolution)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()


            if bestNeighborhoodMove is not None:

                completeRoute = self.constructCompleteRoute(bestNeighborhoodMove)
                bestNeighborhoodSolution = Solution(completeRoute, self.InputData)
                self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

                self.SolutionPool.AddSolution(bestNeighborhoodSolution)

            else:
            
                hasSolutionImproved = False

        return bestNeighborhoodSolution

class DeltaNeighborhood(BaseNeighborhood):
    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

    def EvaluateMove(self, move: BaseMove) -> None:
        raise Exception('EvaluateMove() is not implemented for the abstract DeltaNeighborhood class.')

    def MakeBestMove(self) -> BaseMove:
        ''' Finds one best Move'''
        self.MoveSolutions.sort(key=lambda move: move.Delta)

 
        for move_solution in self.MoveSolutions:

            if self.SingleRouteFeasibilityCheck(move_solution.RouteDayCohort): 
                return move_solution
                    
        return None
            
    
    def EvaluateMovesFirstImprovement(self) -> None:
        """ Evaluate all moves until the first one is found that improves the best solution found so far. """

        for move in self.Moves:

            self.EvaluateMove(move)

            if move.Delta < 0:
                
                if self.SingleRouteFeasibilityCheck(move.RouteDayCohort):
                    
                    self.MoveSolutions.append(move)
                    # abort neighborhood evaluation because an improvement has been found
                    return None
        
        return None
    

    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> Solution:

        hasSolutionImproved = True

        bestNeighborhoodSolution = Solution(solution.RoutePlan, self.InputData)
        self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

        while hasSolutionImproved:
            
            self.Update(bestNeighborhoodSolution.RoutePlan)
            self.DiscoverMoves()
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()

            if bestNeighborhoodMove is not None and bestNeighborhoodMove.Delta < 0:
              
                completeRoute = self.constructCompleteRoute(bestNeighborhoodMove)
                bestNeighborhoodSolution = Solution(completeRoute, self.InputData)
                self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)
            
                self.SolutionPool.AddSolution(bestNeighborhoodSolution)
            else:
                
                hasSolutionImproved = False

        return bestNeighborhoodSolution
    
    
#_______________________________________________________________________________________________________________________

class SwapIntraRouteMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """

    def __init__(self, initialRoutePlan:list, day:int, cohort:int, taskA:int, taskB:int, indexA:int, indexB:int):

        self.RouteDayCohort = initialRoutePlan.copy() # create a copy of the permutation
        self.TaskA = taskA
        self.TaskB = taskB
        self.Day = day
        self.Cohort = cohort
        self.indexA = indexA
        self.indexB = indexB

        #Swap Tasks 
        self.RouteDayCohort[self.indexA], self.RouteDayCohort[self.indexB] = self.TaskB, self.TaskA

class SwapIntraRouteNeighborhood(DeltaNeighborhood):
    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData:InputData, evaluationLogic:EvaluationLogic, solutionPool:SolutionPool, rng):
        super().__init__(inputData,  evaluationLogic, solutionPool, rng)

        self.Type = 'SwapIntraRoute'


    def DiscoverMoves(self):
        """ Generate all $n choose 2$ moves and shuffle them """

        for day in range(len(self.RoutePlan)):
            for cohort in range(len(self.RoutePlan[day])):
                # Get the cohort once and pre-filter tasks <= 1000
                cohort_tasks = self.RoutePlan[day][cohort]
                valid_tasks = {task for task in cohort_tasks if task <= 1000}

                # Generate combinations of two distinct tasks
                for task_i, task_j in itertools.combinations(valid_tasks, 2):
                    index_i = cohort_tasks.index(task_i)
                    index_j = cohort_tasks.index(task_j)
                    # Create Swap Move Objects with different permutations
                    self.Moves.append(SwapIntraRouteMove(cohort_tasks, day, cohort, task_i, task_j, index_i, index_j))

        # Shuffle the Moves at the end
        self.RNG.shuffle(self.Moves)


    def EvaluateMove(self, move:SwapIntraRouteMove) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.EvaluationLogic.CalculateSwapIntraRouteDelta(move))
    
    def MakeOneMove(self, solution: Solution) -> SwapIntraRouteMove:  
        # Randomly select a day and cohort
        day = self.RNG.integers(0, len(solution.RoutePlan))
        cohort = self.RNG.integers(0, len(solution.RoutePlan[day]))

        # Get the cohort once to avoid redundant lookups
        cohort_tasks = solution.RoutePlan[day][cohort]

        validTasks = {task for task in solution.RoutePlan[day][cohort] if task <= 1000}

        # Randomly select two distinct indices in one step
        task_i, task_j = self.RNG.choice(list(validTasks), size=2, replace=False)

        index_i, index_j = cohort_tasks.index(task_i), cohort_tasks.index(task_j)

        # Create and return the move
        return SwapIntraRouteMove(cohort_tasks, day, cohort, task_i, task_j, index_i, index_j)
       
class SwapInterRouteMove(BaseMove):
    """ Represents the swap of tasks between different routes possibly on the same or different days. """

    def __init__(self, initialRoutePlan, dayA:int, cohortA:int, taskA:int, dayB:int, cohortB:int, taskB:int):
        self.RouteDayCohortA = initialRoutePlan[dayA][cohortA].copy() 
        self.RouteDayCohortB = initialRoutePlan[dayB][cohortB].copy() # create a copy of the route plan
        self.TaskA = taskA
        self.TaskB = taskB
        self.DayA = dayA
        self.CohortA = cohortA
        self.DayB = dayB
        self.CohortB = cohortB

        # Get the indices
        self.indexA = self.RouteDayCohortA.index(self.TaskA)
        self.indexB = self.RouteDayCohortB.index(self.TaskB)

        # Swap the tasks between routes
        self.RouteDayCohortA[self.indexA], self.RouteDayCohortB[self.indexB] = self.TaskB, self.TaskA

class SwapInterRouteNeighborhood(DeltaNeighborhood):
    """ Contains all moves for swapping tasks between different routes possibly on the same or different days. """

    def __init__(self, inputData:InputData, evaluationLogic:EvaluationLogic, solutionPool:SolutionPool, rng):
        super().__init__(inputData, evaluationLogic, solutionPool, rng)
        self.Type = 'SwapInterRoute'

    def DiscoverMoves(self, actual_Solution:Solution):
    #def DiscoverMoves(self, actualSolution:Solution):
        """ Generate all possible swaps between tasks in different routes (days and different cohorts). """

        # Choose 2 random days to include in the neighborhood

        days = self.RNG.choice(range(len(self.RoutePlan)), 2)
        #days = range(len(self.RoutePlan))

        # Choose 5 random cohorts (since they are the same across all days)
        cohorts = self.RNG.choice(range(len(self.RoutePlan[0])), 5)
        #cohorts = range(len(self.RoutePlan[0]))


        # Pre-filter tasks to only include those that meet the condition task <= 1000
        valid_tasks_by_day_and_cohort = {
            (day, cohort): {task for task in self.RoutePlan[day][cohort] if task <= 1000}
            for day in days
            for cohort in cohorts
        }

        # Generate valid task pairs across different routes (days) and ensure different cohorts
        for (dayA, cohortA), (dayB, cohortB) in itertools.combinations(valid_tasks_by_day_and_cohort.keys(), 2):

            # Ensure that day and cohort are nrever the same
            if dayA == dayB and cohortA == cohortB:
                continue  # Skip if cohorts are the same
            
            tasksA = valid_tasks_by_day_and_cohort[(dayA, cohortA)]
            tasksB = valid_tasks_by_day_and_cohort[(dayB, cohortB)]
            waiting_timeA = actual_Solution.WaitingTimes[dayA, cohortA]
            waiting_timeB = actual_Solution.WaitingTimes[dayB, cohortB]

            # Precompute service times for tasks in tasksA and tasksB
            #TODO: Test the speed here! 
            service_times_A = {task: self.InputData.allTasks[task].service_time for task in tasksA}
            service_times_B = {task: self.InputData.allTasks[task].service_time for task in tasksB}


            for taskA in tasksA:
                service_time_A = service_times_A[taskA]  # Precomputed service time for taskA
                for taskB in tasksB:
                    service_time_B = service_times_B[taskB]  # Precomputed service time for taskB
                    if waiting_timeA < service_time_B - service_time_A:
                        continue
                    if waiting_timeB < service_time_A - service_time_B:
                        continue
                    # Create the move object for swapping tasks between dayA and dayB, different cohorts
                    self.Moves.append(SwapInterRouteMove(self.RoutePlan, dayA, cohortA, taskA, dayB, cohortB, taskB))
                   

        # Shuffle the generated moves
        self.RNG.shuffle(self.Moves)

    
    def SingleMove(self, solution: Solution, maxAttempts) -> Solution:
        ''' Overwritten to avoid comparisons of strings'''
        
        MAX_ATTEMPTS = maxAttempts  # Maximum attempts limit
        feasible = False
        attempt = 0
        move = None  # Placeholder for the move


        while not feasible and attempt < MAX_ATTEMPTS:
            move = self.MakeOneMove(solution)
            feasible = self.SingleRouteFeasibilityCheck(move.RouteDayCohortA) and self.SingleRouteFeasibilityCheck(move.RouteDayCohortB)
            attempt += 1

        # If a feasible move is found, evaluate and return it
        if feasible:
            self.EvaluateMove(move)
        else: 
            move = None

        return move
    
    
    def constructCompleteRoute(self, move:SwapInterRouteMove, solution = None) -> dict: 
        ''' Constructs the comlete Route from the Move and the BaseMove'''
        adapted_Route_Plan = solution.RoutePlan if solution else self.RoutePlan

        adapted_Route_Plan[move.DayA][move.CohortA] = move.RouteDayCohortA
        adapted_Route_Plan[move.DayB][move.CohortB] = move.RouteDayCohortB

        return adapted_Route_Plan
    
    def EvaluateMovesFirstImprovement(self) -> None:
        """ Evaluate all moves until the first one is found that improves the best solution found so far. 
            Overwritten to avoid string comparisons
        """

        # Retrieve best solution from Solution Pool
        for move in self.Moves:
            
            self.EvaluateMove(move)

            if move.Delta < 0:
                
                if self.SingleRouteFeasibilityCheck(move.RouteDayCohortA) and self.SingleRouteFeasibilityCheck(move.RouteDayCohortB):
                    
                    self.MoveSolutions.append(move)
                    # abort neighborhood evaluation because an improvement has been found
                    return None
        
        return None
    
    def MakeBestMove(self) -> BaseMove:
        ''' Overwritten to avoid string comparisons'''
        self.MoveSolutions.sort(key=lambda move: move.Delta)

        for move_solution in self.MoveSolutions:

            if self.SingleRouteFeasibilityCheck(move_solution.RouteDayCohortA) and self.SingleRouteFeasibilityCheck(move_solution.RouteDayCohortB): 
                return move_solution
                    
        return None


    def EvaluateMove(self, move:SwapInterRouteMove) -> None:

        #Update the Delta of the Move
        move.setDelta(self.EvaluationLogic.CalculateSwapInterRouteDelta(move))
    
    def MakeOneMove(self, solution:Solution) -> SwapInterRouteMove:

        
        dayA, dayB = self.RNG.choice(len(solution.RoutePlan), size=2, replace=True)
        if dayA == dayB:
            cohortA, cohortB = self.RNG.choice(len(solution.RoutePlan[dayB]), size=2, replace=False)
        else:
            cohortA, cohortB = self.RNG.choice(len(solution.RoutePlan[dayB]), size=2, replace=True)

        validTasksA = {task for task in solution.RoutePlan[dayA][cohortA] if task <= 1000}
        validTasksB = {task for task in solution.RoutePlan[dayB][cohortB] if task <= 1000}

        taskA = self.RNG.choice(list(validTasksA))
        taskB = self.RNG.choice(list(validTasksB))

        return SwapInterRouteMove(solution.RoutePlan, dayA, cohortA, taskA, dayB, cohortB, taskB)
    
    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> Solution:
        ''' Own Definition to avoid string comparisons'''

        hasSolutionImproved = True
        bestNeighborhoodSolution = Solution(solution.RoutePlan, self.InputData)
        self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

        while hasSolutionImproved:
            
            self.Update(bestNeighborhoodSolution.RoutePlan)
            self.DiscoverMoves(bestNeighborhoodSolution)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()

            if bestNeighborhoodMove is not None and bestNeighborhoodMove.Delta < 0:

                completeRoute = self.constructCompleteRoute(bestNeighborhoodMove)
                bestNeighborhoodSolution = Solution(completeRoute, self.InputData)
                self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

                self.SolutionPool.AddSolution(bestNeighborhoodSolution)
            else:

                hasSolutionImproved = False

        return bestNeighborhoodSolution
    
class TwoEdgeExchangeMove(BaseMove):
    """ Represents the swap of the element at IndexA with the element at IndexB for a given permutation (= solution). """

    def __init__(self, initialRoutePlan, waiting_time_old_route:int, day:int, cohort:int, taskA:int, taskB:int):
        self.RouteDayCohort = initialRoutePlan.copy()  # Create a copy for RouteDayCohort
        self.OldWaitingTime = waiting_time_old_route  # Waiting Time of old route
        self.Day = day
        self.Cohort = cohort
        self.TaskA = taskA
        self.TaskB = taskB

        # Get the indices
        self.indexA, self.indexB = self.RouteDayCohort.index(self.TaskA), self.RouteDayCohort.index(self.TaskB)

        # Reverse the necessary portion of the list in place (slice assignment)
        if self.indexA < self.indexB:
            self.RouteDayCohort[self.indexA:self.indexB+1] = reversed(self.RouteDayCohort[self.indexA:self.indexB+1])
        else:
            # If indexA is after indexB, still reverse, but handle the indices correctly
            self.RouteDayCohort[self.indexB:self.indexA+1] = reversed(self.RouteDayCohort[self.indexB:self.indexA+1])

class TwoEdgeExchangeNeighborhood(DeltaNeighborhood):         

    """ Contains all $n choose 2$ swap moves for a given permutation (= solution). """

    def __init__(self, inputData:InputData, evaluationLogic:EvaluationLogic, solutionPool:SolutionPool, rng):
        super().__init__(inputData,  evaluationLogic, solutionPool, rng)

        self.Type = 'TwoEdgeExchange'

    def DiscoverMoves(self, waiting_times):
        """ Generate all $n choose 2$ moves. """


        for day in range(len(self.RoutePlan)):
            for cohort in range(len(self.RoutePlan[day])):
                # Get the cohort once
                cohort_tasks = self.RoutePlan[day][cohort]
                
                # Filter tasks that are <= 1000 to reduce unnecessary checks
                valid_tasks = {task for task in cohort_tasks if task <= 1000}

                waiting_time_old_route = waiting_times[day,cohort]

                # Iterate over combinations of task indices (i, j) such that i < j
                for task_i, task_j in itertools.combinations(valid_tasks, 2):
                        
                    # Create the move
                    self.Moves.append(TwoEdgeExchangeMove(self.RoutePlan[day][cohort], waiting_time_old_route, day, cohort, task_i, task_j))

        
        #Shuffles the Moves
        self.RNG.shuffle(self.Moves)


    def EvaluateMove(self, move) -> None:
        ''' Calculates the MakeSpan of thr certain move - adds to recent Solution'''

        #Update the Delta of the Move
        move.setDelta(self.EvaluationLogic.WaitingTimeDifferenceOneRoute(move))
    
    def MakeOneMove(self, solution:Solution) -> TwoEdgeExchangeMove:

        day = self.RNG.integers(0, len(solution.RoutePlan))
        cohort = self.RNG.integers(0, len(solution.RoutePlan[day]))
        waiting_time_old = solution.WaitingTimes[day,cohort]

        cohort_tasks = solution.RoutePlan[day][cohort]
                    
        # Filter tasks that are <= 1000 to reduce unnecessary checks
        valid_tasks = {task for task in cohort_tasks if task <= 1000}

        # Randomly select two distinct tasks
        task_i, task_j = self.RNG.choice(list(valid_tasks), size=2, replace=False)

        return TwoEdgeExchangeMove(cohort_tasks, waiting_time_old,day, cohort, task_i, task_j)
    
    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> Solution:
        ''' Own Definition to avoid string comparisons'''

        hasSolutionImproved = True
        bestNeighborhoodSolution = Solution(solution.RoutePlan, self.InputData)
        self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

        while hasSolutionImproved:# and iterator < 50:
            
            self.Update(bestNeighborhoodSolution.RoutePlan)
            self.DiscoverMoves(bestNeighborhoodSolution.WaitingTimes)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()

            if bestNeighborhoodMove is not None and bestNeighborhoodMove.Delta < 0:

                completeRoute = self.constructCompleteRoute(bestNeighborhoodMove)
                bestNeighborhoodSolution = Solution(completeRoute, self.InputData)
                self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

                self.SolutionPool.AddSolution(bestNeighborhoodSolution)
            else:
                #print(f"\nReached local optimum of {self.Type} neighborhood in iteration {iterator}. Stop local search.\n")
                hasSolutionImproved = False

        return bestNeighborhoodSolution


class ReplaceMove(BaseMove):
    def __init__(self, initialRoutePlan, day:int, cohort:int, taskInRoute:int, unusedTask:int, deltaProfit:int):
        """
        Initializes the SwapExtMove instance.

        Args:
            initialRoutePlan (list): The initial route plan.
            day (int): The day on which the swap is made.
            cohort (int): The cohort that drives the route.
            taskInRoute (int): The task currently in the route.
            unusedTask (int): The unused task to be swapped in.
        """
        self.RouteDayCohort = initialRoutePlan.copy()  # create a copy of the route plan
        self.TaskInRoute = taskInRoute
        self.UnusedTask = unusedTask
        self.Day = day
        self.Cohort = cohort
        self.ProfitDelta = deltaProfit

        # Get the index of the task in the route
        self.indexInRoute = self.RouteDayCohort.index(self.TaskInRoute)

        # Perform the swap: replace the task in the route with the unused task
        self.RouteDayCohort[self.indexInRoute] = self.UnusedTask

class ReplaceDeltaNeighborhood(DeltaNeighborhood):

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):

        super().__init__(inputData, evaluationLogic, solutionPool, rng)

        self.Type = 'ReplaceDelta'

    def DiscoverMoves(self, actual_Solution: Solution) -> None:

        unusedTasks = actual_Solution.UnusedTasks

        # Only consider a subset of all unused tasks to reduce the number of moves
        max_number_to_consider = 100
        if len(unusedTasks) > max_number_to_consider:
            unusedTasks = self.RNG.choice(unusedTasks, max_number_to_consider, replace = False)
            
         # Precompute profits for unused tasks to avoid repeated lookups
        unused_task_profits = {task: self.InputData.allTasks[task].profit for task in unusedTasks}

        # Iterate through the route plan
        for day in range(len(self.RoutePlan)):
            for cohort in range(len(self.RoutePlan[day])):
                waiting_time = actual_Solution.WaitingTimes[day, cohort]
                for taskInRoute in self.RoutePlan[day][cohort]:
                    if taskInRoute > 1000:
                        continue
                    route_task_service_time = self.InputData.allTasks[taskInRoute].service_time
                    route_task_profit = self.InputData.allTasks[taskInRoute].profit  # Access once
                    # Filter unused tasks based on matching profit
                    for unusedTask, unused_profit in unused_task_profits.items():
                        if route_task_profit > unused_profit: #TODO Addede here smaller elkse
                            continue
                        if waiting_time < self.InputData.allTasks[unusedTask].service_time - route_task_service_time:
                            continue
                        # If profit matches, create a swap move
                        delta_profit = unused_profit-route_task_profit
                        self.Moves.append(ReplaceMove(self.RoutePlan[day][cohort], day, cohort, taskInRoute, unusedTask, delta_profit))
                
        #Shuffles the Moves
        self.RNG.shuffle(self.Moves)


    def LocalSearch(self, neighborhoodEvaluationStrategy: str, solution: Solution) -> Solution:
        ''' Own Definition to avoid string comparisons'''

        hasSolutionImproved = True
        bestNeighborhoodSolution = Solution(solution.RoutePlan, self.InputData)
        self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)

        while hasSolutionImproved:# and iterator < 50:
            
            self.Update(bestNeighborhoodSolution.RoutePlan)
            self.DiscoverMoves(bestNeighborhoodSolution)
            self.EvaluateMoves(neighborhoodEvaluationStrategy)

            bestNeighborhoodMove = self.MakeBestMove()

            if bestNeighborhoodMove is not None and bestNeighborhoodMove.Delta < 0:
                #print(f"\nIteration: {iterator} in neighborhood {self.Type}")
                #print("New best solution has been found!")
                #print("Time Delta:" , bestNeighborhoodMove.Delta)
                completeRoute = self.constructCompleteRoute(bestNeighborhoodMove)
                bestNeighborhoodSolution = Solution(completeRoute, self.InputData)
                self.EvaluationLogic.evaluateSolution(bestNeighborhoodSolution)
                #print("New Waiting Time:" , bestNeighborhoodSolution.WaitingTime)
                self.SolutionPool.AddSolution(bestNeighborhoodSolution)
            else:
                #print(f"\nReached local optimum of {self.Type} neighborhood in iteration {iterator}. Stop local search.\n")
                hasSolutionImproved = False

        return bestNeighborhoodSolution


    def EvaluateMove(self, move) -> None:

        #Update the Delta of the Move! 
        move.setDelta(self.EvaluationLogic.CalculateReplaceDelta(move))


    def MakeOneMove(self, solution:Solution) -> ReplaceMove:

        unusedTasksList = solution.UnusedTasks

         # Pre-filter tasks in RoutePlan that are <= 1000 to avoid looping later
        valid_tasks_by_day_and_cohort = {
            (day, cohort): {task for task in solution.RoutePlan[day][cohort] if task <= 1000}
            for day in range(len(solution.RoutePlan))
            for cohort in range(len(solution.RoutePlan[day]))
        }

        taskInRoute = None

        # If no match was found, try different day/cohort combinations
        while taskInRoute is None:
            day, cohort = self.RNG.choice(list(valid_tasks_by_day_and_cohort.keys()))
            unusedTask = self.RNG.choice(unusedTasksList, replace=False)
            unusedTaskProfit = self.InputData.allTasks[unusedTask].profit
            unusedTaskServiceTime = self.InputData.allTasks[unusedTask].service_time

            for task in valid_tasks_by_day_and_cohort[(day, cohort)]:
                task_profit = self.InputData.allTasks[task].profit
                if task_profit <= unusedTaskProfit:
                    if solution.WaitingTimes[day, cohort] >= unusedTaskServiceTime - self.InputData.allTasks[task].service_time:
                        taskInRoute = task
                        profit_delta = task_profit - unusedTaskProfit
                        break
        
        return ReplaceMove(solution.RoutePlan[day][cohort], day, cohort, taskInRoute, unusedTask, profit_delta)


        '''
        return move
    
    
    #def MakeOneMove(self, solution:Solution) -> ReplaceMove: --> möglicherweise war hier ein fehler

        day = self.RNG.integers(0, len(solution.RoutePlan))
        cohort = self.RNG.integers(0, len(solution.RoutePlan[day]))

        unusedTasks = list(solution.UnusedTasks)
        unusedTask = self.RNG.choice(unusedTasks, replace=False)

        taskInRoute = self.RNG.choice(solution.RoutePlan[day][cohort])
        while taskInRoute > 1000:
            taskInRoute = self.RNG.choice(solution.RoutePlan[day][cohort])


        while True:
            if (solution.WaitingTimes[day, cohort] >=
                (self.InputData.allTasks[unusedTask].service_time - self.InputData.allTasks[taskInRoute].service_time) and
                self.InputData.allTasks[taskInRoute].profit == self.InputData.allTasks[unusedTask].profit):
                break

            day = self.RNG.integers(0, len(solution.RoutePlan))
            cohort = self.RNG.integers(0, len(solution.RoutePlan[day]))

            unusedTask = self.RNG.choice(unusedTasks, replace=False)
            taskInRoute = self.RNG.choice(solution.RoutePlan[day][cohort])
            while taskInRoute > 1000:
                taskInRoute = self.RNG.choice(solution.RoutePlan[day][cohort])

        move = ReplaceMove(solution.RoutePlan, day, cohort, taskInRoute, unusedTask, self.InputData)

        return move
      
        '''

#_______________________________________________________________________________________________________________________

class InsertMove(BaseMove):
    """
    Represents a move that inserts a task into various positions within a route.

    Attributes:
        Route (dict): A deep copy of the initial route plan after attempting to insert the task.
    """

    def __init__(self, initialRoutePlan, task: int, day:int, cohort:int, index: int, profit:int):
        """
        Initializes the InsertMove instance by attempting to insert the given task into the route.

        Args:
            initialRoutePlan (dict): The initial route plan.
            task (int): The task to be inserted.
            inputData: Additional input data required for feasibility checks.
        """
        self.RouteDayCohort = initialRoutePlan.copy()
        self.Task = task
        self.Day = day
        self.Cohort = cohort
        self.Index = index
        self.Profit = profit

        self.RouteDayCohort.insert(index, task)

class InsertNeighborhood(ProfitNeighborhood):
    """
    Represents a neighborhood of insert moves in the context of profit optimization.

    Attributes:
        Type (str): The type of the neighborhood, which is 'Insert'.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        """
        Initializes the InsertNeighborhood instance.

        Args:
            inputData (InputData): The input data required for the neighborhood.
            evaluationLogic (EvaluationLogic): The logic used to evaluate solutions.
            solutionPool (SolutionPool): The pool of solutions.

        Returns:
            None
        """
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

        self.Type = 'Insert'

    def DiscoverMoves(self, actual_Solution:Solution):
        """
        Discovers all possible insert moves for unused tasks in the current solution.

        Args:
            actual_Solution (Solution): The current solution from which unused tasks are identified.

        Returns:
            None
        """
        
        unusedTasks = actual_Solution.UnusedTasks

        #Only consider a subset of all unused tasks to reduce the number of moves
        max_number_to_consider = 250
        if len(unusedTasks) > max_number_to_consider:
           unusedTasks = self.RNG.choice(unusedTasks, max_number_to_consider, replace=False)
        
        
        for task in unusedTasks:
            service_time_unused_task = self.InputData.allTasks[task].service_time
            profit_unused_task = self.InputData.allTasks[task].profit
            for day in range(len(self.RoutePlan)):
                for cohort in range(len(self.RoutePlan[day])):
                    for index in range(len(self.RoutePlan[day][cohort]) + 1):
                        if service_time_unused_task < actual_Solution.WaitingTimes[day, cohort]:
                            self.Moves.append(InsertMove(self.RoutePlan[day][cohort], task, day, cohort, index, profit_unused_task))

        
        #Shuffles the Moves
        self.RNG.shuffle(self.Moves)


    def sort_move_solutions(self):
        # Sort solutions by profit and extra time for 'Insert'
        self.MoveSolutions.sort(key=lambda move: (-move.Profit, move.ExtraTime))


    def EvaluateMove(self, move) -> None:

        #Update the Parameter of the Move
        move.setExtraTime(self.EvaluationLogic.CalculateInsertExtraTime(move))
    

class ReplaceProfitNeighborhood(ProfitNeighborhood):
    """
    Represents a neighborhood of Swap moves in the context of profit optimization.

    Attributes:
        Type (str): The type of the neighborhood, which is 'ReplaceProfit'.
    """

    def __init__(self, inputData: InputData, evaluationLogic: EvaluationLogic, solutionPool: SolutionPool, rng):
        """
        Initializes the ReplaceProfitNeighborhood instance.

        Args:
            inputData (InputData): The input data required for the neighborhood.
            evaluationLogic (EvaluationLogic): The logic used to evaluate solutions.
            solutionPool (SolutionPool): The pool of solutions.

        Returns:
            None
        """
        super().__init__(inputData, evaluationLogic, solutionPool, rng)

        self.Type = 'ReplaceProfit'

    
    def sort_move_solutions(self):
        # Sort solutions by profit delta and delta for 'ReplaceProfit'
        self.MoveSolutions.sort(key=lambda move: (-move.ProfitDelta, move.Delta))

    def DiscoverMoves(self,actual_Solution:Solution):
        """
        Discovers all possible swap moves for unused tasks in the current solution.

        Args:
            actual_Solution (Solution): The current solution from which unused tasks are identified.

        Returns:
            None
        """

        unusedTasks = actual_Solution.UnusedTasks

        # Precompute profits for unused tasks to avoid repeated lookups
        unused_task_profits = {task: self.InputData.allTasks[task].profit for task in unusedTasks}

        for day in range(len(self.RoutePlan)):
            for cohort in range(len(self.RoutePlan[day])):
                waiting_time = actual_Solution.WaitingTimes[day, cohort]
                for taskInRoute in self.RoutePlan[day][cohort]:
                    if taskInRoute > 1000:
                        continue
                    route_task_profit = self.InputData.allTasks[taskInRoute].profit  # Access once
                    route_task_service_time = self.InputData.allTasks[taskInRoute].service_time
                    # Filter unused tasks based on matching profit
                    for unusedTask, unused_profit in unused_task_profits.items():
                        if route_task_profit >= unused_profit: #TODO Addede here smaller elkse
                            continue
                        if waiting_time < self.InputData.allTasks[unusedTask].service_time - route_task_service_time:
                            continue
                        # If profit matches, create a swap move
                        delta_profit = unused_profit-route_task_profit
                        self.Moves.append(ReplaceMove(self.RoutePlan[day][cohort], day, cohort, taskInRoute, unusedTask, delta_profit))
        
        #Shuffles the Moves
        self.RNG.shuffle(self.Moves)

    def EvaluateMove(self, move) -> None:

        #Updates the Parameter
        move.setDelta(self.EvaluationLogic.CalculateReplaceDelta(move))


    def MakeOneMove(self, solution:Solution) -> ReplaceMove:

        unusedTasksList = list(solution.UnusedTasks)

         # Pre-filter tasks in RoutePlan that are <= 1000 to avoid looping later
        valid_tasks_by_day_and_cohort = {
            (day, cohort): {task for task in solution.RoutePlan[day][cohort] if task <= 1000}
            for day in range(len(solution.RoutePlan))
            for cohort in range(len(solution.RoutePlan[day]))
        }

        # Randomly select a day and cohort with valid tasks
        day, cohort = self.RNG.choice(list(valid_tasks_by_day_and_cohort.keys()))

        unusedTask = self.RNG.choice(unusedTasksList, replace = False)

        taskInRoute = self.RNG.choice(valid_tasks_by_day_and_cohort[(day, cohort)],replace = False)

        return ReplaceMove(solution.RoutePlan[day][cohort], day, cohort, taskInRoute, unusedTask, self.InputData)
    

    

#_______________________________________________________________________________________________________________________

