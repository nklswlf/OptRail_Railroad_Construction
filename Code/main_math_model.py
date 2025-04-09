import InputData
import OutputData
import MIP_Flow
import pandas as pd
from pathlib import Path
import MIP_Upper_Bound



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



def upper_bound():

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
    
    instances = ["Construction_a25_o306_m13_an127_ar31.json"]
    
    for instance in instances:

        upper_bound = "worker"
        upper_bound = "machine"
        upper_bound = "both"
        
        data = InputData.InputData(instance)

        optimizer = MIP_Upper_Bound.UpperBound(data, upper_bound)

        site_fulfillment = optimizer.execute()

        print(f"Site fulfillment for instance {instance} and upper bound {upper_bound}:")
        print(site_fulfillment)
        print(instance)

    



def main():
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
    
    instances = ["Construction_a10_o107_m5_an57_ar12.json"]
    
    
    objective_strategies = ["hierarchical", "hierarchical_tolerance"]
    number_of_objectives = [6, 3, 4, 5]

    


    for number_obj in number_of_objectives:
        for instance in instances:
            for objective_strategy in objective_strategies:

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
                       #OutputData.GanttDiagramGenerator(data.instance_filename, data._parent_folder, objective_strategy, number_obj).create_gantt_diagrams()
                
                else:
                    print(f"No solution found for instance {instance}")

                    
                    


if __name__ == "__main__":
    #TestInputData()
    #pareto()
    #main()
    upper_bound()








def pareto():
    instances = ["Construction_a3_o80_m10_an10_ar9_reduced.json"]
    pareto_attributes = ["MachineTransportDistance", "WorkerWorkDistance", "MachineUsage", "WorkerUsage", "NonRegularDriverUsage"]
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

            pareto_path = Path.cwd().parent / "Data" / "Solution_math_model" / data._parent_folder / data.instance / objective_strategy
            pareto_path.mkdir(parents=True, exist_ok=True)

            pareto_results_df.to_csv(pareto_path / f"{pareto_attribute}_pareto_results.csv", index=False)