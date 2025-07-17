"""
Main Execution Script for Railroad Construction Optimization

This script orchestrates comprehensive experiments for railroad construction scheduling
using multiple metaheuristic algorithms and problem instances. It provides flexible
execution modes for different analysis phases and comprehensive performance evaluation.

Core Functionality:
- Multi-instance experimental runs across different problem sizes
- Multiple algorithm comparison (PSA, DBSA, TPSA)
- Phase-wise execution support (Bound, Construction, Building, Full)
- Performance profiling and timing analysis
- Automated metrics calculation and CSV export

Execution Modes:
- Full Pipeline: Complete optimization with all phases
- Phase-specific: Individual phase analysis (Bound/Greedy/Building)
- Batch Processing: Multiple instances and algorithms
- Performance Profiling: Detailed execution analysis

Dependencies:
- Core optimization modules (InputData, Solver, algorithms)
- Performance analysis and metrics calculation
- Data export and visualization preparation
"""

from Code.InputData import InputData
from Code.OutputData import *
from Code.ConstructiveHeuristic import *
from Code.EvaluationLogic import *
from Code.ImprovementAlgorithm import *
from Code.Solver import *
from Data.Solutions.front_metrics import Run

import cProfile
import pstats
import json
from time import time
import pandas as pd
from pathlib import Path


# =============================================================================
# PROBLEM INSTANCE CONFIGURATIONS
# =============================================================================

# Test instances with varying complexity levels
# Format: Construction_a{orders}_o{order_items}_m{machines}_an{attachments}_ar{worker}.json
instances = [   "Construction_a3_o80_m10_an10_ar9_reduced.json",      # Small instance
                "Construction_a5_o96_m10_an10_ar10_reduced.json",     # 
                "Construction_a10_o107_m5_an57_ar12.json",            # 
                "Construction_a10_o114_m6_an57_ar11.json",
                "Construction_a10_o128_m6_an51_ar13.json",
                "Construction_a10_o144_m6_an53_ar12.json",
                "Construction_a15_o170_m9_an80_ar18.json",            # Medium instances
                "Construction_a20_o236_m12_an106_ar24.json",
                "Construction_a25_o306_m13_an127_ar31.json",
                "Construction_a30_o355_m18_an148_ar42.json",          # Large instances
                "Construction_a40_o476_m22_an215_ar51.json",          
                "Construction_a50_o578_m28_an276_ar66.json"]


# Real-world instances from actual railroad construction projects
'''
instances = ["Construction_RealLife_2024_3.json",   # Location: 0/0
            "Construction_RealLife_2024_4.json",    # Location: 0/0
            "Construction_RealLife_2024_5.json",    # Location: 0/0
            "Construction_RealLife_2024_6.json",    # Location: 0/0
            "Construction_RealLife_2024_7.json",    # checked
            "Construction_RealLife_2024_8.json",    # checked
            "Construction_RealLife_2024_9.json",    # checked
            "Construction_RealLife_2024_10.json",   # checked
            "Construction_RealLife_2024_11.json",   # empty instance
            "Construction_RealLife_2023_5.json"]    # Older (smaller) instance

# Specific real-world instance variants for detailed analysis
instances = ["Construction_RealLife_2024_7_1_2.json",
            "Construction_RealLife_2024_8_1_2.json",
            "Construction_RealLife_2024_9_1_2.json",
            "Construction_RealLife_2024_10_1_2.json",
            "Construction_RealLife_2024_7_2_2.json",
            "Construction_RealLife_2024_8_2_2.json",
            "Construction_RealLife_2024_9_2_2.json",
            "Construction_RealLife_2024_10_2_2.json"]

# Single instance for focused testing and development --> used in thesis
instances = ["Construction_RealLife_2024_7_1_2.json"]
'''


# =============================================================================
# NEIGHBORHOOD OPERATION CONFIGURATIONS
# =============================================================================

# Complete set of neighborhood operations for comprehensive local search
neighboorhood_types = ['Replace_Shift_Worker',      # Worker assignment modifications
                       'Replace_Shift_Machine',     # Machine allocation changes
                       'Replace_Shift_Attachment',  # Attachment redistribution
                       'Swap_Shift_Worker',         # Worker position exchanges
                       'Swap_Shift_Machine',        # Machine position swaps
                       'Swap_Shift_Attachment',     # Attachment position exchanges
                       'Swap_Shift_External',       # Cross-shift resource swaps
                       'Insert_Shift']              # Schedule insertion operations

# Focused neighborhood types for local search algorithms
neighboorhood_types_local_search = ['Swap_Shift_External']

