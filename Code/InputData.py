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
        self._load_data()

        self.create_priorities()

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

        
    def create_priorities(self):
        ''' Create a priority position for each order based on the number of order items '''

        # First parameter: order_item_count --> Less order items are better
        sorted_orders = sorted(self.orders, key=lambda order: len(order.order_item_ids))
        current_rank = 1
        last_item_count = None 
        for i, order in enumerate(sorted_orders):
            item_count = len(order.order_item_ids)
            if item_count != last_item_count:
                current_rank = i + 1 
                last_item_count = item_count
            order._priority = {"order_item_count": current_rank}

        
        # Second parameter: machine_type_count --> Less machine types are better
        sorted_orders = sorted(self.orders, key=lambda order: len(set([item.machine_type for item in self.order_items if item.order_number == order.order_number])))
        current_rank = 1
        last_machine_type_count = None
        for i, order in enumerate(sorted_orders):
            machine_type_count = len(set([item.machine_type for item in self.order_items if item.order_number == order.order_number]))
            if machine_type_count != last_machine_type_count:
                current_rank = i + 1 
                last_machine_type_count = machine_type_count
            order._priority["machine_type_count"] = current_rank



        # Third parameter: regular_driver_count --> More (possible) regular drivers are better
        machine_types = dict()
        possible_regular_drivers = dict()
        for order in self.orders:
            if order.order_number not in machine_types:
                machine_types[order.order_number] = set()
            if order.order_number not in possible_regular_drivers:
                possible_regular_drivers[order.order_number] = set()

            machine_types[order.order_number].update(item.machine_type for order_item in order.order_item_ids for item in self.order_items if item.id == order_item)

            for machines in self.machines:
                default_drivers = machines.default_drivers
                if machines.type in machine_types[order.order_number]:
                    possible_regular_drivers[order.order_number].update(default_drivers)


            # Check if necessary to add all drivers as possible regular drivers if there are no regular drivers !!!

        sorted_orders = sorted(self.orders, key = lambda order: len(possible_regular_drivers[order.order_number]), reverse=True)
        current_rank = 1
        last_driver_count = None
        for i, order in enumerate(sorted_orders):
            driver_count = len(possible_regular_drivers[order.order_number])
            if driver_count != last_driver_count:
                current_rank = i + 1
                last_driver_count = driver_count
            order._priority["regular_driver_count"] = current_rank


        # Fourth parameter: worker_distance --> Less distance to workers home is better 
        worker_distances = dict()
        for order in self.orders:
            if order.order_number not in worker_distances:
                worker_distances[order.order_number] = 0
            for worker in self.workers:
                worker_distances[order.order_number] += self.work_routes[worker.personal_number][order.site_number]

            worker_distances[order.order_number] /= len(self.workers)

        sorted_orders = sorted(self.orders, key = lambda order: worker_distances[order.order_number])
        current_rank = 1
        last_distance = None
        for i, order in enumerate(sorted_orders):
            distance = worker_distances[order.order_number]
            if distance != last_distance:
                current_rank = i + 1
                last_distance = distance
            order._priority["worker_distance"] = current_rank

        
        # Fifth parameter: transport_distance --> Less distance for machine transport is better
        transport_distances = dict()
        for order in self.orders:
            if order.order_number not in transport_distances:
                transport_distances[order.order_number] = 0
            for site in range(0, len(self.transport_routes)):
                transport_distances[order.order_number] += self.transport_routes[order.site_number][site]

            transport_distances[order.order_number] /= len(self.transport_routes)

        sorted_orders = sorted(self.orders, key = lambda order: transport_distances[order.order_number])
        current_rank = 1
        last_distance = None
        for i, order in enumerate(sorted_orders):
            distance = transport_distances[order.order_number]
            if distance != last_distance:
                current_rank = i + 1
                last_distance = distance
            order._priority["transport_distance"] = current_rank

        
 
        # Sixth parameter: worker_qualification_count --> Less worker qualifications are better

        worker_qualifications = dict()
        for order in self.orders:
            if order.order_number not in worker_qualifications:
                worker_qualifications[order.order_number] = set()
            for item in self.order_items:
                if item.order_number == order.order_number:
                    worker_qualifications[order.order_number].update(item.worker_qualifications)

        sorted_orders = sorted(self.orders, key = lambda order: len(worker_qualifications[order.order_number]))
        current_rank = 1
        last_qualification_count = None
        for i, order in enumerate(sorted_orders):
            qualification_count = len(worker_qualifications[order.order_number])
            if qualification_count != last_qualification_count:
                current_rank = i + 1
                last_qualification_count = qualification_count
            order._priority["worker_qualification_count"] = current_rank


        print(f"Worker Qualifications: {worker_qualifications}")


        # Create an overall priority score and create a ranking based on the scores
        for order in self.orders:
            order._priority["overall"] = sum(order.priority.values())
        
        print(f"Order Priorities Overall: {[order.priority['overall'] for order in self.orders]}")
        sorted_orders = sorted(self.orders, key = lambda order: order.priority["overall"])
        current_rank = 1
        last_score = None
        for i, order in enumerate(sorted_orders):
            score = order.priority["overall"]
            if score != last_score:
                current_rank = i + 1
                last_score = score
            order._priority["overall"] = current_rank

        




        # Debug-Ausgabe
        print("Order Priorities:")
        for order in self.orders:
            print(f"Order Number: {order.order_number}, Priority: {order.priority}")


        

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

            # Load each data category
            self._orders = [Order(order) for order in data.get("Auftraege", [])]
            self._order_items = [OrderItem(item) for item in data.get("Bestellpositionen", [])]
            self._attachments = [Attachment(attachment) for attachment in data.get("Anbaugeraete", [])]
            self._workers = [Worker(worker) for worker in data.get("Arbeiter", [])]
            self._machines = [Machine(machine) for machine in data.get("Maschinen", [])]
            
            # Convert ArbeitswegeString and TransportwegeString to 2D lists
            self._transport_routes = self._convert_square_2d_list(data.get("TransportwegeString", {}))
            self._work_routes = self._convert_rectangular_2d_list(data.get("ArbeitswegeString", {}))

            print(f"Data loaded from '{self.instance_filename}' in folder '{self._parent_folder}'.")

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


class Order:
    def __init__(self, json_data):
        self._order_number = json_data.get("Auftragsnummer", "")
        self._site_number = int(json_data.get("Baustellennummer", 0))
        self._start_time = datetime.fromisoformat(json_data.get("Start", "1970-01-01T00:00:00"))
        self._end_time = datetime.fromisoformat(json_data.get("Ende", "1970-01-01T00:00:00"))
        self._order_item_ids = [int(item) for item in json_data.get("BestellpositionenStrings", [])]
        self._location = json_data.get("Standort", {"Item1": 0.0, "Item2": 0.0})
        self._priority = {}
        self._machine_priority = {}
        self._worker_priority = {}

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
        self._order_number = str(json_data.get("Auftragsnummer", ""))
        self._machine_type = int(json_data.get("MaschinenTyp", 0))
        self._equipment_types = json_data.get("AnbaugeraeteTypen", [])
        self._worker_qualifications = json_data.get("ArbeiterQualifikationen", [])
        self._assigned_machine = json_data.get("zugewieseneMaschine", None)
        self._type = int(json_data.get("Typ", 0))

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

    def __str__(self):
        return (f"Machine(ID: {self._id}, Name: {self._name}, Type: {self._type}, "
                f"Year of Manufacture: {self._year_of_manufacture}, Default Drivers: {self._default_drivers})")