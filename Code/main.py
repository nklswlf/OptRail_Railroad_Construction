import InputData
import OutputData
import MIP_Flow
import pandas as pd
from pathlib import Path



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



# Options
objective_strategies = ["weighted", "hierarchical", "hierarchical_tolerance" , "costs", "pareto"]
pareto_attributes = ["MachineTransportDistance", "WorkerWorkDistance", "MachineUsage", "WorkerUsage", "NonRegularDriverUsage"]
number_of_objectives = [3, 4, 5, 6]


def main():
    instances = ["Construction_a3_o80_m10_an10_ar9_reduced.json"]
    objective_strategies = ["costs", "weighted", "hierarchical", "hierarchical_tolerance"]
    number_of_objectives = [3, 4, 5, 6]

    for number_obj in number_of_objectives:
        for objective_strategy in objective_strategies:
            for instance in instances:
                data = InputData.InputData(instance)
                optimizer = MIP_Flow.FlowFormulation(data, objective_strategy, number_obj)
                MIP_solution, objectives = optimizer.execute()

                if MIP_solution is not None:
                    feasible = MIP_solution.feasibility_check()
                    if not feasible:
                        raise Exception(f"Infeasible solution for instance {instance}")
                    else:
                        for obj in objectives:
                            print(f"{obj['Objective']} = {obj['Value']}")
                        optimizer.save_solution_to_file()
                        #OutputData.GanttDiagramGenerator(data.instance_filename, data._parent_folder, objective_strategy).create_gantt_diagrams()
                
                else:
                    print(f"No solution found for instance {instance}")

                    
                    


if __name__ == "__main__":
    #TestInputData()
    #pareto()
    main()








def pareto():
    instances = ["Construction_a3_o80_m10_an10_ar9_reduced.json"]
    pareto_attributes = ["MachineTransportDistance", "NonRegularDriverUsage"] 
    objective_strategy = "pareto"

    for instance in instances:
        data = InputData.InputData(instance)
        number_of_sites = len(data.orders)
        pareto_constructions = range(1, number_of_sites + 1)

        for pareto_attribute in pareto_attributes:
            pareto_results = []
            pareto_results.append({"Construction Fulfillment": 0, pareto_attribute: 0})

            for pareto_construction in pareto_constructions:
                optimizer = MIP_Flow.FlowFormulation(data, objective_strategy, pareto_attribute, pareto_construction)
                MIP_solution, objectives = optimizer.execute()

                if MIP_solution is not None:
                    feasible = MIP_solution.feasibility_check()

                    if not feasible:
                        raise Exception(f"Infeasible solution for {instance}, attribute {pareto_attribute}")
                    else:
                        result_row = {}
                        for obj in objectives:
                            result_row[obj["Objective"]] = obj["Value"]
                        pareto_results.append(result_row)
                else:
                    break

            # Ergebnisse speichern
            pareto_results_df = pd.DataFrame(pareto_results)
            print(f"Pareto-Ergebnisse für Instanz {instance} und Attribut {pareto_attribute}:")
            print(pareto_results_df)

            pareto_path = Path.cwd().parent / "Data" / "Solution" / data._parent_folder / data.instance / objective_strategy
            pareto_path.mkdir(parents=True, exist_ok=True)

            pareto_results_df.to_csv(pareto_path / f"{pareto_attribute}_pareto_results.csv", index=False)




def TestInputData():
    instance_filename = "Construction_a20_o276_m12_an101_ar25.json"

    # Erstellen einer InputData-Instanz
    data = InputData(instance_filename)
    
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

    for order in data.orders:
        print(order.order_number)
        print(order.order_item_ids)