# =============================================================================
# CONSTRUCTIVE HEURISTIC CONFIGURATIONS
# =============================================================================

# Machine selection strategies for constructive heuristics
machine_attractiveness_techniques = ["balanced_greedy",                    # Equal weighting approach
                                     "machine_planned_importance",         # Ressource efficiency-based
                                     "worker_default_driver_importance"]   # Driver-focused strategy

# Order item prioritization methods
order_item_attractiveness_techniques = ["balanced_greedy",                 # Balanced selection
                                        "dynamic_percentage_importance",   # Order fullfillment-based
                                        "time_difference_importance"]      # time-based priority

# Worker assignment strategies
worker_attractiveness_techniques = ["balanced_greedy",                     # Equal consideration
                                    "worker_planned_importance",           # ressource efficiency-based
                                    "qualifications_importance"]           # Skill-based selection

# Constructive heuristic configuration A: Order-item-driven approach
greedy_technique_a = {'order_item_greedy': {'worker_attractiveness_technique': 'balanced_greedy', 
                                            'machine_attractiveness_technique': 'balanced_greedy'}}

# Constructive heuristic configuration B: Worker-driven approach
greedy_technique_b = {'worker_greedy': {'order_item_attractiveness_technique': 'balanced_greedy',
                                        'machine_attractiveness_technique': 'balanced_greedy'}}

# Collection of all constructive heuristic techniques
greedy_techniques = [greedy_technique_a, greedy_technique_b]

# =============================================================================
# EXECUTION CONTROL PARAMETERS
# =============================================================================

# Execution step control - determines which phase of the algorithm to run
step = None          # Full pipeline execution (all phases)
#step = 'Bound'      # Only upper bound calculation
#step = 'Greedy'     # Only up till and including constructive heuristic phase
#step = 'Building'   # Only up till and including building phase

# Metaheuristic algorithms for comparison
algortihms = ['PSA',     # Pareto Simulated Annealing
              'DBSA',    # Dominance-Based Simulated Annealing  
              'TPSA']    # Two-Phase Simulated Annealing

# Random seeds for reproducible experiments
seeds = [100]  # Single seed for testing
# seeds = [100, 101, 102, 103]  # Multiple seeds for statistical analysis


