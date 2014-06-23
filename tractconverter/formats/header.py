'''
Created on 2012-02-22

@author: coteharn
'''
import nibabel as nib
import numpy as np


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


def get_header_from_anat(anat_file, hdr={}):
    if anat_file is None:
        if len(hdr) == 0:
            # Defaults
            hdr[Header.VOXEL_SIZES] = (0, 0, 0)
            hdr[Header.DIMENSIONS] = (1, 1, 1)

        return hdr

    anat = nib.load(anat_file)

    hdr[Header.VOXEL_SIZES] = tuple(anat.get_header().get_zooms())[:3]
    hdr[Header.DIMENSIONS] = tuple(anat.get_header().get_data_shape())[:3]
    hdr[Header.VOXEL_TO_WORLD] = anat.get_header().get_best_affine()

    # We can guess the voxel order from the affine if there is no 0 on the diagonal.
    if not np.any(np.diag(hdr[Header.VOXEL_TO_WORLD]) == 0):
        hdr[Header.VOXEL_ORDER] = ''.join(nib.aff2axcodes(hdr[Header.VOXEL_TO_WORLD]))

    return hdr
