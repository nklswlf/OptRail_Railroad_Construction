import json
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime,timedelta
import itertools

class InputData:
    '''Class for creating Data objects based on formatted JSON Files containing the information of orders, machines, workers, attachments, and routes'''

    def __init__(self, instance_filename: str, algo:str):
        '''
        Initialize the InputData object with paths to the JSON file.

        :param instance_filename: Name of the JSON file containing the data.
        '''
        
        # File name and instance number
        self.instance_filename = instance_filename
        self.instance = instance_filename.split('Construction_')[1].split('.json')[0]
        self._data_path, self._parent_folder = self._find_instance_file()

        print(f"\nInstance: {self.instance}")
        print(f"\nLoading data from '{instance_filename}'...")

        # AHP weights for the different criteria
        self._ahp_weights = {"order_item_count": 0.54437184,
                            "regular_driver_count": 0.1707523,
                            "worker_distance": 0.12839376,
                            "transport_distance": 0.07315951,
                            "machine_type_count": 0.04935076,
                            "worker_qualification_count": 0.03397183
                            }
        self.complexity_ahp = {"order_item_count": 0.40671321997258464,
                               "regular_driver_count": 0.2125882387371141,
                               "worker_distance": 0.1445266762045684,
                               "transport_distance": 0.09585079248980775,
                               "machine_type_count": 0.061996079901354036,
                               "worker_qualification_count": 0.03916249634728554,
                               "attachment_count": 0.03916249634728554
                               }
    
        # Default values for Occupational Safety
        self._max_consecutive_night_shifts = 5 # Max consecutive night shifts
        self._max_shifts_in_time_period = 10 # Max shifts in a time period
        self._time_period_for_max_shifts = timedelta(days=14) # Time period for max shifts in days
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

        # Dynamic value for maximum possible sites to be fulfilled
        self.site_fulfillment = 0

        # Load data from JSON file
        self._load_data()

        # Transform data for easier access and usage
        self._transfrom_data()

        # Create a folder in .../Data/Solutions/ instance / the current date
        solutions_path = Path.cwd().parent / "Data" / "Solutions" / self._parent_folder / self.instance / datetime.now().strftime("%m-%d") / algo
        solutions_path.mkdir(parents=True, exist_ok=True)
        self.solutions_path = solutions_path


        print(f"Data loaded from '{self.instance_filename}' in folder '{self._parent_folder}'.")

    def check_order_usability(self):
        '''
        Check if the orders are unuseable and set the status accordingly.
        '''
        for order in self.orders:
            '''
            if not all(
                order_item.machine_type in {machine.type for machine in self.machines} and
                set(order_item.equipment_types).issubset({attachment.type for attachment in self.attachments}) and
                any(set(order_item.worker_qualifications).issubset(worker.qualifications) for worker in self.workers)
                for order_item in order.order_items
            ):
                order.unuseable = True
            '''
            if not all(order_item.machine_type in {machine.type for machine in self.machines} for order_item in order.order_items):
                not_found_machine_type = set(order_item.machine_type for order_item in order.order_items) - {machine.type for machine in self.machines}
                print(f"Order {order.order_number} is not useable because of machine type(s): {not_found_machine_type}.")

            if not all(set(order_item.equipment_types).issubset({attachment.type for attachment in self.attachments}) for order_item in order.order_items):
                not_found_attachment_type = set(order_item.equipment_types for order_item in order.order_items) - {attachment.type for attachment in self.attachments}
                print(f"Order {order.order_number} is not useable because of attachment type(s): {not_found_attachment_type}.")

            if not all(any(set(order_item.worker_qualifications).issubset(worker.qualifications) for worker in self.workers) for order_item in order.order_items):
                not_found_worker_qualification = set(order_item.worker_qualifications for order_item in order.order_items) - {worker.qualifications for worker in self.workers}
                print(f"Order {order.order_number} is not useable because of worker qualifications: {not_found_worker_qualification}.")

            else:
                print(f"Order {order.order_number} is useable.")
                          
    def activate_order(self, order_number: int) -> None:
        """Aktiviert eine Order und alle zugehörigen OrderItems."""
        for order in self.orders:
            if order.order_number == order_number:
                order.status = True
                self.site_fulfillment += 1
                for order_item in order.order_items:
                    order_item.status = True
                break

    def deactivate_order(self, order_number: int) -> None:
        """Deaktiviert eine Order und alle zugehörigen OrderItems."""
        for order in self.orders:
            if order.order_number == order_number:
                order.status = False
                self.site_fulfillment -= 1
                for order_item in order.order_items:
                    order_item.status = False
                break   

    def unuseable_order(self, order_number: int) -> None:
        """Markiert eine Order als unbrauchbar."""
        for order in self.orders:
            if order.order_number == order_number:
                order.unuseable = True
                for order_item in order.order_items:
                    order_item.status = False
                break
        
    def connect_order_item_to_order(self):
        '''
        Connect each order item to its corresponding order.
        '''
        for order in self.orders:
            order.order_items = [order_item for order_item in self.order_items if order_item.order_number == order.order_number]



    def calculate_complexity(self):
        """
        Generate priorities for all orders based on multiple criteria.

        This function calculates ranks for different parameters (e.g., order items, machine types)
        and combines them into an overall priority score with Borda Count (BC) and Analytic Hierarchy Process (AHP).
        """
        # 1. Calculate rank for order_item_count (more are more complex)
        self.complexity_rank(
            self.orders, 
            lambda order: len(order.order_item_ids), 
            "order_item_count",
            reverse=True
        )


        # 2. Calculate rank for regular_driver_count (less is more complex)
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
        self.complexity_rank(
            self.orders, 
            lambda order: len(possible_regular_drivers[order.order_number]), 
            "regular_driver_count"
        )

        # 3. Calculate rank for worker_distance (longer distances are more complex)
        worker_distances = {
            order.order_number: sum(
                self.work_routes[worker.personal_number][order.site_number]
                for worker in self.workers
            ) / len(self.workers)
            for order in self.orders
        }
        self.complexity_rank(
            self.orders, 
            lambda order: worker_distances[order.order_number], 
            "worker_distance",
            reverse=True
        )

        # 4. Calculate rank for transport_distance (longer distances are more complex)
        transport_distances = {
            order.order_number: sum(
                self.transport_routes[order.site_number][site]
                for site in range(len(self.transport_routes))
            ) / len(self.transport_routes)
            for order in self.orders
        }
        self.complexity_rank(
            self.orders, 
            lambda order: transport_distances[order.order_number], 
            "transport_distance",
            reverse=True
        )

        # 5. Calculate rank for machine_type_count (more machine types are more complex)
        self.complexity_rank(
            self.orders, 
            lambda order: len(set(
                item.machine_type for item in self.order_items if item.order_number == order.order_number
            )), 
            "machine_type_count",
            reverse=True
        )
    

        # 6. Calculate rank for worker_qualification_count (more qualifications are more complex)
        worker_qualifications = {
            order.order_number: set(
                qualification for item in self.order_items
                if item.order_number == order.order_number
                for qualification in item.worker_qualifications
            )
            for order in self.orders
        }
        self.complexity_rank(
            self.orders, 
            lambda order: len(worker_qualifications[order.order_number]), 
            "worker_qualification_count",
            reverse=True
        )

        # 7. Calculate rank for attachment_count (more attachments are more complex)
        self.complexity_rank(
            self.orders, 
            lambda order: len(list(
                item.equipment_types for item in self.order_items if item.order_number == order.order_number
            )), 
            "attachment_count",
            reverse=True
        )

        
        # 7. Calculate overall Rank with Borda Count
        self.complexity_borda_count_ahp()
        self.assign_complexity_classes_from_final_score()
    
    def complexity_rank(self, orders, key_func, rank_name, reverse=False):
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
            order._complexity[rank_name] = current_rank

    def complexity_borda_count_ahp(self):
        """
        Calculate the overall priority rank using Borda Count combined with Analytic Hierarchy Process (AHP).
        """

        borda_count_ahp = {
            order.order_number: sum(
                (len(self.orders) - rank + 1)
                * self.complexity_ahp[rank_name]
                for rank_name, rank in order._complexity.items()
            )
            for order in self.orders
        }

        self.calculate_rank(
            self.orders, 
            lambda order: borda_count_ahp[order.order_number], 
            "complexity_borda_count_ahp", 
            reverse=True
        )

    def assign_complexity_classes_from_final_score(self, num_classes: int = 3) -> None:
        """
        Assign complexity classes to orders based on the final Borda Count rank stored in order._complexity["borda_count_ahp"].
        Orders are sorted by their rank (lower = more complex). Each order's complexity_score is set to the rank,
        and complexity_class is assigned starting from 1 (most complex) to num_classes (least complex).
 
        :param num_classes: Number of complexity classes (default is 3), where 1 is most complex.
        """
        sorted_orders = sorted(self.orders, key=lambda order: order._complexity.get("complexity_borda_count_ahp", 0))
        total_orders = len(sorted_orders)
        if total_orders == 0:
            return
        group_size = total_orders / num_classes
        for i, order in enumerate(sorted_orders):
            complexity_class = int(i // group_size) + 1
            order.complexity_score = num_classes - complexity_class + 1
            if complexity_class > num_classes:
                complexity_class = num_classes
            order.complexity_class = complexity_class




        
    def create_priorities_orders(self):
        """
        Generate priorities for all orders based on multiple criteria.

        This function calculates ranks for different parameters (e.g., order items, machine types)
        and combines them into an overall priority score with Borda Count (BC) and Analytic Hierarchy Process (AHP).
        """
        # 1. Calculate rank for order_item_count (fewer items are better)
        self.calculate_rank(
            self.orders, 
            lambda order: len(order.order_item_ids), 
            "order_item_count"
        )


        # 2. Calculate rank for regular_driver_count (more regular drivers are better)
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

        # 3. Calculate rank for worker_distance (shorter distances are better)
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

        # 4. Calculate rank for transport_distance (shorter distances are better)
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

        # 5. Calculate rank for machine_type_count (fewer machine types are better)
        self.calculate_rank(
            self.orders, 
            lambda order: len(set(
                item.machine_type for item in self.order_items if item.order_number == order.order_number
            )), 
            "machine_type_count"
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

        # 7. Calculate rank for attachment_count fewer attachments are better
        self.calculate_rank(
            self.orders, 
            lambda order: len(list(
                item.equipment_types for item in self.order_items if item.order_number == order.order_number
            )), 
            "attachment_count"
        )

        
        # 7. Calculate overall Rank with Borda Count
        self.calculate_borda_count_ahp()

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

    def calculate_borda_count_ahp(self, ahp=True):
        """
        Calculate the overall priority rank using Borda Count combined with Analytic Hierarchy Process (AHP).
        """
        if ahp:
            borda_count_ahp = {
                order.order_number: sum(
                    (len(self.orders) - rank + 1)
                    * self._ahp_weights[rank_name]
                    for rank_name, rank in order._priority.items()
                )
                for order in self.orders
            }

            self.calculate_rank(
                self.orders, 
                lambda order: borda_count_ahp[order.order_number], 
                "borda_count_ahp", 
                reverse=True
            )


        elif not ahp:
            borda_count = {
                order.order_number: sum(
                    (len(self.orders) - rank + 1)
                    for rank_name, rank in order._priority.items()
                )
                for order in self.orders
            }

            self.calculate_rank(
                self.orders, 
                lambda order: borda_count[order.order_number], 
                "borda_count", 
                reverse=True
            )



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

    
            
            
    def _transfrom_data(self) -> None:
            
        # Convert distance matrix from order to order item
        self._transport_routes_order_item = self._convert_from_order_to_order_item(self._transport_routes, "transport")
        self._work_routes_order_item = self._convert_from_order_to_order_item(self._work_routes, "work")

        # Add data to order items (day or night shift)
        for order_item in self.order_items:
            order_item.day_or_night(self)

        # Add data to workers and machines (predessors, successors, possible order items)
        for machine in self.machines:
            machine.add_data(self)
        for worker in self.workers:
            worker.add_data(self)
        for attachment in self.attachments:
            attachment.add_data(self)

        # Calculate average, min, and max distances for transport and work routes for normalization during optimization
        self._average_transport_distance = sum(sum(row) for row in self._transport_routes) / (len(self._transport_routes)*len(self._transport_routes[0]))
        self._min_transport_distance = min(min(row) for row in self._transport_routes if any(row))            
        self._max_transport_distance = max(max(row) for row in self._transport_routes if any(row))
        self._average_work_distance = sum(sum(row) for row in self._work_routes) / (len(self._work_routes)*len(self._work_routes[0]))
        self._min_work_distance = (min(min(row) for row in self._work_routes if any(row)))
        self._max_work_distance = (max(max(row) for row in self._work_routes if any(row)))


        # Connect order items to their corresponding orders
        self.connect_order_item_to_order()

        # Check orders for usability
        self.check_order_usability()


        # Complexity for orders
        #self.calculate_complexity()


        # Greedy "WorkerGreedy" Data Preparation

        # Priorities for orders
        #self.create_priorities_orders()

        # Dynamic dictionary for planned shifts
        #self.planned_shifts_worker = dict()
        #self.planned_shifts_machine = dict()
        #for order in self.orders:
        #    self.planned_shifts_worker[order] = list()
        #    self.planned_shifts_machine[order] = list()
            


            



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
    
    @property
    def average_transport_distance(self) -> float:
        return self._average_transport_distance
    
    @property
    def average_work_distance(self) -> float:
        return self._average_work_distance
    
    @property
    def min_transport_distance(self) -> float:
        return self._min_transport_distance
    
    @property
    def min_work_distance(self) -> float:
        return self._min_work_distance
    
    @property
    def max_transport_distance(self) -> float:
        return self._max_transport_distance
    
    @property
    def max_work_distance(self) -> float:
        return self._max_work_distance

    
class Order:
    def __init__(self, json_data):
        self._order_number = int(json_data.get("Auftragsnummer", ""))
        self._site_number = int(json_data.get("Baustellennummer", 0))
        self._start_time = datetime.fromisoformat(json_data.get("Start", "1970-01-01T00:00:00"))
        self._end_time = datetime.fromisoformat(json_data.get("Ende", "1970-01-01T00:00:00"))
        self._order_item_ids = [int(item) for item in json_data.get("BestellpositionenStrings", [])]
        self._location = json_data.get("Standort", {"Item1": 0.0, "Item2": 0.0})
        self._priority = {}
        self._complexity = {}
        self.dynamic_percentage = 0
        self.status = False
        self.unuseable = False
        self.complexity_score = None
        self.complexity_class = None





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
    def complexity(self) -> dict[str, int]:
        return self._complexity
    
    

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
        self.status = False
    




    def day_or_night(self, input_data: InputData):
        if self._start_time.hour < input_data._day_and_night_shift_boundary:
            self.day_shift = True
            self.night_shift = False
        else:
            self.night_shift = True
            self.day_shift = False

        




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
    
    #@property
    #def priority(self) -> int:
    #    return self._priority

    
    

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
        self._possible_order_items = dict()  # Als Dictionary mit `order` als Key
        self._possible_order_item_ids = dict()  # Als Dictionary mit `order` als Key
        self._predecessors = dict()
        self._predecessor_ids = dict()
        self._successors = dict()
        self._successor_ids = dict()


    def add_data(self, input_data: InputData):
        self._possible_order_items = {order: [] for order in input_data.orders}
        self._possible_order_item_ids = {order.order_number: [] for order in input_data.orders}

        for order_item in input_data.order_items:
            for order in input_data.orders:
                if order_item.order_number == order.order_number and self._type in order_item.equipment_types:
                    self._possible_order_items[order].append(order_item)
                    self._possible_order_item_ids[order.order_number].append(order_item.id)

        all_order_items = list({oi for items in self._possible_order_items.values() for oi in items})
        seconds_per_day = input_data._seconds_a_day
        speed_kmh = input_data._transport_speed_kmh
        transport_matrix = input_data._transport_routes_order_item
        break_time = input_data._hours_between_shifts / 24

        times = {
            oi.id: (
                (oi.start_time - input_data.start_date).total_seconds() / seconds_per_day,
                (oi.end_time - input_data.start_date).total_seconds() / seconds_per_day
            )
            for oi in all_order_items
        }

        self._predecessors.clear()
        self._predecessor_ids.clear()
        self._successors.clear()
        self._successor_ids.clear()

        for oi1 in all_order_items:
            self._predecessors[oi1] = []
            self._predecessor_ids[oi1.id] = []
            self._successors[oi1] = []
            self._successor_ids[oi1.id] = []

            st1, et1 = times[oi1.id]
            for oi2 in all_order_items:
                if oi1.id == oi2.id:
                    continue
                st2, et2 = times[oi2.id]
                transport_time = transport_matrix[oi1.id][oi2.id] / speed_kmh / 24

                if transport_time > break_time:
                    raise ValueError(f"Attachment transport time ({transport_time:.2f}) > break ({break_time:.2f}) between {oi1.id} and {oi2.id}")

                if st1 >= et2 + transport_time:
                    self._predecessors[oi1].append(oi2)
                    self._predecessor_ids[oi1.id].append(oi2.id)

                if st2 >= et1 + transport_time:
                    self._successors[oi1].append(oi2)
                    self._successor_ids[oi1.id].append(oi2.id)
            
        

    @property
    def id(self) -> int:
        return self._id

    @property
    def year_of_manufacture(self) -> int:
        return self._year_of_manufacture

    @property
    def type(self) -> int:
        return self._type
    
    @property
    def possible_order_items(self) -> dict[int, List[int]]:
        return self._possible_order_items
    
    @property
    def possible_order_item_ids(self) -> dict[int, List[int]]:
        return self._possible_order_item_ids
    
    @property
    def predecessors(self) -> dict[int, List[int]]:
        return self._predecessors
    
    @property
    def successors(self) -> dict[int, List[int]]:
        return self._successors
    
    @property
    def predecessor_ids(self) -> dict[int, List[int]]:
        return self._predecessor_ids
    
    @property
    def successor_ids(self) -> dict[int, List[int]]:
        return self._successor_ids
    

    def __str__(self):
        return f"Attachment(ID: {self._id}, Type: {self._type}, Year of Manufacture: {self._year_of_manufacture})"


class Worker:
    def __init__(self, json_data):
        self._personal_number = int(json_data.get("Personalnummer", 0))
        self._name = str(json_data.get("Name", ""))
        self._qualifications = json_data.get("Qualifikationen", [])
        self._residence = json_data.get("Wohnort", {"Item1": 0.0, "Item2": 0.0})
        self._possible_order_items = dict()  # Jetzt als Dictionary
        self._possible_order_item_ids = dict()  # Jetzt als Dictionary
        self._predecessors = dict()
        self._predecessor_ids = dict()
        self._successors = dict()
        self._successor_ids = dict()
        self.work_hours = 0

    def add_data(self, input_data: InputData):

        self._possible_order_items = {order: [] for order in input_data.orders}
        self._possible_order_item_ids = {order.order_number: [] for order in input_data.orders}

        qualifications_set = set(self._qualifications)
        for order_item in input_data.order_items:
            if not order_item.worker_qualifications or set(order_item.worker_qualifications).issubset(qualifications_set):
                for order in input_data.orders:
                    if order_item.order_number == order.order_number:
                        self._possible_order_items[order].append(order_item)
                        self._possible_order_item_ids[order.order_number].append(order_item.id)
                        break

        all_order_items = [item for items in self._possible_order_items.values() for item in items]
        seconds_per_day = input_data._seconds_a_day
        speed_kmh = input_data._transport_speed_kmh
        break_time = input_data._hours_between_shifts / 24
        transport_matrix = input_data._transport_routes_order_item

        rtimes = {
            oi.id: (
                (oi.start_time - input_data.start_date).total_seconds() / seconds_per_day,
                (oi.end_time - input_data.start_date).total_seconds() / seconds_per_day
            )
            for oi in all_order_items
        }

        self._predecessors.clear()
        self._predecessor_ids.clear()
        self._successors.clear()
        self._successor_ids.clear()

        for oi1 in all_order_items:
            self._predecessors[oi1] = []
            self._predecessor_ids[oi1.id] = []
            self._successors[oi1] = []
            self._successor_ids[oi1.id] = []

            st1, et1 = rtimes[oi1.id]
            for oi2 in all_order_items:
                if oi1.id == oi2.id:
                    continue

                st2, et2 = rtimes[oi2.id]
                transport_time = transport_matrix[oi1.id][oi2.id] / speed_kmh / 24

                if transport_time > break_time:
                    raise Exception(f"Transport time {transport_time:.2f} > break {break_time:.2f} between {oi1.id} and {oi2.id}.")

                if st1 >= et2 + break_time:
                    self._predecessors[oi1].append(oi2)
                    self._predecessor_ids[oi1.id].append(oi2.id)
                if st2 >= et1 + break_time:
                    self._successors[oi1].append(oi2)
                    self._successor_ids[oi1.id].append(oi2.id)

        self._night_shifts = [oi for oi in all_order_items if oi.night_shift]
        self._night_shift_ids = [oi.id for oi in self._night_shifts]

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
    def possible_order_items(self) -> dict[int, List[int]]:
        return self._possible_order_items
    
    @property
    def possible_order_item_ids(self) -> dict[int, List[int]]:
        return self._possible_order_item_ids
    
    @property
    def predecessors(self) -> dict[int, List[int]]:
        return self._predecessors
    
    
    @property
    def successors(self) -> dict[int, List[int]]:
        return self._successors
    
    @property
    def predecessor_ids(self) -> dict[int, List[int]]:
        return self._predecessor_ids
    
    @property
    def successor_ids(self) -> dict[int, List[int]]:
        return self._successor_ids
    
    @property
    def night_shifts(self) -> List[int]:
        return self._night_shifts
    
    @property
    def night_shift_ids(self) -> List[int]:
        return self._night_shift_ids
    
    

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
        self._possible_order_items = dict()  # Als Dictionary mit `order` als Key
        self._possible_order_item_ids = dict()  # Als Dictionary mit `order` als Key
        self._predecessors = dict()
        self._predecessor_ids = dict()
        self._successors = dict()
        self._successor_ids = dict()

    def add_data(self, input_data: InputData):
        # Initialisiere `_possible_order_items` als Dictionary
        for order in input_data.orders:
            self._possible_order_items[order] = []
            self._possible_order_item_ids[order.order_number] = []

        # Füge mögliche Order Items basierend auf `machine_type` hinzu
        for order_item in input_data.order_items:
            if order_item.machine_type == self.type:
                for order in input_data.orders:
                    if order_item.order_number == order.order_number:
                        self._possible_order_items[order].append(order_item)
                        self._possible_order_item_ids[order.order_number].append(order_item.id)

        # Vorberechnete Zeiten & Transportdistanzen
        seconds_per_day = input_data._seconds_a_day
        speed_kmh = input_data._transport_speed_kmh
        transport_matrix = input_data._transport_routes_order_item

        all_order_items = list({oi for items in self._possible_order_items.values() for oi in items})
        times = {
            oi.id: (
                (oi.start_time - input_data.start_date).total_seconds() / seconds_per_day,
                (oi.end_time - input_data.start_date).total_seconds() / seconds_per_day
            )
            for oi in all_order_items
        }

        self._predecessors.clear()
        self._predecessor_ids.clear()
        self._successors.clear()
        self._successor_ids.clear()

        for oi1 in all_order_items:
            self._predecessors[oi1] = []
            self._predecessor_ids[oi1.id] = []
            self._successors[oi1] = []
            self._successor_ids[oi1.id] = []

            st1, et1 = times[oi1.id]
            for oi2 in all_order_items:
                if oi1.id == oi2.id:
                    continue

                st2, et2 = times[oi2.id]
                transport_time = transport_matrix[oi1.id][oi2.id] / speed_kmh / 24

                if st1 >= et2 + transport_time:
                    self._predecessors[oi1].append(oi2)
                    self._predecessor_ids[oi1.id].append(oi2.id)

                if st2 >= et1 + transport_time:
                    self._successors[oi1].append(oi2)
                    self._successor_ids[oi1.id].append(oi2.id)


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
    def default_drivers(self) -> List[int]:
        return self._default_drivers
    
    @property
    def possible_order_items(self) -> dict[int, List[int]]:
        return self._possible_order_items
    
    @property
    def possible_order_item_ids(self) -> dict[int, List[int]]:
        return self._possible_order_item_ids
    
    @property
    def predecessors(self) -> dict[int, List[int]]:
        return self._predecessors
    
    @property
    def successors(self) -> dict[int, List[int]]:
        return self._successors
    
    @property
    def predecessor_ids(self) -> dict[int, List[int]]:
        return self._predecessor_ids
    
    @property
    def successor_ids(self) -> dict[int, List[int]]:
        return self._successor_ids
    

    def __str__(self):
        return (f"Machine(ID: {self._id}, Name: {self._name}, Type: {self._type}, "
                f"Year of Manufacture: {self._year_of_manufacture}, Default Drivers: {self._default_drivers})")