def main(): 
    """
    Main experimental execution function for railroad construction optimization.
    
    Orchestrates comprehensive experiments across multiple problem instances,
    algorithms, and execution modes. Supports both individual phase analysis
    and complete optimization pipeline execution with automated performance
    tracking and metrics calculation.
    
    Execution Flow:
    1. Iterate through random seeds for statistical analysis
    2. Process each problem instance with all specified algorithms
    3. Initialize solver and algorithm configurations
    4. Execute selected optimization phase(s)
    5. Collect timing and performance metrics
    6. Export results for analysis and visualization
    
    Features:
    - Multi-algorithm comparison (PSA, DBSA, TPSA)
    - Phase-specific execution support
    - Automated metrics calculation and export
    - Performance profiling and timing analysis
    """
    # Execute experiments for each random seed
    for seed in seeds:
        df_testing = pd.DataFrame()  # Initialize results DataFrame for current seed
        
        # Process each problem instance
        for i in instances:
            # Run experiments for each algorithm
            for algortihm in algortihms:
            
                # Initialize input data based on execution mode
                if step == None:
                    data = InputData(i, algortihm)  # Full algorithm execution
                else:
                    data = InputData(i, step)       # Phase-specific execution

                # Initialize solver with problem data and random seed
                solver = Solver(data, seed)
                # =============================================================================
                # ALGORITHM CONFIGURATIONS
                # =============================================================================

                # Local search algorithm for iterative improvement
                local_search = IterativeImprovement(inputData=data,
                                                    neighborhoodTypes=neighboorhood_types_local_search)

                # Building phase simulated annealing for resource optimization
                building_sa = BuildingSimulatedAnnealing(  inputData=data,
                                                            start_temp=20,        # Initial temperature
                                                            min_temp=0.1,         # Final temperature
                                                            cooling_rate=0.95,    # Temperature reduction factor
                                                            max_iterations=3000,  # Maximum iterations
                                                            fallback_threshold=25,# Diversification trigger
                                                            scaling_energy=30)    # Energy scaling factor
                                                        
                # Configure metaheuristic algorithm based on selection
                if algortihm == 'PSA':
                    # Pareto Simulated Annealing configuration
                    algo = ParetoSimulatedAnnealing( inputData=data,
                                                    start_temp=50,              # Initial temperature
                                                    min_temp=0.1,               # Final temperature
                                                    cooling_rate=0.95,          # Cooling schedule
                                                    max_iterations=100,         # Iteration limit
                                                    fallback_threshold=0,       # Currently not used
                                                    scaling_energy=50,          # Energy normalization
                                                    weight_alpha=1.1,           # Pareto weight factor
                                                    max_single_move_tries=30,   # Move attempt limit
                                                    start_size_population=8)    # Initial population size

                elif algortihm == 'DBSA':
                    # Dominance-Based Simulated Annealing configuration
                    algo = DominanceBasedSimulatedAnnealing( inputData=data,
                                                            start_temp=50,              # Initial temperature
                                                            min_temp=0.1,               # Final temperature
                                                            cooling_rate=0.95,          # Cooling schedule
                                                            max_iterations=400,         # Iteration limit
                                                            fallback_threshold=0,       # Currently not used
                                                            scaling_energy=0,           # Currently not used
                                                            max_single_move_tries=30,   # Move attempt limit
                                                            parallel_runs=0)            # Parallel execution count

                elif algortihm == 'TPSA':
                    # Two-Phase Simulated Annealing configuration
                    algo = TwoPhaseSimulatedAnnealing(  inputData=data,
                                                        start_temp=50,              # Initial temperature
                                                        min_temp=0.1,               # Final temperature
                                                        cooling_rate=0.95,          # Cooling schedule
                                                        max_iterations_first=400,   # First phase iterations
                                                        max_iterations_second=400,  # Second phase iterations
                                                        fallback_threshold=0,       # Currently not used
                                                        scaling_energy=50,          # Energy normalization
                                                        max_single_move_tries=30,   # Move attempt limit
                                                        parallel_runs=0)            # Parallel execution count

                # =============================================================================
                # EXECUTION PHASE CONTROL
                # =============================================================================

                # Execute specific optimization phase based on step configuration
                if step == 'Bound':
                    # Upper bound calculation phase only
                    bound_time = solver.RunBound(UB_technique="LP")
                    print("Bound Time:", round(bound_time, 2))
                
                elif step == 'Greedy':
                    # Constructive heuristic phase only
                    solution, time = solver.RunConstructive(UB_technique="LP",
                            greedy_technique=greedy_technique_a)
                    print("\nGreedy Time: ", round(time, 2))

                    # Extract solution attributes for analysis
                    solution_attributes = {
                        "Instance": data.instance,
                        "Greedy_Technique": greedy_technique_a,
                        "Finished_Orders": solution.number_of_finished_orders,
                        "Finished_Order_Items": solution.number_of_finished_order_items,
                        "Total_Time": round(time, 2)
                    }

                    # Append results to DataFrame and export
                    df_testing = pd.concat([df_testing, pd.DataFrame([solution_attributes])], ignore_index=True)
                    df_testing.to_csv("Greedy.csv", index=False)  # Save greedy phase results

                elif step == 'Building':
                    # Resource optimization phase only
                    solution, time = solver.RunBuilding(UB_technique="LP",
                            greedy_technique=greedy_technique_a,
                            building_algorithm=building_sa)
                    print("\nBuilding Time: ", round(time, 2))

                    # Extract solution attributes for analysis
                    solution_attributes = {
                        "Instance": data.instance,
                        "Finished_Orders": solution.number_of_finished_orders,
                        "Finished_Order_Items": solution.number_of_finished_order_items,
                        "Total_Time": round(time, 2)
                    }
                    
                    # Append results to DataFrame and export
                    df_testing = pd.concat([df_testing, pd.DataFrame([solution_attributes])], ignore_index=True)
                    df_testing.to_csv("Building.csv", index=False)  # Save building phase results

                else:
                    # Complete optimization pipeline execution
                    times = solver.Run( UB_technique="LP",
                        greedy_technique=greedy_technique_a,
                        building_algorithm=building_sa,
                        improvement_algorithm=algo)

                    # Display comprehensive timing breakdown
                    print("\nBound Time: ", round(times["Bound Time"], 2))
                    print("Greedy Time: ", round(times["Greedy Time"], 2))
                    print("Building Time: ", round(times["Building Time"], 2))
                    print("Improvement Time: ", round(times["Improvement Time"], 2))
                    print("Total Time: ", round(times["Total Time"], 2))

                    # Extract run attributes for comparative analysis
                    run_attributes = {
                        "Instance": data.instance,
                        "Algorithm": algortihm,
                        "Improvement_Time": round(times["Improvement Time"], 2)
                    }

                    # Append timing data to results DataFrame
                    df_testing = pd.concat([df_testing, pd.DataFrame([run_attributes])], ignore_index=True)

                    # Export detailed timing information
                    output_file = data.solutions_path/"run_times.json"
                    with open(output_file, "w") as f:
                        json.dump(times, f, indent=4)


            # =============================================================================
            # METRICS CALCULATION AND EXPORT
            # =============================================================================
            
            # Calculate comprehensive metrics only for complete pipeline runs
            if step is None:                             
                # Calculate Pareto front quality metrics for all algorithms
                metrics_df = Run(data.instance, algortihms)
                metrics_df["Instance"] = data.instance  # Add instance identifier

                # Transform metrics to wide format for analysis
                metric_data_pivot = metrics_df.pivot(index=["Instance", "Algorithm"],
                                                    columns="Metric", values="Value").reset_index()

                # Normalize key columns for proper merging
                df_testing["Instance"] = df_testing["Instance"].astype(str).str.strip()
                df_testing["Algorithm"] = df_testing["Algorithm"].astype(str).str.strip()
                metric_data_pivot["Instance"] = metric_data_pivot["Instance"].astype(str).str.strip()
                metric_data_pivot["Algorithm"] = metric_data_pivot["Algorithm"].astype(str).str.strip()

                # Merge timing data with quality metrics
                df_testing = df_testing.set_index(["Instance", "Algorithm"])
                metric_data_pivot = metric_data_pivot.set_index(["Instance", "Algorithm"])

                # Add comprehensive metrics to results DataFrame
                df_testing.loc[metric_data_pivot.index, metric_data_pivot.columns] = metric_data_pivot

                # Reset indices for final export
                df_testing = df_testing.reset_index()
                metric_data_pivot = metric_data_pivot.reset_index()

                # Export comprehensive results with timing and quality metrics
                df_testing.to_csv(f"Metrics_{seed}.csv", index=False)
                print("\nMetrics:\n", df_testing)


