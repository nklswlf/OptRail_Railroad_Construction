from InputData import InputData
import OutputData
from ConstructiveHeuristic import *
import pandas as pd
from pathlib import Path
from EvaluationLogic import *
from time import time
from ImprovementAlgorithm import *
from Solver import *



# Reduced
'''
Construction_a3_o80_m10_an10_ar9_reduced.json
Construction_a5_o96_m10_an10_ar10_reduced.json
'''

# 10 Sites
'''
Construction_a10_o107_m5_an57_ar12.json
Construction_a10_o114_m6_an57_ar11.json
Construction_a10_o128_m6_an51_ar13.json
Construction_a10_o144_m6_an53_ar12.json
'''


# 15 Sites
'''
Construction_a15_o170_m9_an80_ar18.json

'''

# 20 Sites
'''
Construction_a20_o236_m12_an106_ar24.json
'''

# 25 Sites
'''
Construction_a25_o306_m13_an127_ar31.json
'''

# 30 Sites
'''
Construction_a30_o355_m18_an148_ar42.json
'''

# 40 Sites
'''
Construction_a40_o476_m22_an215_ar51.json
'''

# 50 Sites
'''
Construction_a50_o578_m28_an276_ar66.json
'''

instances = ["Construction_a3_o80_m10_an10_ar9_reduced.json",
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
                "Construction_a40_o476_m22_an215_ar51.json", # UB not reached!!! because not machine type 2 does not exist for a machine in the instance
                                                            # Reached after pre-processing in InputData
                "Construction_a50_o578_m28_an276_ar66.json"]

instances = ["Construction_a20_o236_m12_an106_ar24.json"]



machine_attractiveness_techniques = ["balanced_greedy",
                                     "machine_planned_importance",
                                     "worker_default_driver_importance",
                                     "possible_default_drivers_importance"]

order_item_attractiveness_techniques = ["balanced_greedy",
                                        "order_priority_importance",
                                        "dynamic_percentage_importance",
                                        "time_difference_importance"]



neighboorhood_types = ['Replace_Shift_Worker', 'Replace_Shift_Machine', 'Replace_Shift_Attachment',
                       'Swap_Shift_Worker', 'Swap_Shift_Machine', 'Swap_Shift_Attachment',
                       'Swap_Shift_External', 'Insert_Shift']

neighboorhood_types_local_search = ['Replace_Shift_Worker', 'Replace_Shift_Machine', 'Replace_Shift_Attachment']



objectives = ["commute_distance", "transport_distance", "attachment_distance",
              "worker_count", "machine_count", "attachment_count",
              "dynamic_percentage", "driver_violation"]



types_and_objectives = {"dynamic_percentage_order": ["Insert_Shift", "Swap_Shift_External"],
                        "driver_violation": ["Insert_Shift", "Swap_Shift_External", 'Swap_Shift_Machine', 'Swap_Shift_Worker', 'Replace_Shift_Worker', 'Replace_Shift_Machine'],
                        "commute_distance": ["Insert_Shift", "Swap_Shift_External", 'Swap_Shift_Worker', 'Replace_Shift_Worker'],
                        "transport_distance": ["Insert_Shift", "Swap_Shift_External", 'Swap_Shift_Machine', 'Replace_Shift_Machine'],
                        "attachment_distance": ["Insert_Shift", "Swap_Shift_External", 'Swap_Shift_Attachment', 'Replace_Shift_Attachment'],
                        "machine_count": ["Insert_Shift", "Swap_Shift_External", 'Replace_Shift_Machine'],
                        "worker_count": ["Insert_Shift", 'Replace_Shift_Worker'],
                        "attachment_count": ["Insert_Shift", "Swap_Shift_External", 'Replace_Shift_Attachment']}



building_types_and_objectives = {"dynamic_percentage_order": ["Insert_Shift", "Swap_Shift_External"],
                        "commute_distance": ["Insert_Shift", "Swap_Shift_External", 'Swap_Shift_Worker', 'Replace_Shift_Worker'],
                        "transport_distance": ["Insert_Shift", "Swap_Shift_External", 'Swap_Shift_Machine', 'Replace_Shift_Machine'],
                        "attachment_distance": ["Insert_Shift", "Swap_Shift_External", 'Swap_Shift_Attachment', 'Replace_Shift_Attachment']}



