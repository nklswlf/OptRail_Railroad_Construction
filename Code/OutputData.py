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
        self.number_sites = - 1
        self.route_plan_worker = route_plan_worker
        self.route_plan_machine = route_plan_machine

    def __str__(self) -> str:
        ''' Define the string representation of the solution'''
        return f"Route Plan Worker: {self.route_plan_worker}\nRoute Plan Machine: {self.route_plan_machine}\n"



    def feasibility_check(self):
        ''' Check the feasibility of the solution'''
        print("Checking the feasibility of the solution...")

        for machine_name, route in self.route_plan_machine.items():

            machine_object = next((m for m in self.data.machines if m.name == machine_name), None)
            
            order_item_objects = [next((o for o in self.data.order_items if o.id == order_id), None) for order_id in route]

            # Check if the machine type is correct for the order items in the route
            for order_item in order_item_objects:
                if machine_object.type != order_item.machine_type:
                    #print(f"Machine {machine_name} is not correct assigned to order item {order_item.id}.")
                    return False
                else:
                    #print(f"Machine {machine_name} is wanted in order item {order_item.id}.")
                    pass

            
            # Check if the sequence of the order items is correct
            for order_item_i in order_item_objects:
                for order_item_j in order_item_objects:
                    order_item_i_index = order_item_objects.index(order_item_i)
                    order_item_j_index = order_item_objects.index(order_item_j)

                    

                    if order_item_i_index + 1 == order_item_j_index:

                        order_i = next((order for order in self.data.orders if int(order_item_i.id) in [int(item) for item in order.order_item_ids]), None)
                        order_j = next((order for order in self.data.orders if int(order_item_j.id) in [int(item) for item in order.order_item_ids]), None)
                        
                        distance = self.data.transport_routes[order_i.site_number][order_j.site_number]
                        travel_time = (distance / self.data._transport_speed_kmh)
                        travel_time = timedelta(hours=travel_time)
                        print(f"Travel time between order {order_i.order_number} and order {order_j.order_number} is {travel_time}.")
                        

                        if order_item_i.end_time + travel_time >= order_item_j.start_time:
                            print(f"Order item {order_item_i.id} is not correctly sequenced with order item {order_item_j.id}.")
                            return False
                        else:
                            print(f"Order item {order_item_i.id} is correctly sequenced with order item {order_item_j.id}.")
                            pass

            
                
        
            




        print("Solution is feasible.")
        return True
        





class GanttDiagramGenerator:
    def __init__(self, input_file, parent_folder):
        """
        Initialize the GanttDiagramGenerator with input file and parent folder.
        """
        self.input_file = input_file
        self.parent_folder = parent_folder
        self.instance = input_file.split('Construction_')[1].split('.json')[0]
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Paths for input and output files
        self.input_file_path = os.path.join(
            self.script_dir, "..", "Data", "Instanzen", parent_folder, input_file
        )
        self.output_file_path = os.path.join(
            self.script_dir, "..", "Data", "Solution", parent_folder, self.instance , f"Solution_{input_file}"
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
            self.script_dir, "..", "Data", "Solution", self.parent_folder, self.instance, file_name
        )
        os.makedirs(os.path.dirname(html_file_path), exist_ok=True)
        fig.write_html(html_file_path)
        #fig.show()
