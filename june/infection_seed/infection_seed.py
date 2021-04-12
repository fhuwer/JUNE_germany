import numpy as np
import pandas as pd
from random import shuffle
import datetime
from collections import Counter
from june import paths
from typing import List, Optional

from june.records import Record
from june.domain import Domain
from june.demography import Population
from june.geography import SuperAreas
from june.infection.infection_selector import InfectionSelector
from june.infection.health_index.health_index import HealthIndexGenerator


class InfectionSeed:
    def __init__(
        self,
        world: "World",
        infection_selector: InfectionSelector,
        seed_strength: float = 1.0,
        age_profile: Optional[dict] = None,
        path_to_csv: Optional[str] = None,
        age_bins: Optional[dict] = None,
    ):
        """
        Class that generates the seed for the infection.

        Parameters
        ----------
        world:
            world to infect
        infection_selector:
            selector to generate infections
        seed_strength:
            float that controls the strength of the seed
        age_profile:
            dictionary with weight on age groups. Example:
            age_profile = {'0-20': 0., '21-50':1, '51-100':0.}
            would only infect people aged between 21 and 50
        path_to_csv:
            string with path to infektion.csv
        age_bins:
            dictionary with boolean to infect age groups.
            Required form: {'00-04':True,'05-14':False,'15-34':True,'35-59':True,'60-79':False,'80-':True}
            if path_to_csv is given but no age_bins dictionary,
            all age groups are infected.

        """
        self.world = world
        self.infection_selector = infection_selector
        self.seed_strength = seed_strength
        self.age_profile = age_profile
        if age_bins is not None:
            self.age_bins = list(
                filter(age_bins.get, age_bins)
            )  # select only True age bins
        else:
            self.age_bins = {
                "00-04": True,
                "05-14": True,
                "15-34": True,
                "35-59": True,
                "60-79": True,
                "80-120": True,
            }
        self.path_to_csv = path_to_csv
        if path_to_csv is not None:
            self.daily_super_area_cases = self.csv_to_daily_super_area_cases()
            self.min_date = datetime.datetime.strptime(self.daily_super_area_cases.columns.min(),"%Y-%m-%d")
            self.max_date = datetime.datetime.strptime(self.daily_super_area_cases.columns.max(),"%Y-%m-%d")
            self.dates_seeded = []

    def csv_to_daily_super_area_cases(self):
        """
        reads path_to_csv file and brings it to the form of daily_super_area_cases
        """
        df = pd.read_csv(self.path_to_csv)
        df.drop(columns=["_id", "ags2", "bundesland", "kreis"], inplace=True)
        df["ags5"] = df["ags5"].astype(str)
        df["ags5"] = df["ags5"].apply(lambda x: f"D{x:0>5}")
        df["sex"] = df["variable"].apply(
            lambda x: x[-7].lower()
            if x.startswith("kr_inf_") and len(x) == 14
            else x[-5].lower()
            if x.startswith("kr_inf_w")
            and len(x) == 12
            or x.startswith("kr_inf_m")
            and len(x) == 12
            else None
        )

        df["age_bin"] = df["variable"].apply(
            lambda x: f"{x[-4:-2]}-{x[-2:]}"
            if x.startswith("kr_inf_") and len(x) == 14
            else f"{x[-2:]}-120"
            if x.startswith("kr_inf_w")
            and len(x) == 12
            or x.startswith("kr_inf_m")
            and len(x) == 12
            else None
        )
        df["age_bin"] = df["age_bin"].apply(lambda x: x if x in self.age_bins else None)
        df = df[df["age_bin"].notna()]
        df = (
            df[df["sex"].notna()]
            .drop(columns=["variable"])
            .set_index(["ags5", "sex", "age_bin"])
        )
        redate = lambda x: x[1:5] + "-" + x[5:7] + "-" + x[7:9] if x[0] == "d" else x
        df.rename(mapper=redate, axis="columns", inplace=True)
        return df

    def unleash_virus(
        self,
        population: "Population",
        n_cases: int,
        mpi_rank: int = 0,
        mpi_comm: Optional["MPI.COMM_WORLD"] = None,
        mpi_size: Optional[int] = None,
        box_mode=False,
        record: Optional["Record"] = None,
    ):
        """
        Infects ```n_cases``` people in ```population```

        Parameters
        ----------
        population:
            population to infect
        n_cases:
            number of initial cases
        mpi_rank:
            rank of the process
        mpi_comm:
            mpi comm_world to enable communication between
            different processes
        mpi_size:
            number of processes
        box_mode:
            whether to run on box mode
        """

        if mpi_rank == 0:
            susceptible_ids = [
                person.id for person in population.people if person.susceptible
            ]
            n_cases = round(self.seed_strength * n_cases)
            if self.age_profile is None:
                ids_to_infect = np.random.choice(
                    susceptible_ids,
                    n_cases,
                    replace=False,
                )
            else:
                ids_to_infect = self.select_susceptiles_by_age(susceptible_ids, n_cases)
        if mpi_comm is not None:
            for rank_receiving in range(1, mpi_size):
                mpi_comm.send(ids_to_infect, est=rank_receiving, tag=0)
            if mpi_rank > 0:
                ids_to_infect = mpi_comm.recv(source=0, tag=0)
            for inf_id in ids_to_infect:
                if inf_id in self.world.people.people_dict:
                    person = self.world.people.get_from_id(inf_id)
                    self.infection_selector.infect_person_at_time(person, 0.0)
                    if record is not None:
                        record.accumulate(
                            table_name="infections",
                            location_spec="infection_seed",
                            region_name=person.super_area.region.name,
                            location_id=0,
                            infected_ids=[person.id],
                            infector_ids=[person.id],
                        )
        else:
            for inf_id in ids_to_infect:
                # if isinstance(self.world, Domain):
                if box_mode:
                    person_to_infect = self.world.members[0].people[inf_id]
                else:
                    person_to_infect = self.world.people.get_from_id(inf_id)
                self.infection_selector.infect_person_at_time(person_to_infect, 0.0)
                if record is not None:
                    record.accumulate(
                        table_name="infections",
                        location_spec="infection_seed",
                        region_name=person_to_infect.super_area.region.name,
                        location_id=0,
                        infected_ids=[person_to_infect.id],
                        infector_ids=[person_to_infect.id],
                    )

    def select_susceptiles_by_age(
        self, susceptible_ids: List[int], n_cases: int
    ) -> List[int]:
        """
        Select cases according to an age profile

        Parameters
        ----------
        susceptible_ids:
            list of ids of susceptible people to select from
        n_cases:
            number of cases

        Returns
        -------
        choices:
            ids of people to infect, following the age profile given
        """
        n_per_age_group = n_cases * np.array(list(self.age_profile.values()))
        shuffle(susceptible_ids)
        choices = []
        for idx, age_group in enumerate(self.age_profile.keys()):
            age_choices = self.get_people_from_age_group(
                susceptible_ids, int(round(n_per_age_group[idx])), age_group
            )
            choices.extend(age_choices)
        return choices

    def get_people_from_age_group(
        self, susceptible_ids: List[int], n_people: int, age_group: str
    ) -> List[int]:
        """
        Get ```n_people``` in a given ```age_group``` from the list of susceptible_ids

        Parameters
        ----------
        susceptible_ids:
            list of ids of susceptible people to select from
        n_people:
            number of people to select
        age_group:
            age limits to select from (Example: '18-25')

        Returns
        -------
        ids of people in age group
        """
        choices = []
        for person_id in susceptible_ids:
            if len(choices) == n_people:
                break
            if (
                int(age_group.split("-")[0])
                <= self.world.people.get_from_id(person_id).age
                < int(age_group.split("-")[1])
            ):
                choices.append(person_id)
        return choices

    def infect_super_areas(
        self, n_cases_per_super_area: pd.DataFrame, record: Optional["Record"] = None
    ):
        """
        Infect super areas with numer of cases given by data frame

        Parameters
        ----------
        n_cases_per_super_area:
            data frame containig the number of cases per super area
        """
        for super_area in self.world.super_areas:
            try:
                for sex in ["m", "w"]:
                    self.age_profile = n_cases_per_super_area[super_area.name][sex].to_dict()
                    if sex == "w":
                        sex = "f"
                    people = [p for p in super_area.people if p.sex == sex]

                    self.unleash_virus(
                        Population(people), n_cases=1, record=record
                    )  # n_cases is 1 since self.age_profile is already in absolute values

            except KeyError as e:
                raise KeyError("There is no data on cases for super area: %s" % str(e))

    def unleash_virus_per_day(self, date: "datetime", record: Optional[Record] = None):
        """
        Infect super areas at a given ```date```

        Parameters
        ----------
        date:
            datetime object
        """
        date_str = date.strftime("%Y-%m-%d")
        date = date.date()
        if (
            date not in self.dates_seeded
            and date_str in self.daily_super_area_cases.columns
        ):
            self.infect_super_areas(
                self.daily_super_area_cases.loc[:][date_str], record=record
            )
            self.dates_seeded.append(date)