'''
Created on 2012-02-22

@author: coteharn
'''


class Header:
    NB_FIBERS = 0
    STEP = 1
    METHOD = 2
    NB_SCALARS_BY_POINT = 3
    NB_PROPERTIES_BY_TRACT = 4
    NB_POINTS = 5
    VOXEL_SIZES = 6
    DIMENSIONS = 7
    MAGIC_NUMBER = 8
    ORIGIN = 9
    VOXEL_TO_WORLD = 10
    VOXEL_ORDER = 11
    WORLD_ORDER = 12
    ENDIAN = 13


def set_header_from_anat(anat_file, hdr):
    import nibabel
    anat = nibabel.load(anat_file)
    hdr[Header.VOXEL_SIZES] = list(anat.get_header().get_zooms())[:3]
    hdr[Header.DIMENSIONS] = list(anat.get_header().get_data_shape())
