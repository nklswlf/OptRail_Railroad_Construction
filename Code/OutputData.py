'''
Notwendige Daten:
- Number of Tasks
- Worker Job Sequence
- Machine Job Sequence
- Attachment Job Sequence
- Travel Distance for each Worker and Machine
'''

import json
from InputData import *


class Solution:

    def __init__(self, route_plan_worker:dict, route_plan_machine:dict, route_plan_attachment:dict, data:InputData):
        ''' Define the attributes for solution'''

        self._number_tasks = -1
        self._route_plan_worker = route_plan_worker
        self._route_plan_machine = route_plan_machine
        self._route_plan_attachment = route_plan_attachment
        self._create_unused_tasks(data)
        self._travel_distance_worker = self._calculate_travel_distance_worker(data)
        self._travel_distance_machine = self._calculate_travel_distance_machine(data)
