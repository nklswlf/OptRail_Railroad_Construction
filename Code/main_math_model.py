"""
Mathematical optimization model execution and experimentation script.

This module provides functionality to run mathematical optimization experiments
using Mixed Integer Programming (MIP) models for railroad construction scheduling.
Supports both Binary Integer Programming (BIP) and Linear Programming (LP) relaxations
with comprehensive result analysis and CSV export capabilities.
"""

import InputData
import OutputData
import pandas as pd
from pathlib import Path
import MIP_UB as MIP_UB
import OutputData
import EvaluationLogic

# Instance file collections organized by problem size and complexity

# Reduced complexity test instances for initial validation
"""
Construction_a3_o80_m10_an10_ar9_reduced.json
Construction_a5_o96_m10_an10_ar10_reduced.json
"""

# 10 construction sites instances
# Note: "Construction_a10_o118_m6_an53_ar13.json" excluded - contains order without order items
"""
Construction_a10_o107_m5_an57_ar12.json
Construction_a10_o114_m6_an57_ar11.json
Construction_a10_o128_m6_an51_ar13.json
Construction_a10_o144_m6_an53_ar12.json
"""

# 15 construction sites instances
"""
Construction_a15_o170_m9_an80_ar18.json
"""

# 20 construction sites instances
"""
Construction_a20_o236_m12_an106_ar24.json
"""

# 25 construction sites instances
"""
Construction_a25_o306_m13_an127_ar31.json
"""

# 30 construction sites instances
"""
Construction_a30_o355_m18_an148_ar42.json
"""

# 40 construction sites instances
"""
Construction_a40_o476_m22_an215_ar51.json
"""

# 50 construction sites instances
"""
Construction_a50_o578_m28_an276_ar66.json
"""





def experiments():
    """
    Executes comprehensive optimization experiments across multiple instances.
    
    Runs mathematical optimization experiments using different techniques (BIP/LP)
    on various problem instances ranging from small to large scale. Collects
    performance metrics, solution quality data, and exports results to CSV files.
    """
    bound_technique = "BIP"  # Optimization technique: Binary Integer Programming

    # Curated list of test instances with increasing complexity
    instances = ["Construction_a3_o80_m10_an10_ar9_reduced.json",
                "Construction_a5_o96_m10_an10_ar10_reduced.json",
                "Construction_a10_o107_m5_an57_ar12.json",
                "Construction_a10_o114_m6_an57_ar11.json",
                "Construction_a10_o128_m6_an51_ar13.json", # Known issue: UB not reached due to insufficient qualified workers (q=9,4)
                                                            # Resolved after site editing
                "Construction_a10_o144_m6_an53_ar12.json",
                "Construction_a15_o170_m9_an80_ar18.json",
                "Construction_a20_o236_m12_an106_ar24.json", # Known issue: UB not reached due to insufficient attachment types (type=8)
                                                            # Requires LP relaxation analysis including attachments
                "Construction_a25_o306_m13_an127_ar31.json",
                "Construction_a30_o355_m18_an148_ar42.json"]
                # Commented out large instances due to known issues:
                #"Construction_a40_o476_m22_an215_ar51.json", # UB not reached: missing machine type 2
                                                            # Resolved after InputData preprocessing
                #"Construction_a50_o578_m28_an276_ar66.json"]
        
    # Dictionary to store experimental results for all instances
    dict_solution = dict()

    # Experiment numbers to execute (allows selective testing)
    experimentos = [2, 3]

    # Main experimental loop: iterate through experiments and instances
    for exp in experimentos:
        for i in instances:
            
            # Initialize data structures for current instance
            data = InputData.InputData(i, 'UB')  # Load instance data with upper bound configuration
            instance = data.instance
            evaluation = EvaluationLogic.EvaluationLogic(data)  # Create evaluation logic

            # Initialize mathematical optimizer with specified technique
            optimizer = MIP_UB.UpperBound(data, bound_technique=bound_technique, testing=True, experiment=exp)

            # Execute optimization and collect performance metrics
            solution, obj_value, order_count, runtime, status, gap = optimizer.execute()

            # Process optimization results
            if solution is not None:
                # Validate solution feasibility
                feasible = solution.feasibility_check()
                if not feasible:
                    raise Exception(f"Infeasible solution for instance {instance}")
                else:
                    print(f"Feasible solution for instance {instance}")
                
                # Evaluate solution quality and extract key metrics
                evaluation.evaluate(solution)

                # Extract detailed solution metrics
                order_item_count = solution.number_of_finished_order_items  # Completed work tasks
                driver_violation = solution.driver_violation               # Regulatory violations
                commute_distance = solution.total_commute_distance         # Worker travel distance
                transport_distance = solution.total_transport_distance     # Machine transport distance
                attachment_distance = solution.total_transport_distance_attachments  # Attachment transport
                machine_count = solution.number_of_machines               # Machines utilized
                worker_count = solution.number_of_workers                 # Workers utilized
                attachment_count = solution.number_of_attachments         # Attachments utilized

            else:
                # Handle case where no solution was found
                order_item_count = None
                driver_violation = None
                commute_distance = None
                transport_distance = None
                attachment_distance = None
                machine_count = None
                worker_count = None
                attachment_count = None

            # Store comprehensive results for current instance
            dict_solution[instance] = [obj_value, order_count, runtime, status, gap, 
                                     order_item_count, driver_violation, commute_distance, 
                                     transport_distance, attachment_distance, machine_count, 
                                     worker_count, attachment_count]

        # Convert results to DataFrame for analysis and export
        df_upper_bound = pd.DataFrame.from_dict(dict_solution, orient="index", 
                                              columns=["Objective Value", "Order Count", "Runtime (s)", 
                                                     "Status", "Gap", "Order Item Count", "Driver Violation", 
                                                     "Commute Distance", "Transport Distance", 
                                                     "Attachment Distance", "Machine Count", 
                                                     "Worker Count", "Attachment Count"])
        df_upper_bound.index.name = "Instance"
        df_upper_bound.reset_index(inplace=True)
        
        # Create output directory and export results to CSV
        upper_bound_path = Path.cwd().parent / "Data" / "Solution_math_model"
        upper_bound_path.mkdir(parents=True, exist_ok=True)
        df_upper_bound.to_csv(upper_bound_path / f"{bound_technique}_experiment_{exp}_full_solution.csv", index=False)
        print(df_upper_bound)



