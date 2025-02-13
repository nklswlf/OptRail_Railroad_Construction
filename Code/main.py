from InputData import *
import OutputData
from ConstructiveHeuristic import *
import pandas as pd
from pathlib import Path
from EvaluationLogic import *
from time import time
from ImprovementAlgorithm import *



# Reduced
'''
Construction_a3_o80_m10_an10_ar9_reduced.json
Construction_a5_o96_m10_an10_ar10_reduced.json
'''

# 10 Sites --> "Construction_a10_o118_m6_an53_ar13.json": Instance not duable since one order has no order items
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



machine_attractiveness_techniques = ["balanced_greedy",
                                     "machine_planned_importance",
                                     "worker_default_driver_importance",
                                     "possible_default_drivers_importance"]

order_item_attractiveness_techniques = ["balanced_greedy",
                                        "order_priority_importance",
                                        "dynamic_percentage_importance",
                                        "time_difference_importance"]


machine_attractiveness_techniques = ["balanced_greedy"]

order_item_attractiveness_techniques = ["balanced_greedy"]
                                    

def main():
    for instance in instances:
        for machine_attractiveness_technique in machine_attractiveness_techniques:
            for order_item_attractiveness_technique in order_item_attractiveness_techniques:
                print("Instance: ", instance)
                print("Machine Attractiveness Technique: ", machine_attractiveness_technique)
                print("Order Item Attractiveness Technique: ", order_item_attractiveness_technique)
                print("\n")
                single_run(instance, order_item_attractiveness_technique, machine_attractiveness_technique)
                print("\n")

neighboorhood_types = ['Replace_Shift_Worker', 'Swap_Shift_Worker', 'Insert_Shift', 'Replace_Shift_Machine', 'Swap_Shift_Machine', 'Swap_Shift_External']
neighboorhood_types = ['Insert_Shift']

def single_run(instance_filename = "Construction_a10_o107_m5_an57_ar12.json", order_item_attractiveness_technique="balanced_greedy", machine_attractiveness_technique="balanced_greedy"):

    #time_start = time()
    data = InputData(instance_filename)
    #time_end = time()
    #time_for_data_loading = time_end - time_start

    for order_item in data.order_items:
        if len(order_item.equipment_types) > 0:
            print(f"Order Item: {order_item.id} --> Equipment Types: {order_item.equipment_types} + Possible equipments: {set(attachment.id for attachment in data.attachments if attachment.type in order_item.equipment_types)}")


    evaluationLogic = EvaluationLogic(data)
    solutionPool = SolutionPool()
    
    #time_start = time()
    construct = ConstructiveHeuristics(solutionPool= None, evaluationLogic = evaluationLogic)
    construct_solution = construct.Run(data, order_item_attractiveness_technique, machine_attractiveness_technique)
    #time_end = time()
    #time_for_construction = time_end - time_start


    print(f"\nSolution after construction: \n{construct_solution}")


    localSearch = IterativeImprovement(data, neighborhoodTypes=neighboorhood_types)
    
    localSearch.Initialize(evaluationLogic=evaluationLogic, solutionPool=solutionPool)

    local_search_solution = localSearch.Run(construct_solution)


    print(f"\nAverage transport distance: {data.average_transport_distance}")
    print(f"\nMax transport distance: {data.max_transport_distance}")
    print(f"Min transport distance: {data.min_transport_distance}")
    print(f"\nAverage work distance: {data.average_work_distance}")
    print(f"\nMax work distance: {data.max_work_distance}")
    print(f"Min work distance: {data.min_work_distance}")
    print(f"Min dynamic change: {data._min_dynamic_precentage_change}")
    print(f"Max dynamic change: {data._max_dynamic_precentage_change}")


    #solution.create_output_file_greedy(time_for_data_loading, time_for_construction ,order_item_attractiveness_technique, machine_attractiveness_technique)





def TestInputData():
    instance_filename = "Construction_a10_o107_m5_an57_ar12.json"

    for instance_filename in instances:
        # Erstellen einer InputData-Instanz
        data = InputData(instance_filename)




    '''
    # Anzeigen der Vorgänger-Nachfolger-Beziehungen
    print("\Worker-Predecessors-Successors:")
    for worker in data.workers:
        print(worker.personal_number, worker.predecessors)
        print(worker.personal_number, worker.successors)

    print("\nMachine-Predecessors-Successors:")
    for machine in data.machines:
        print(machine.id, machine.predecessors)
        print(machine.id, machine.successors)


    # Anzeigen der geladenen Daten mit strukturierten Ausgaben
    print("\nOrders:")
    for order in data.orders:
        print(order)

    print("\nOrder Items:")
    for item in data.order_items:
        print(item)

    print("\nAttachments:")
    for attachment in data.attachments:
        print(attachment)

    print("\nWorkers:")
    for worker in data.workers:
        print(worker)

    print("\nMachines:")
    for machine in data.machines:
        print(machine)

    # Anzeigen der Instanz-Metadaten
    print("\nStart Date:", data.start_date)
    print("End Date:", data.end_date)
    print("Contains Durations:", data.contains_durations)

    # Anzeigen der Transport- und Arbeitswege
    print("\nTransport Routes:")
    for row in data.transport_routes:
        print(row)

    print("\nWork Routes:")
    for row in data.work_routes:
        print(row)
    '''


def feasi_check():

    attachment_route = {0: [23], 1: [19], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: [], 9: [], 10: [], 11: [], 12: [23, 34], 13: [], 14: [], 15: [], 16: [], 17: [23], 18: [], 19: [], 20: [], 21: [], 22: [], 23: [], 24: [], 25: [], 26: [23], 27: [], 28: [], 29: [], 30: [], 31: [], 32: [], 33: [], 34: [], 35: [19], 36: [], 37: [], 38: [], 39: [], 40: [], 41: [], 42: [], 43: [], 44: [], 45: [], 46: [], 47: [], 48: [], 49: [], 50: [23], 51: [], 52: [], 53: [], 54: [], 55: [23], 56: []}
    machine_route = {0: [22, 87, 28, 104, 31, 33, 36, 41], 1: [19, 20, 17, 18, 23, 24, 82, 83, 25, 84, 26, 85, 27, 86, 100, 13, 14, 15, 16, 30, 106, 32, 34, 35, 38, 39, 40], 2: [88, 89, 78, 80], 3: [21, 93, 94, 95, 96, 97, 98, 99, 101, 102, 103, 29, 105, 90, 91, 92, 37], 4: []}
    worker_route = {0: [17, 23, 25, 26, 27, 13, 15, 30, 32, 34, 38, 40], 1: [14, 16, 106], 2: [93, 95, 97, 99, 101, 103, 105], 3: [94, 96, 98, 100, 102], 4: [18, 24, 104, 31, 33, 36, 41], 5: [], 6: [39], 7: [19, 21, 28, 35, 37], 8: [20, 22, 29, 90, 91, 92], 9: [], 10: [], 11: [82, 83, 84, 85, 86, 87, 88, 89, 78, 80]}

    data = InputData("Construction_a10_o107_m5_an57_ar12.json")

    evaluationLogic = EvaluationLogic(data)

    solution = Solution(worker_route, machine_route, attachment_route, data)

    solution.feasibility_check()



    
if __name__ == "__main__":
    #TestInputData()
    single_run()
    #main()
    #feasi_check()