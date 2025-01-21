import json
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime


class InputData:
    '''Class for creating Data objects based on formatted JSON Files containing the information of orders, machines, workers, attachments, and routes'''

    def __init__(self, instance_filename: str) -> None:
        '''
        Initialize the InputData object with paths to the JSON file.

        :param instance_filename: Name of the JSON file containing the data.
        '''
        self.instance_filename = instance_filename
        self.instance = instance_filename.split('Construction_')[1].split('.json')[0]
        self._data_path, self._parent_folder = self._find_instance_file()
        

        # Default values for Occupational Safety
        self._consecutive_night_shifts = 5 # Max consecutive night shifts
        self._max_shifts_in_time_period = 10 # Max shifts in a time period
        self._time_period_for_max_shifts = 14 # Time period for max shifts in days
        self._max_working_hours = 160 # Max working hours in the full planning horizon
        self._day_and_night_shift_boundary = 12 # Start before 12 is day shift, after 12 is night shift

        # Default values for Machine and Worker characteristics
        self._seconds_a_day = 86400  # Number of seconds in a day
        self._transport_speed_kmh = 70  # Machine transport speed (km/h)
        self._hours_between_shifts = 9  # Rest period between shifts in hours

        # Default values for costs
        self._construction_revenue = 1000000  # Imaginary revenue for the construction project
        self._machine_fixed_cost = 9000  # Fixed cost for using a machine in a month / renting price per machine in a month
        self._worker_fixed_cost = 4800  # Fixed cost for using a worker / salary + costs per worker in a month
        self._penalty_cost_non_regular_driver = (self._worker_fixed_cost/20) * 0.2  # 48 euro per shift since 20 shifts per month and 20% of the cost
        self._worker_travel_cost_per_km = 0.5  # Travel cost per km for a worker
        self._machine_transport_cost_per_km = 1.6  # Transport cost per km for a machine


        self._load_data()

        self.create_priorities_orders()

        # Dynamic dictionary for planned shifts for greedy algorithm
        self.planned_shifts_worker = dict()
        self.planned_shifts_machine = dict()
        for order in self.orders:
            self.planned_shifts_worker[order] = list()
            self.planned_shifts_machine[order] = list()


        
    def create_priorities_orders(self):
        """
        Generate priorities for all orders based on multiple criteria.

        This function calculates ranks for different parameters (e.g., order items, machine types)
        and combines them into an overall priority score.
        """
        # 1. Calculate rank for order_item_count (fewer items are better)
        self.calculate_rank(
            self.orders, 
            lambda order: len(order.order_item_ids), 
            "order_item_count"
        )

        # 2. Calculate rank for machine_type_count (fewer machine types are better)
        self.calculate_rank(
            self.orders, 
            lambda order: len(set(
                item.machine_type for item in self.order_items if item.order_number == order.order_number
            )), 
            "machine_type_count"
        )

        # 3. Calculate rank for regular_driver_count (more regular drivers are better)
        machine_types = {
            order.order_number: set(
                item.machine_type for item in self.order_items if item.order_number == order.order_number
            )
            for order in self.orders
        }
        possible_regular_drivers = {
            order.order_number: {
                driver for machine in self.machines
                if machine.type in machine_types[order.order_number]
                for driver in machine.default_drivers
            }
            for order in self.orders
        }
        self.calculate_rank(
            self.orders, 
            lambda order: len(possible_regular_drivers[order.order_number]), 
            "regular_driver_count", 
            reverse=True
        )

        # 4. Calculate rank for worker_distance (shorter distances are better)
        worker_distances = {
            order.order_number: sum(
                self.work_routes[worker.personal_number][order.site_number]
                for worker in self.workers
            ) / len(self.workers)
            for order in self.orders
        }
        self.calculate_rank(
            self.orders, 
            lambda order: worker_distances[order.order_number], 
            "worker_distance"
        )

        # 5. Calculate rank for transport_distance (shorter distances are better)
        transport_distances = {
            order.order_number: sum(
                self.transport_routes[order.site_number][site]
                for site in range(len(self.transport_routes))
            ) / len(self.transport_routes)
            for order in self.orders
        }
        self.calculate_rank(
            self.orders, 
            lambda order: transport_distances[order.order_number], 
            "transport_distance"
        )

        # 6. Calculate rank for worker_qualification_count (fewer qualifications are better)
        worker_qualifications = {
            order.order_number: set(
                qualification for item in self.order_items
                if item.order_number == order.order_number
                for qualification in item.worker_qualifications
            )
            for order in self.orders
        }
        self.calculate_rank(
            self.orders, 
            lambda order: len(worker_qualifications[order.order_number]), 
            "worker_qualification_count"
        )

        # 7. Calculate the overall priority score
        for order in self.orders:
            order._priority["overall"] = sum(order._priority.values())
        self.calculate_rank(
            self.orders, 
            lambda order: order._priority["overall"], 
            "overall"
        )

        # 8. Add overall priority score to each order_item in the order
        for order in self.orders:
            for item in self.order_items:
                if item.order_number == order.order_number:
                    item._priority = order._priority["overall"]



        #for order in self.orders:
        #    self.create_priorities_machines(order)

        '''
        # Debug-Ausgabe
        print("Order Priorities:")
        for order in self.orders:
            print(f"Order Number: {order.order_number}, Priority: {order.priority}")
        
        
        for order in self.orders:
            print(f"Order Number: {order.order_number}, Machine Priority: {order.machine_priority}")
        '''

        



    def create_priorities_machines(self, order):
        """
        Calculate the priority for each machine for every order.
        """

        # 1. Berechne die Anzahl der Order Items, die jede Maschine verarbeiten kann
        machine_order_items = {
            machine.id: sum(
                1 for item in self.order_items
                if item.order_number == order.order_number and item.machine_type == machine.type
            )
            for machine in self.machines
        }

        # Entferne Maschinen mit einer Summe von 0
        machine_order_items = {machine_id: count for machine_id, count in machine_order_items.items() if count > 0}

        print(f"Order Number: {order.order_number}")
        print(f"Filtered Machine Order Items: {machine_order_items}")

        # 2. Sortiere nur die Maschinen, die in machine_order_items vorhanden sind
        sorted_machines = sorted(
            (machine for machine in self.machines if machine.id in machine_order_items),
            key=lambda machine: machine_order_items[machine.id],
            reverse=True
        )

        # 3. Berechne die Prioritäten für Maschinen
        current_rank = 1
        last_value = None
        machine_order_items_priority = {}
        for i, machine in enumerate(sorted_machines):
            value = machine_order_items[machine.id]
            if value != last_value:
                current_rank = i + 1
                last_value = value
            machine_order_items_priority[machine.id] = current_rank

        print(f"Machine Priority: {machine_order_items_priority}")




        # rank for machine_order_items (more items are better) and add it to the dictionary self._machine_priority
        # dont use the function calculate_rank, because we need machines not orders
        #sorted_machines = sorted(self.machines, key=lambda machine: machine_order_items[machine.id], reverse=True)
        #current_rank = 1
        #last_value = None
        # add to the dictionary self._machine_priority
        #for i, machine in enumerate(sorted_machines):
        #    value = machine_order_items[machine.id]
        #    if value != last_value:
        #        current_rank = i + 1
        #        last_value = value
        #    order._machine_priority[machine.id] = current_rank





    def calculate_rank(self, orders, key_func, rank_name, reverse=False):
        """
        Calculate the rank for orders based on a key function.

        Parameters:
            orders (list): List of order objects.
            key_func (function): Function to determine the key value for ranking.
            rank_name (str): The name of the rank attribute to store (e.g., 'order_item_count').
            reverse (bool): Whether to sort in descending order (default: False).
        """
        sorted_orders = sorted(orders, key=key_func, reverse=reverse)
        current_rank = 1
        last_value = None

        for i, order in enumerate(sorted_orders):
            value = key_func(order)
            if value != last_value:
                current_rank = i + 1
                last_value = value
            order._priority[rank_name] = current_rank


        

    def _find_instance_file(self) -> tuple[str, str]:
        '''
        Recursively search for the instance file in the Data/Instanzen directory
        and store the parent folder where the file is found.

        :param instance_filename: Name of the file to search for.
        :return: A tuple containing the absolute path to the found file and the parent folder name.
        :raises FileNotFoundError: If the file is not found in the directory.
        '''
        base_path = Path.cwd().parent / "Data" / "Instanzen"
        for file_path in base_path.rglob(self.instance_filename):  # Recursively search for the file
            return str(file_path.resolve()), file_path.parent.name  # Return file path and parent folder name

        raise FileNotFoundError(f"File '{self.instance_filename}' not found in directory '{base_path}'.")



    def _load_data(self) -> None:
        ''' Load data from the JSON file and initialize lists of objects. '''
        with open(self._data_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            
            # Instance metadata
            self._start_date = datetime.fromisoformat(data.get("Start", "1970-01-01T00:00:00"))
            self._end_date = datetime.fromisoformat(data.get("Ende", "1970-01-01T00:00:00"))
            self._contains_durations = data.get("EnthaeltDauern", False)

            # Load each data category part 1
            self._orders = [Order(order) for order in data.get("Auftraege", [])]
            self._order_items = [OrderItem(item) for item in data.get("Bestellpositionen", [])]
            self._attachments = [Attachment(attachment) for attachment in data.get("Anbaugeraete", [])]
            self._workers = [Worker(worker) for worker in data.get("Arbeiter", [])]
            self._machines = [Machine(machine) for machine in data.get("Maschinen", [])]

            # Convert ArbeitswegeString and TransportwegeString to 2D lists
            self._transport_routes = self._convert_square_2d_list(data.get("TransportwegeString", {}))
            self._work_routes = self._convert_rectangular_2d_list(data.get("ArbeitswegeString", {}))
            # Convert distance matrix from order to order item
            self._transport_routes_order_item = self._convert_from_order_to_order_item(self._transport_routes, "transport")
            self._work_routes_order_item = self._convert_from_order_to_order_item(self._work_routes, "work")

            # Add data to workers and machines (predessors, successors, possible order items)
            for machine in self.machines:
                machine.add_data(self)
            for worker in self.workers:
                worker.add_data(self)
                #print(f"Worker {worker.personal_number} - Total items in list:", len(worker._possible_order_items))
                # Listen-Ansatz: Gesamtanzahl aller Elemente
                successors = list()
                predecessors = list()
                print(f"\nDictionary Worker {worker.personal_number}")
                for key in worker._successors.keys():
                    successors.append(f"{key.id} : {[item.id for item in worker._successors[key]]}")
                    predecessors.append(f"{key.id} : {[item.id for item in worker._predecessors[key]]}")

                print(f"\nSuccessors: {successors}")
                print(f"\nPredecessors: {predecessors}")
            

            
            print(f"Data loaded from '{self.instance_filename}' in folder '{self._parent_folder}'.")

    def _convert_from_order_to_order_item(self, routes_matrix, route_type):
        
        final_routes_matrix = []

        if route_type == "transport":
            for order_item_1 in self.order_items:
                row = []
                for order_item_2 in self.order_items:
                    distance = routes_matrix[order_item_1.order_number][order_item_2.order_number]
                    row.append(distance)
                final_routes_matrix.append(row)

        elif route_type == "work":
            for worker in self.workers:
                row = []
                for order_item in self.order_items:
                    distance = routes_matrix[worker.personal_number][order_item.order_number]
                    row.append(distance)
                final_routes_matrix.append(row)

        return final_routes_matrix


    def _convert_square_2d_list(self, routes_dict: dict) -> List[List[Optional[float]]]:
        ''' Convert a nested dictionary of routes to a square 2D list (matrix) '''
        max_index = max(int(key) for key in routes_dict.keys())
        routes_matrix = [[None for _ in range(max_index + 1)] for _ in range(max_index + 1)]

        for start, destinations in routes_dict.items():
            start_idx = int(start)
            for end, distance in destinations.items():
                end_idx = int(end)
                routes_matrix[start_idx][end_idx] = float(distance)
        
        return routes_matrix

    def _convert_rectangular_2d_list(self, routes_dict: dict) -> List[List[Optional[float]]]:
        ''' Convert a nested dictionary of routes to a rectangular 2D list (matrix) '''
        # Determine matrix dimensions
        row_count = max(int(key) for key in routes_dict.keys()) + 1
        col_count = max(int(dest_key) for destinations in routes_dict.values() for dest_key in destinations.keys()) + 1
        routes_matrix = [[None for _ in range(col_count)] for _ in range(row_count)]

        for start, destinations in routes_dict.items():
            start_idx = int(start)
            for end, distance in destinations.items():
                end_idx = int(end)
                routes_matrix[start_idx][end_idx] = float(distance)
        
        return routes_matrix

    @property
    def orders(self) -> List['Order']:
        return self._orders

    @property
    def order_items(self) -> List['OrderItem']:
        return self._order_items

    @property
    def attachments(self) -> List['Attachment']:
        return self._attachments

    @property
    def workers(self) -> List['Worker']:
        return self._workers

    @property
    def machines(self) -> List['Machine']:
        return self._machines

    @property
    def start_date(self) -> datetime:
        return self._start_date

    @property
    def end_date(self) -> datetime:
        return self._end_date

    @property
    def contains_durations(self) -> bool:
        return self._contains_durations

    @property
    def transport_routes(self) -> List[List[Optional[float]]]:
        ''' Returns the transport routes matrix '''
        return self._transport_routes

    @property
    def work_routes(self) -> List[List[Optional[float]]]:
        ''' Returns the work routes matrix '''
        return self._work_routes
    
    @property
    def transport_routes_order_item(self) -> List[List[Optional[float]]]:
        ''' Returns the transport routes matrix '''
        return self._transport_routes_order_item
    
    @property
    def work_routes_order_item(self) -> List[List[Optional[float]]]:
        ''' Returns the work routes matrix '''
        return self._work_routes_order_item
    


class Order:
    def __init__(self, json_data):
        self._order_number = int(json_data.get("Auftragsnummer", ""))
        self._site_number = int(json_data.get("Baustellennummer", 0))
        self._start_time = datetime.fromisoformat(json_data.get("Start", "1970-01-01T00:00:00"))
        self._end_time = datetime.fromisoformat(json_data.get("Ende", "1970-01-01T00:00:00"))
        self._order_item_ids = [int(item) for item in json_data.get("BestellpositionenStrings", [])]
        self._location = json_data.get("Standort", {"Item1": 0.0, "Item2": 0.0})
        self._priority = {}
        self._machine_priority = {}
        self._worker_priority = {}
        self.dynamic_percentage = 0

    @property
    def order_number(self) -> str:
        return self._order_number

    @property
    def site_number(self) -> int:
        return self._site_number

    @property
    def start_time(self) -> datetime:
        return self._start_time

    @property
    def end_time(self) -> datetime:
        return self._end_time

    @property
    def order_item_ids(self) -> List[str]:
        return self._order_item_ids

    @property
    def location(self) -> Tuple[float, float]:
        latitude = self._location.get("Item1", 0.0)
        longitude = self._location.get("Item2", 0.0)
        return (latitude, longitude)
    
    @property
    def priority(self) -> dict[str, int]:
        return self._priority
    
    @property
    def machine_priority(self) -> dict[int, int]:
        return self._machine_priority
    
    @property
    def worker_priority(self) -> dict[int, int]:
        return self._worker_priority
    

    def __str__(self):
        return (f"Order(Order Number: {self._order_number}, Site Number: {self._site_number}, "
                f"Start: {self._start_time}, End: {self._end_time}, "
                f"Order Item IDs: {self._order_item_ids}, Location: {self.location})")


class OrderItem:
    def __init__(self, json_data):
        self._id = int(json_data.get("ID", 0))
        self._start_time = datetime.fromisoformat(json_data.get("Start", "1970-01-01T00:00:00"))
        self._end_time = datetime.fromisoformat(json_data.get("Ende", "1970-01-01T00:00:00"))
        self._duration = int(json_data.get("Dauer", 0))
        self._order_number = int(json_data.get("Auftragsnummer", ""))
        self._machine_type = int(json_data.get("MaschinenTyp", 0))
        self._equipment_types = json_data.get("AnbaugeraeteTypen", [])
        self._worker_qualifications = json_data.get("ArbeiterQualifikationen", [])
        self._assigned_machine = json_data.get("zugewieseneMaschine", None)
        self._type = int(json_data.get("Typ", 0))
        self._priority = 0

    @property
    def id(self) -> int:
        return self._id

    @property
    def start_time(self) -> datetime:
        return self._start_time

    @property
    def end_time(self) -> datetime:
        return self._end_time

    @property
    def duration(self) -> int:
        return self._duration

    @property
    def order_number(self) -> str:
        return self._order_number

    @property
    def machine_type(self) -> int:
        return self._machine_type

    @property
    def equipment_types(self) -> List[int]:
        return self._equipment_types

    @property
    def worker_qualifications(self) -> List[int]:
        return self._worker_qualifications

    @property
    def assigned_machine(self) -> Optional[int]:
        return self._assigned_machine

    @property
    def type(self) -> int:
        return self._type
    
    @property
    def priority(self) -> int:
        return self._priority

    
    

    def __str__(self):
        return (f"OrderItem(ID: {self._id}, Start: {self._start_time}, End: {self._end_time}, "
                f"Duration: {self._duration}, Order Number: {self._order_number}, "
                f"Machine Type: {self._machine_type}, Equipment Types: {self._equipment_types}, "
                f"Worker Qualifications: {self._worker_qualifications}, Assigned Machine: {self._assigned_machine}, Type: {self._type})")


class Attachment:
    def __init__(self, json_data):
        self._id = int(json_data.get("ID", 0))
        self._year_of_manufacture = int(json_data.get("Baujahr", 0))
        self._type = int(json_data.get("Typ", 0))

    @property
    def id(self) -> int:
        return self._id

    @property
    def year_of_manufacture(self) -> int:
        return self._year_of_manufacture

    @property
    def type(self) -> int:
        return self._type

    def __str__(self):
        return f"Attachment(ID: {self._id}, Type: {self._type}, Year of Manufacture: {self._year_of_manufacture})"


class Worker:
    def __init__(self, json_data):
        self._personal_number = int(json_data.get("Personalnummer", 0))
        self._name = str(json_data.get("Name", ""))
        self._qualifications = json_data.get("Qualifikationen", [])
        self._residence = json_data.get("Wohnort", {"Item1": 0.0, "Item2": 0.0})
        self._possible_order_items = []
        self._predecessors = dict()
        self._successors = dict()
        self.work_hours = 0



    def add_data(self, input_data: InputData):
        # Add possible order items for the worker
        for order_item in input_data.order_items:
            if not order_item.worker_qualifications: # If no qualifications are required
                self._possible_order_items.append(order_item)
            elif set(order_item.worker_qualifications).issubset(self.qualifications): # If worker has all required qualifications
                self._possible_order_items.append(order_item)

        # Add predecessors and successors for the worker
        for order_item_1 in self._possible_order_items:
            self._predecessors[order_item_1] = []
            self._successors[order_item_1] = []

            for order_item_2 in self._possible_order_items:
                if order_item_1 != order_item_2:

                    start_time_order_item_1 = order_item_1.start_time - input_data.start_date
                    start_time_order_item_1 = start_time_order_item_1.total_seconds() / input_data._seconds_a_day
                    end_time_order_item_1 = order_item_1.end_time - input_data.start_date
                    end_time_order_item_1 = end_time_order_item_1.total_seconds() / input_data._seconds_a_day
                    start_time_order_item_2 = order_item_2.start_time - input_data.start_date
                    start_time_order_item_2 = start_time_order_item_2.total_seconds() / input_data._seconds_a_day
                    end_time_order_item_2 = order_item_2.end_time - input_data.start_date
                    end_time_order_item_2 = end_time_order_item_2.total_seconds() / input_data._seconds_a_day

                    break_time = input_data._hours_between_shifts / 24

                    if start_time_order_item_1 >= end_time_order_item_2 + break_time:
                        self._predecessors[order_item_1].append(order_item_2)
                    
                    if start_time_order_item_2 >= end_time_order_item_1 + break_time:
                        self._successors[order_item_1].append(order_item_2)

    @property
    def personal_number(self) -> int:
        return self._personal_number

    @property
    def name(self) -> str:
        return self._name

    @property
    def qualifications(self) -> List[int]:
        return self._qualifications

    @property
    def residence(self) -> Tuple[float, float]:
        latitude = self._residence.get("Item1", 0.0)
        longitude = self._residence.get("Item2", 0.0)
        return (latitude, longitude)
    
    @property
    def possible_order_items(self) -> List[int]:
        return self._possible_order_items
    
    @property
    def predecessors(self) -> dict[int, List[int]]:
        return self._predecessors
    
    @property
    def successors(self) -> dict[int, List[int]]:
        return self._successors
    

    def __str__(self):
        return (f"Worker(Personal Number: {self._personal_number}, Name: {self._name}, "
                f"Qualifications: {self._qualifications}, Residence: {self.residence})")


class Machine:
    def __init__(self, json_data):
        self._id = int(json_data.get("ID", 0))
        self._year_of_manufacture = int(json_data.get("Baujahr", 0))
        self._name = str(json_data.get("Name", ""))
        self._type = int(json_data.get("Typ", 0))
        self._default_drivers = [int(driver) for driver in json_data.get("StammfahrerStrings", [])]
        self._possible_order_items = []
        self._predecessors = dict()
        self._successors = dict()

    def add_data(self, input_data: InputData):
        # Add possible order items for the machine
        for order_item in input_data.order_items:
            if order_item.machine_type == self.type:
                self._possible_order_items.append(order_item)

        # Add predecessors and successors for the machine
        for order_item_1 in self._possible_order_items:
            self._predecessors[order_item_1] = []
            self._successors[order_item_1] = []

            for order_item_2 in self._possible_order_items:
                if order_item_1 != order_item_2:

                    start_time_order_item_1 = order_item_1.start_time - input_data.start_date
                    start_time_order_item_1 = start_time_order_item_1.total_seconds() / input_data._seconds_a_day
                    end_time_order_item_1 = order_item_1.end_time - input_data.start_date
                    end_time_order_item_1 = end_time_order_item_1.total_seconds() / input_data._seconds_a_day
                    start_time_order_item_2 = order_item_2.start_time - input_data.start_date
                    start_time_order_item_2 = start_time_order_item_2.total_seconds() / input_data._seconds_a_day
                    end_time_order_item_2 = order_item_2.end_time - input_data.start_date
                    end_time_order_item_2 = end_time_order_item_2.total_seconds() / input_data._seconds_a_day

                    transport_distance = input_data._transport_routes_order_item[order_item_1.id][order_item_2.id]
                    transport_time = transport_distance / input_data._transport_speed_kmh

                    if start_time_order_item_1 >= end_time_order_item_2 + transport_time:
                        self._predecessors[order_item_1].append(order_item_2)

                    if start_time_order_item_2 >= end_time_order_item_1 + transport_time:
                        self._successors[order_item_1].append(order_item_2)



    @property
    def id(self) -> int:
        return self._id

    @property
    def year_of_manufacture(self) -> int:
        return self._year_of_manufacture

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> int:
        return self._type

    @property
    def default_drivers(self) -> List[str]:
        return self._default_drivers
    
    @property
    def possible_order_items(self) -> List[int]:
        return self._possible_order_items
    
    @property
    def predecessors(self) -> dict[int, List[int]]:
        return self._predecessors
    
    @property
    def successors(self) -> dict[int, List[int]]:
        return self._successors
    

    def __str__(self):
        return (f"Machine(ID: {self._id}, Name: {self._name}, Type: {self._type}, "
                f"Year of Manufacture: {self._year_of_manufacture}, Default Drivers: {self._default_drivers})")