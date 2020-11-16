import numpy as np
import yaml
import numba as nb
from random import random
from typing import List, Dict
from itertools import chain
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from june.demography import Population

from june.exc import InteractionError
from june.utils import parse_age_probabilities
from june.groups.group.interactive import InteractiveGroup
from june.groups import InteractiveSchool
from june.records import Record
from june import paths

default_config_filename = paths.configs_path / "defaults/interaction/interaction.yaml"

default_sector_beta_filename = (
    paths.configs_path / "defaults/interaction/sector_beta.yaml"
)


class Interaction:
    """
    Class to handle interaction in groups.

    Parameters
    ----------
    alpha_physical
        Scaling factor for physical contacts, an alpha_physical factor of 1, means that physical
        contacts count as much as non-physical contacts.
    beta
        dictionary mapping the group specs with their contact intensities
    contact_matrices
        dictionary mapping the group specs with their contact matrices
    susceptibilities_by_age
        dictionary mapping age ranges to their susceptibility.
        Example: susceptibilities_by_age = {"0-13" : 0.5, "13-99" : 0.5}
        note that the right limit of the range is not included.
    population
        list of people to have the susceptibilities changed.
    """

    def __init__(
        self,
        alpha_physical: float,
        betas: Dict[str, float],
        contact_matrices: dict,
        susceptibilities_by_age: Dict[str, int] = None,
        population: "Population" = None,
        interactive_groups_config: dict = None,
    ):
        self.alpha_physical = alpha_physical
        self.betas = betas or {}
        self.interactive_groups_config = interactive_groups_config or {}
        contact_matrices = contact_matrices or {}
        self.contact_matrices = self.process_contact_matrices(
            input_contact_matrices=contact_matrices,
            groups=self.betas.keys(),
            alpha_physical=alpha_physical,
        )
        self.susceptibilities_by_age = susceptibilities_by_age
        if self.susceptibilities_by_age is not None:
            if population is None:
                raise InteractionError(
                    f"Need to pass population to change susceptibilities by age."
                )
            self.set_population_susceptibilities(
                susceptibilities_by_age=susceptibilities_by_age, population=population
            )
        self.beta_reductions = None # This dict is to keep track of beta reductions introduced by policies.

    @classmethod
    def from_file(
        cls,
        config_filename: str = default_config_filename,
        population: "Population" = None,
    ) -> "Interaction":
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        contact_matrices = config["contact_matrices"]
        if "susceptibilities" in config:
            susceptibilities_by_age = config["susceptibilities"]
        else:
            susceptibilities_by_age = None
        return Interaction(
            alpha_physical=config["alpha_physical"],
            betas=config["betas"],
            contact_matrices=contact_matrices,
            susceptibilities_by_age=susceptibilities_by_age,
            population=population,
            interactive_groups_config=config["interactive_groups"],
        )

    def set_population_susceptibilities(
        self, susceptibilities_by_age: dict, population: "Population"
    ):
        """
        Changes the population susceptibility to the disease.
        """
        susceptibilities_array = parse_age_probabilities(susceptibilities_by_age)
        for person in population:
            if person.age >= len(susceptibilities_array):
                person.susceptibility = susceptibilities_array[-1]
            else:
                person.susceptibility = susceptibilities_array[person.age]

    def process_contact_matrices(
        self, groups: List[str], input_contact_matrices: dict, alpha_physical: float
    ):
        """
        Processes the input data regarding to contacts to construct the contact matrix used in the interaction.
        In particular, given a contact matrix, a matrix of physical contact ratios, and the physical contact weighting
        (alpha_physical) constructs the contact matrix via:
        $ contact_matrix = contact_matrix * (1 + (alpha_physical - 1) * physical_ratios) $

        Parameters
        ----------
        groups
            a list of group names that will be handled by the interaction
        input_contact_data
            configuration regarding contact matrices and physical contacts
        alpha_physical
            The relative weight of physical conctacts respect o non-physical ones.
        """
        contact_matrices = {}
        for group in groups:
            # school is a special case.
            contact_data = input_contact_matrices.get(group, {})
            contact_matrix = np.array(contact_data.get("contacts", [[1]]))
            proportion_physical = np.array(contact_data.get("proportion_physical", [[0]]))
            characteristic_time = contact_data.get("characteristic_time", 8)
            if group == "school":
                contact_matrix = InteractiveSchool.get_processed_contact_matrix(
                    contact_matrix=contact_matrix,
                    proportion_physical=proportion_physical,
                    alpha_physical=alpha_physical,
                    characteristic_time=characteristic_time
                )
            else:
                contact_matrix = InteractiveGroup.get_processed_contact_matrix(
                    contact_matrix=contact_matrix,
                    proportion_physical=proportion_physical,
                    alpha_physical=alpha_physical,
                    characteristic_time=characteristic_time
                )
            contact_matrices[group] = contact_matrix
        return contact_matrices

    #def get_beta_for_group(self, group: "InteractiveGroup"):
    #    if self.regional_compliance is not None and group.spec in self.distanced_groups:
    #        beta = (
    #            self.original_betas[group.spec]
    #            * (self.beta_reductions[group.spec] - 1.0)
    #            * self.regional_compliance.get(group.region.name, 1.0)
    #            + self.original_betas[group.spec]
    #        )
    #    else:
    #        beta = self.beta[group.spec]
    #    return beta

    def time_step_for_group(
        self,
        group: "Group",
        delta_time: float,
        people_from_abroad: dict = None,
        record: Record = None,
    ):
        """
        Runs an interaction time step for the given interactive group. First, we
        give the beta and contact matrix to the group to process it. There may be groups
        that change the betas depending on the situation, ie, a school interactive group,
        has to treat the contact matrix on a special way, or the company beta may change
        due to the company's sector. Second, we iterate over all subgroups that contain
        susceptible people, and compute the interaction between them and the subgroups that
        contain infected people.

        Parameters
        ----------
        group:
            An instance of InteractiveGroup
        delta_time:
            Time interval of the interaction
        """
        interactive_group = group.get_interactive_group(
            people_from_abroad=people_from_abroad
        )
        if not interactive_group.must_timestep:
            return [], interactive_group.size
        infected_ids = []
        beta = group.get_processed_beta(beta=self.betas[group.spec])
        contact_matrix = self.contact_matrices[group.spec]
        for susceptible_subgroup_index, susceptible_subgroup_global_index in enumerate(
            group.subgroups_susceptible
        ):
            # the susceptible_subgroup_index tracks the particular subgroup inside the list of susceptible subgroups
            # the susceptible_subgroup_global_index tracks the particular subgroup inside the list of all subgroups
            infected_ids += self._time_step_for_subgroup(
                susceptible_subgroup_index=susceptible_subgroup_index,
                susceptible_subgroup_global_index=susceptible_subgroup_global_index,
                group=group,
                beta=beta,
                contact_matrix=contact_matrix,
                delta_time=delta_time,
            )
        if record:
            self._log_infections_to_record(
                infected_ids=infected_ids,
                interactive_group=interactive_group,
                record=record,
            )
        return infected_ids, interactive_group.size

    def _time_step_for_subgroup(
        self,
        susceptible_subgroup_index: int,
        susceptible_subgroup_global_index: int,
        group: InteractiveGroup,
        beta: float,
        contact_matrix: float,
        delta_time: float,
    ) -> List[int]:
        """
        Time step for one susceptible subgroup. We first compute the combined
        effective transmission probability of all the subgroups that contain infected
        people, and then run this effective transmission over the susceptible subgroup,
        to check who got infected.

        Parameters
        ----------
        susceptible_subgroup_index:
            index of the susceptible subgroup that is interacting with the infected subgroups.
        group
            The InteractiveGroup of the time step.
        beta
            Interaction intensity for this particular interactive group
        contact matrix
            contact matrix of this interactive group
        delta_time
            time interval
        """
        effective_transmission = self.compute_effective_transmission(
            susceptible_subgroup_global_index=susceptible_subgroup_global_index,
            group=group,
            beta=beta,
            contact_matrix=contact_matrix,
            delta_time=delta_time,
        )
        subgroup_infected_ids = self._sample_new_infected_people(
            effective_transmission=effective_transmission,
            subgroup_susceptible_ids=group.susceptible_ids[susceptible_subgroup_index],
            subgroup_suscetibilities=group.susceptibilities[susceptible_subgroup_index],
        )
        return subgroup_infected_ids

    def _compute_effective_transmission_exponent(
        self,
        susceptible_subgroup_global_index: int,
        group: InteractiveGroup,
        beta: float,
        contact_matrix: np.array,
        delta_time: float,
    ):
        """
        Computes the effective transmission probability of all the infected people in the group,
        that is, the sum of all infection probabilities divided by the number of infected people.
    
        Parameters
        ----------
        - subgroup_transmission_probabilities : transmission probabilities per subgroup.
        - susceptibles_group_idx : indices of suceptible people
        - infector_subgroup_sizes : subgroup sizes where the infected people are.
        - contact_matrix : contact matrix of the group
        """
        transmission_exponent = 0.0
        infector_subgroup_sizes = group.infector_subgroup_sizes
        for infector_subgroup_index, infector_subgroup_global_index in enumerate(
            infector_subgroup_sizes
        ):
            infector_subgroup_size = group.infector_subgroup_sizes[
                infector_subgroup_index
            ]
            # same logic in this loop as in the previous susceptible subgroups loop
            if infector_subgroup_global_index == susceptible_subgroup_global_index:
                # subgroup interacting with itself, must discount the own person.
                infector_subgroup_size -= 1
                if infector_subgroup_size == 0:
                    continue
            n_contacts_between_subgroups = group.get_contacts_between_subgroups(
                contact_matrix=contact_matrix,
                subgroup_1_idx=susceptible_subgroup_global_index,
                subgroup_2_idx=infector_subgroup_global_index,
            )
            infector_subgroup_mean_transmission_probability = (
                sum(group.transmission_probabilities[infector_subgroup_index])
                / infector_subgroup_size
            )
            transmission_exponent += (
                infector_subgroup_mean_transmission_probability
                * n_contacts_between_subgroups
            )
        return transmission_exponent * delta_time * beta

    def _sample_new_infected_people(
        self,
        effective_transmission_exponent,
        subgroup_susceptible_ids,
        subgroup_suscetibilities,
    ):
        """
        Samples for new infections in the interaction of a susceptible subgroup with all the infector subgroups.

        Parameters
        ----------
        effective_transmission_exponent
            Part of the exponent of the transmission probability. The complete formula is
            Ptrans = 1 - np.exp(- effective_transmission_exponent * susceptibility)
        susceptible_ids
            list of ids of susceptible people to check for new infections
        suscetibilities
            susceptibilities of the susceptible people
        """
        infected_ids = []
        for susceptible_id, susceptibility in zip(
            subgroup_susceptible_ids, subgroup_suscetibilities
        ):
            transmission_probability = 1.0 - np.exp(
                -effective_transmission_exponent * susceptibility
            )
            if random() < transmission_probability:
                infected_ids.append(susceptible_id)
        return infected_ids

    def _log_infections_to_record(
        self,
        infected_ids: list,
        interactive_group: InteractiveGroup,
        group: "Group",
        record: Record,
    ):
        """
        Logs new infected people to record, and their infectors.
        TODO: assign infection blame proportionally to transmission probability.
        """
        n_infected = len(infected_ids)
        tprob_norm = sum(interactive_group.transmission_probabilities)
        infector_ids = list(chain.from_iterable(interactive_group.infector_ids))
        infector_ids = np.random.choice(
            infector_ids,
            n_infected,
            # TODO: p=np.array(transmission_probabilities) / tprob_norm,
        )
        record.accumulate(
            table_name="infections",
            location_spec=group.spec,
            location_id=group.id,
            region_name=group.super_area.region.name,
            infected_ids=infected_ids,
            infector_ids=infector_ids,
        )
