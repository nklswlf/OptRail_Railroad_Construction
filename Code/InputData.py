"""

===============================================================================
                            INPUT DATA MODULE
===============================================================================

InputData.py - Railroad Construction Optimization Instance Data Management

This module provides comprehensive data management functionality for railroad construction
scheduling optimization problems. It handles the loading, transformation, and preparation
of construction project data for various optimization algorithms.


1. **Data Loading and Parsing**
   - JSON instance file parsing with comprehensive error handling
   - Hierarchical data structure creation (Orders → OrderItems → Resources)
   - Route matrix conversion from nested dictionaries to 2D arrays
   - Time window and duration extraction with proper datetime handling

2. **Resource Management**
   - Machine allocation with type compatibility checking
   - Worker assignment with qualification validation
   - Attachment scheduling with equipment type matching
   - Transport route calculation between construction sites

3. **Scheduling Constraints**
   - Work hour limitations and shift pattern enforcement
   - Night shift restrictions and safety regulations
   - Mandatory rest periods between shifts
   - Resource availability and capacity constraints

4. **Data Transformation**
   - Order-based to order-item-based route matrix conversion
   - Predecessor/successor relationship calculation
   - Distance normalization for optimization algorithms
   - Priority and complexity ranking systems


"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime,timedelta
import itertools

class InputData:
    """
    Central data management class for railroad construction optimization instances.
    
    This class loads and processes data from JSON files containing information about
    construction orders, machines, workers, attachments, and transportation routes.
    It handles data transformation, validation, and preparation for optimization algorithms.
    """

    def __init__(self, instance_filename: str, algo:str):
        """
        Initialize the InputData object with instance file and algorithm configuration.
        
        Args:
            instance_filename: Name of the JSON file containing the construction data
            algo: Algorithm identifier for organizing solution output paths
        """
        self.algo = algo

        # Extract instance information from filename
        self.instance_filename = instance_filename
        self.instance = instance_filename.split('Construction_')[1].split('.json')[0]
        self._data_path, self._parent_folder = self._find_instance_file()

        print(f"\nInstance: {self.instance}")
        print(f"\nLoading data from '{instance_filename}'...")

        # AHP (Analytic Hierarchy Process) weights for different optimization criteria
        # Currently commented out - not used in current version
        """
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
        """
    
        # Occupational safety and work regulations parameters
        self._max_consecutive_night_shifts = 5  # Maximum consecutive night shifts allowed
        self._max_shifts_in_time_period = 10   # Maximum shifts within specified time period
        self._time_period_for_max_shifts = timedelta(days=14)  # Time period for shift counting
        
        # Adjust working hours based on instance type (real vs test instances)
        if self._parent_folder == "2_piece":
            self._max_working_hours = 160/2  # Reduced hours for real-life instances
        else:
            self._max_working_hours = 160   # Standard hours for test instances
        print(f"Max working hours: {self._max_working_hours}")
        
        # Shift classification boundary (hours)
        self._day_and_night_shift_boundary = 12  # Start before 12h = day shift, after 12h = night shift

        # Physical and operational constraints
        self._seconds_a_day = 86400           # Seconds in a day for time calculations
        self._transport_speed_kmh = 70        # Machine transport speed in km/h
        self._hours_between_shifts = 9        # Mandatory rest period between shifts

        # Economic parameters for cost calculations
        self._construction_revenue = 1000000                    # Project revenue baseline
        self._machine_fixed_cost = 9000                        # Monthly machine rental cost
        self._worker_fixed_cost = 4800                         # Monthly worker salary and costs
        self._penalty_cost_non_regular_driver = (self._worker_fixed_cost/20) * 0.2  # Penalty for non-regular drivers
        self._worker_travel_cost_per_km = 0.5                  # Worker travel reimbursement per km
        self._machine_transport_cost_per_km = 1.6              # Machine transport cost per km

        # Dynamic tracking of solution quality
        self.site_fulfillment = 0  # Number of sites that can be fulfilled with current resources

        # Work hour sum after orders are chosen
        self.work_hour_sum = None

        # Load and process data from JSON file
        self._load_data()

        # Transform and prepare data for optimization algorithms
        self._transfrom_data()

        # Create solution output directory structure
        solutions_path = Path.cwd().parent / "OptRail_Railroad_Construction" / "Data" / "Solutions" / self.instance / self.algo
        solutions_path.mkdir(parents=True, exist_ok=True)
        self.solutions_path = solutions_path
        
          
        print(f"Data loaded from '{self.instance_filename}' in folder '{self._parent_folder}'.")

    def check_order_usability(self):
        """
        Validates order feasibility by checking resource availability.
        
        Verifies that each order can be completed with available machines,
        attachments, and qualified workers. Marks orders as unusable if
        required resources are not available in the fleet.
        """
        for order in self.orders:
            is_usable = True

            # Check if required machine types are available in fleet
            machine_types_available = {machine.type for machine in self.machines}
            missing_machine_types = {
                order_item.machine_type
                for order_item in order.order_items
                if order_item.machine_type not in machine_types_available
            }
            if missing_machine_types:
                print(f"Order {order.order_number} is not useable because of machine type(s): {missing_machine_types}.")
                is_usable = False

            # Check if required attachment types are available
            attachment_types_available = {attachment.type for attachment in self.attachments}
            required_attachment_types = {
                atype
                for order_item in order.order_items
                for atype in order_item.equipment_types
            }
            missing_attachment_types = required_attachment_types - attachment_types_available
            if missing_attachment_types:
                print(f"Order {order.order_number} is not useable because of attachment type(s): {missing_attachment_types}.")
                is_usable = False

            # Check if workers with required qualifications are available
            all_worker_qualifications = [worker.qualifications for worker in self.workers]
            missing_qualifications = []
            for order_item in order.order_items:
                if not any(set(order_item.worker_qualifications).issubset(q) for q in all_worker_qualifications):
                    missing_qualifications.append(order_item.worker_qualifications)

            if missing_qualifications:
                print(f"Order {order.order_number} is not useable because of worker qualification(s): {missing_qualifications}.")
                is_usable = False

            # Set final usability status
            order.unuseable = not is_usable
            if is_usable:
                print(f"Order {order.order_number} is useable.")
                          
    def activate_order(self, order_number: int) -> None:
        """
        Activates an order and all its associated order items for scheduling.
        
        Args:
            order_number: Order number to activate
        """
        for order in self.orders:
            if order.order_number == order_number:
                order.status = True
                self.site_fulfillment += 1  # Increment fulfilled sites counter
                for order_item in order.order_items:
                    order_item.status = True
                break

    def deactivate_order(self, order_number: int) -> None:
        """
        Deactivates an order and all its associated order items.
        
        Args:
            order_number: Order number to deactivate
        """
        for order in self.orders:
            if order.order_number == order_number:
                order.status = False
                self.site_fulfillment -= 1  # Decrement fulfilled sites counter
                for order_item in order.order_items:
                    order_item.status = False
                break   

    def unuseable_order(self, order_number: int) -> None:
        """
        Marks an order as unusable due to resource constraints.
        
        Args:
            order_number: Order number to mark as unusable
        """
        for order in self.orders:
            if order.order_number == order_number:
                order.unuseable = True
                for order_item in order.order_items:
                    order_item.status = False  # Deactivate all related order items
                break
        
    def connect_order_item_to_order(self):
        """
        Establishes connections between orders and their constituent order items.
        
        Links each order with its associated order items based on order numbers,
        creating the hierarchical structure needed for scheduling algorithms.
        """
        for order in self.orders:
            order.order_items = [order_item for order_item in self.order_items if order_item.order_number == order.order_number]





    def calculate_complexity(self):
        """
        Calculates complexity scores for all orders using multiple criteria.

        Uses Analytic Hierarchy Process (AHP) combined with Borda Count ranking
        to evaluate order complexity based on resource requirements, distances,
        and operational constraints. Higher complexity indicates more difficult scheduling.
        """
        # 1. Rank by number of order items (more items = higher complexity)
        self.complexity_rank(
            self.orders, 
            lambda order: len(order.order_item_ids), 
            "order_item_count",
            reverse=True  # More items = higher complexity rank
        )

        # 2. Rank by available regular drivers (fewer drivers = higher complexity)
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
            "regular_driver_count"  # Fewer drivers = higher complexity
        )

        # 3. Rank by average worker commute distance (longer = higher complexity)
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
            reverse=True  # Longer distances = higher complexity
        )

        # 4. Rank by average transport distance to other sites (longer = higher complexity)
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
            reverse=True  # Longer distances = higher complexity
        )

        # 5. Rank by number of different machine types required (more = higher complexity)
        self.complexity_rank(
            self.orders, 
            lambda order: len(set(
                item.machine_type for item in self.order_items if item.order_number == order.order_number
            )), 
            "machine_type_count",
            reverse=True  # More machine types = higher complexity
        )

        # 6. Rank by number of unique worker qualifications needed (more = higher complexity)
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
            reverse=True  # More qualifications = higher complexity
        )

        # 7. Rank by number of attachments required (more = higher complexity)
        self.complexity_rank(
            self.orders, 
            lambda order: len(list(
                item.equipment_types for item in self.order_items if item.order_number == order.order_number
            )), 
            "attachment_count",
            reverse=True  # More attachments = higher complexity
        )

        # 8. Calculate overall complexity using Borda Count with AHP weights
        self.complexity_borda_count_ahp()
        self.assign_complexity_classes_from_final_score()
    
    def complexity_rank(self, orders, key_func, rank_name, reverse=False):
        """
        Calculates ranking for orders based on a specific criterion.

        Args:
            orders: List of order objects to rank
            key_func: Function that extracts the ranking criterion value from each order
            rank_name: Name of the ranking criterion for storage
            reverse: If True, higher values get better ranks (for complexity metrics)
        """
        sorted_orders = sorted(orders, key=key_func, reverse=reverse)
        current_rank = 1
        last_value = None

        # Assign ranks, handling ties by giving same rank to equal values
        for i, order in enumerate(sorted_orders):
            value = key_func(order)
            if value != last_value:
                current_rank = i + 1
                last_value = value
            order._complexity[rank_name] = current_rank

    def complexity_borda_count_ahp(self):
        """
        Calculates overall complexity ranking using Borda Count with AHP weights.
        
        Combines individual criterion rankings into a single complexity score
        using Analytic Hierarchy Process weights to reflect criterion importance.
        """
        borda_count_ahp = {
            order.order_number: sum(
                (len(self.orders) - rank + 1)  # Convert rank to Borda points
                * self.complexity_ahp[rank_name]  # Apply AHP weight
                for rank_name, rank in order._complexity.items()
            )
            for order in self.orders
        }

        # Calculate final complexity ranking
        self.calculate_rank(
            self.orders, 
            lambda order: borda_count_ahp[order.order_number], 
            "complexity_borda_count_ahp", 
            reverse=True  # Higher Borda score = higher complexity rank
        )

    def assign_complexity_classes_from_final_score(self, num_classes: int = 3) -> None:
        """
        Assigns complexity classes to orders based on final Borda Count ranking.
        
        Orders are divided into complexity classes where class 1 represents the most
        complex orders requiring careful scheduling attention.
        
        Args:
            num_classes: Number of complexity classes to create (default: 3)
        """
        sorted_orders = sorted(self.orders, key=lambda order: order._complexity.get("complexity_borda_count_ahp", 0))
        total_orders = len(sorted_orders)
        if total_orders == 0:
            return
            
        group_size = total_orders / num_classes
        
        # Assign complexity classes and scores
        for i, order in enumerate(sorted_orders):
            complexity_class = int(i // group_size) + 1
            order.complexity_score = num_classes - complexity_class + 1  # Invert for intuitive scoring
            if complexity_class > num_classes:
                complexity_class = num_classes
            order.complexity_class = complexity_class




        
    def create_priorities_orders(self):
        """
        Generates priority rankings for all orders based on multiple scheduling criteria.

        Calculates priority scores using Borda Count and Analytic Hierarchy Process (AHP)
        to determine optimal order sequencing. Lower values indicate higher scheduling priority.
        """
        # 1. Rank by number of order items (fewer items = higher priority)
        self.calculate_rank(
            self.orders, 
            lambda order: len(order.order_item_ids), 
            "order_item_count"  # Fewer items = easier to schedule first
        )

        # 2. Rank by available regular drivers (more drivers = higher priority)
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
            reverse=True  # More regular drivers = higher priority
        )

        # 3. Rank by average worker commute distance (shorter = higher priority)
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
            "worker_distance"  # Shorter distances = higher priority
        )

        # 4. Rank by average transport distance (shorter = higher priority)
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
            "transport_distance"  # Shorter distances = higher priority
        )

        # 5. Rank by machine type diversity (fewer types = higher priority)
        self.calculate_rank(
            self.orders, 
            lambda order: len(set(
                item.machine_type for item in self.order_items if item.order_number == order.order_number
            )), 
            "machine_type_count"  # Fewer machine types = higher priority
        )

        # 6. Rank by worker qualification requirements (fewer = higher priority)
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
            "worker_qualification_count"  # Fewer qualifications = higher priority
        )

        # 7. Rank by attachment requirements (fewer = higher priority)
        self.calculate_rank(
            self.orders, 
            lambda order: len(list(
                item.equipment_types for item in self.order_items if item.order_number == order.order_number
            )), 
            "attachment_count"  # Fewer attachments = higher priority
        )

        # 8. Calculate overall priority using Borda Count with AHP weights
        self.calculate_borda_count_ahp()

    def calculate_rank(self, orders, key_func, rank_name, reverse=False):
        """
        Calculates ranking for orders based on a specific criterion.

        Args:
            orders: List of order objects to rank
            key_func: Function that extracts the ranking criterion value from each order
            rank_name: Name of the ranking criterion for storage
            reverse: If True, higher values get better ranks
        """
        sorted_orders = sorted(orders, key=key_func, reverse=reverse)
        current_rank = 1
        last_value = None

        # Assign ranks, handling ties by giving same rank to equal values
        for i, order in enumerate(sorted_orders):
            value = key_func(order)
            if value != last_value:
                current_rank = i + 1
                last_value = value
            order._priority[rank_name] = current_rank

    def calculate_borda_count_ahp(self, ahp=True):
        """
        Calculates overall priority ranking using Borda Count with optional AHP weights.
        
        Args:
            ahp: If True, applies AHP weights; if False, uses equal weighting
        """
        if ahp:
            # Apply AHP weights to combine criteria importance
            borda_count_ahp = {
                order.order_number: sum(
                    (len(self.orders) - rank + 1)  # Convert rank to Borda points
                    * self._ahp_weights[rank_name]  # Apply AHP weight
                    for rank_name, rank in order._priority.items()
                )
                for order in self.orders
            }

            # Calculate final priority ranking with AHP weights
            self.calculate_rank(
                self.orders, 
                lambda order: borda_count_ahp[order.order_number], 
                "borda_count_ahp", 
                reverse=True  # Higher Borda score = higher priority rank
            )

        elif not ahp:
            # Use simple Borda Count without weights
            borda_count = {
                order.order_number: sum(
                    (len(self.orders) - rank + 1)  # Convert rank to Borda points
                    for rank_name, rank in order._priority.items()
                )
                for order in self.orders
            }

            # Calculate final priority ranking without weights
            self.calculate_rank(
                self.orders, 
                lambda order: borda_count[order.order_number], 
                "borda_count", 
                reverse=True  # Higher Borda score = higher priority rank
            )



    def _find_instance_file(self) -> tuple[str, str]:
        """
        Recursively searches for the instance file in the Data/Instanzen directory.
        
        Returns:
            Tuple containing the absolute path to the found file and parent folder name
            
        Raises:
            FileNotFoundError: If the instance file is not found in the directory structure
        """
        base_path = Path.cwd().parent / "OptRail_Railroad_Construction" / "Data" / "Instanzen"
        for file_path in base_path.rglob(self.instance_filename):  # Recursive search
            print(f"Found file: {file_path}")
            print(f"Parent folder: {file_path.parent.name}")
            return str(file_path.resolve()), file_path.parent.name

        raise FileNotFoundError(f"File '{self.instance_filename}' not found in directory '{base_path}'.")

    def _load_data(self) -> None:
        """
        Loads raw data from the JSON instance file and creates object collections.
        
        Parses the JSON structure and initializes lists of Order, OrderItem, Machine,
        Worker, and Attachment objects along with route matrices for optimization.
        """
        with open(self._data_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            
            # Extract instance metadata and time boundaries
            self._start_date = datetime.fromisoformat(data.get("Start", "1970-01-01T00:00:00"))
            self._end_date = datetime.fromisoformat(data.get("Ende", "1970-01-01T00:00:00"))
            self._contains_durations = data.get("EnthaeltDauern", False)

            # Create object collections from JSON data
            self._orders = [Order(order) for order in data.get("Auftraege", [])]
            self._order_items = [OrderItem(item) for item in data.get("Bestellpositionen", [])]
            #self._attachments = [Attachment(attachment) for attachment in data.get("Anbaugeraete", [])]
            self._workers = [Worker(worker) for worker in data.get("Arbeiter", [])]
            self._machines = [Machine(machine) for machine in data.get("Maschinen", [])]

            # Convert route matrices from nested dictionaries to 2D arrays
            self._transport_routes = self._convert_square_2d_list(data.get("TransportwegeString", {}))
            self._work_routes = self._convert_rectangular_2d_list(data.get("ArbeitswegeString", {}))

    
            
            
    def _transfrom_data(self) -> None:
        """
        Transforms and enriches loaded data for optimization algorithm consumption.
        
        Converts route matrices from order-based to order-item-based indexing,
        calculates derived properties, and establishes relationships between objects.
        """
        # Convert distance matrices to order-item level for detailed scheduling
        self._transport_routes_order_item = self._convert_from_order_to_order_item(self._transport_routes, "transport")
        self._work_routes_order_item = self._convert_from_order_to_order_item(self._work_routes, "work")

        # Classify order items as day or night shifts
        for order_item in self.order_items:
            order_item.day_or_night(self)

        # Enrich resource objects with scheduling relationships and constraints
        for machine in self.machines:
            machine.add_data(self)  # Add predecessor/successor relationships
        for worker in self.workers:
            worker.add_data(self)   # Add possible assignments and constraints

        # Calculate distance statistics for normalization in optimization algorithms
        self._average_transport_distance = sum(sum(row) for row in self._transport_routes) / (len(self._transport_routes)*len(self._transport_routes[0]))
        self._min_transport_distance = min(min(row) for row in self._transport_routes if any(row))            
        self._max_transport_distance = max(max(row) for row in self._transport_routes if any(row))
        self._average_work_distance = sum(sum(row) for row in self._work_routes) / (len(self._work_routes)*len(self._work_routes[0]))
        self._min_work_distance = (min(min(row) for row in self._work_routes if any(row)))
        self._max_work_distance = (max(max(row) for row in self._work_routes if any(row)))
        self._max_duration = max(order_item.duration for order_item in self._order_items)
        self._min_duration = min(order_item.duration for order_item in self._order_items)

        # Establish order-to-order-item hierarchical relationships
        self.connect_order_item_to_order()

        # Optional data analysis and preparation (currently disabled)
        # self.check_order_usability()        # Validate resource availability
        # self.calculate_complexity()          # Calculate order complexity scores
        # self.create_priorities_orders()      # Generate priority rankings

        # Initialize dynamic scheduling data structures
        self.planned_shifts_worker = dict()   # Track planned worker shifts by order
        self.planned_shifts_machine = dict()  # Track planned machine shifts by order
        for order in self.orders:
            self.planned_shifts_worker[order] = list()
            self.planned_shifts_machine[order] = list()
            


            



    def _convert_from_order_to_order_item(self, routes_matrix, route_type):
        """
        Converts route matrices from order-based to order-item-based indexing.
        
        Args:
            routes_matrix: Original route matrix indexed by orders
            route_type: Type of routes ("transport" or "work")
            
        Returns:
            New matrix indexed by order items for detailed scheduling
        """
        final_routes_matrix = []

        if route_type == "transport":
            # Create transport distance matrix between all order item pairs
            for order_item_1 in self.order_items:
                row = []
                for order_item_2 in self.order_items:
                    distance = routes_matrix[order_item_1.order_number][order_item_2.order_number]
                    row.append(distance)
                final_routes_matrix.append(row)

        elif route_type == "work":
            # Create work commute distance matrix from workers to order items
            for worker in self.workers:
                row = []
                for order_item in self.order_items:
                    distance = routes_matrix[worker.personal_number][order_item.order_number]
                    row.append(distance)
                final_routes_matrix.append(row)

        return final_routes_matrix

    def _convert_square_2d_list(self, routes_dict: dict) -> List[List[Optional[float]]]:
        """
        Converts nested dictionary of routes to a square 2D matrix.
        
        Args:
            routes_dict: Nested dictionary with start->end->distance structure
            
        Returns:
            Square matrix with distances indexed by start and end locations
        """
        max_index = max(int(key) for key in routes_dict.keys())
        routes_matrix = [[None for _ in range(max_index + 1)] for _ in range(max_index + 1)]

        # Fill matrix with distances from dictionary
        for start, destinations in routes_dict.items():
            start_idx = int(start)
            for end, distance in destinations.items():
                end_idx = int(end)
                routes_matrix[start_idx][end_idx] = float(distance)
        
        return routes_matrix

    def _convert_rectangular_2d_list(self, routes_dict: dict) -> List[List[Optional[float]]]:
        """
        Converts nested dictionary of routes to a rectangular 2D matrix.
        
        Args:
            routes_dict: Nested dictionary with worker->order->distance structure
            
        Returns:
            Rectangular matrix with distances from workers to orders
        """
        # Determine matrix dimensions from dictionary keys
        row_count = max(int(key) for key in routes_dict.keys()) + 1
        col_count = max(int(dest_key) for destinations in routes_dict.values() for dest_key in destinations.keys()) + 1
        routes_matrix = [[None for _ in range(col_count)] for _ in range(row_count)]

        # Fill matrix with distances from dictionary
        for start, destinations in routes_dict.items():
            start_idx = int(start)
            for end, distance in destinations.items():
                end_idx = int(end)
                routes_matrix[start_idx][end_idx] = float(distance)
        
        return routes_matrix

    # Property accessors for data objects and configuration parameters
    
    @property
    def orders(self) -> List['Order']:
        """Returns list of all construction orders in the instance."""
        return self._orders

    @property
    def order_items(self) -> List['OrderItem']:
        """Returns list of all individual work tasks within orders."""
        return self._order_items

#   @property
#   def attachments(self) -> List['Attachment']:
#       """Returns list of all available construction attachments."""
#       return self._attachments

    @property
    def workers(self) -> List['Worker']:
        """Returns list of all available construction workers."""
        return self._workers

    @property
    def machines(self) -> List['Machine']:
        """Returns list of all available construction machines."""
        return self._machines

    @property
    def start_date(self) -> datetime:
        """Returns the project start date."""
        return self._start_date

    @property
    def end_date(self) -> datetime:
        """Returns the project end date."""
        return self._end_date

    @property
    def contains_durations(self) -> bool:
        """Returns whether the instance contains duration information."""
        return self._contains_durations

    @property
    def transport_routes(self) -> List[List[Optional[float]]]:
        """Returns the transport distance matrix between orders."""
        return self._transport_routes

    @property
    def work_routes(self) -> List[List[Optional[float]]]:
        """Returns the commute distance matrix from workers to orders."""
        return self._work_routes
    
    @property
    def transport_routes_order_item(self) -> List[List[Optional[float]]]:
        """Returns the transport distance matrix between order items."""
        return self._transport_routes_order_item
    
    @property
    def work_routes_order_item(self) -> List[List[Optional[float]]]:
        """Returns the commute distance matrix from workers to order items."""
        return self._work_routes_order_item
    
    @property
    def average_transport_distance(self) -> float:
        """Returns the average transport distance for normalization."""
        return self._average_transport_distance
    
    @property
    def average_work_distance(self) -> float:
        """Returns the average work commute distance for normalization."""
        return self._average_work_distance
    
    @property
    def min_transport_distance(self) -> float:
        """Returns the minimum transport distance for normalization."""
        return self._min_transport_distance
    
    @property
    def min_work_distance(self) -> float:
        """Returns the minimum work commute distance for normalization."""
        return self._min_work_distance
    
    @property
    def max_transport_distance(self) -> float:
        """Returns the maximum transport distance for normalization."""
        return self._max_transport_distance
    
    @property
    def max_work_distance(self) -> float:
        """Returns the maximum work commute distance for normalization."""
        return self._max_work_distance

    @property
    def min_duration(self) -> float:
        """Returns the minimum duration of all order items for normalization."""
        return self._min_duration

    @property
    def max_duration(self) -> float:
        """Returns the maximum duration of all order items for normalization."""
        return self._max_duration


class Order:
    """
    Represents a construction order containing multiple work tasks.
    
    Each order corresponds to a construction site with specific time windows,
    location coordinates, and a collection of order items that define the
    required work to be completed.
    """
    
    def __init__(self, json_data):
        """
        Initialize order from JSON data structure.
        
        Args:
            json_data: Dictionary containing order information from instance file
        """
        # Basic order identification and timing
        self._order_number = int(json_data.get("Auftragsnummer", ""))
        self._site_number = int(json_data.get("Baustellennummer", 0))
        self._start_time = datetime.fromisoformat(json_data.get("Start", "1970-01-01T00:00:00"))
        self._end_time = datetime.fromisoformat(json_data.get("Ende", "1970-01-01T00:00:00"))
        self._order_item_ids = [int(item) for item in json_data.get("BestellpositionenStrings", [])]
        self._location = json_data.get("Standort", {"Item1": 0.0, "Item2": 0.0})
        
        # Analysis and optimization metadata
        self._priority = {}          # Priority ranking scores for different criteria
        self._complexity = {}        # Complexity ranking scores for different criteria
        
        # Dynamic scheduling state
        self.dynamic_percentage = 0  # Percentage of order completion
        self.status = False          # Whether order is active in current solution
        self.unuseable = False       # Whether order can be completed with available resources
        self.complexity_score = None # Overall complexity score (1-3, higher = more complex)
        self.complexity_class = None # Complexity class assignment





    # Property accessors for Order attributes
    
    @property
    def order_number(self) -> str:
        """Returns the unique order number identifier."""
        return self._order_number

    @property
    def site_number(self) -> int:
        """Returns the construction site number where work is to be performed."""
        return self._site_number

    @property
    def start_time(self) -> datetime:
        """Returns the earliest allowed start time for this order."""
        return self._start_time

    @property
    def end_time(self) -> datetime:
        """Returns the latest allowed completion time for this order."""
        return self._end_time

    @property
    def order_item_ids(self) -> List[str]:
        """Returns list of order item IDs that belong to this order."""
        return self._order_item_ids

    @property
    def location(self) -> Tuple[float, float]:
        """Returns the geographic coordinates (latitude, longitude) of the construction site."""
        latitude = self._location.get("Item1", 0.0)
        longitude = self._location.get("Item2", 0.0)
        return (latitude, longitude)
    
    @property
    def priority(self) -> dict[str, int]:
        """Returns dictionary of priority rankings for different criteria."""
        return self._priority
    
    @property
    def complexity(self) -> dict[str, int]:
        """Returns dictionary of complexity rankings for different criteria."""
        return self._complexity

    def __str__(self):
        """Returns string representation of the order with key information."""
        return (f"Order(Order Number: {self._order_number}, Site Number: {self._site_number}, "
                f"Start: {self._start_time}, End: {self._end_time}, "
                f"Order Item IDs: {self._order_item_ids}, Location: {self.location})")


class OrderItem:
    """
    Represents an individual work task within a construction order.
    
    Each order item defines specific work requirements including machine type,
    worker qualifications, attachments needed, timing constraints, and duration.
    Order items are the atomic units of work that get scheduled to resources.
    """
    
    def __init__(self, json_data):
        """
        Initialize order item from JSON data structure.
        
        Args:
            json_data: Dictionary containing order item information from instance file
        """
        # Basic identification and timing
        self._id = int(json_data.get("ID", 0))
        self._start_time = datetime.fromisoformat(json_data.get("Start", "1970-01-01T00:00:00"))
        self._end_time = datetime.fromisoformat(json_data.get("Ende", "1970-01-01T00:00:00"))
        self._duration = int(json_data.get("Dauer", 0))
        self._order_number = int(json_data.get("Auftragsnummer", ""))
        
        # Resource requirements
        self._machine_type = int(json_data.get("MaschinenTyp", 0))
        self._equipment_types = json_data.get("AnbaugeraeteTypen", [])
        self._worker_qualifications = json_data.get("ArbeiterQualifikationen", [])
        self._assigned_machine = json_data.get("zugewieseneMaschine", None)
        self._type = int(json_data.get("Typ", 0))
        
        # Scheduling state
        self.status = False  # Whether this order item is included in current solution

    def day_or_night(self, input_data: InputData):
        """
        Classifies the order item as day or night shift based on start time.
        
        Args:
            input_data: InputData instance containing shift boundary configuration
        """
        if self._start_time.hour < input_data._day_and_night_shift_boundary:
            self.day_shift = True
            self.night_shift = False
        else:
            self.night_shift = True
            self.day_shift = False

        




    # Property accessors for OrderItem attributes
    
    @property
    def id(self) -> int:
        """Returns the unique order item identifier."""
        return self._id

    @property
    def start_time(self) -> datetime:
        """Returns the scheduled start time for this work task."""
        return self._start_time

    @property
    def end_time(self) -> datetime:
        """Returns the scheduled end time for this work task."""
        return self._end_time

    @property
    def duration(self) -> int:
        """Returns the expected duration of work in hours."""
        return self._duration

    @property
    def order_number(self) -> str:
        """Returns the order number this item belongs to."""
        return self._order_number

    @property
    def machine_type(self) -> int:
        """Returns the type of machine required for this work task."""
        return self._machine_type

    @property
    def equipment_types(self) -> List[int]:
        """Returns list of attachment/equipment types required."""
        return self._equipment_types

    @property
    def worker_qualifications(self) -> List[int]:
        """Returns list of worker qualifications required."""
        return self._worker_qualifications

    @property
    def assigned_machine(self) -> Optional[int]:
        """Returns the machine ID if pre-assigned, None otherwise."""
        return self._assigned_machine

    @property
    def type(self) -> int:
        """Returns the work task type identifier."""
        return self._type

    def __str__(self):
        """Returns string representation of the order item with key information."""
        return (f"OrderItem(ID: {self._id}, Start: {self._start_time}, End: {self._end_time}, "
                f"Duration: {self._duration}, Order Number: {self._order_number}, "
                f"Machine Type: {self._machine_type}, Equipment Types: {self._equipment_types}, "
                f"Worker Qualifications: {self._worker_qualifications}, Assigned Machine: {self._assigned_machine}, Type: {self._type})")


class Attachment:
    """
    Represents construction equipment attachments that can be mounted on machines.
    
    Attachments provide specialized functionality for construction tasks and have
    compatibility constraints with both machines and order requirements. They must
    be transported between job sites and scheduled efficiently.
    """
    
    def __init__(self, json_data):
        """
        Initialize attachment from JSON data structure.
        
        Args:
            json_data: Dictionary containing attachment information from instance file
        """
        # Basic attachment properties
        self._id = int(json_data.get("ID", 0))
        self._year_of_manufacture = int(json_data.get("Baujahr", 0))
        self._type = int(json_data.get("Typ", 0))
        
        # Scheduling and compatibility data (populated during data transformation)
        self._possible_order_items = dict()     # Order items compatible with this attachment
        self._possible_order_item_ids = dict()  # IDs of compatible order items
        self._predecessors = dict()             # Order items that can precede others in sequence
        self._predecessor_ids = dict()          # IDs of predecessor order items
        self._successors = dict()               # Order items that can follow others in sequence
        self._successor_ids = dict()            # IDs of successor order items


    def add_data(self, input_data: InputData):
        """
        Enriches attachment with scheduling and compatibility information.
        
        Calculates which order items are compatible with this attachment and
        determines feasible sequencing relationships based on transport times.
        
        Args:
            input_data: InputData instance containing all scheduling information
        """
        # Initialize compatibility dictionaries for each order
        self._possible_order_items = {order: [] for order in input_data.orders}
        self._possible_order_item_ids = {order.order_number: [] for order in input_data.orders}

        # Find order items that require this attachment type
        for order_item in input_data.order_items:
            for order in input_data.orders:
                if order_item.order_number == order.order_number and self._type in order_item.equipment_types:
                    self._possible_order_items[order].append(order_item)
                    self._possible_order_item_ids[order.order_number].append(order_item.id)

        # Calculate predecessor and successor relationships for scheduling
        all_order_items = list({oi for items in self._possible_order_items.values() for oi in items})
        seconds_per_day = input_data._seconds_a_day
        speed_kmh = input_data._transport_speed_kmh
        transport_matrix = input_data._transport_routes_order_item

        # Convert all order item times to normalized day values
        times = {
            oi.id: (
                (oi.start_time - input_data.start_date).total_seconds() / seconds_per_day,
                (oi.end_time - input_data.start_date).total_seconds() / seconds_per_day
            )
            for oi in all_order_items
        }

        # Initialize relationship dictionaries
        self._predecessors.clear()
        self._predecessor_ids.clear()
        self._successors.clear()
        self._successor_ids.clear()

        # Calculate feasible sequencing relationships
        for oi1 in all_order_items:
            self._predecessors[oi1] = []
            self._predecessor_ids[oi1.id] = []
            self._successors[oi1] = []
            self._successor_ids[oi1.id] = []

            st1, et1 = times[oi1.id]  # Start and end times for first order item
            for oi2 in all_order_items:
                if oi1.id == oi2.id:
                    continue  # Skip self-comparison
                    
                st2, et2 = times[oi2.id]  # Start and end times for second order item
                transport_time = transport_matrix[oi1.id][oi2.id] / speed_kmh / 24  # Convert to days

                # Check if oi2 can precede oi1 (oi2 ends + transport time <= oi1 starts)
                if st1 >= et2 + transport_time:
                    self._predecessors[oi1].append(oi2)
                    self._predecessor_ids[oi1.id].append(oi2.id)

                # Check if oi1 can precede oi2 (oi1 ends + transport time <= oi2 starts)
                if st2 >= et1 + transport_time:
                    self._successors[oi1].append(oi2)
                    self._successor_ids[oi1.id].append(oi2.id)
            
        

    # Property accessors for Attachment attributes
    
    @property
    def id(self) -> int:
        """Returns the unique attachment identifier."""
        return self._id

    @property
    def year_of_manufacture(self) -> int:
        """Returns the manufacturing year of the attachment."""
        return self._year_of_manufacture

    @property
    def type(self) -> int:
        """Returns the attachment type identifier."""
        return self._type
    
    @property
    def possible_order_items(self) -> dict[int, List[int]]:
        """Returns dictionary mapping orders to compatible order items."""
        return self._possible_order_items
    
    @property
    def possible_order_item_ids(self) -> dict[int, List[int]]:
        """Returns dictionary mapping order numbers to compatible order item IDs."""
        return self._possible_order_item_ids
    
    @property
    def predecessors(self) -> dict[int, List[int]]:
        """Returns dictionary of order items that can precede each order item."""
        return self._predecessors
    
    @property
    def successors(self) -> dict[int, List[int]]:
        """Returns dictionary of order items that can follow each order item."""
        return self._successors
    
    @property
    def predecessor_ids(self) -> dict[int, List[int]]:
        """Returns dictionary of predecessor order item IDs."""
        return self._predecessor_ids
    
    @property
    def successor_ids(self) -> dict[int, List[int]]:
        """Returns dictionary of successor order item IDs."""
        return self._successor_ids

    def __str__(self):
        """Returns string representation of the attachment with key information."""
        return f"Attachment(ID: {self._id}, Type: {self._type}, Year of Manufacture: {self._year_of_manufacture})"


class Worker:
    """
    Represents a construction worker with specific qualifications and constraints.
    
    Workers have skill sets that determine which order items they can perform,
    residential locations affecting commute distances, and work hour limitations
    for compliance with labor regulations.
    """
    
    def __init__(self, json_data):
        """
        Initialize worker from JSON data structure.
        
        Args:
            json_data: Dictionary containing worker information from instance file
        """
        # Basic worker information
        self._personal_number = int(json_data.get("Personalnummer", 0))
        self._name = str(json_data.get("Name", ""))
        self._qualifications = json_data.get("Qualifikationen", [])
        self._residence = json_data.get("Wohnort", {"Item1": 0.0, "Item2": 0.0})
        
        # Scheduling and compatibility data (populated during data transformation)
        self._possible_order_items = dict()     # Order items this worker can perform
        self._possible_order_item_ids = dict()  # IDs of compatible order items
        self._predecessors = dict()             # Order items that can precede others in worker's schedule
        self._predecessor_ids = dict()          # IDs of predecessor order items
        self._successors = dict()               # Order items that can follow others in worker's schedule
        self._successor_ids = dict()            # IDs of successor order items
        
        # Work tracking
        self.work_hours = 0  # Total work hours assigned to this worker

    def add_data(self, input_data: InputData):
        """
        Enriches worker with scheduling and compatibility information.
        
        Determines which order items this worker can perform based on qualifications,
        calculates feasible work sequences considering travel and rest time requirements.
        
        Args:
            input_data: InputData instance containing all scheduling information
        """
        # Initialize compatibility dictionaries for each order
        self._possible_order_items = {order: [] for order in input_data.orders}
        self._possible_order_item_ids = {order.order_number: [] for order in input_data.orders}

        # Find order items this worker can perform based on qualifications
        qualifications_set = set(self._qualifications)
        for order_item in input_data.order_items:
            # Worker can perform task if they have all required qualifications (or task has no requirements)
            if not order_item.worker_qualifications or set(order_item.worker_qualifications).issubset(qualifications_set):
                for order in input_data.orders:
                    if order_item.order_number == order.order_number:
                        self._possible_order_items[order].append(order_item)
                        self._possible_order_item_ids[order.order_number].append(order_item.id)
                        break

        # Calculate predecessor and successor relationships for worker scheduling
        all_order_items = [item for items in self._possible_order_items.values() for item in items]
        seconds_per_day = input_data._seconds_a_day
        speed_kmh = input_data._transport_speed_kmh
        break_time = input_data._hours_between_shifts / 24  # Convert to days
        transport_matrix = input_data._transport_routes_order_item

        # Convert all order item times to normalized day values
        rtimes = {
            oi.id: (
                (oi.start_time - input_data.start_date).total_seconds() / seconds_per_day,
                (oi.end_time - input_data.start_date).total_seconds() / seconds_per_day
            )
            for oi in all_order_items
        }

        # Initialize relationship dictionaries
        self._predecessors.clear()
        self._predecessor_ids.clear()
        self._successors.clear()
        self._successor_ids.clear()

        # Calculate feasible work sequences considering travel and rest time
        for oi1 in all_order_items:
            self._predecessors[oi1] = []
            self._predecessor_ids[oi1.id] = []
            self._successors[oi1] = []
            self._successor_ids[oi1.id] = []

            st1, et1 = rtimes[oi1.id]  # Start and end times for first order item
            for oi2 in all_order_items:
                if oi1.id == oi2.id:
                    continue  # Skip self-comparison

                st2, et2 = rtimes[oi2.id]  # Start and end times for second order item
                transport_time = transport_matrix[oi1.id][oi2.id] / speed_kmh / 24  # Convert to days
                added_time = max(transport_time, break_time)  # Use larger of transport or rest time

                # Debug output for transport time usage (normally disabled)
                if added_time == transport_time:
                    print(f"Transport time {transport_time} for {oi1.id} to {oi2.id} is used as added time.")

                # Check if oi2 can precede oi1 (oi2 ends + break/transport time <= oi1 starts)
                if st1 >= et2 + added_time:
                    self._predecessors[oi1].append(oi2)
                    self._predecessor_ids[oi1.id].append(oi2.id)
                
                # Check if oi1 can precede oi2 (oi1 ends + break/transport time <= oi2 starts)
                if st2 >= et1 + added_time:
                    self._successors[oi1].append(oi2)
                    self._successor_ids[oi1.id].append(oi2.id)

        # Identify night shift work for compliance tracking
        self._night_shifts = [oi for oi in all_order_items if oi.night_shift]
        self._night_shift_ids = [oi.id for oi in self._night_shifts]

    # Property accessors for Worker attributes
    
    @property
    def personal_number(self) -> int:
        """Returns the unique worker personal identification number."""
        return self._personal_number

    @property
    def name(self) -> str:
        """Returns the worker's name."""
        return self._name

    @property
    def qualifications(self) -> List[int]:
        """Returns list of qualification IDs this worker possesses."""
        return self._qualifications

    @property
    def residence(self) -> Tuple[float, float]:
        """Returns the worker's residential coordinates (latitude, longitude)."""
        latitude = self._residence.get("Item1", 0.0)
        longitude = self._residence.get("Item2", 0.0)
        return (latitude, longitude)
    
    @property
    def possible_order_items(self) -> dict[int, List[int]]:
        """Returns dictionary mapping orders to order items this worker can perform."""
        return self._possible_order_items
    
    @property
    def possible_order_item_ids(self) -> dict[int, List[int]]:
        """Returns dictionary mapping order numbers to compatible order item IDs."""
        return self._possible_order_item_ids
    
    @property
    def predecessors(self) -> dict[int, List[int]]:
        """Returns dictionary of order items that can precede each order item in worker's schedule."""
        return self._predecessors
    
    @property
    def successors(self) -> dict[int, List[int]]:
        """Returns dictionary of order items that can follow each order item in worker's schedule."""
        return self._successors
    
    @property
    def predecessor_ids(self) -> dict[int, List[int]]:
        """Returns dictionary of predecessor order item IDs for scheduling."""
        return self._predecessor_ids
    
    @property
    def successor_ids(self) -> dict[int, List[int]]:
        """Returns dictionary of successor order item IDs for scheduling."""
        return self._successor_ids
    
    @property
    def night_shifts(self) -> List[int]:
        """Returns list of night shift order items this worker can perform."""
        return self._night_shifts
    
    @property
    def night_shift_ids(self) -> List[int]:
        """Returns list of night shift order item IDs for compliance tracking."""
        return self._night_shift_ids

    def __str__(self):
        """Returns string representation of the worker with key information."""
        return (f"Worker(Personal Number: {self._personal_number}, Name: {self._name}, "
                f"Qualifications: {self._qualifications}, Residence: {self.residence})")


