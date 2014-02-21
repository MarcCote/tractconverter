#!/usr/bin/env python

import argparse
import logging
import os
import tractconverter.info as info

import tractconverter
from tractconverter import FORMATS
from tractconverter import EXT_ANAT

# Script description
DESCRIPTION = """
TractInfo {0}.
Print info about a streamlines file.
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
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()

    in_filename = args.input

    if not os.path.isfile(in_filename):
        parser.error('"{0}" must be an existing file!'.format(in_filename))

    if not tractconverter.is_supported(in_filename):
        parser.error('Input file must be one of {0}!'.format(",".join(FORMATS.keys())))

    inFormat = tractconverter.detect_format(in_filename)

    #Print info about the input file.
    print inFormat(in_filename, None)

if __name__ == "__main__":
    main()
