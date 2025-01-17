import numpy 
from copy import deepcopy
from InputData import InputData
from OutputData import Solution

class EvaluationLogic:
    ''' Evalution Objects to calculate objectives of the given solutions'''

    def __init__(self, inputData:InputData):
        ''' Initialize by addinbg data'''
        self._data = inputData      


    def evaluateSolution(self, currentSolution:Solution) -> None:
        ''' Calculates the profit of the given solution'''
        
        sum_profit = 0
        sum_tasks = 0

        all_Tasks = self._data.allTasks

        for day in range(self._data.days):
            for cohort in range(self._data.cohort_no):
                sum_tasks += len(currentSolution.RoutePlan[day][cohort])
                for task_no in currentSolution.RoutePlan[day][cohort]:
                    sum_profit += all_Tasks[task_no].profit

        currentSolution.setTotalProfit(sum_profit) 
        currentSolution.setTotalTasks(sum_tasks)

        self.calculateWaitingTime(currentSolution)

    def calculateWaitingTime(self, currentSolution: Solution) -> None:
        """Calculates the waiting time of the given solution"""
        
        # Cache commonly accessed attributes
        max_route_duration = self._data.maxRouteDuration
        distances = self._data.distances
        all_tasks = self._data.allTasks
        route_plan = currentSolution.RoutePlan
        waiting_times = currentSolution.WaitingTimes

        # Loop through days and cohorts
        for day in range(self._data.days):
            for cohort in range(self._data.cohort_no):
                route_time = max_route_duration
                previous_task = 0
                current_route = route_plan[day][cohort]  # Cache the route for the cohort

                # Loop through tasks in the current route
                for task_i in current_route:
                    route_time -= distances[previous_task][task_i]  # Subtract travel time
                    route_time -= all_tasks[task_i].service_time  # Subtract service time
                    previous_task = task_i

                # Subtract return distance to the start point
                route_time -= distances[previous_task][0]
                
                # Store the result in the waiting times matrix
                waiting_times[day, cohort] = route_time

        # Sum all waiting times using NumPy for efficiency
        total_waiting_time = numpy.sum(waiting_times)
        
        # Set the waiting time in the solution
        currentSolution.setWaitingTime(total_waiting_time)

    def WaitingTimeOneRoute(self, RouteDayCohort: list[int]) -> int:
        """Calculates the Waiting Time for one route."""

        # Cache commonly used attributes
        max_route_duration = self._data.maxRouteDuration
        distances = self._data.distances
        all_tasks = self._data.allTasks

        # Initialize route time and previous task
        route_time = max_route_duration
        previous_task = 0

        # Loop through each task in the route
        for task_i in RouteDayCohort:
            # Subtract travel time and service time in one step
            route_time -= distances[previous_task][task_i] + all_tasks[task_i].service_time
            previous_task = task_i

        # Subtract return distance to the start (task 0)
        route_time -= distances[previous_task][0]

        return route_time

    def WaitingTimeDifferenceOneRoute(self, move) -> int:
        ''' Calculates the Difference of the Waiting Time for old and new Two Edge Exchange Route'''

        difference = move.OldWaitingTime - self.WaitingTimeOneRoute(move.RouteDayCohort)

        return difference

    def CalculateDistanceSubtractionTwoEdge(self, move, successor_list, precessor_list):
        """Calculates the distance subtraction for two edges"""

        # Cache distances and tasks for efficiency
        distances = self._data.distances
        taskA = move.TaskA
        taskB = move.TaskB

        # Precompute the old distances
        distance_old = distances[precessor_list[0]][taskA] + distances[taskB][successor_list[1]]

        # Precompute the new distances after the swap
        distance_new = distances[taskA][successor_list[1]] + distances[precessor_list[0]][taskB]

        # Calculate the total distance difference
        difference = distance_new - distance_old

        return difference

    
    def CalculateDistanceSubtraction(self, move, successor_list, precessor_list):
        """Calculates the distance subtraction of the given lists"""

        # Cache distances for efficiency
        distances = self._data.distances
        taskA = move.TaskA
        taskB = move.TaskB

        # Precompute the old distances
        distance_old_a = distances[precessor_list[0]][taskA] + distances[taskA][successor_list[0]]
        distance_old_b = distances[precessor_list[1]][taskB] + distances[taskB][successor_list[1]]

        # Precompute the new distances after the swap
        distance_new_a = distances[precessor_list[1]][taskA] + distances[taskA][successor_list[1]]
        distance_new_b = distances[precessor_list[0]][taskB] + distances[taskB][successor_list[0]]

        # Calculate the total distance difference
        difference = (distance_new_a + distance_new_b) - (distance_old_a + distance_old_b)

        return difference

  
    def get_predecessors_and_successors(self, route: list[int], indexes: list[int]):
        """Helper function to get predecessors and successors for swap moves."""
        
        n = len(route)
        
        # Preallocate lists to avoid repeated appends
        precessors = [0] * len(indexes)
        successors = [0] * len(indexes)

        for i, index in enumerate(indexes):
            if index == 0:
                precessors[i] = 0
                successors[i] = route[index + 1] # Ensure the route has more than 1 task
            elif index == n - 1:
                precessors[i] = route[index - 1]
                successors[i] = 0
            else:
                precessors[i] = route[index - 1]
                successors[i] = route[index + 1]

        return precessors, successors

    
        
    def get_predecessor_and_succesor(self, route:list[int], index:int):
        ''' Calculates the precessor and successor for one Index'''

        # Determine predecessor and successor
        if len(route) > 1:
            if index == 0:
                return 0, route[1]
            elif index == len(route) - 1:
                return route[index - 1], 0
            else:
                return route[index - 1], route[index + 1]
        else: 
            return 0,0

    

    def CalculateSwapIntraRouteDelta(self, move): 
        '''Calculates the delta of the given swap move'''

        # Retrieve the route for the given day and cohort
        precessors, successors = self.get_predecessors_and_successors(route=move.RouteDayCohort, indexes=[move.indexA, move.indexB])

        # Calculate the delta using the distance subtraction method
        delta = self.CalculateDistanceSubtraction(move, successors, precessors)

        return delta
    
    def CalculateSwapInterRouteDelta(self, move): 
        '''Calculates the delta of the given swap move'''

        predA, succA = self.get_predecessor_and_succesor(move.RouteDayCohortA, move.indexA)
        predB, succB = self.get_predecessor_and_succesor(move.RouteDayCohortB, move.indexB)


        # Calculate the delta using the distance subtraction method
        delta = self.CalculateDistanceSubtraction(move, [succA, succB], [predA, predB])
        #print("Delta: ",delta)

        return delta


    def CalculateTwoEdgeExchangeDelta(self, move):
        '''Calculates the delta of the given two edge exchange move'''

        # Retrieve the route for the given day and cohort
        precessors, successors = self.get_predecessors_and_successors(route=move.RouteDayCohort, indexes=[move.indexA, move.indexB])

        # Calculate the delta using the distance subtraction method
        delta = self.CalculateDistanceSubtractionTwoEdge(move, successors, precessors)

        return delta
    
    def CalculateReplaceDelta(self, move):
        """Calculates the delta of the Replace Delta action"""

        # Cache commonly used data
        distances = self._data.distances
        all_tasks = self._data.allTasks
        task_in_route = move.TaskInRoute
        unused_task = move.UnusedTask

        # Get predecessor and successor for the current task in the route
        precessor, successor = self.get_predecessor_and_succesor(move.RouteDayCohort, move.indexInRoute)

        # Calculate the old distances for the task being replaced
        distance_old = distances[precessor][task_in_route] + distances[task_in_route][successor]

        # Calculate the new distances for the task being inserted (unused task)
        distance_new = distances[precessor][unused_task] + distances[unused_task][successor]

        # Get service times for the old and new tasks
        service_time_old = all_tasks[task_in_route].service_time
        service_time_new = all_tasks[unused_task].service_time

        # Calculate the delta
        delta = (distance_new + service_time_new) - (distance_old + service_time_old)

        return delta


    def CalculateInsertExtraTime(self, move):
        """Calculates the delta of the given insert move"""

        # Cache data access to minimize repeated lookups
        distances = self._data.distances
        all_tasks = self._data.allTasks
        task = move.Task

        # Retrieve predecessor and successor once
        precessor, successor = self.get_predecessor_and_succesor(move.RouteDayCohort, move.Index)

        # Calculate old distance
        distance_old = distances[precessor][successor]

        # Calculate new distance after insertion of 'task'
        distance_new = distances[precessor][task] + distances[task][successor]

        # Fetch the service time for the task being inserted
        service_time = all_tasks[task].service_time

        # Calculate the extra time
        extra_time = distance_new + service_time - distance_old

        return extra_time
