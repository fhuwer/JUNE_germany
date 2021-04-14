import pytest
import numpy as np
import pandas as pd
import numpy.testing as npt
from time import time

from june.geography import geography as g


@pytest.fixture()
def geography_example():
    return g.Geography.from_file(filter_key={"super_area": ["D07339"]})


def test__create_geographical_hierarchy():
    hierarchy_df = pd.DataFrame(
        {
            "area": ["area_1", "area_2", "area_3", "area_4",],
            "super_area": [
                "super_area_1",
                "super_area_1",
                "super_area_1",
                "super_area_2",
            ],
            "region": ["region_1", "region_1", "region_1", "region_2"],
        }
    )
    area_coordinates_df = pd.DataFrame(
        {
            "area": ["area_1", "area_2", "area_3", "area_4"],
            "longitude": [0.0, 1.0, 2.0, 3.0],
            "latitude": [0.0, 1.0, 2.0, 3.0],
        }
    )
    area_coordinates_df.set_index("area", inplace=True)
    super_area_coordinates_df = pd.DataFrame(
        {
            "super_area": ["super_area_1", "super_area_2"],
            "longitude": [0.0, 1.0],
            "latitude": [0.0, 1.0],
        }
    )
    super_area_coordinates_df.set_index("super_area", inplace=True)
    areas, super_areas, regions = g.Geography.create_geographical_units(
        hierarchy=hierarchy_df,
        area_coordinates=area_coordinates_df,
        super_area_coordinates=super_area_coordinates_df,
    )

    assert len(areas) == 4
    assert len(super_areas) == 2
    assert len(regions) == 2

    assert regions[0].super_areas[0].name == super_areas[0].name
    assert regions[1].super_areas[0].name == super_areas[1].name

    assert super_areas[0].region == regions[0]
    assert super_areas[1].region == regions[1]

    assert super_areas[0].areas == [areas[0], areas[1], areas[2]]
    assert super_areas[1].areas == [areas[3]]


def test__nr_of_members_in_units(geography_example):
    assert len(geography_example.areas) == 66
    assert len(geography_example.super_areas) == 1


def test__area_attributes(geography_example):
    area = geography_example.areas.get_from_name("D073390005005")
    assert area.name == "D073390005005"
    npt.assert_almost_equal(
        area.coordinates, [49.947799484915365, 7.9360448700887485], decimal=3,
    )
    assert area.super_area.name == "D07339"


def test__super_area_attributes(geography_example):
    super_area = geography_example.super_areas.get_from_name("D07339")
    assert super_area.name == "D07339"
    npt.assert_almost_equal(
        super_area.coordinates, [49.92201623715109, 8.079637166959145], decimal=3,
    )
    assert "D073390005005" in [area.name for area in super_area.areas]


def test__create_single_area():
    geography = g.Geography.from_file(filter_key={"area": ["D073390005005"]})
    assert len(geography.areas) == 1


def test_create_ball_tree_for_super_areas():
    geo = g.Geography.from_file(filter_key={"super_area": ["D07315", "D07339"]})
    super_area = geo.super_areas.get_closest_super_areas(
        coordinates=[49.974186337513885, 8.241497125821837]
    )[0]
    assert super_area.name == "D07315"
    assert (
        len(
            geo.super_areas.get_closest_super_areas(
                coordinates=[49.974186337513885, 8.241497125821837], k=2
            )
        )
        == 2
    )
    assert (
        len(
            geo.areas.get_closest_areas(
                coordinates=[49.974186337513885, 8.241497125821837], k=10
            )
        )
        == 10
    )
