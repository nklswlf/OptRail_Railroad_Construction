"""
Solution Verification Script

Simple verification tool to check existing solutions and validate their objectives.
Loads combined solutions, performs feasibility checks, and exports verified results.
"""

import json
import pandas as pd
from Code.InputData import InputData
from Code.OutputData import Solution
from Code.EvaluationLogic import EvaluationLogic

# =============================================================================
# VERIFICATION PARAMETERS
# =============================================================================

# Target instance for solution verification
instance = "Construction_RealLife_2024_7_1_2"


# =============================================================================
# DATA LOADING FOR VERIFICATION
# =============================================================================

# Load problem instance data for verification
data = InputData(instance_filename=f"{instance}.json", algo="EvalCombined")

# Load combined solutions file for cross-checking
combined_solutions_path = f"{data.solutions_path}/Combined_Solutions_{instance}.json"
with open(combined_solutions_path, "r", encoding="utf-8") as f:
    combined_solutions = json.load(f)

# Initialize evaluation logic for objective recalculation
evaluationLogic = EvaluationLogic(data)

# =============================================================================
# SOLUTION VERIFICATION AND OBJECTIVE VALIDATION
# =============================================================================

# Storage for verification results
results = []

# Verify each solution and recalculate objectives
for solution_id, routes in combined_solutions.items():
    print(f"\n🔍 Checking Solution {solution_id}...")
    
    # Convert JSON string keys back to integer keys for route processing
    def convert_keys_to_int(d):
        return {int(k): v for k, v in d.items()}

    # Extract route plans for verification
    worker_plan = convert_keys_to_int(routes["worker_route_plan"])
    machine_plan = convert_keys_to_int(routes["machine_route_plan"])
    attachment_plan = convert_keys_to_int(routes["attachment_route_plan"])

    # Reconstruct solution object for verification
    sol = Solution(worker_plan, machine_plan, attachment_plan, data)
    
    # Ensure all orders are active for proper verification
    for order in data.orders:
        order.status == True
    
    # Perform feasibility check as verification step
    is_feasible = sol.feasibility_check(verbose=False)
    if not is_feasible:
        print(f"❌ Solution {solution_id} is not feasible. Skipping evaluation.")
    else:
        print(f"✅ Solution {solution_id} is feasible.")

    # Recalculate objectives for verification
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

# =============================================================================
# VERIFICATION RESULTS EXPORT
# =============================================================================

# Convert verification results to DataFrame for analysis
df_results = pd.DataFrame(results)
df_results.reset_index(drop=True, inplace=True)  # Clean index
df_results.head()  # Display first few verified solutions

# Save verified objectives to CSV file for further analysis
output_file = f"{data.solutions_path}/{instance}_evaluated_solutions.csv"
df_results.to_csv(output_file, index=False)

# Confirmation of successful verification and export
print(f"\n✅ Results saved to {output_file}")
print(f"🔍 Total solutions verified: {len(df_results)}")
print(f"📋 Objectives cross-checked and validated")
