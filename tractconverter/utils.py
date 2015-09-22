import os
import logging
from pdb import set_trace as dbg

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


def convert(input, output, verbose=False, keep_open=False):
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

    if not keep_open:
        output.close()

    logging.info('Done! (' + str(nbFibers) + "/" + str(input.hdr[Header.NB_FIBERS]) + ' fibers)')
    return nbFibers


def merge(inputs, output, verbose=False):
    #from tractconverter.formats.header import Header

    #streamlines = []
    nb_streamlines = 0
    for input in inputs:
        nb_streamlines += convert(input, output, verbose=verbose, keep_open=True)
        #streamlines += [s for s in f]

    #output.hdr[Header.NB_FIBERS] = len(streamlines)
    #output.writeHeader() # Update existing header
    #output += streamlines

    # I'm not sure this is doing something anyway.
    output.close()

    logging.info('Done! (' + str(nb_streamlines) + " streamlines merged.)")
