"""
Solver Module for Railroad Construction Optimization

This module provides the main orchestration framework for solving complex railroad
construction scheduling problems using multi-phase optimization approaches.

Core Components:
- Solver: Main orchestration class coordinating all optimization phases
- Multi-phase algorithm execution: Bound → Construction → Building → Improvement
- Pareto front management for multi-objective optimization
- Solution export and timing analysis capabilities

Algorithm Phases:
1. Bound Phase: Calculate upper bounds using mathematical programming techniques
2. Construction Phase: Generate initial solutions using constructive heuristics
3. Building Phase: Staff and resource allocation optimization
4. Improvement Phase: Local search and metaheuristic optimization

Dependencies:
- InputData: Problem instance data management
- ConstructiveHeuristic: Initial solution generation algorithms
- ImprovementAlgorithm: Metaheuristic optimization methods
- EvaluationLogic: Solution quality assessment and constraint validation
- MIP_UB: Mathematical programming upper bound calculations
- OutputData: Solution representation and Pareto front management
"""

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
    """
    Main orchestration class for railroad construction optimization algorithms.
    
    The Solver coordinates all phases of the optimization process, from initial
    bound calculation through constructive heuristics, resource allocation,
    and iterative improvement. It manages the complete workflow for solving
    complex scheduling problems with multiple objectives and constraints.
    
    Architecture:
    - Phase-based optimization pipeline
    - Integrated Pareto front management
    - Configurable algorithm selection for each phase
    - Comprehensive timing and performance tracking
    - Solution export and persistence capabilities
    
    Key Features:
    - Multi-objective optimization support
    - Flexible algorithm composition
    - Reproducible results via seeded random number generation
    - Detailed performance profiling and timing analysis
    """
    
    def __init__(self, inputData: InputData, seed: int):
        """
        Initialize the Solver with problem data and random seed.
        
        Sets up all necessary components for the optimization pipeline including
        evaluation logic, Pareto front management, and constructive heuristics.
        The seed ensures reproducible results across multiple runs.
        
        Args:
            inputData (InputData): Complete problem instance with orders, resources, constraints
            seed (int): Random seed for reproducible algorithm behavior
        """
        self.InputData = inputData                                          # Problem instance data
        self.Seed = seed                                                   # Random seed for reproducibility
        self.RNG = numpy.random.default_rng(self.Seed)                    # Seeded random number generator
        self.EvaluationLogic = EvaluationLogic(inputData)                 # Solution quality assessment
        self.ParetoSolutions = ParetoSolutions(inputData, self.RNG)       # Multi-objective front management
        
        # Initialize constructive heuristics with evaluation and randomization
        self.ConstructiveHeuristic = ConstructiveHeuristics(evaluationLogic=self.EvaluationLogic, rng=self.RNG)


    def BoundPhase(self, UB_technique):
        """
        Execute upper bound calculation phase to reduce problem complexity.
        
        This phase uses mathematical programming techniques to calculate tight
        upper bounds and identify the most promising orders for execution.
        Only orders that contribute to optimal solutions are activated for
        subsequent phases, significantly reducing the search space.
        
        Algorithm Process:
        1. Initialize upper bound optimizer with specified technique
        2. Solve mathematical programming model to identify best orders
        3. Activate selected orders in the input data
        4. Deactivate non-promising orders to reduce complexity
        
        Args:
            UB_technique (str): Upper bound calculation method
                - Options: "LP", "MIP", "Heuristic"
                
        Effects:
            - Modifies InputData.active_orders based on optimization results
            - Reduces problem size for subsequent phases
        """
        print("\nCalculating Upper Bound...")

        # Initialize optimizer with specified bounding technique
        optimizer = UpperBound(self.InputData, bound_technique=UB_technique)
        
        # Execute mathematical programming model to identify promising orders
        best_orders = optimizer.execute()

        # Activate only the most promising orders for subsequent optimization
        for order_number in best_orders:
            self.InputData.activate_order(order_number)

    

    def ConstructionPhase(self, greedy_technique) -> Solution:
        """
        Generate initial feasible solution using constructive heuristics.
        
        This phase creates the foundation solution by systematically building
        a complete schedule that satisfies all hard constraints. The constructive
        heuristic uses greedy strategies to make locally optimal decisions while
        maintaining global feasibility.
        
        Constructive Process:
        1. Select orders based on greedy criteria
        2. Assign resources (workers, machines, attachments) to tasks
        3. Schedule activities while respecting temporal constraints
        4. Ensure all precedence and resource availability constraints
        
        Args:
            greedy_technique (str): Constructive heuristic method
                - Options: "EDD", "SPT", "LPT", "Random", "Weighted"
                
        Returns:
            Solution: Initial feasible solution with complete resource assignments
                     and activity schedules
        """
        # Execute selected constructive heuristic to build initial solution
        start_solution = self.ConstructiveHeuristic.Run(self.InputData, greedy_technique)

        return start_solution
    

    def BuildingPhase(self, startSolution: Solution, algorithm: ImprovementAlgorithm) -> Solution:
        """
        Enhance initial solution through resource optimization and staffing.
        
        This phase takes the basic feasible solution from the construction phase
        and optimizes resource allocation, staffing levels, and activity scheduling
        to improve solution quality across multiple objectives.
        
        Building Process:
        1. Initialize improvement algorithm with evaluation components
        2. Optimize worker assignments and skill matching
        3. Refine machine and attachment allocations
        4. Balance workload distribution across resources
        5. Minimize transportation and setup costs
        
        Args:
            startSolution (Solution): Initial feasible solution from construction phase
            algorithm (ImprovementAlgorithm): Building algorithm instance
                - Examples: LocalSearch, TabuSearch, GeneticAlgorithm
                
        Returns:
            Solution: Enhanced solution with optimized resource allocation
                     and improved objective values
        """
        print("\nBuilding Phase started...")

        # Initialize algorithm with evaluation logic and Pareto front management
        algorithm.Initialize(self.EvaluationLogic, self.ParetoSolutions, self.RNG)
        
        # Execute building optimization to enhance solution quality
        staffed_solution = algorithm.Run(startSolution)

        return staffed_solution


    def ImprovementPhase(self, startSolution: Solution, algorithm: ImprovementAlgorithm) -> Solution:
        """
        Execute final optimization phase using advanced metaheuristics.
        
        This phase performs intensive local search and metaheuristic optimization
        to discover high-quality solutions and build a comprehensive Pareto front
        for multi-objective decision making. The algorithm explores the solution
        space systematically to find optimal trade-offs between objectives.
        
        Improvement Process:
        1. Initialize metaheuristic with solution and parameters
        2. Perform iterative improvement through neighborhood exploration
        3. Apply diversification and intensification strategies
        4. Maintain and update Pareto front with non-dominated solutions
        5. Track convergence and termination criteria
        
        Args:
            startSolution (Solution): Enhanced solution from building phase
            algorithm (ImprovementAlgorithm): Metaheuristic algorithm instance
                - Examples: SimulatedAnnealing, TabuSearch, GRASP, VNS
                
        Effects:
            - Updates ParetoSolutions.ParetoFront with discovered solutions
            - Modifies algorithm internal state through iterative improvement
            
        Note: This method does not return a solution as it focuses on
              Pareto front construction rather than single solution optimization
        """
        print("\nImprovement Phase with", self.InputData.algo, "started...")

        # Initialize algorithm with evaluation components and random number generator
        algorithm.Initialize(self.EvaluationLogic, self.ParetoSolutions, self.RNG)
        
        # Execute metaheuristic optimization to build Pareto front
        algorithm.Run(startSolution)



    
