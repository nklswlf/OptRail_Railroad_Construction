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


instances = [   "Construction_a3_o80_m10_an10_ar9_reduced.json",
                "Construction_a5_o96_m10_an10_ar10_reduced.json",
                "Construction_a10_o107_m5_an57_ar12.json",
                "Construction_a10_o114_m6_an57_ar11.json",
                "Construction_a10_o128_m6_an51_ar13.json",
                "Construction_a10_o144_m6_an53_ar12.json",
                "Construction_a15_o170_m9_an80_ar18.json",
                "Construction_a20_o236_m12_an106_ar24.json",
                "Construction_a25_o306_m13_an127_ar31.json",
                "Construction_a30_o355_m18_an148_ar42.json",
                "Construction_a40_o476_m22_an215_ar51.json",
                "Construction_a50_o578_m28_an276_ar66.json"]

'''
instances = ["Construction_RealLife_2024_3.json", # Location: 0/0
            "Construction_RealLife_2024_4.json", # Location: 0/0
            "Construction_RealLife_2024_5.json", # Location: 0/0
            "Construction_RealLife_2024_6.json", # Location: 0/0
            "Construction_RealLife_2024_7.json", # checked
            "Construction_RealLife_2024_8.json", # checked
            "Construction_RealLife_2024_9.json", # checked
            "Construction_RealLife_2024_10.json", # checked
            "Construction_RealLife_2024_11.json"] # empty instance

'''
instances = ["Construction_RealLife_2024_7_1_2.json",
            "Construction_RealLife_2024_8_1_2.json",
            "Construction_RealLife_2024_9_1_2.json",
            "Construction_RealLife_2024_10_1_2.json",
            "Construction_RealLife_2024_7_2_2.json",
            "Construction_RealLife_2024_8_2_2.json",
            "Construction_RealLife_2024_9_2_2.json",
            "Construction_RealLife_2024_10_2_2.json"]


instances = ["Construction_RealLife_2023_5.json"]


neighboorhood_types = ['Replace_Shift_Worker', 'Replace_Shift_Machine', 'Replace_Shift_Attachment',
                       'Swap_Shift_Worker', 'Swap_Shift_Machine', 'Swap_Shift_Attachment',
                       'Swap_Shift_External', 'Insert_Shift']

neighboorhood_types_local_search = ['Swap_Shift_External']





## Greedy Techniques

machine_attractiveness_techniques = ["balanced_greedy",
                                     "machine_planned_importance",
                                     "worker_default_driver_importance"]

order_item_attractiveness_techniques = ["balanced_greedy",
                                        "dynamic_percentage_importance",
                                        "time_difference_importance"]

worker_attractiveness_techniques = ["balanced_greedy",
                                    "worker_planned_importance",
                                    "qualifications_importance"]

greedy_technique_a = {'order_item_greedy': {'worker_attractiveness_technique': 'balanced_greedy', 
                                            'machine_attractiveness_technique': 'balanced_greedy'}}


greedy_technique_b = {'worker_greedy': {'order_item_attractiveness_technique': 'balanced_greedy',
                                        'machine_attractiveness_technique': 'balanced_greedy'}}



greedy_techniques = [greedy_technique_a, greedy_technique_b]

step = None
#step = 'Bound'
#step = 'Greedy'
#step = 'Building'

algortihm = 'DBSA'

algortihms = ['TPSA'] 
                

seeds = [104]#,105,107,109,110,111]#,112,113]


