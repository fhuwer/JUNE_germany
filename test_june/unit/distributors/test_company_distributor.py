from pytest import fixture 
from june.geography import Geography, SuperArea
from june.demography import Demography
from june import World
from june.groups import Companies, Company
from june.demography import Person
from june.distributors import CompanyDistributor


@fixture(name="super_area")
def make_super_area():
    super_area = SuperArea()
    for i in range(3):
        super_area.companies.append(Company(sector=i, n_workers_max=i))
        person = Person()
        person.sector = i
        super_area.workers.append(person)
    return super_area

def test__company_distributor(super_area):
    cd = CompanyDistributor()
    cd.distribute_adults_to_companies_in_super_area(super_area)
    for company in super_area.companies:
        assert len(company.people) == 1
        assert list(company.people)[0].sector == company.sector
