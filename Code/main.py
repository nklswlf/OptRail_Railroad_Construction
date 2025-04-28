from InputData import InputData
import OutputData
from ConstructiveHeuristic import *
import pandas as pd
from pathlib import Path
from EvaluationLogic import *
from time import time
from ImprovementAlgorithm import *
from Solver import *
import cProfile
import pstats
import json

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


instances = ["Construction_a50_o578_m28_an276_ar66.json"]




neighboorhood_types = ['Replace_Shift_Worker', 'Replace_Shift_Machine', 'Replace_Shift_Attachment',
                       'Swap_Shift_Worker', 'Swap_Shift_Machine', 'Swap_Shift_Attachment',
                       'Swap_Shift_External', 'Insert_Shift']

neighboorhood_types_local_search = ['Swap_Shift_External']





## Greedy Techniques

machine_attractiveness_techniques = ["balanced_greedy",
                                     "machine_planned_importance",
                                     "worker_default_driver_importance",
                                     "possible_default_drivers_importance"]

order_item_attractiveness_techniques = ["balanced_greedy",
                                        "order_priority_importance",
                                        "dynamic_percentage_importance",
                                        "time_difference_importance"]

worker_attractiveness_techniques = ["balanced_greedy",
                                    "worker_planned_importance",
                                    "qualifications_importance"]


greedy_technique_a = {'worker_greedy': {'order_item_attractiveness_technique': 'time_difference_importance',
                                        'machine_attractiveness_technique': 'balanced_greedy'}}


greedy_technique_b = {'order_item_greedy': {'worker_attractiveness_technique': 'balanced_greedy',
                                            'machine_attractiveness_technique': 'balanced_greedy'}}




step = None
#step = 'Bound'
#step = 'Greedy'
#step = 'Building'

algortihm = 'TPSA'

algortihms = ['PSA', 'DBSA', 'TPSA']


def main():

    for i in instances:
        #for algortihm in algortihms:
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
                                                max_iterations=500,
                                                fallback_threshold=25,
                                                scaling_energy=30)

            elif algortihm == 'DBSA':
                algo = DominanceBasedSimulatedAnnealing( inputData=data,
                                                        start_temp=20,
                                                        min_temp=0.1,
                                                        cooling_rate=0.95,
                                                        max_iterations=500,
                                                        fallback_threshold=25,
                                                        scaling_energy=30,
                                                        max_single_move_tries=30)

            
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
                time = solver.RunBound(UB_technique="LP")
                print("\nBound Time: ", round(time, 2))
            
            elif step == 'Greedy':
                solution, time = solver.RunConstructive(UB_technique="LP",
                        greedy_technique=greedy_technique_b)
                print("\nGreedy Time: ", round(time, 2))

                
            elif step == 'Building':
                solution, time = solver.RunBuilding(UB_technique="LP",
                        greedy_technique=greedy_technique_b,
                        building_algorithm=building_sa)
                print("\nBuilding Time: ", round(time, 2))

            else:
                times = solver.Run( UB_technique="LP",
                    greedy_technique=greedy_technique_b,
                    building_algorithm=building_sa,
                    improvement_algorithm=algo)

                print("\nBound Time: ", round(times["Bound Time"], 2))
                print("Greedy Time: ", round(times["Greedy Time"], 2))
                print("Building Time: ", round(times["Building Time"], 2))
                print("Improvement Time: ", round(times["Improvement Time"], 2))
                print("Total Time: ", round(times["Total Time"], 2))

                output_file = data.solutions_path/"run_times.json"
                with open(output_file, "w") as f:
                    json.dump(times, f, indent=4)



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