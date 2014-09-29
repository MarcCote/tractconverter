import os
import logging
import numpy as np

from tractconverter.formats.tck import TCK
from tractconverter.formats.trk import TRK
from tractconverter.formats.fib import FIB
from tractconverter.formats.vtk import VTK

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
        return FORMATS.get(filename[-3:], None)

    for format in FORMATS.values():
        if format._check(filename):
            return format

    return None


def convert(input, output):
    from tractconverter.formats.header import Header

    nbFibers = 0
    fibers = []

    display_threshold = 10000 if input.hdr[Header.NB_FIBERS] > 100000 else 1000

    for i, f in enumerate(input):
        fibers.append(f)
        if (i + 1) % 1000 == 0:
            output += fibers
            fibers = []

        if i % display_threshold == 0:
            logging.info('(' + str(nbFibers) + "/" + str(input.hdr[Header.NB_FIBERS]) + ' fibers)')

        nbFibers += 1

    if len(fibers) > 0:
        output += fibers

    output.close()

    logging.info('Done! (' + str(nbFibers) + "/" + str(input.hdr[Header.NB_FIBERS]) + ' fibers)')


def merge(inputs, output):
    from tractconverter.formats.header import Header

    streamlines = []
    for f in inputs:
        streamlines += [s for s in f]

    output.hdr[Header.NB_FIBERS] = len(streamlines)
    output.writeHeader()  # Update existing header
    output += streamlines

    logging.info('Done! (' + str(len(streamlines)) + " streamlines merged.)")


def transform(input, output, affine):
    from tractconverter.formats.header import Header

    nbFibers = 0
    fibers = []
    for i, f in enumerate(input):
        fibers.append(np.dot(f, affine[:3, :3].T) + affine[:3, -1])
        if (i + 1) % 100 == 0:
            output += fibers
            fibers = []

        if i % 1000 == 0:
            logging.info('(' + str(nbFibers) + "/" + str(input.hdr[Header.NB_FIBERS]) + ' fibers)')

        nbFibers += 1

    if len(fibers) > 0:
        output += fibers

    output.close()

    logging.info('Done! (' + str(nbFibers) + "/" + str(input.hdr[Header.NB_FIBERS]) + ' fibers)')