improve_types_and_objectives = {
                        "driver_violation": ['Swap_Shift_Machine', 'Swap_Shift_Worker', 'Replace_Shift_Worker', 'Replace_Shift_Machine'],
                        "commute_distance": ['Swap_Shift_Worker', 'Replace_Shift_Worker'],
                        "transport_distance": ['Swap_Shift_Machine', 'Replace_Shift_Machine'],
                        "attachment_distance": ['Swap_Shift_Attachment', 'Replace_Shift_Attachment'],
                        "machine_count": ['Replace_Shift_Machine'],
                        "worker_count": ['Replace_Shift_Worker'],
                        "attachment_count": ['Replace_Shift_Attachment']}


energy_dominance_neighborhoods = {  'Replace_Shift_Worker': ['driver_violation', 'commute_distance', 'worker_count'],
                                    'Replace_Shift_Machine': ['driver_violation', 'transport_distance', 'machine_count'],
                                    'Replace_Shift_Attachment': ['attachment_distance', 'attachment_count'],
                                    'Swap_Shift_Worker': ['driver_violation', 'commute_distance'],
                                    'Swap_Shift_Machine': ['driver_violation', 'transport_distance'],
                                    'Swap_Shift_Attachment': ['attachment_distance']}

                        


only_constructive = False

def main():

    for i in instances:
        start_time = time.time()
        data = InputData(i)
        current_time = time.time() - start_time
        print(f"Input Data loaded in {round(current_time,2)} seconds")
        
        solver = Solver(data, 1)


        local_search = IterativeImprovement(inputData=data,
                                            neighborhoodTypes=neighboorhood_types_local_search)

        pareto_simulated_annealing = ParetoSimulatedAnnealing(inputData=data,
                                                                        start_temp=20,
                                                                        min_temp=0.1,
                                                                        cooling_rate=0.95,
                                                                        max_iterations= 100,
                                                                        fallback_threshold=25,
                                                                        scaling_energy= 30,
                                                                        max_building_iterations_without_improvement=20000,
                                                                        neighborhoodTypes=neighboorhood_types,
                                                                        energyDominanceNeighborhoods=energy_dominance_neighborhoods,
                                                                        buildingTypesObjectives=building_types_and_objectives,
                                                                        improveTypesObjectives=improve_types_and_objectives,
                                                                        improveIndividualStrategy="parallel")




        if only_constructive:
            # Run ONLY the constructive heuristic
            solver.ConstructionPhase(
                order_item_attractiveness_technique="balanced_greedy",
                machine_attractiveness_technique="balanced_greedy"
            )
        else:
            # Run the algorithm
            ub_time, construction_time, building_time, individual_time, dominance_time, feasibility_check_time, algo_time = solver.RunAlgorithm(
                order_item_attractiveness_technique="time_difference_importance",
                machine_attractiveness_technique="balanced_greedy",
                algorithm=pareto_simulated_annealing
            )

        end_time = time.time() - start_time


        input_dict = {
            "Data": round(current_time, 2),
            "LP-Relax": round(ub_time, 2),
        }
        data_time = round(current_time, 2) + round(ub_time, 2)

        sa_dict = {
            "Construction": round(construction_time, 2),
            "Building": round(building_time, 2),
            "Individual": round(individual_time, 2),
            "Dominance": round(dominance_time, 2),
            "Feasibility": round(feasibility_check_time, 2),
        }


        time_entries = [
            ("Phase", "Time"),
            ("============", "======"),
        ] + list(input_dict.items()) + [
            ("------------", "-----"),
            ("Input Time", data_time),
            ("============", "======"),
        ] + list(sa_dict.items()) + [
            ("------------", "-----"),
            ("Algo Time", round(algo_time, 2)),
            ("============", "======"),
            ("Total Time", round(end_time, 2))
        ]

        df = pd.DataFrame(time_entries[1:], columns=time_entries[0])

        print("\n")
        print("Time Statistics:")
        print(df.to_string(index=False))
        print("\n")

        


        


if __name__ == "__main__":
    main()