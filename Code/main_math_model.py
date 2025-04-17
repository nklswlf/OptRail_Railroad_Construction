import InputData
import OutputData
import MIP_Flow
import pandas as pd
from pathlib import Path
import MIP_UB as MIP_UB
import OutputData



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





def experiments():

    bound_technique = "MIP"

    instances = ["Construction_a3_o80_m10_an10_ar9_reduced.json",
                "Construction_a5_o96_m10_an10_ar10_reduced.json",
                "Construction_a10_o107_m5_an57_ar12.json",
                "Construction_a15_o170_m9_an80_ar18.json",
                "Construction_a20_o236_m12_an106_ar24.json",
                "Construction_a25_o306_m13_an127_ar31.json",
                "Construction_a30_o355_m18_an148_ar42.json",
                "Construction_a40_o476_m22_an215_ar51.json",
                "Construction_a50_o578_m28_an276_ar66.json"]
    
    dict_upper_bound = dict()


    for instance in instances:
        
        data = InputData.InputData(instance)

        if bound_technique == "LP":
            optimizer = MIP_UB.UpperBound(data, bound_technique=bound_technique)
        elif bound_technique == "MIP":
            optimizer = MIP_UB.UpperBound(data, bound_technique=bound_technique)

        obj_value, order_count, order_item_count, runtime, status, gap = optimizer.execute()

        dict_upper_bound[instance] = [obj_value, order_count, order_item_count, runtime, status, gap]


    df_upper_bound = pd.DataFrame.from_dict(dict_upper_bound,orient="index",columns=["Objective Value", "Order Count", "Order Item Count", "Runtime (s)", "Status", "Gap"])
    df_upper_bound.index.name = "Instance"
    upper_bound_path = Path.cwd().parent / "Data" / "Solution_math_model" / "Upper_Bound"
    upper_bound_path.mkdir(parents=True, exist_ok=True)
    df_upper_bound.to_csv(upper_bound_path / f"upper_bound_{bound_technique}.csv", index=False)
    print(df_upper_bound)



def single_run():
    instance = "Construction_a20_o236_m12_an106_ar24.json"
    strategy = "LP"

    data = InputData.InputData(instance)
    
    if strategy == "MIP":
        optimizer = MIP_UB.UpperBound(data,bound_technique='MIP' ,upper_bound="all")
    elif strategy == "LP":
        optimizer = MIP_UB.UpperBound(data,bound_technique='LP' ,upper_bound="all")

    solution = optimizer.execute()

    print(f"\nObjective value: {solution[0]}")
    print(f"Orders: {solution[1]}")
    print(f"Order items: {solution[2]}")
    print(f"Order List: {solution[3]}")
    print(f"Length of Order List: {len(solution[3])}")

    if strategy == "MIP":
        route = optimizer.extract_routes_from_solution()
        Solution = OutputData.Solution(route[1], route[0], route[2], data)
        feasible = Solution.feasibility_check()
        if not feasible:
            raise Exception(f"Infeasible solution for instance {instance}")
        else:
            print("Feasible solution")
    


if __name__ == "__main__":
    #experiments()
    single_run()




'''
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
    
    
    objective_strategies = ["hierarchical"]
    number_of_objectives = [3]

    
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

'''