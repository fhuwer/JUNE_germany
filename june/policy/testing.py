import logging
from datetime import datetime, timedelta
from .policy import Policy, PolicyCollection
from numpy.random import rand
from typing import List, Optional
from random import random

logger = logging.getLogger(__name__)



class Testing(Policy):
    population = None

    policy_type = 'testing'
    
    def __init__(self,
                start_time,
                end_time,
                primary_activity=None,
                frequency: dict=None,
                specificity: float=None,
                compliance: float=1.,
        ):
        self.frequency = frequency
        self.start_time = start_time
        self.end_time = end_time
        self.specificity = specificity
        self.primary_activity = primary_activity
        self.compliance = compliance

    @classmethod
    def get_world(self, world_people):
        self.population = world_people

    def _people_to_test(self):
        test_people = []
        if self.primary_activity is not None:
            for p in self.population:
                if not p.test_result:
                    if p.subgroups.primary_activity is not None:
                        if (
                            p.subgroups.primary_activity.group.spec
                            in self.primary_activity
                        ):
                            test_people.append(p)
        else:
            for p in self.population:
                if not p.test_result:
                    test_people.append(p)
        return test_people


class Testings(PolicyCollection):
    policy_type = "testing"

    def apply(self, initial_day, days_from_start, record: Optional["record"] = None):
        for policy in self.policies:
            people_to_test = policy._people_to_test()
            current_day = initial_day + timedelta(days=days_from_start)
            weekday = current_day.strftime("%A")

            if policy.is_active(datetime.date(current_day)):
                if policy.frequency.get(weekday, False):
                    for p in people_to_test:
                        true_pos, false_pos, true_neg, false_neg = -1, -1, -1, -1
                        if random() < policy.compliance:
                            p.days_from_start_of_test = days_from_start
                            if p.infected:
                                if rand() < self.sensitivity(p):
                                    p.test_result = True
                                    true_pos = p.id
                                else:
                                    p.test_result = False
                                    false_neg = p.id

                            else:
                                if rand() > policy.specificity:
                                    p.test_result = True
                                    false_pos = p.id
                                else:
                                    p.test_result = False
                                    true_neg = p.id
                            if record is not None:
                                record.accumulate(
                                    table_name="tests",
                                    region_name=p.super_area.region.name,
                                    false_positive_ids=false_pos,
                                    true_positive_ids=true_pos,
                                    false_negative_ids=false_neg,
                                    true_negative_ids=true_neg,
                                )

    def sensitivity(self, person):
        tag = str(person.symptoms.tag).split(".")[1]
        if tag == "exposed":
            return 0.1
        if tag == "mild":
            return 0.95
        if tag == "severe":
            return 0.99
        else:
            return 1
