#!/usr/bin/env python
'''
Created on 2012-02-10

@author: coteharn
'''
import argparse
import logging
import os
import tractconverter.info as info

import tractconverter
from tractconverter import FORMATS
from tractconverter import EXT_ANAT

# Script description
DESCRIPTION = """
TractConverter {0}.
Convert streamlines files.
Supported formats are {1}
""".format(info.__version__,
           ",".join(FORMATS.keys()))


#####
# Script part
###
def buildArgsParser():
    p = argparse.ArgumentParser(description=DESCRIPTION)
    p.add_argument('-i', action='store', dest='input',
                   metavar='FILE', required=True,
                   help='input track file ({0})'.format(",".join(FORMATS.keys())))
    p.add_argument('-o', action='store', dest='output',
                   metavar='FILE', required=True,
                   help='output track file ({0})'.format(",".join(FORMATS.keys())))
    p.add_argument('-a', action='store', dest='anat',
                   metavar='FILE', required=False,
                   help='input anatomy file ({0})'.format(EXT_ANAT))
    p.add_argument('-f', action='store_true', dest='isForce',
                   help='force (pass extension check; overwrite output file)')
    p.add_argument('-v', action='store_true', dest='isVerbose',
                   help='produce verbose output')
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()

    in_filename = args.input
    out_filename = args.output
    anat_filename = args.anat
    isForcing = args.isForce
    isVerbose = args.isVerbose

    if isVerbose:
        logging.basicConfig(level=logging.DEBUG)

    if not os.path.isfile(in_filename):
        parser.error('"{0}" must be an existing file!'.format(in_filename))

    if not tractconverter.is_supported(in_filename):
        parser.error('Input file must be one of {0}!'.format(",".join(FORMATS.keys())))

    if not tractconverter.is_supported(out_filename):
        parser.error('Output file must be one of {0}!'.format(",".join(FORMATS.keys())))

    if os.path.isfile(out_filename):
        if isForcing:
            if out_filename == in_filename:
                parser.error('Cannot use the same name for input and output files. Conversion would fail.')
            else:
                logging.info('Overwriting "{0}".'.format(out_filename))
        else:
            parser.error('"{0}" already exist! Use -f to overwrite it.'.format(out_filename))

    inFormat = tractconverter.detect_format(in_filename)
    outFormat = tractconverter.detect_format(out_filename)

    #if inFormat == outFormat:
    #    parser.error('Input and output must be from different types!'.format(",".join(FORMATS.keys())))

    if anat_filename is not None:
        if not any(map(anat_filename.endswith, EXT_ANAT.split('|'))):
            if isForcing:
                logging.info('Reading "{0}" as a {1} file.'.format(anat_filename.split("/")[-1], EXT_ANAT))
            else:
                parser.error('Anatomy file must be one of {1}!'.format(EXT_ANAT))

        if not os.path.isfile(anat_filename):
            parser.error('"{0}" must be an existing file!'.format(anat_filename))

    #Convert input to output
    input = inFormat(in_filename, anat_filename)
    output = outFormat.create(out_filename, input.hdr, anat_filename)
    tractconverter.convert(input, output)

if __name__ == "__main__":
    main()
