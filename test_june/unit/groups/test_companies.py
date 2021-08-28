import os
from pathlib import Path

import pytest
import numpy as np
import pandas as pd
from collections import defaultdict

from june.geography import Geography, Area
from june.demography import Person
from june.groups.company import Company, Companies


default_data_path = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "data/processed/census_data/company_data/"

@pytest.fixture(name="super_area_companies", scope="module")
def create_geography():
    g = Geography.from_file(filter_key={"super_area" : ["D07315"]})
    return g.super_areas.members[0]

@pytest.fixture(name="person")
def create_person():
    return Person(sex="m", age=44)


class TestCompany:
    @pytest.fixture(name="company")
    def create_company(self, super_area_companies):
        return Company(
            super_area = super_area_companies,
            n_workers_max = 115,
            sector = "Q",
        )
    
    def test__company_grouptype(self, company):
        assert company.SubgroupType.workers == 0

    def test__empty_company(self, company):
        assert len(company.people) == 0
    
    def test__filling_company(self, person, company):
        company.add(person)
        assert list(company.people)[0] == person

    def test__person_is_employed(self, person, company):
        company.add(person)
        assert person.primary_activity == company.subgroups[Company.SubgroupType.workers]


@pytest.fixture(name="companies_example")
def create_companies(super_area_companies):
    companies = Companies.for_super_areas(
        [super_area_companies],
    )
    return companies

def test__company_sizes(companies_example):
    assert len(companies_example) == 8328
    sizes_dict = defaultdict(int)
    bins = [0, 10, 50, 250, 1500]
    for company in companies_example:
        size = company.n_workers_max
        idx = np.searchsorted(bins, size) - 1
        sizes_dict[idx] += 1
    assert np.isclose(sizes_dict[0], 7459, atol=20)
    assert np.isclose(sizes_dict[1], 699, atol=20)
    assert np.isclose(sizes_dict[2], 141, atol=10)
    assert np.isclose(sizes_dict[3], 29, atol=10)

def test__company_ids(companies_example, super_area_companies):
    for company_id, company in companies_example.members_by_id.items():
        assert company.id == company_id
    for company in companies_example:
        assert company.super_area == super_area_companies