def profile_main():
    """
    Execute main function with comprehensive performance profiling.
    
    Provides detailed execution analysis including function call statistics,
    cumulative time measurements, and performance bottleneck identification.
    Results are saved to a structured profiling report for optimization analysis.
    
    Profiling Features:
    - Function-level timing analysis
    - Call frequency statistics
    - Cumulative time measurements
    - Performance bottleneck identification
    - Structured report generation
    
    Output:
    - Profiler/main_profile.txt: Detailed performance analysis report
    """
    # Initialize performance profiler
    pr = cProfile.Profile()
    pr.enable()

    # Execute main experimental function
    main()

    # Stop profiling and generate analysis
    pr.disable()
    
    # Ensure profiler directory exists
    Path("Profiler").mkdir(parents=True, exist_ok=True)
    
    # Generate comprehensive profiling report
    with open(Path("Profiler") / "main_profile.txt", "w") as f:
        ps = pstats.Stats(pr, stream=f).sort_stats("cumtime")  # Sort by cumulative time
        ps.print_stats(300)  # Print top 300 functions by execution time


if __name__ == "__main__":
    # Execute main experimental pipeline with performance profiling
    main()

# =============================================================================
# ALTERNATIVE ALGORITHM CONFIGURATIONS (ARCHIVED)
# =============================================================================
# Historical algorithm variants for reference and potential future use

'''
# Pareto Simulated Annealing with archive-based selection strategy
elif algortihm == 'PSA_archive_setter':
    algo = ParetoSimulatedAnnealing_archive_setter( inputData=data,
                                            start_temp=20,           # Initial temperature
                                            min_temp=0.1,            # Final temperature
                                            cooling_rate=0.95,       # Cooling schedule
                                            max_iterations=50,       # Iteration limit
                                            fallback_threshold=25,   # Diversification trigger
                                            scaling_energy=30,       # Energy scaling
                                            weight_alpha=1.1,        # Pareto weight factor
                                            max_single_move_tries=30,# Move attempt limit
                                            start_size_population=4) # Initial population size

# Pareto Simulated Annealing with global archive management
elif algortihm == 'PSA_global_archive_setter':
    algo = ParetoSimulatedAnnealing_global_archive_setter( inputData=data,
                                            start_temp=20,           # Initial temperature
                                            min_temp=0.1,            # Final temperature
                                            cooling_rate=0.95,       # Cooling schedule
                                            max_iterations=500,      # Extended iteration limit
                                            fallback_threshold=25,   # Diversification trigger
                                            scaling_energy=30,       # Energy scaling
                                            weight_alpha=1.1,        # Pareto weight factor
                                            max_single_move_tries=30,# Move attempt limit
                                            start_size_population=4) # Initial population size
'''