class Machine:
    """
    Represents a construction machine with specific capabilities and operators.
    
    Machines have types that determine compatibility with order items, regular
    drivers for optimal operation, and transport constraints between job sites.
    They are major resources in the scheduling optimization process.
    """
    
    def __init__(self, json_data):
        """
        Initialize machine from JSON data structure.
        
        Args:
            json_data: Dictionary containing machine information from instance file
        """
        # Basic machine properties
        self._id = int(json_data.get("ID", 0))
        self._year_of_manufacture = int(json_data.get("Baujahr", 0))
        self._name = str(json_data.get("Name", ""))
        self._type = int(json_data.get("Typ", 0))
        self._default_drivers = [int(driver) for driver in json_data.get("StammfahrerStrings", [])]
        
        # Scheduling and compatibility data (populated during data transformation)
        self._possible_order_items = dict()     # Order items this machine can perform
        self._possible_order_item_ids = dict()  # IDs of compatible order items
        self._predecessors = dict()             # Order items that can precede others in machine's schedule
        self._predecessor_ids = dict()          # IDs of predecessor order items
        self._successors = dict()               # Order items that can follow others in machine's schedule
        self._successor_ids = dict()            # IDs of successor order items

    def add_data(self, input_data: InputData):
        """
        Enriches machine with scheduling and compatibility information.
        
        Determines which order items this machine can perform based on machine type,
        calculates feasible sequencing relationships considering transport times.
        
        Args:
            input_data: InputData instance containing all scheduling information
        """
        # Initialize compatibility dictionaries for each order
        for order in input_data.orders:
            self._possible_order_items[order] = []
            self._possible_order_item_ids[order.order_number] = []

        # Find order items this machine can perform based on machine type compatibility
        for order_item in input_data.order_items:
            if order_item.machine_type == self.type:
                for order in input_data.orders:
                    if order_item.order_number == order.order_number:
                        self._possible_order_items[order].append(order_item)
                        self._possible_order_item_ids[order.order_number].append(order_item.id)

        # Calculate predecessor and successor relationships for machine scheduling
        seconds_per_day = input_data._seconds_a_day
        speed_kmh = input_data._transport_speed_kmh
        transport_matrix = input_data._transport_routes_order_item

        # Get all order items this machine can work on
        all_order_items = list({oi for items in self._possible_order_items.values() for oi in items})
        
        # Convert all order item times to normalized day values
        times = {
            oi.id: (
                (oi.start_time - input_data.start_date).total_seconds() / seconds_per_day,
                (oi.end_time - input_data.start_date).total_seconds() / seconds_per_day
            )
            for oi in all_order_items
        }

        # Initialize relationship dictionaries
        self._predecessors.clear()
        self._predecessor_ids.clear()
        self._successors.clear()
        self._successor_ids.clear()

        # Calculate feasible machine sequencing relationships
        for oi1 in all_order_items:
            self._predecessors[oi1] = []
            self._predecessor_ids[oi1.id] = []
            self._successors[oi1] = []
            self._successor_ids[oi1.id] = []

            st1, et1 = times[oi1.id]  # Start and end times for first order item
            for oi2 in all_order_items:
                if oi1.id == oi2.id:
                    continue  # Skip self-comparison

                st2, et2 = times[oi2.id]  # Start and end times for second order item
                transport_time = transport_matrix[oi1.id][oi2.id] / speed_kmh / 24  # Convert to days

                # Check if oi2 can precede oi1 (oi2 ends + transport time <= oi1 starts)
                if st1 >= et2 + transport_time:
                    self._predecessors[oi1].append(oi2)
                    self._predecessor_ids[oi1.id].append(oi2.id)

                # Check if oi1 can precede oi2 (oi1 ends + transport time <= oi2 starts)
                if st2 >= et1 + transport_time:
                    self._successors[oi1].append(oi2)
                    self._successor_ids[oi1.id].append(oi2.id)


    # Property accessors for Machine attributes
    
    @property
    def id(self) -> int:
        """Returns the unique machine identifier."""
        return self._id

    @property
    def year_of_manufacture(self) -> int:
        """Returns the manufacturing year of the machine."""
        return self._year_of_manufacture

    @property
    def name(self) -> str:
        """Returns the machine name or model designation."""
        return self._name

    @property
    def type(self) -> int:
        """Returns the machine type identifier."""
        return self._type

    @property
    def default_drivers(self) -> List[int]:
        """Returns list of regular driver IDs who can operate this machine optimally."""
        return self._default_drivers
    
    @property
    def possible_order_items(self) -> dict[int, List[int]]:
        """Returns dictionary mapping orders to order items this machine can perform."""
        return self._possible_order_items
    
    @property
    def possible_order_item_ids(self) -> dict[int, List[int]]:
        """Returns dictionary mapping order numbers to compatible order item IDs."""
        return self._possible_order_item_ids
    
    @property
    def predecessors(self) -> dict[int, List[int]]:
        """Returns dictionary of order items that can precede each order item in machine's schedule."""
        return self._predecessors
    
    @property
    def successors(self) -> dict[int, List[int]]:
        """Returns dictionary of order items that can follow each order item in machine's schedule."""
        return self._successors
    
    @property
    def predecessor_ids(self) -> dict[int, List[int]]:
        """Returns dictionary of predecessor order item IDs for scheduling."""
        return self._predecessor_ids
    
    @property
    def successor_ids(self) -> dict[int, List[int]]:
        """Returns dictionary of successor order item IDs for scheduling."""
        return self._successor_ids

    def __str__(self):
        """Returns string representation of the machine with key information."""
        return (f"Machine(ID: {self._id}, Name: {self._name}, Type: {self._type}, "
                f"Year of Manufacture: {self._year_of_manufacture}, Default Drivers: {self._default_drivers})")