def main(): 
    for seed in seeds:
        df_testing = pd.DataFrame()
        for i in instances:
            for algortihm in algortihms:
            
                if step == None:
                    data = InputData(i, algortihm)
                else:
                    data = InputData(i, step)

                solver = Solver(data, seed)
                

                local_search = IterativeImprovement(inputData=data,
                                                    neighborhoodTypes=neighboorhood_types_local_search)


                building_sa = BuildingSimulatedAnnealing(  inputData=data,
                                                            start_temp=20,
                                                            min_temp=0.1,
                                                            cooling_rate=0.95,
                                                            max_iterations=3000,
                                                            fallback_threshold=25,
                                                            scaling_energy=30)
                                                        
                if algortihm == 'PSA':
                    algo = ParetoSimulatedAnnealing( inputData=data,
                                                    start_temp=50,
                                                    min_temp=0.1,
                                                    cooling_rate=0.95,
                                                    max_iterations=100,
                                                    fallback_threshold=0, # Currently not used
                                                    scaling_energy=50,
                                                    weight_alpha=1.1,
                                                    max_single_move_tries=30,
                                                    start_size_population=8)

                elif algortihm == 'DBSA':
                    algo = DominanceBasedSimulatedAnnealing( inputData=data,
                                                            start_temp=50,
                                                            min_temp=0.1,
                                                            cooling_rate=0.95,
                                                            max_iterations=400,
                                                            fallback_threshold=0, # Currently not used
                                                            scaling_energy=0, # Currently not used
                                                            max_single_move_tries=30,
                                                            parallel_runs=0)

                
                elif algortihm == 'TPSA':
                    algo = TwoPhaseSimulatedAnnealing(  inputData=data,
                                                        start_temp=50,
                                                        min_temp=0.1,
                                                        cooling_rate=0.95,
                                                        max_iterations_first=400,
                                                        max_iterations_second=400,
                                                        fallback_threshold=0, # Currently not used
                                                        scaling_energy=50,
                                                        max_single_move_tries=30,
                                                        parallel_runs=0)

                if step == 'Bound':
                    bound_time = solver.RunBound(UB_technique="LP")
                    print("Bound Time:", round(bound_time, 2))
                
                elif step == 'Greedy':
                    solution, time = solver.RunConstructive(UB_technique="LP",
                            greedy_technique=None)
                    print("\nGreedy Time: ", round(time, 2))

                    # Extract relevant solution attributes
                    solution_attributes = {
                        "Instance": data.instance,
                        "Greedy_Technique": None,
                        "Finished_Orders": solution.number_of_finished_orders,
                        "Finished_Order_Items": solution.number_of_finished_order_items,
                        "Total_Time": round(time, 2)
                    }

                    # Append the solution attributes to the DataFrame
                    df_testing = pd.concat([df_testing, pd.DataFrame([solution_attributes])], ignore_index=True)

                    # Save the DataFrame to a CSV file
                    df_testing.to_csv("Greedy.csv", index=False)


                    
                elif step == 'Building':
                    solution, time = solver.RunBuilding(UB_technique="LP",
                            greedy_technique=greedy_technique_a,
                            building_algorithm=building_sa)
                    print("\nBuilding Time: ", round(time, 2))


                    # Extract relevant solution attributes
                    solution_attributes = {
                        "Instance": data.instance,
                        "Finished_Orders": solution.number_of_finished_orders,
                        "Finished_Order_Items": solution.number_of_finished_order_items,
                        "Total_Time": round(time, 2)
                    }
                    # Append the solution attributes to the DataFrame
                    df_testing = pd.concat([df_testing, pd.DataFrame([solution_attributes])], ignore_index=True)

                    # Save the DataFrame to a CSV file
                    df_testing.to_csv("Building.csv", index=False)


                else:
                    times = solver.Run( UB_technique="LP",
                        greedy_technique=greedy_technique_a,
                        building_algorithm=building_sa,
                        improvement_algorithm=algo)

                    print("\nBound Time: ", round(times["Bound Time"], 2))
                    print("Greedy Time: ", round(times["Greedy Time"], 2))
                    print("Building Time: ", round(times["Building Time"], 2))
                    print("Improvement Time: ", round(times["Improvement Time"], 2))
                    print("Total Time: ", round(times["Total Time"], 2))

                    # Extract relevant attributes for the current run
                    run_attributes = {
                        "Instance": data.instance,
                        "Algorithm": algortihm,
                        "Improvement_Time": round(times["Improvement Time"], 2)
                    }

                    # Append the attributes to the DataFrame
                    df_testing = pd.concat([df_testing, pd.DataFrame([run_attributes])], ignore_index=True)

                    # Save the DataFrame to a CSV file
                    #df_testing.to_csv("Improvement_Times.csv", index=False)

                    output_file = data.solutions_path/"run_times.json"
                    with open(output_file, "w") as f:
                        json.dump(times, f, indent=4)


            if step is None:                             
                metrics_df = Run(data.instance, algortihms)
                # Add the instance name to the metrics DataFrame
                metrics_df["Instance"] = data.instance

                # Pivot to wide format: each metric becomes a column
                metric_data_pivot = metrics_df.pivot(index=["Instance", "Algorithm"],
                                                    columns="Metric", values="Value").reset_index()

                # Normalize both key columns
                df_testing["Instance"] = df_testing["Instance"].astype(str).str.strip()
                df_testing["Algorithm"] = df_testing["Algorithm"].astype(str).str.strip()
                metric_data_pivot["Instance"] = metric_data_pivot["Instance"].astype(str).str.strip()
                metric_data_pivot["Algorithm"] = metric_data_pivot["Algorithm"].astype(str).str.strip()

                # Ensure metric data is correctly added or updated
                df_testing = df_testing.set_index(["Instance", "Algorithm"])
                metric_data_pivot = metric_data_pivot.set_index(["Instance", "Algorithm"])

                # Add or update all metrics, even if NaN
                df_testing.loc[metric_data_pivot.index, metric_data_pivot.columns] = metric_data_pivot

                # Reset the index
                df_testing = df_testing.reset_index()
                metric_data_pivot = metric_data_pivot.reset_index()

                # Save to CSV
                df_testing.to_csv(f"Metrics_{seed}.csv", index=False)
                print("\nMetrics:\n", df_testing)


def profile_main():
    pr = cProfile.Profile()
    pr.enable()

    main()

    pr.disable()
    Path("Profiler").mkdir(parents=True, exist_ok=True)
    with open(Path("Profiler") / "main_profile.txt", "w") as f:
        ps = pstats.Stats(pr, stream=f).sort_stats("cumtime")
        ps.print_stats(300)


if __name__ == "__main__":
    profile_main()


    '''
                    
            elif algortihm == 'PSA_archive_setter':
                algo = ParetoSimulatedAnnealing_archive_setter( inputData=data,
                                                start_temp=20,
                                                min_temp=0.1,
                                                cooling_rate=0.95,
                                                max_iterations=50,
                                                fallback_threshold=25,
                                                scaling_energy=30,
                                                weight_alpha=1.1,
                                                max_single_move_tries=30,
                                                start_size_population=4)
                
            elif algortihm == 'PSA_global_archive_setter':
                algo = ParetoSimulatedAnnealing_global_archive_setter( inputData=data,
                                                start_temp=20,
                                                min_temp=0.1,
                                                cooling_rate=0.95,
                                                max_iterations=500,
                                                fallback_threshold=25,
                                                scaling_energy=30,
                                                weight_alpha=1.1,
                                                max_single_move_tries=30,
                                                start_size_population=4)
                

    '''