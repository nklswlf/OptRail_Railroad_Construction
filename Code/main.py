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

                        


only_greedy = False

def main():

    for i in instances:
        start_time = time.time()
        data = InputData(i)
        current_time = time.time() - start_time
        print(f"Input Data loaded in {round(current_time,2)} seconds")
        
        solver = Solver(data, 1)


        local_search = IterativeImprovement(inputData=data,
                                            neighborhoodTypes=neighboorhood_types_local_search)


        building_sa = BuildingSimulatedAnnealing(inputData=data,
                                                 start_temp=20,
                                                    min_temp=0.1,
                                                    cooling_rate=0.95,
                                                    max_iterations=3000,
                                                    fallback_threshold=25,
                                                    scaling_energy=30)
                                                 


        mosa = MOSA(inputData=data,
                    start_temp=20,
                    min_temp=0.1,
                    cooling_rate=0.95,
                    max_iterations= 100,
                    fallback_threshold=25,
                    scaling_energy= 30,
                    max_building_iterations_without_improvement=20000,
                    neighborhoodTypes=neighboorhood_types,
                    energyDominanceNeighborhoods=energy_dominance_neighborhoods,
                    improveTypesObjectives=improve_types_and_objectives,
                    improveIndividualStrategy="parallel")
        
        algorithms = [building_sa, mosa]


        if only_greedy:
            solver.RunConstructive(UB_technique="LP",
                                   order_item_attractiveness_technique="time_difference_importance",
                                   machine_attractiveness_technique="balanced_greedy",
                                   worker_attractiveness_technique = "balanced_greedy")
        else:
            solver.RunAlgorithm(UB_technique="LP",
                                order_item_attractiveness_technique="time_difference_importance",
                                machine_attractiveness_technique="balanced_greedy",
                                worker_attractiveness_technique = "balanced_greedy",
                                algorithm=algorithms)



        

def feasibility_check():

    data = InputData("Construction_a20_o236_m12_an106_ar24.json")

    machine = {0: [101, 194, 82, 153, 69], 1: [128, 84, 167, 168, 94, 95, 114, 71, 174, 73, 118, 177, 188, 180, 105, 182, 161], 2: [86, 140, 70, 145, 75, 76, 233, 193, 184, 157, 200, 201], 3: [85, 87, 88, 89, 166, 5, 92, 173, 99, 100, 120, 190, 234, 83, 158, 159, 109, 112], 4: [164, 131, 90, 63, 143, 74, 178, 103, 79, 152, 149, 160], 5: [124, 125, 127, 130, 133, 135, 91, 139, 121, 181, 183, 81, 187, 199, 68, 205, 113], 6: [93, 171, 172, 115, 72, 175, 189, 104, 123, 197, 202, 151, 111], 7: [134, 136, 170, 98, 146, 147, 231, 232, 235, 185, 64, 65, 67, 155, 150, 110], 8: [1, 129, 2, 3, 137, 138, 142, 116, 107, 186, 108, 204, 163], 9: [0, 96, 144, 176, 230, 78, 106, 195, 66], 10: [165, 132, 62, 169, 141, 97, 117, 119, 77, 191, 80, 196, 156, 148, 203, 162], 11: [126, 4, 102, 179, 122, 192, 198, 154]}
    worker = {0: [235], 1: [], 2: [164, 86, 89, 137, 169, 173, 145, 75, 121, 79, 152, 200, 150, 110], 3: [4, 231, 234, 80, 83], 4: [165, 172, 116, 74, 120, 122, 106, 194, 65, 148, 160], 5: [133, 92, 170, 142, 144, 100, 190, 107, 196, 156, 68, 112], 6: [0, 130, 134, 167, 171, 143, 101, 77, 123, 193, 153, 69, 151, 163], 7: [124, 131, 93, 114, 174, 146, 178, 104, 192, 195, 187, 149, 113], 8: [], 9: [126, 166, 140, 70, 73, 147, 179, 105, 198, 158, 108, 205], 10: [5], 11: [127, 88, 91, 139, 95, 98, 118, 102, 181, 186, 199, 202, 204], 12: [], 13: [3, 62, 63, 82], 14: [], 15: [230, 81], 16: [125, 85, 168, 141, 71, 99, 177, 189, 183, 66, 154, 109], 17: [232], 18: [129, 132, 2, 136, 138, 94, 97, 175, 76, 180, 157, 159, 161, 111], 19: [], 20: [], 21: [233], 22: [87, 135, 115, 117, 119, 103, 191, 184, 64, 67, 201, 203], 23: [1, 128, 84, 90, 96, 72, 176, 188, 78, 182, 185, 197, 155, 162]}
    attachment = {0: [], 1: [164], 2: [82], 3: [], 4: [189, 196, 198], 5: [], 6: [], 7: [188, 194], 8: [], 9: [], 10: [], 11: [0], 12: [], 13: [], 14: [], 15: [], 16: [0], 17: [], 18: [], 19: [], 20: [], 21: [], 22: [0], 23: [], 24: [], 25: [232, 234], 26: [82], 27: [], 28: [], 29: [], 30: [], 31: [], 32: [233], 33: [], 34: [], 35: [], 36: [], 37: [], 38: [], 39: [], 40: [], 41: [], 42: [], 43: [], 44: [], 45: [], 46: [], 47: [], 48: [164, 82], 49: [82], 50: [], 51: [], 52: [], 53: [], 54: [], 55: [], 56: [], 57: [], 58: [], 59: [], 60: [], 61: [190], 62: [], 63: [], 64: [], 65: [0], 66: [], 67: [192], 68: [], 69: [], 70: [], 71: [], 72: [], 73: [], 74: [], 75: [68], 76: [], 77: [], 78: [], 79: [], 80: [0], 81: [], 82: [], 83: [], 84: [], 85: [], 86: [], 87: [], 88: [], 89: [], 90: [], 91: [], 92: [], 93: [191], 94: [197], 95: [], 96: [70], 97: [], 98: [], 99: [], 100: [195], 101: [], 102: [], 103: [], 104: [], 105: [193]}
    
    check_solution = Solution(route_plan_worker=worker,
                            route_plan_machine=machine,
                            route_plan_attachment=attachment,
                            data=data)
    
    feasible = check_solution.feasibility_check()

    print("Feasible: ", feasible)
                            




if __name__ == "__main__":
    main()
    #feasibility_check()