def single_run():
    """
    Executes a single optimization run for detailed analysis and debugging.
    
    Performs optimization on a specific instance using either Binary Integer Programming (BIP)
    or Linear Programming (LP) relaxation. Provides detailed output for solution analysis
    and feasibility validation. Useful for debugging and detailed instance examination.
    """
    # Configuration for single instance execution
    instance = "Construction_a20_o236_m12_an106_ar24.json"  # Target instance file
    strategy = "LP"  # Optimization strategy: "BIP" for exact, "LP" for relaxation

    # Load instance data (without algorithm-specific path configuration)
    data = InputData.InputData(instance)
    
    # Initialize optimizer based on selected strategy
    if strategy == "BIP":
        # Binary Integer Programming for exact solutions
        optimizer = MIP_UB.UpperBound(data, bound_technique='BIP', upper_bound="all")
    elif strategy == "LP":
        # Linear Programming relaxation for bounds and feasibility analysis
        optimizer = MIP_UB.UpperBound(data, bound_technique='LP', upper_bound="all")

    # Execute optimization and collect results
    solution = optimizer.execute()

    # Display high-level solution metrics
    print(f"\nObjective value: {solution[0]}")      # Optimization objective value
    print(f"Orders: {solution[1]}")                # Number of orders in solution
    print(f"Order items: {solution[2]}")           # Number of order items completed
    print(f"Order List: {solution[3]}")            # List of selected orders
    print(f"Length of Order List: {len(solution[3])}")  # Count of selected orders

    # For BIP solutions, perform detailed feasibility analysis
    if strategy == "BIP":
        # Extract detailed routing information from optimization solution
        route = optimizer.extract_routes_from_solution()
        
        # Create solution object with worker routes, machine routes, and attachment routes
        Solution = OutputData.Solution(route[1], route[0], route[2], data)
        
        # Validate solution feasibility against all constraints
        feasible = Solution.feasibility_check()
        if not feasible:
            raise Exception(f"Infeasible solution for instance {instance}")
        else:
            print("Feasible solution")


if __name__ == "__main__":
    """
    Main execution entry point for mathematical optimization experiments.
    
    Provides two execution modes:
    1. experiments() - Comprehensive batch processing of multiple instances
    2. single_run() - Detailed analysis of individual instance
    
    Switch between modes by commenting/uncommenting the appropriate function call.
    """
    experiments()    # Execute comprehensive experimental analysis
    #single_run()    # Execute single instance detailed analysis