# =============================================================================
# ALGORITHM EXECUTION METHODS
# =============================================================================
# The following methods provide different execution modes for the optimization
# algorithm, allowing users to run individual phases or complete pipelines
# depending on their analysis requirements and computational constraints.
# =============================================================================
   
    
    def RunBound(self, UB_technique):
        """
        Execute only the bounding phase for preprocessing analysis.
        
        This method is useful for analyzing the effectiveness of different
        upper bound techniques and understanding their computational impact
        on problem complexity reduction.
        
        Performance Metrics:
        - Measures pure bounding computation time
        - Evaluates order selection quality
        - Analyzes problem size reduction effectiveness
        
        Args:
            UB_technique (str): Upper bound calculation method to evaluate
            
        Returns:
            float: Execution time for bound calculation in seconds
        """
        # Record start time for performance measurement
        start_time = time.time()

        # Execute bounding phase with specified technique
        self.BoundPhase(UB_technique)

        # Calculate and return elapsed time
        bound_time = time.time() - start_time

        return bound_time


    
    def RunConstructive(self, UB_technique, greedy_technique):
        """
        Execute bound and construction phases for initial solution analysis.
        
        This method is particularly useful for evaluating different constructive
        heuristics and their interaction with bounding techniques. It provides
        the foundation for solution quality assessment before resource optimization.
        
        Analysis Capabilities:
        - Compare constructive heuristic effectiveness
        - Evaluate impact of bound quality on construction
        - Measure initial solution generation performance
        
        Args:
            UB_technique (str): Upper bound calculation method
            greedy_technique (str): Constructive heuristic approach
            
        Returns:
            tuple: (startSolution, greedy_time)
                - startSolution (Solution): Initial feasible solution
                - greedy_time (float): Construction phase execution time in seconds
        """
        # Execute bounding phase to reduce problem complexity
        self.BoundPhase(UB_technique)

        # Record start time for construction phase timing
        start_time = time.time()

        # Generate initial solution using specified constructive heuristic
        startSolution = self.ConstructionPhase(greedy_technique)

        # Calculate construction phase execution time
        greedy_time = time.time() - start_time

        return startSolution, greedy_time



    def RunBuilding(self, UB_technique, greedy_technique, building_algorithm):
        """
        Execute bound, construction, and building phases for resource optimization analysis.
        
        This method provides comprehensive evaluation of the first three optimization
        phases, allowing detailed analysis of how different techniques interact and
        contribute to overall solution quality before final improvement.
        
        Performance Analysis:
        - Individual phase timing breakdown
        - Algorithm combination effectiveness
        - Resource optimization quality assessment
        - Intermediate solution quality evaluation
        
        Args:
            UB_technique (str): Upper bound calculation method
            greedy_technique (str): Constructive heuristic approach  
            building_algorithm (ImprovementAlgorithm): Resource optimization algorithm
            
        Returns:
            tuple: (staffed_solution, building_time)
                - staffed_solution (Solution): Resource-optimized solution
                - building_time (float): Building phase execution time in seconds
        """
        # Execute and time bounding phase
        start_time = time.time()
        self.BoundPhase(UB_technique)
        bound_time = time.time() - start_time
        print("Bound Time:", bound_time)

        # Execute and time construction phase
        start_time = time.time()
        startSolution = self.ConstructionPhase(greedy_technique)
        greedy_time = time.time() - start_time
        print("Greedy Time:", greedy_time)

        # Execute and time building phase
        start_time = time.time()
        staffed_solution = self.BuildingPhase(startSolution, building_algorithm)
        building_time = time.time() - start_time
        print("Building Time:", building_time)

        return staffed_solution, building_time




    def Run(self, UB_technique, greedy_technique, building_algorithm, improvement_algorithm):
        """
        Execute complete optimization pipeline with all four phases.
        
        This is the main method for full optimization runs, executing the complete
        algorithm pipeline from bounding through final improvement. It provides
        comprehensive timing analysis and exports the resulting Pareto front for
        multi-objective decision making.
        
        Complete Pipeline:
        1. Bound Phase: Mathematical programming upper bounds
        2. Construction Phase: Initial feasible solution generation  
        3. Building Phase: Resource allocation optimization
        4. Improvement Phase: Metaheuristic Pareto front construction
        5. Export Phase: Solution persistence and timing analysis
        
        Args:
            UB_technique (str): Upper bound calculation method
            greedy_technique (str): Constructive heuristic approach
            building_algorithm (ImprovementAlgorithm): Resource optimization algorithm
            improvement_algorithm (ImprovementAlgorithm): Final metaheuristic optimizer
            
        Returns:
            dict: Comprehensive timing breakdown with keys:
                - "Bound Time": Upper bound calculation time
                - "Greedy Time": Construction phase time  
                - "Building Time": Resource optimization time
                - "Improvement Time": Metaheuristic optimization time
                - "Total Time": Complete pipeline execution time
        """
        # Initialize total timing measurement
        start_time = time.time()

        # Phase 1: Execute bounding for problem reduction
        self.BoundPhase(UB_technique)
        bound_time = time.time() - start_time

        # Phase 2: Generate initial feasible solution
        startSolution = self.ConstructionPhase(greedy_technique)
        greedy_time = time.time() - start_time - bound_time

        # Phase 3: Optimize resource allocation and staffing
        staffed_solution = self.BuildingPhase(startSolution, building_algorithm)
        building_time = time.time() - start_time - bound_time - greedy_time

        # Phase 4: Execute metaheuristic improvement for Pareto front construction
        self.ImprovementPhase(staffed_solution, improvement_algorithm)

        # Prepare output file path for Pareto front export
        output_file = os.path.join(self.InputData.solutions_path, "pareto_solutions.json")

        # Recursive function to convert all NumPy types to JSON-serializable Python types
        def convert_numpy(val):
            """Convert nested NumPy types to native Python types for JSON serialization."""
            if isinstance(val, dict):
                return {k: convert_numpy(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [convert_numpy(v) for v in val]
            elif isinstance(val, tuple):
                return tuple(convert_numpy(v) for v in val)
            elif isinstance(val, numpy.ndarray):
                return convert_numpy(val.tolist())
            elif isinstance(val, (numpy.integer,)):
                return int(val)
            elif isinstance(val, (numpy.floating,)):
                return float(val)
            else:
                return val

        # Extract and structure solution data from Pareto front
        solutions_data = {}
        for idx, solution in enumerate(self.ParetoSolutions.ParetoFront):
            raw_entry = {
                # Route plans for all resource types
                "worker_route_plan": getattr(solution, "route_plan_worker", None),
                "attachment_route_plan": getattr(solution, "route_plan_attachment", None),
                "machine_route_plan": getattr(solution, "route_plan_machine", None),
                
                # Completion metrics
                "Orders": getattr(solution, "number_of_finished_orders", None),
                "Order Items": getattr(solution, "number_of_finished_order_items", None),
                
                # Constraint violation metrics
                "Driver Violation": getattr(solution, "driver_violation", None),
                
                # Transportation cost objectives
                "Commute Distance": round(getattr(solution, "total_commute_distance", 0), 2),
                "Transport Machines": round(getattr(solution, "total_transport_distance", 0), 2),
                "Transport Attachments": round(getattr(solution, "total_transport_distance_attachments", 0), 2),
                
                # Resource utilization objectives
                "Machines": getattr(solution, "number_of_machines", None),
                "Workers": getattr(solution, "number_of_workers", None),
                "Attachments": getattr(solution, "number_of_attachments", None)
            }

            # Convert NumPy types and store solution data
            solutions_data[idx + 1] = convert_numpy(raw_entry)
        
        # Export Pareto front solutions to JSON file
        with open(output_file, "w") as f:
            json.dump(solutions_data, f, indent=2)

        # Calculate final phase timing and total execution time
        improvement_time = time.time() - start_time - bound_time - greedy_time - building_time
        total_time = time.time() - start_time

        # Compile comprehensive timing breakdown
        times = {
            "Bound Time": bound_time,
            "Greedy Time": greedy_time,
            "Building Time": building_time,
            "Improvement Time": improvement_time,
            "Total Time": total_time
        }

        return times



