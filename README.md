# OptRail_Railroad_Construction

This project focuses on the optimization of machine and workforce assignment for railway construction sites across Germany. It was developed as part of my diploma thesis in Industrial Engineering and Management at TU Dresden.

## 🔍 Project Goal

The aim is to assign workers, machines, and equipment (attachments) to fixed construction shifts while optimizing multiple conflicting objectives. The challenge is modeled as a large-scale, multi-objective combinatorial optimization problem.

## 🎯 Optimization Objectives

The optimization model aims to balance and improve multiple competing objectives relevant to large-scale construction planning. Specifically, it considers the following eight goals:

1. **Maximize** construction site fulfillment  
2. **Minimize** transport distances of machines  
3. **Minimize** transport distances of attachments  
4. **Minimize** commuting distances for workers  
5. **Minimize** violations of preferred (staffed) driver assignments  
6. **Minimize** the total number of workers deployed  
7. **Minimize** the total number of machines used  
8. **Minimize** the total number of attachments utilized

## 🧠 Methods Used

- **Mathematical Solver**: Gurobi (for MIP baseline)
- **Heuristic Approaches**: Constructive Greedy --> Pareto Simulated Annealing 
- **Visualization**: Streamlit-based comparison tool
- **Evaluation**: Pareto front analysis for trade-off comparison

## 📁 Project Files Overview

| File                         | Description                                                                 |
|------------------------------|-----------------------------------------------------------------------------|
| `Solver.py`                 | Main entry point to coordinate the entire optimization process              |
| `MIP_Flow.py`, `MIP_Upper_Bound.py` | Variants and extensions of the base MIP formulation                 |
| `ConstructiveHeuristic.py`  | Builds initial feasible solutions using greedy heuristics                   |
| `ImprovementAlgorithm.py`   | Applies metaheuristics (e.g., Simulated Annealing) to improve solutions     |
| `Neighborhood.py`           | Defines neighborhood operators for local search and metaheuristics           |
| `EvaluationLogic.py`        | Computes objective values for each solution                                 |
| `InputData.py`              | Handles data import and preprocessing                                       |
| `OutputData.py`             | Writes solutions, objective values, and keeps pareto archive                |
| `main_math_model.py`        | Script to manually launch mathematical solver                               |
| `main.py`                   | Script to manually launch metaheuristic optimization and log experiments    |
