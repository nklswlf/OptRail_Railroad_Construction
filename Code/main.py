import InputData
import OutputData
import MIP_Flow
import pandas as pd
from pathlib import Path



# Reduced
'''
Construction_a1_o12_m3_an5_ar3_reduced.json
Construction_a3_o80_m10_an10_ar9_reduced.json
Construction_a5_o96_m10_an10_ar10_reduced.json
'''
'''
Construction_a1_o12_m3_an5_ar3_reduced.json
Construction_a3_o80_m10_an10_ar9_reduced.json
Construction_a5_o96_m10_an10_ar10_reduced.json
'''

# 10 Sites --> "Construction_a10_o118_m6_an53_ar13.json": Instance not duable since one order has no order items
'''
Construction_a10_o107_m5_an57_ar12.json
Construction_a10_o114_m6_an57_ar11.json
Construction_a10_o119_m5_an54_ar13.json
Construction_a10_o128_m6_an51_ar13.json
Construction_a10_o144_m6_an53_ar12.json
'''
'''
Construction_a10_o107_m5_an57_ar12.json
Construction_a10_o114_m6_an57_ar11.json
Construction_a10_o119_m5_an54_ar13.json
Construction_a10_o128_m6_an51_ar13.json
Construction_a10_o144_m6_an53_ar12.json
'''

# 15 Sites
'''
Construction_a15_o170_m9_an80_ar18.json
Construction_a15_o191_m8_an74_ar18.json
Construction_a15_o195_m8_an81_ar20.json

'''
'''
Construction_a15_o170_m9_an80_ar18.json
Construction_a15_o191_m8_an74_ar18.json
Construction_a15_o195_m8_an81_ar20.json

'''

# 20 Sites
'''
Construction_a20_o236_m12_an106_ar24.json
Construction_a20_o259_m11_an101_ar26.json
Construction_a20_o268_m11_an118_ar26.json
'''

# 25 Sites
'''
Construction_a25_o306_m13_an127_ar31.json
Construction_a25_o335_m16_an145_ar31.json
Construction_a25_o360_m15_an149_ar34.json
'''

# 30 Sites
'''
Construction_a30_o355_m18_an148_ar42.json
Construction_a30_o397_m17_an150_ar42.json
Construction_a30_o428_m16_an168_ar43.json
'''

# 40 Sites
'''
Construction_a40_o476_m22_an215_ar51.json
Construction_a40_o502_m21_an197_ar55.json
Construction_a40_o551_m25_an221_ar53.json
'''
'''
Construction_a20_o236_m12_an106_ar24.json
Construction_a20_o259_m11_an101_ar26.json
Construction_a20_o268_m11_an118_ar26.json
'''

# 25 Sites
'''
Construction_a25_o306_m13_an127_ar31.json
Construction_a25_o335_m16_an145_ar31.json
Construction_a25_o360_m15_an149_ar34.json
'''

# 30 Sites
'''
Construction_a30_o355_m18_an148_ar42.json
Construction_a30_o397_m17_an150_ar42.json
Construction_a30_o428_m16_an168_ar43.json
'''

# 40 Sites
'''
Construction_a40_o476_m22_an215_ar51.json
Construction_a40_o502_m21_an197_ar55.json
Construction_a40_o551_m25_an221_ar53.json
'''

# 50 Sites
'''
Construction_a50_o578_m28_an276_ar66.json
Construction_a50_o639_m28_an269_ar63.json
Construction_a50_o668_m29_an248_ar68.json
'''


instances = ["Construction_a15_o170_m9_an80_ar18.json",
             "Construction_a15_o191_m8_an74_ar18.json",
             "Construction_a15_o195_m8_an81_ar20.json",
             "Construction_a20_o236_m12_an106_ar24.json"
            ]

             

'''
Construction_a50_o578_m28_an276_ar66.json
Construction_a50_o639_m28_an269_ar63.json
Construction_a50_o668_m29_an248_ar68.json
'''


instances = ["Construction_a10_o107_m5_an57_ar12.json",
             "Construction_a10_o114_m6_an57_ar11.json",
             "Construction_a10_o119_m5_an54_ar13.json",
        
             "Construction_a15_o170_m9_an80_ar18.json",
             "Construction_a20_o236_m12_an106_ar24.json",
             "Construction_a25_o306_m13_an127_ar31.json",
            ]

instances = ["Construction_a1_o12_m3_an5_ar3_reduced.json",
             "Construction_a3_o80_m10_an10_ar9_reduced.json",
             "Construction_a5_o96_m10_an10_ar10_reduced.json"]



# Options
objective_strategies = ["weighted", "hierarchical", "hierarchical_tolerance" , "single", "pareto"]
pareto_attributes = ["MachineTransportDistance", "WorkerWorkDistance", "MachineUsage", "WorkerUsage"]#, "NonRegularDriverUsage"]


def main():

    for i in instances:

        data = InputData.InputData(i)
        objective_strategy = "hierarchical_tolerance"
        
        if objective_strategy == "pareto":
            number_of_sites = len(data.orders)
            pareto_constructions = range(1,number_of_sites+1)
            pareto_attributes = ["MachineUsage", "WorkerUsage"]

            for pareto_attribute in pareto_attributes:
                pareto_results = []
                pareto_results.append({"Construction Fulfillment": 0, pareto_attribute: 0})

                for pareto_construction in pareto_constructions:
                    
                    optimizer = MIP_Flow.FlowFormulation(data, objective_strategy, pareto_attribute, pareto_construction)
                    MIP_solution, objectives = optimizer.execute()

                    if MIP_solution is not None:

                        feasible = MIP_solution.feasibility_check()

                        if not feasible:
                            raise Exception("Infeasible solution")
                        
                        else:
                            result_row = {}
                            for obj in objectives:
                                result_row[obj["Objective"]] = obj["Value"]
                            pareto_results.append(result_row)

                    else:
                        break

                pareto_results_df = pd.DataFrame(pareto_results)

                print(pareto_results_df)

                pareto_path = Path.cwd().parent / "Data" / "Solution" / data._parent_folder / data.instance / objective_strategy
                pareto_path.mkdir(parents=True, exist_ok=True)

                pareto_results_df.to_csv(pareto_path / f"{pareto_attribute}_pareto_results.csv", index=False)
        
        else:
            optimizer = MIP_Flow.FlowFormulation(data, objective_strategy)
            MIP_solution, objectives = optimizer.execute()

            if MIP_solution is not None:

                feasible = MIP_solution.feasibility_check()

                if not feasible:
                    raise Exception("Infeasible solution")
                
                else:
                    for obj in objectives:
                        print(obj["Objective"], obj["Value"])
            else:
                print("No solution found")

            if feasible:
                optimizer.save_solution_to_file()
                #OutputData.GanttDiagramGenerator(data.instance_filename , data._parent_folder, objective_strategy).create_gantt_diagrams()
            




if __name__ == "__main__":
    main()









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