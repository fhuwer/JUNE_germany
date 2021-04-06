import numpy as np
import pandas as pd
import yaml

from .social_venue import SocialVenue, SocialVenues, SocialVenueError
from .social_venue_distributor import SocialVenueDistributor
from june.paths import data_path, configs_path

from june.geography import Geography
from june.geography import Area, Areas, SuperArea, SuperAreas


# loading the location of the gyms from a file
default_config_filename = configs_path / "defaults/groups/leisure/gyms.yaml"
# check path , in intput or in data
default_gyms_coordinates_filename = data_path / "input/leisure/gyms_per_super_area.csv"


class Gym(SocialVenue):
    max_size = 100
    pass


class Gyms(SocialVenues):
    social_venue_class = Gym
    default_coordinates_filename = default_gyms_coordinates_filename


class GymDistributor(SocialVenueDistributor):
    default_config_filename = default_config_filename
