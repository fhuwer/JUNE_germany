import numpy as np
from june.groups import University, Universities
from june.geography import Area, Areas, SuperArea, Geography, SuperAreas


def test__university_init():
    university = University(coordinates = np.array([1, 2]), n_students_max = 500)
    assert (university.coordinates == np.array([1,2])).all()
    assert university.n_students_max == 500

def test__university_for_super_areas():
    super_area = SuperArea(name="mainz", areas=None, coordinates=[49.974186337513885, 8.241497125821837])
    area = Area(name='mainz_central', super_area=super_area, coordinates=super_area.coordinates)
    areas = Areas([area])
    super_area.areas = areas
    super_areas = SuperAreas([super_area])
    unis  = Universities.for_areas(areas)
    durham_uni = unis[0]
    assert durham_uni.n_students_max == 31064


