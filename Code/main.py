from InputData import *
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
                "Construction_a10_o128_m6_an51_ar13.json",
                "Construction_a10_o144_m6_an53_ar12.json",
                "Construction_a15_o170_m9_an80_ar18.json",
                "Construction_a20_o236_m12_an106_ar24.json",
                "Construction_a25_o306_m13_an127_ar31.json",
                "Construction_a30_o355_m18_an148_ar42.json",
                "Construction_a40_o476_m22_an215_ar51.json",
                "Construction_a50_o578_m28_an276_ar66.json"]

#instances = ["Construction_a10_o128_m6_an51_ar13.json"]



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

neighboorhood_types_simulated_annealing = ['Replace_Shift_Worker', 'Replace_Shift_Machine', 'Swap_Shift_Worker', 'Swap_Shift_Machine','Insert_Shift', 'Replace_Shift_Attachment']
#neighboorhood_types_simulated_annealing = ['Insert_Shift']

neighboorhood_types_local_search = ['Replace_Shift_Attachment', 'Insert_Shift', 'Swap_Shift_Attachment']
neighboorhood_types_local_search = ['Swap_Shift_External']



only_constructive = False

def main():

    for i in instances:
        data = InputData(i)
        print(f"Instance: {data.instance}")

        solver = Solver(data, 3)


        local_search = IterativeImprovement(inputData=data,
                                            neighborhoodTypes=neighboorhood_types_local_search)

        simulated_annealing_local_search = SimulatedAnnealingLocalSearch(inputData=data,
                                                                        start_temp=100,
                                                                        min_temp=0.1,
                                                                        cooling_rate=0.9,
                                                                        max_iterations=5000,
                                                                        neighborhoodTypesSA=neighboorhood_types_simulated_annealing,
                                                                        neighborhoodTypesLS=neighboorhood_types_local_search)

        if only_constructive:
            # Run ONLY the constructive heuristic
            solver.ConstructionPhase(
                order_item_attractiveness_technique="balanced_greedy",
                machine_attractiveness_technique="balanced_greedy"
            )
        else:
            # Run the algorithm
            solver.RunAlgorithm(
                order_item_attractiveness_technique="balanced_greedy",
                machine_attractiveness_technique="balanced_greedy",
                algorithm=local_search
            )




if __name__ == "__main__":
    main()