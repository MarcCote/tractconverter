#!/usr/bin/env python

import argparse
import logging
import os
import tractconverter.info as info

import tractconverter
from tractconverter import FORMATS
from tractconverter import EXT_ANAT

from tractconverter.formats.header import Header

# Script description
DESCRIPTION = """
TractMerger {0}.
Merge streamlines files.
Supported formats are {1}
""".format(info.__version__,
           ",".join(FORMATS.keys()))


#####
# Script part
###
def buildArgsParser():
    p = argparse.ArgumentParser(description=DESCRIPTION)
    p.add_argument('-i', action='store', dest='input', nargs='+',
                   metavar='FILE', required=True,
                   help='input streamlines file ({0})'.format(",".join(FORMATS.keys())))
    p.add_argument('-o', action='store', dest='output',
                   metavar='FILE', required=True,
                   help='merged streamline file ({0})'.format(",".join(FORMATS.keys())))
    # p.add_argument('-a', action='store', dest='anat',
    #                metavar='FILE', required=False,
    #                help='input anatomy file ({0})'.format(EXT_ANAT))
    p.add_argument('-f', action='store_true', dest='isForce',
                   help='force (pass extension check; overwrite output file)')
    p.add_argument('-v', action='store_true', dest='isVerbose',
                   help='produce verbose output')
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()

    in_filenames = args.input
    out_filename = args.output
    #anat_filename = args.anat
    isForcing = args.isForce
    isVerbose = args.isVerbose

    if isVerbose:
        logging.basicConfig(level=logging.DEBUG)

    for in_filename in in_filenames:
        if not os.path.isfile(in_filename):
            parser.error('"{0}" must be an existing file!'.format(in_filename))

        if not tractconverter.is_supported(in_filename):
            parser.error('Input file must be one of {0}!'.format(",".join(FORMATS.keys())))

    if not tractconverter.is_supported(out_filename):
        parser.error('Output file must be one of {0}!'.format(",".join(FORMATS.keys())))

    if os.path.isfile(out_filename):
        if isForcing:
            logging.info('Overwriting "{0}".'.format(out_filename))
        else:
            parser.error('"{0}" already exist! Use -f to overwrite it.'.format(out_filename))

    inFormats = [tractconverter.detect_format(in_filename) for in_filename in in_filenames]
    outFormat = tractconverter.detect_format(out_filename)

    # if anat_filename is not None:
    #     if not any(map(anat_filename.endswith, EXT_ANAT.split('|'))):
    #         if isForcing:
    #             logging.info('Reading "{0}" as a {1} file.'.format(anat_filename.split("/")[-1], EXT_ANAT))
    #         else:
    #             parser.error('Anatomy file must be one of {1}!'.format(EXT_ANAT))

    #     if not os.path.isfile(anat_filename):
    #         parser.error('"{0}" must be an existing file!'.format(anat_filename))


    #TODO: Consider different anat, space.
    hdr = {}
    hdr[Header.DIMENSIONS] = (1,1,1)
    hdr[Header.ORIGIN] = (1,1,1)
    hdr[Header.NB_FIBERS] = 0  # The actual number of streamlines will be added later.

    #Merge inputs to output
    inputs = (in_format(in_filename) for in_filename, in_format in zip(in_filenames, inFormats))
    output = outFormat.create(out_filename, hdr)
    tractconverter.merge(inputs, output)

if __name__ == "__main__":
    main()
