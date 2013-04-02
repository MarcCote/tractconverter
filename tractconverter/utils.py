import os
import logging

from tractconverter.formats.tck import TCK
from tractconverter.formats.trk import TRK
from tractconverter.formats.fib import FIB
from tractconverter.formats.vtk import VTK

from tractconverter.formats.header import Header

# Supported format
FORMATS = {"tck": TCK,
           "trk": TRK,
           "fib": FIB,
           "vtk": VTK}

# Input and output extensions.
EXT_ANAT = ".nii|.nii.gz"


def is_supported(filename):
    return detect_format(filename) is not None


def detect_format(filename):
    if not os.path.isfile(filename):
        return filename[-3:] in FORMATS.keys()

    for format in FORMATS.values():
        if format._check(filename):
            return format

    return None


def convert(input, output):
    nbFibers = 0
    fibers = []
    for i, f in enumerate(input):
        fibers.append(f)
        if (i + 1) % 100 == 0:
            output += fibers
            fibers = []

        nbFibers += 1

    output += fibers
    output.close()

    logging.info('Done! (' + str(nbFibers) + "/" + str(input.hdr[Header.NB_FIBERS]) + ' fibers)')
