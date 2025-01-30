from InputData import *
import json
import pandas as pd
import plotly.express as px
import os
from datetime import timedelta


class Solution:

    def __init__(self, route_plan_worker:dict, route_plan_machine:dict, data:InputData):
        ''' Define the attributes for solution'''

        self.data = data
        self.route_plan_worker = route_plan_worker
        self.route_plan_machine = route_plan_machine
        
        self.finished_orders = []
        self.semifinished_orders = []
        self.not_started_orders = []
        self.share_finished_orders = -0
        self.number_of_finished_orders = -0
        self.number_of_finished_order_items = -0

        self.transport_distance_per_machine = {}
        self.total_transport_distance = -0
        self.commute_distance_per_worker = {}
        self.total_commute_distance = -0
        self.number_of_workers = -0
        self.number_of_machines = -0
        self.driver_violation = -0
        self.worker_work_time = {}
        self.machine_utilization_time = {}



    def __str__(self) -> str:
        ''' Define the string representation of the solution'''
        return (f"Number of finished orders: {self.number_of_finished_orders}\n"
                f"Number of finished order items: {self.number_of_finished_order_items}\n"
                f"Driver violation: {self.driver_violation}\n"
                f"Commute distance: {round(self.total_commute_distance, 2)}\n"
                f"Transport distance: {round(self.total_transport_distance, 2)}\n"
                f"Number of workers: {self.number_of_workers}\n"
                f"Number of machines: {self.number_of_machines}")
    

    def repair_solution(self):
        ''' Repair the solution by deleting all order items of semi-finished orders from the route plans'''
        ## OR
        ''' Repair the solution with heuristic or mathamatical optimization by reassigning the order items of semi-finished orders to the route plans'''

        ## TO DO: Implement the repair solution method
        pass


    def create_output_file_greedy(self, time_for_data_loading, time_for_construction ,order_item_attractiveness_technique:str, machine_attractiveness_technique:str):
        ''' Create the output file for the greedy solution for comparing different strategies'''

        # Create a dictionary for the solution
        solution = {
            "Instance": self.data.instance,
            "Time_for_data_loading": time_for_data_loading,
            "Time_for_construction": time_for_construction,
            "Order_item_attractiveness_technique": order_item_attractiveness_technique,
            "Machine_attractiveness_technique": machine_attractiveness_technique,
            "Number_of_finished_orders": self.number_of_finished_orders,
            "Number_of_semifinished_orders": len(self.semifinished_orders),
            "Number_of_not_started_orders": len(self.not_started_orders),
            "Number_of_finished_order_items": self.number_of_finished_order_items,
            "Driver_violation": self.driver_violation,
            "Commute_distance": round(self.total_commute_distance, 2),
            "Transport_distance": round(self.total_transport_distance, 2),
            "Number_of_workers": self.number_of_workers,
            "Number_of_machines": self.number_of_machines,
            "Sum_dynamic_precentage": round(sum([order.dynamic_percentage for order in self.data.orders]),4),
            "Dynamic_percentage": [round(order.dynamic_percentage,4) for order in self.data.orders],
            "Worker_route_plan": self.route_plan_worker,
            "Machine_route_plan": self.route_plan_machine
        }


        print("\nCreating output file...")

        # Define the base directory (parent of the 'Code' directory)
        base_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Build the output file path
        output_file_path = os.path.join(
            base_directory, "Data", "Solution", "Greedy_Testing",  self.data._parent_folder, self.data.instance , f"OI_{order_item_attractiveness_technique}_M_{machine_attractiveness_technique}_{self.data.instance}.json"
        )

        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        # Write the solution to the JSON file
        with open(output_file_path, 'w') as file:
            json.dump(solution, file, indent=4)

        print(f"Solution saved to: {output_file_path}")

        

    

    def feasibility_check(self, verbose=False):
        ''' Check the feasibility of the solution'''
        if verbose:
            print("\nChecking the feasibility of the solution...")

        # ========================
        # 1. Order Item Feasibility
        # ========================
        if verbose:
            print("\nChecking if the assigned order items are present in both route plans...")

        # Check if all order items in machine route are present in worker route
        for machine_route_order_items in self.route_plan_machine.values():
            for order_item in machine_route_order_items:
                if not any(order_item in worker_route_order_items for worker_route_order_items in self.route_plan_worker.values()):
                    if verbose:
                        print(f"Order item {order_item} is not present in the worker route.")
                    return False

        # Check if all order items in worker route are present in machine route
        for worker_route_order_items in self.route_plan_worker.values():
            for order_item in worker_route_order_items:
                if not any(order_item in machine_route_order_items for machine_route_order_items in self.route_plan_machine.values()):
                    if verbose:
                        print(f"Order item {order_item} is not present in the machine route.")
                    return False

        # Check that no order item is assigned to more than one worker
        for worker_id, route in self.route_plan_worker.items():
            for order_item in route:
                if sum(order_item in worker_route for worker_route in self.route_plan_worker.values()) > 1:
                    if verbose:
                        print(f"Order item {order_item} is assigned to more than one worker.")
                    return False

        # Check that no order item is assigned to more than one machine
        for machine_id, route in self.route_plan_machine.items():
            for order_item in route:
                if sum(order_item in machine_route for machine_route in self.route_plan_machine.values()) > 1:
                    if verbose:
                        print(f"Order item {order_item} is assigned to more than one machine.")
                    return False

        if verbose:
            print("The assigned order items are present in both route plans.")

        # ========================
        # 2. Machine Route Feasibility
        # ========================
        for machine_name, route in self.route_plan_machine.items():
            if verbose:
                print(f"\nChecking route for machine {machine_name}...")

            machine_object = next((m for m in self.data.machines if m.id == machine_name), None)
            order_item_objects = [next((o for o in self.data.order_items if o.id == order_id), None) for order_id in route]

            # Check if the machine type is correct for the order items in the route
            for order_item in order_item_objects:
                if machine_object.type != order_item.machine_type:
                    if verbose:
                        print(f"Machine {machine_name} is not correct assigned to order item {order_item.id}.")
                    return False

            # Check if the sequence of the order items is correct with start, end and travel times
            for order_item_i in order_item_objects:
                for order_item_j in order_item_objects:
                    order_item_i_index = order_item_objects.index(order_item_i)
                    order_item_j_index = order_item_objects.index(order_item_j)
                    if order_item_i_index + 1 == order_item_j_index:
                        order_i = next((order for order in self.data.orders if int(order_item_i.id) in [int(item) for item in order.order_item_ids]), None)
                        order_j = next((order for order in self.data.orders if int(order_item_j.id) in [int(item) for item in order.order_item_ids]), None)
                        distance = self.data.transport_routes[order_i.site_number][order_j.site_number]
                        travel_time_double = (distance / self.data._transport_speed_kmh)
                        travel_time = timedelta(hours=travel_time_double)
                        if order_item_i.end_time + travel_time >= order_item_j.start_time:
                            if verbose:
                                print(f"Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                            return False

            if verbose:
                print(f"Route for machine {machine_name} is feasible.")

        # ========================
        # 3. Worker Route Feasibility
        # ========================
        for worker_id, route in self.route_plan_worker.items():
            if verbose:
                print(f"\nChecking route for worker {worker_id}...")

            worker_object = next((w for w in self.data.workers if w.personal_number == worker_id), None)
            order_item_objects = [next((o for o in self.data.order_items if o.id == order_id), None) for order_id in route]

            # Check if the worker qualifications are correct for the order items in the route
            for order_item in order_item_objects:
                if order_item.worker_qualifications:
                    if not set(order_item.worker_qualifications).issubset(set(worker_object.qualifications)):
                        if verbose:
                            print(f"Worker {worker_id} (Qualifications: {worker_object.qualifications}) does not have the correct qualifications for order item {order_item.id} (Qualifications: {order_item.worker_qualifications}).")
                        return False

            # Check if the sequence of the order items is correct with start, end and break times
            for order_item_i in order_item_objects:
                for order_item_j in order_item_objects:
                    order_item_i_index = order_item_objects.index(order_item_i)
                    order_item_j_index = order_item_objects.index(order_item_j)
                    if order_item_i_index + 1 == order_item_j_index:
                        break_time_double = self.data._hours_between_shifts
                        break_time = timedelta(hours=break_time_double)
                        if order_item_i.end_time + break_time >= order_item_j.start_time:
                            if verbose:
                                print(f"Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                            return False

            # Check if the worker does not work more than 5 consecutive night shifts
            checked_indices = set()
            for i, order_item_i in enumerate(order_item_objects):
                if i in checked_indices:
                    continue
                if order_item_i.start_time.hour >= self.data._day_and_night_shift_boundary:
                    night_shifts = 1
                    for j in range(i + 1, len(order_item_objects)):
                        order_item_j = order_item_objects[j]
                        time_difference = (order_item_j.start_time - order_item_i.start_time).days
                        if time_difference == night_shifts:
                            if order_item_j.start_time.hour >= self.data._day_and_night_shift_boundary:
                                night_shifts += 1
                                checked_indices.add(j)
                            else:
                                break
                        else:
                            break
                    if night_shifts > self.data._max_consecutive_night_shifts:
                        if verbose:
                            print(f"Worker {worker_id} has more than {self.data._max_consecutive_night_shifts} consecutive night shifts ({night_shifts}).")
                        return False
                    checked_indices.add(i)

            # Check if the worker does not work more than 10 shifts in 14 days
            for i, order_item_i in enumerate(order_item_objects):
                window_start = order_item_i.start_time.date()
                window_end = window_start + self.data._time_period_for_max_shifts
                shift_count = 0
                for order_item_j in order_item_objects:
                    if window_start <= order_item_j.start_time.date() < window_end:
                        shift_count += 1
                if shift_count > self.data._max_shifts_in_time_period:
                    if verbose:
                        print(f"Worker {worker_id} has more than {self.data._max_shifts_in_time_period} shifts ({shift_count}) within the {self.data._time_period_for_max_shifts}-day period starting on {window_start}.")
                    return False

            # Check if the worker does not work more than 160 hours in a month
            total_duration_hours = sum(order_item.duration for order_item in order_item_objects)
            if total_duration_hours > self.data._max_working_hours:
                if verbose:
                    print(f"Worker {worker_id} exceeds the maximum allowed total working hours ({self.data._max_working_hours} hours) with {total_duration_hours:.2f} hours.")
                return False

            if verbose:
                print(f"Route for worker {worker_id} is feasible.")

        if verbose:
            print("\nFeasibility check completed. Solution is feasible.")
        return True


       

class SolutionPool:
    ''' Class for creating lits objects containing solution objects'''

    def __init__(self):
        ''' Create an empty list for the solutions'''
        self.Solutions = []
        

    def AddSolution(self, newSolution:Solution) -> None:
        ''' Add a new solution to the solution pool'''
        self.Solutions.append(newSolution)

    def GetHighestProfitSolution(self) -> Solution:
        ''' Sort all the solutions in regard to their makespan and return the solution with the lowest makespan'''
        self.Solutions.sort(key=lambda solution: (solution.TotalProfit, solution.WaitingTime), reverse=True) # sort solutions according to Profit and waiting time

        return self.Solutions[0]
    
    def GetHighestWaitingTimeSolution(self) -> Solution:
        ''' Sort all the solutions in regard to their makespan and return the solution with the lowest makespan'''
        self.Solutions.sort(key=lambda solution: (solution.WaitingTime), reverse=True) # sort solutions according to Profit and waiting time

        return self.Solutions[0]




class GanttDiagramGenerator:
    def __init__(self, input_file, parent_folder, optimization_strategy, number_of_objectives):
        """
        Initialize the GanttDiagramGenerator with input file and parent folder.
        """
        self.input_file = input_file
        self.parent_folder = parent_folder
        self.instance = input_file.split('Construction_')[1].split('.json')[0]
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.optimization_strategy = optimization_strategy
        self.number_of_objectives = number_of_objectives

        # Paths for input and output files
        self.input_file_path = os.path.join(
            self.script_dir, "..", "Data", "Instanzen", parent_folder, input_file
        )
        self.output_file_path = os.path.join(
            self.script_dir, "..", "Data", "Solution", parent_folder, self.instance, f"{self.number_of_objectives}_Objectives" ,self.optimization_strategy, f"Solution_{input_file}"
        )

        # Load input and output data
        self.input_data = self._load_json(self.input_file_path)
        self.output_data = self._load_json(self.output_file_path)

    @staticmethod
    def _load_json(file_path):
        """
        Load JSON data from the given file path.
        """
        with open(file_path, 'r') as file:
            return json.load(file)

    def create_gantt_diagrams(self):
        """
        Generate Gantt diagrams for both worker shifts and machine assignments.
        """
        print(f"Creating Gantt diagrams for instance {self.instance}...")

        self._create_shift_plan()
        self._create_machine_plan()

        print(f"Gantt diagrams have been created.\n")

    def _create_shift_plan(self):
        """
        Create a Gantt diagram for worker shifts based on input and output data.
        """
        worker_assignments = self.output_data['Arbeiterzuweisung']
        unassigned_workers = [
            w['Name'] for w in self.input_data['Arbeiter'] if w['Name'] not in worker_assignments
        ]

        # Build DataFrame for worker shifts
        df = pd.DataFrame([
            {'Arbeiter': worker, 'Start': shift['Start'], 'Ende': shift['Ende'], 'ID': shift['ID']}
            for worker, shifts in worker_assignments.items() for shift in shifts
        ])

        # Determine shift type (early or late shift) based on start time
        df['Shift_Type'] = df['Start'].apply(
            lambda start: 'Early Shift' if pd.to_datetime(start).hour < 14 else 'Late Shift'
        )

        # Add site number based on task ID
        df['Site_Number'] = df['ID'].apply(self._get_site_number)

        # Create Gantt chart
        fig = px.timeline(
            df, x_start="Start", x_end="Ende", y="Arbeiter", color="Shift_Type",
            hover_data={'Shift_Type': False, 'Site_Number': True, 'Start': True, 'Ende': True, 'Arbeiter': False},
            category_orders={"Arbeiter": sorted(df["Arbeiter"].unique(), key=lambda x: int(x.split("_")[1]), reverse=True)},
            color_discrete_map={"Early Shift": "lightblue", "Late Shift": "lightcoral"}
        )
        fig.update_layout(
            title=f"Worker Assignments with Site Information for Instance {self.instance}",
            xaxis_title="Date", yaxis_title="Worker"
        )

        # Save and show the chart
        self._save_chart(fig, f"Shift_Plan_{self.instance}.html")
        print(f"Workers without shifts: {unassigned_workers}")

    def _create_machine_plan(self):
        """
        Create a Gantt diagram for machine and attachment assignments.
        """
        machine_assignments = self.output_data['Maschinenzuweisung']
        attachment_assignments = self.output_data.get('Anbaugeraetzuweisung', {})
        unassigned_machines = [
            m['Name'] for m in self.input_data['Maschinen'] if m['Name'] not in machine_assignments
        ]

        # Build DataFrames for machines and attachments
        machine_rows = [
            {'Name': machine, 'Start': usage['Start'], 'Ende': usage['Ende'], 'ID': usage['ID'], 'Type': 'Machine'}
            for machine, usages in machine_assignments.items() for usage in usages
        ]
        attachment_rows = [
            {'Name': attachment, 'Start': usage['Start'], 'Ende': usage['Ende'], 'ID': usage['ID'], 'Type': 'Attachment'}
            for attachment, usages in attachment_assignments.items() for usage in usages
        ]
        df_combined = pd.concat([pd.DataFrame(machine_rows), pd.DataFrame(attachment_rows)])

        # Add site number based on task ID
        df_combined['Site_Number'] = df_combined['ID'].apply(self._get_site_number)

        # Create Gantt chart
        fig = px.timeline(
            df_combined, x_start="Start", x_end="Ende", y="Name", color="Site_Number",
            hover_data={'Site_Number': False, 'Start': True, 'Ende': True, 'Type': True, 'Name': False},
            category_orders={
                "Name": sorted(df_combined["Name"].unique(), reverse=True),
                "Site_Number": sorted(df_combined["Site_Number"].unique(), key=lambda x: int(x))
            }
        )
        fig.update_layout(
            title=f"Machine and Attachment Assignments by Site for Instance {self.instance}",
            xaxis_title="Date", yaxis_title="Name"
        )

        # Save and show the chart
        self._save_chart(fig, f"Machine_Plan_{self.instance}.html")
        print(f"Machines without assignments: {unassigned_machines}")

    def _get_site_number(self, task_id):
        """
        Get the site number for a given task ID.
        """
        for task in self.input_data['Bestellpositionen']:
            if task['ID'] == task_id:
                return task['Auftragsnummer']
        return None

    def _save_chart(self, fig, file_name):
        """
        Save the Gantt chart as an HTML file and display it.
        """

        html_file_path = os.path.join(
            self.script_dir, "..", "Data", "Solution", self.parent_folder, self.instance, f"{self.number_of_objectives}_Objectives" , self.optimization_strategy,file_name
        )
        os.makedirs(os.path.dirname(html_file_path), exist_ok=True)
        fig.write_html(html_file_path)
        #fig.show()
