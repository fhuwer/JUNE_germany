from collections import Counter
from covid.groups import *
import pickle
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

@pytest.fixture(name="hospitals", scope="session")
def create_hospitals():
    data_directory = Path(__file__).parent.parent.parent.parent
    hospital_path = data_directory / "data/processed/hospital_data/england_hospitals.csv"
    config_path = data_directory / "configs/defaults/hospitals.yaml"
    return Hospitals.from_file(hospital_path, config_path)

@pytest.fixture(name="hospitals_df", scope="session")
def create_hospitals_df():
    data_directory = Path(__file__).parent.parent.parent.parent
    hospital_path = data_directory / "data/processed/hospital_data/england_hospitals.csv"
    config_path = data_directory / "configs/defaults/hospitals.yaml"
    return  pd.read_csv(hospital_path)


def test__total_number_hospitals_is_correct(hospitals, hospitals_df):
    assert len(hospitals.members) == len(hospitals_df)


@pytest.mark.parametrize("index", [5, 20])
def test__given_hospital_finds_itself_as_closest(hospitals, hospitals_df, index):

    r_max = 150.
    distances, closest_idx = hospitals.get_closest_hospitals(
        hospitals_df[["Latitude", "Longitude"]].iloc[index].values, 
        r_max,
    )

    # All distances are actually smaller than r_max
    assert np.sum(distances > r_max) == 0

    closest_hospital_idx = closest_idx[0]

    assert hospitals.members[closest_hospital_idx].name == hospitals.members[index].name

class MockHealthInformation:
    def __init__(self, tag):
        self.tag = tag

@pytest.mark.parametrize("health_info", ["hospitalised", "intensive care"])
def test__add_patient_release_patient(hospitals, health_info):
    dummy_person = Person()
    dummy_person.health_information = MockHealthInformation(health_info) 
    assert dummy_person.in_hospital is None
    hospitals.members[0].add_as_patient(dummy_person)
    if health_info == 'hospitalised':
        assert hospitals.members[0].patients[0] == dummy_person
    elif health_info == 'intensive care':
        assert hospitals.members[0].icu_patients[0] == dummy_person
    assert dummy_person.in_hospital is not None

    hospitals.members[0].release_as_patient(dummy_person)
    assert dummy_person.in_hospital is None
    assert len(hospitals.members[0].icu_patients) == 0 
    assert len(hospitals.members[0].patients) == 0 


@pytest.mark.parametrize("health_info", ["hospitalised", "intensive care"])
def test__allocate_patient(hospitals, health_info):
    dummy_person = Person()
    dummy_person.health_information = MockHealthInformation(health_info) 
    assert dummy_person.in_hospital is None
    hospitals.allocate_patient(dummy_person)
    if health_info == 'hospitalised':
        assert hospitals.members[0].patients[0] == dummy_person
    elif health_info == 'intensive care':
        assert hospitals.members[0].icu_patients[0] == dummy_person
    assert dummy_person.in_hospital is not None

