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

- **Mathematical Solver**: Gurobi (for MIP baseline)
- **Heuristic Approaches**: Constructive Greedy --> Pareto Simulated Annealing 
- **Visualization**: Streamlit-based comparison tool
- **Evaluation**: Pareto front analysis for trade-off comparison

## 📁 Project Files Overview

| File                         | Description                                                                 |
|------------------------------|-----------------------------------------------------------------------------|
| `Solver.py`                 | Main entry point to coordinate the entire optimization process              |
| `main_math_model.py`        | Defines the Mixed-Integer Programming (MIP) model using Gurobi              |
| `MIP_Flow.py`, `MIP_Upper_Bound.py` | Variants and extensions of the base MIP formulation                 |
| `ConstructiveHeuristic.py`  | Builds initial feasible solutions using greedy heuristics                   |
| `ImprovementAlgorithm.py`   | Applies metaheuristics (e.g., Simulated Annealing) to improve solutions     |
| `Neighborhood.py`           | Defines neighborhood operators for local search and metaheuristics           |
| `EvaluationLogic.py`        | Computes objective values for each solution                                 |
| `InputData.py`              | Handles data import and preprocessing                                       |
| `OutputData.py`             | Writes solutions, objective values, and keeps pareto archive                |
| `main.py`                   | Script to manually launch optimization and log experiments                  |

> 🛠 Note: This repository is currently private and contains anonymized data and experimental code structures used during thesis development.
