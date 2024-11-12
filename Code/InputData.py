import json
import csv
import math
from pathlib import Path


from datetime import datetime
from typing import List, Tuple, Optional

class OrderItem:
    def __init__(self, json_data):
        # Convert and assign each attribute with explicit data type conversion and make them private
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

    def __str__(self):
        return (f"OrderItem(ID: {self._id}, Start: {self._start_time}, End: {self._end_time}, "
                f"Duration: {self._duration}h, Order Number: {self._order_number}, "
                f"Machine Type: {self._machine_type}, Equipment Types: {self._equipment_types}, "
                f"Worker Qualifications: {self._worker_qualifications}, Assigned Machine: {self._assigned_machine}, Type: {self._type})")

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
    

class Order:
    def __init__(self, json_data):
        # Initialisiert und setzt Standardwerte, falls bestimmte Felder fehlen
        self._order_number = str(json_data.get("Auftragsnummer", ""))
        self._site_number = int(json_data.get("Baustellennummer", 0))
        self._start_time = datetime.fromisoformat(json_data.get("Start", "1970-01-01T00:00:00"))
        self._end_time = datetime.fromisoformat(json_data.get("Ende", "1970-01-01T00:00:00"))
        self._order_item_ids = json_data.get("BestellpositionenStrings", [])
        self._location = json_data.get("Standort", {"Item1": 0.0, "Item2": 0.0})

    def __str__(self):
        return (f"Order(Order Number: {self._order_number}, Site Number: {self._site_number}, "
                f"Start Time: {self._start_time}, End Time: {self._end_time}, "
                f"Order Item IDs: {self._order_item_ids}, Location: {self._location})")

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
        '''Gibt die IDs der Bestellpositionen zurück, die diesem Auftrag zugeordnet sind'''
        return self._order_item_ids

    @property
    def location(self) -> Tuple[float, float]:
        '''Gibt die Standortkoordinaten als Tuple (Latitude, Longitude) zurück'''
        latitude = self._location.get("Item1", 0.0)
        longitude = self._location.get("Item2", 0.0)
        return (latitude, longitude)
    

class Attachment:
    def __init__(self, json_data):
        # Initialisiert und setzt Standardwerte für fehlende Felder
        self._id = int(json_data.get("ID", 0))
        self._year_of_manufacture = int(json_data.get("Baujahr", 0))
        self._type = int(json_data.get("Typ", 0))

    def __str__(self):
        return (f"Attachment(ID: {self._id}, Year of Manufacture: {self._year_of_manufacture}, "
                f"Type: {self._type})")

    @property
    def id(self) -> int:
        return self._id

    @property
    def year_of_manufacture(self) -> int:
        return self._year_of_manufacture

    @property
    def type(self) -> int:
        return self._type


class Worker:
    def __init__(self, json_data):
        # Initialisiert und setzt Standardwerte für fehlende Felder
        self._personal_number = int(json_data.get("Personalnummer", 0))
        self._name = str(json_data.get("Name", ""))
        self._qualifications = json_data.get("Qualifikationen", [])
        self._residence = json_data.get("Wohnort", {"Item1": 0.0, "Item2": 0.0})

    def __str__(self):
        return (f"Worker(Personal Number: {self._personal_number}, Name: {self._name}, "
                f"Qualifications: {self._qualifications}, Residence: {self.residence})")

    @property
    def personal_number(self) -> int:
        return self._personal_number

    @property
    def name(self) -> str:
        return self._name

    @property
    def qualifications(self) -> List[int]:
        '''Gibt die Liste der Qualifikationen des Arbeiters zurück'''
        return self._qualifications

    @property
    def residence(self) -> Tuple[float, float]:
        '''Gibt den Wohnort als Tuple (Latitude, Longitude) zurück'''
        latitude = self._residence.get("Item1", 0.0)
        longitude = self._residence.get("Item2", 0.0)
        return (latitude, longitude)
    

class Machine:
    def __init__(self, json_data):
        # Initialisiert und setzt Standardwerte für fehlende Felder
        self._id = int(json_data.get("ID", 0))
        self._year_of_manufacture = int(json_data.get("Baujahr", 0))
        self._name = str(json_data.get("Name", ""))
        self._type = int(json_data.get("Typ", 0))
        self._default_drivers = json_data.get("StammfahrerStrings", [])

    def __str__(self):
        return (f"Machine(ID: {self._id}, Year of Manufacture: {self._year_of_manufacture}, "
                f"Name: {self._name}, Type: {self._type}, Default Drivers: {self._default_drivers})")

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
        '''Gibt eine Liste der Standardfahrer für die Maschine zurück'''
        return self._default_drivers
    

import json
from pathlib import Path
from typing import List
from datetime import datetime

class InputData:
    '''Class for creating Data objects based on formatted JSON Files containing the information of orders, machines, workers, and attachments'''

    def __init__(self, instance_filename: str) -> None:
        '''
        Initialize the InputData object with paths to the JSON file.

        :param instance_filename: Name of the JSON file containing the data.
        '''
        self._data_path = str((Path.cwd() / "Data" / "Instanzen" / instance_filename).resolve())
        self._load_data()

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

    @property
    def orders(self) -> List['Order']:
        ''' Returns the list of orders '''
        return self._orders

    @property
    def order_items(self) -> List['OrderItem']:
        ''' Returns the list of order items '''
        return self._order_items

    @property
    def attachments(self) -> List['Attachment']:
        ''' Returns the list of attachments '''
        return self._attachments

    @property
    def workers(self) -> List['Worker']:
        ''' Returns the list of workers '''
        return self._workers

    @property
    def machines(self) -> List['Machine']:
        ''' Returns the list of machines '''
        return self._machines

    @property
    def start_date(self) -> datetime:
        ''' Returns the start date of the instance '''
        return self._start_date

    @property
    def end_date(self) -> datetime:
        ''' Returns the end date of the instance '''
        return self._end_date

    @property
    def contains_durations(self) -> bool:
        ''' Returns whether the instance contains durations '''
        return self._contains_durations
