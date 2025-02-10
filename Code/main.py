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
                                     "posible_order_items_best_order_importance",
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

neighboorhood_types = ['Replace_Shift_Worker', 'Swap_Shift_Worker', 'Insert_Shift', 'Replace_Shift_Machine', 'Swap_Shift_Machine', 'Replace_Shift']

neighboorhood_types = ['Swap_Shift_Machine']


def single_run(instance_filename = "Construction_a20_o236_m12_an106_ar24.json", order_item_attractiveness_technique="balanced_greedy", machine_attractiveness_technique="balanced_greedy"):

    #time_start = time()
    data = InputData(instance_filename)
    #time_end = time()
    #time_for_data_loading = time_end - time_start

    evaluationLogic = EvaluationLogic(data)
    solutionPool = SolutionPool()
    
    #time_start = time()
    construct = ConstructiveHeuristics(solutionPool= None, evaluationLogic = evaluationLogic)
    construct_solution = construct.Run(data, order_item_attractiveness_technique, machine_attractiveness_technique)
    #time_end = time()
    #time_for_construction = time_end - time_start


    print(f"\nSolution after construction: \n{construct_solution}")


    repair = RepairAlgorithm(data)
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

    # Erstellen einer InputData-Instanz
    data = InputData(instance_filename)

    # Anzeigen der Instanz-Metadaten
    print("\nInstance Name:", data.instance)




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



    
if __name__ == "__main__":
    #TestInputData()
    single_run()
    #main()