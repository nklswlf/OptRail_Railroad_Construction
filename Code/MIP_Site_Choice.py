import gurobipy as gp
from gurobipy import GRB
from InputData import *
from OutputData import *



class SiteChoiceMIP:
    def __init__(self, I, c, capacity):
        self.I = I
        self.c = c
        self.capacity = capacity
        self.model = gp.Model("SimpleMIP")
        # Create a variable x[i] for each element in I
        self.x = self.model.addVars(I, vtype=GRB.CONTINUOUS, name="x")
        # Set objective: maximize sum(c[i] * x[i])
        self.model.setObjective(gp.quicksum(c[i] * self.x[i] for i in I), GRB.MAXIMIZE)
        # Add constraint: sum(x[i]) <= capacity
        self.model.addConstr(gp.quicksum(self.x[i] for i in I) <= capacity, name="capacity_constraint")


    
    def solve(self):
        self.model.optimize()
        if self.model.status == GRB.OPTIMAL:
            print("Optimal solution found:")
            for i in self.I:
                print(f"x[{i}] = {self.x[i].X}")
        else:
            print("No optimal solution found. Status:", self.model.status)