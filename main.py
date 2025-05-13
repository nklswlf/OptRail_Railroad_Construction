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
                "Construction_a10_o128_m6_an51_ar13.json", # UB not reached!!! because not enough worker with qualification (q = 9,4) are available for shifts at the same time
                                                            # Reached after Edit Sites
                "Construction_a10_o144_m6_an53_ar12.json",
                "Construction_a15_o170_m9_an80_ar18.json",
                "Construction_a20_o236_m12_an106_ar24.json", # UB not reached!!! because not enough attachment types (type = 8) are available for shifts at the same time
                                                            # Check with UB LP Relaxation including ATTACHMENTS
                "Construction_a25_o306_m13_an127_ar31.json",
                "Construction_a30_o355_m18_an148_ar42.json",
                "Construction_a40_o476_m22_an215_ar51.json", # UB not reached!!! because machine type 2 does not exist for a machine in the instance
                                                            # Reached after pre-processing in InputData
                "Construction_a50_o578_m28_an276_ar66.json"]


#instances = [   "Construction_a30_o355_m18_an148_ar42.json"]



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

algortihms = ['PSA', 'DBSA']#, 'TPSA']


def main():
    df_testing = pd.DataFrame()

    for i in instances:
        for algortihm in algortihms:
        #for gt in greedy_techniques:
            if step == None:
                data = InputData(i, algortihm)
            else:
                data = InputData(i, step)

            solver = Solver(data, 100)
            

            local_search = IterativeImprovement(inputData=data,
                                                neighborhoodTypes=neighboorhood_types_local_search)


            building_sa = BuildingSimulatedAnnealing(   inputData=data,
                                                        start_temp=20,
                                                        min_temp=0.1,
                                                        cooling_rate=0.95,
                                                        max_iterations=3000,
                                                        fallback_threshold=25,
                                                        scaling_energy=30)
                                                    
            if algortihm == 'PSA':
                algo = ParetoSimulatedAnnealing( inputData=data,
                                                start_temp=20,
                                                min_temp=0.1,
                                                cooling_rate=0.95,
                                                max_iterations=1,
                                                fallback_threshold=25,
                                                scaling_energy=30,
                                                weight_alpha=1.1,
                                                max_single_move_tries=30,
                                                start_size_population=8)

            elif algortihm == 'DBSA':
                algo = DominanceBasedSimulatedAnnealing( inputData=data,
                                                        start_temp=20,
                                                        min_temp=0.1,
                                                        cooling_rate=0.95,
                                                        max_iterations=1,
                                                        fallback_threshold=25,
                                                        scaling_energy=30,
                                                        max_single_move_tries=30,
                                                        parallel_runs=8)

            
            elif algortihm == 'TPSA':
                algo = TwoPhaseSimulatedAnnealing(  inputData=data,
                                                    start_temp_individual=20,
                                                    min_temp_individual=0.1,
                                                    cooling_rate_individual=0.95,
                                                    max_iterations_individual=500,
                                                    fallback_threshold_individual=25,
                                                    scaling_energy_individual=30,

                                                    start_temp_dominance=20,
                                                    min_temp_dominance=0.1,
                                                    cooling_rate_dominance=0.95,
                                                    max_iterations_dominance=500,
                                                    fallback_threshold_dominance=25,
                                                    scaling_energy_dominance=30,
                                                    max_single_move_tries_dominance=30)

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
                df_testing.to_csv("Improvement_Times.csv", index=False)

                output_file = data.solutions_path/"run_times.json"
                with open(output_file, "w") as f:
                    json.dump(times, f, indent=4)

        if step == None:
            combined_results = Run(data.instance)
            # Append metric data to the DataFrame
            metric_data = combined_results.get_metrics()
            metric_data["Instance"] = data.instance
            df_testing = pd.concat([df_testing, pd.DataFrame([metric_data])], ignore_index=True)

            # Save the updated DataFrame to a CSV file
            df_testing.to_csv(f"Metrics_{data.instance}.csv", index=False)


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