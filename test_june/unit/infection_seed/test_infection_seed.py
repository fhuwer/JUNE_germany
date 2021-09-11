import pandas as pd
import pytest
import numpy as np
from collections import Counter
from june.geography import Geography, SuperArea, SuperAreas, Area
from june.demography import Demography, Person, Population
from june import World
from june.infection_seed import InfectionSeed
from pathlib import Path
from june.time import Timer

from june import paths

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
        dir_pwd.parent.parent.parent
        / "configs/defaults/transmission/TransmissionConstant.yaml"
)

infpath = paths.data_path / "infection_seed/infektionen.csv"

@pytest.fixture(name="world", scope="module")
def create_world():
    people = [
        Person.from_attributes(age=np.random.randint(0, 100), sex="f")
        for i in range(100)
    ]
    world = World()
    world.people = Population(people)
    area_1 = Area(name="area_1", super_area=None, coordinates=None)
    area_1.people = people[:20]
    area_2 = Area(name="area_2", super_area=None, coordinates=None)
    area_2.people = people[20:]
    super_area_1 = SuperArea("super_1", areas=[area_1], coordinates=(1.0, 1.0))
    super_area_2 = SuperArea("super_2", areas=[area_2], coordinates=(1.0, 2.0))
    super_areas = [super_area_1, super_area_2]
    world.super_areas = SuperAreas(super_areas)
    return world


def clean_world(world):
    for person in world.people:
        person.infection = None
        person.susceptibility = 1.0


def test__simplest_seed(world, selector):
    seed = InfectionSeed(
        world=world,
        infection_selector=selector,
        path_to_csv=infpath,
    )
    n_cases = 10
    seed.unleash_virus(Population(world.people), n_cases=n_cases)
    infected_people = len([person for person in world.people if person.infected])
    assert infected_people == n_cases


def test__seed_strength(world, selector):
    clean_world(world)
    n_cases = 10
    seed = InfectionSeed(
        world=world,
        infection_selector=selector,
        seed_strength=0.2,
        path_to_csv=infpath,
    )
    seed.unleash_virus(Population(world.people), n_cases=n_cases)
    infected_people = len([person for person in world.people if person.infected])
    np.testing.assert_allclose(0.2 * n_cases, infected_people, rtol=0.01)


def test__infection_by_super_area(world, selector):
    clean_world(world)
    seed = InfectionSeed(
        world=world,
        infection_selector=selector,
        path_to_csv=infpath,
    )
    n_cases_by_super_area = pd.DataFrame(
        {
            "sex": ['m', 'm', 'w', 'w'],
            "age_bin": ["0-4", "5-14", "0-4", "5-14"],
            "super_1": [2, 3, 8, 2],
            "super_2": [4, 1, 1, 1]
        }
    ).set_index(['sex', 'age_bin'])

    seed.infect_super_areas(n_cases_by_super_area)

    infected_super_1 = len([person for person in world.super_areas[0].people if person.infected])
    infected_super_2 = len([person for person in world.super_areas[1].people if person.infected])
    for p in world.people.infected:
        assert p.age < 15

    assert infected_super_1 <= 8 + 2  # as only women are generated in dummy world
    assert infected_super_2 <= 1 + 1


def test__infection_by_super_area_errors(world, selector):
    clean_world(world)
    seed = InfectionSeed(
        world=world,
        infection_selector=selector,
        path_to_csv=infpath,
    )

    n_daily_cases_by_super_area = pd.DataFrame(
        {
            "sex": ['m', 'm', 'w', 'w'],
            "age_bin": ["0-4", "5-14", "0-4", "5-14"],
            "date": ["2020-04-20", "2020-04-20", "2020-04-20", "2020-04-20"],
            "super_3": [2, 3, 8, 2],
            "super_2": [4, 1, 1, 1]
        }
    ).set_index(['sex', 'age_bin'])

    with pytest.raises(KeyError, match=r"There is no data on cases for"):
        seed.infect_super_areas(n_daily_cases_by_super_area)


def test__infection_per_day(world, selector):
    clean_world(world)
    world.super_areas.members[0].name = "D01001"
    world.super_areas.members[1].name = "D01002"

    seed = InfectionSeed(
        world=world,
        infection_selector=selector,
        path_to_csv=infpath,
    )

    timer = Timer(initial_day="2020-04-20", total_days=7, )
    # each timestep during weekdays = 12h
    seed.unleash_virus_per_day(timer.date)
    next(timer)  # 2020-04-20 0:00
    assert (
            len([person for person in world.super_areas[0].people if person.infected]) == 0
    )
    assert (
            len([person for person in world.super_areas[1].people if person.infected]) == 9
    )

    seed.unleash_virus_per_day(timer.date)
    next(timer)  # 2020-04-20 12:00
    assert (
            len([person for person in world.super_areas[0].people if person.infected]) == 0
    )
    assert (
            len([person for person in world.super_areas[1].people if person.infected]) == 9
    )

    seed.unleash_virus_per_day(timer.date)
    next(timer)  # 2020-04-21 0:00

    assert (
            len([person for person in world.super_areas[0].people if person.infected])
            == 0 + 0
    )
    assert (
            len([person for person in world.super_areas[1].people if person.infected])
            == 9 + 4
    )

    seed.unleash_virus_per_day(timer.date)
    next(timer)  # 2020-04-21 12:00

    assert (
            len([person for person in world.super_areas[0].people if person.infected])
            == 0 + 0
    )
    assert (
            len([person for person in world.super_areas[1].people if person.infected])
            == 9 + 4
    )

    seed.unleash_virus_per_day(timer.date)
    next(timer)  # 2020-04-22 0:00

    assert (
            len([person for person in world.super_areas[0].people if person.infected])
            == 0 + 0
    )
    assert (
            len([person for person in world.super_areas[1].people if person.infected])
            == 9 + 4 + 3
    )


def test__age_profile(world, selector):
    clean_world(world)
    seed = InfectionSeed(
        world=world,
        infection_selector=selector,
        age_profile={"0-9": 0.0, "10-39": 1.0, "40-100": 0.0},
        path_to_csv=infpath,
    )
    seed.unleash_virus(Population(world.people), n_cases=20)
    should_not_infected = [
        person
        for person in world.people
        if person.infected and (person.age < 10 or person.age >= 40)
    ]

    assert len(should_not_infected) == 0
    should_infected = [
        person
        for person in world.people
        if person.infected and (10 <= person.age < 40)
    ]
    assert len(should_infected) == 20 
