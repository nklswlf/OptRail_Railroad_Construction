# OptRail_Railroad_Construction

This project focuses on the optimization of machine and workforce assignment for railway construction sites across Germany. It was developed as part of my diploma thesis in Industrial Engineering and Management at TU Dresden.

## 🔍 Project Goal

The aim is to assign workers, machines, and equipment (attachments) to fixed construction shifts while optimizing multiple conflicting objectives. The challenge is modeled as a large-scale, multi-objective combinatorial optimization problem.

## 🎯 Objectives

The optimization process considers the following eight objectives:

1. Construction fulfillment (maximize)
2. Transport distance of machines (minimize)
3. Transport distance of attachments (minimize)
4. Work distance for workers (minimize)
5. Violation of preferred/staffed drivers (minimize)
6. Total number of workers used (minimize)
7. Total number of machines used (minimize)
8. Total number of attachments used (minimize)

## 🧠 Methods Used

- **Heuristic Approaches**: Simulated Annealing, NSGA-II  
- **Mathematical Solver**: Gurobi (for MIP baseline)
- **Visualization**: Streamlit-based comparison tool
- **Evaluation**: Pareto front analysis for trade-off comparison
