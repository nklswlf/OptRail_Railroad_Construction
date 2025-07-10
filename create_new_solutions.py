import json
import pandas as pd
from Code.InputData import InputData
from Code.OutputData import Solution
from Code.EvaluationLogic import EvaluationLogic

# === Parameter ===
instance = "Construction_RealLife_2024_7_1_2"


# === Daten einlesen ===
data = InputData(instance_filename=f"{instance}.json", algo="EvalCombined")  # algo-Ordner wird ggf. erstellt
combined_solutions_path = f"{data.solutions_path}/Combined_Solutions_{instance}.json"
with open(combined_solutions_path, "r", encoding="utf-8") as f:
    combined_solutions = json.load(f)

evaluationLogic = EvaluationLogic(data)

# === Alle Lösungen evaluieren ===
results = []

for solution_id, routes in combined_solutions.items():
    print(f"\n🔍 Checking Solution {solution_id}...")
    
    # Keys der Routenpläne in int umwandeln
    def convert_keys_to_int(d):
        return {int(k): v for k, v in d.items()}

    worker_plan = convert_keys_to_int(routes["worker_route_plan"])
    machine_plan = convert_keys_to_int(routes["machine_route_plan"])
    attachment_plan = convert_keys_to_int(routes["attachment_route_plan"])

    
    # Create and evaluate Solution
    sol = Solution(worker_plan, machine_plan, attachment_plan, data)
    for order in data.orders:
        order.status == True
    is_feasible = sol.feasibility_check(verbose=False)
    if not is_feasible:
        print(f"❌ Solution {solution_id} is not feasible. Skipping evaluation.")
    else:
        print(f"✅ Solution {solution_id} is feasible.")

    evaluationLogic.evaluate(sol)

    print(f"Number of finished orders: {sol.number_of_finished_orders}")
    print(f"Number of unrecognized orders: {sol.number_of_unrecognized_orders}")

    # Evaluation wird ggf. automatisch gemacht – falls nicht, kannst du hier z. B. sol.evaluate() aufrufen
    result = {
        "Solution ID": solution_id,
        "Orders": sol.number_of_finished_orders,
        "Order Items": sol.number_of_finished_order_items,
        "Driver Violation": sol.driver_violation,
        "Commute Distance": round(sol.total_commute_distance, 2),
        "Transport Machines": round(sol.total_transport_distance, 2),
        "Transport Attachments": round(sol.total_transport_distance_attachments, 2),
        "Machines": sol.number_of_machines,
        "Workers": sol.number_of_workers,
        "Attachments": sol.number_of_attachments,
    }
    results.append(result)

# === Ergebnisse als DataFrame anzeigen
df_results = pd.DataFrame(results)
df_results.reset_index(drop=True, inplace=True)
df_results.head()
# === Ergebnisse speichern ===
output_file = f"{data.solutions_path}/{instance}_evaluated_solutions.csv"
df_results.to_csv(output_file, index=False)
print(f"\n✅ Results saved to {output_file}")
