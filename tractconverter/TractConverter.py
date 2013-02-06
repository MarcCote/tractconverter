'''
Created on 2012-02-10

@author: coteharn
'''
import argparse
import logging
import os
from tractconverter.formats.tck import TCK
from tractconverter.formats.trk import TRK
from tractconverter.formats.fib import FIB
from tractconverter.formats.vtk import VTK
from tractconverter.formats.header import Header

# Input and output extensions.
EXT_ANAT = ".nii|.nii.gz"

FORMATS = {"tck": TCK,
           "trk": TRK,
           "fib": FIB,
           "vtk": VTK}

# Script description
DESCRIPTION = 'Convert track files for {0}'.format(",".join(FORMATS.keys()))


def convert(inFile, outFile, anatFile):

    inFormat = FORMATS[inFile[-3:]]
    outFormat = FORMATS[outFile[-3:]]

    input = inFormat(inFile, anatFile)
    output = outFormat.create(outFile, input.hdr, anatFile)

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
#    args = parser.parse_args(['-i', r'P:\temp jc\for_marc\voi_seeding_1_1mm_Left_Brodmann_area_19_Roland_2_Left_Brodmann_area_37_Roland_det_curv0.tck',
#                              '-o', r'P:\temp jc\for_marc\voi_seeding_1_1mm_Left_Brodmann_area_19_Roland_2_Left_Brodmann_area_37_Roland_det_curv0.fib',
#                              '-a', r'P:\temp jc\for_marc\t1.nii',
#                              '-f', '-v'])

#    args = parser.parse_args(['-i', r'C:\tata.tck',
#                              '-o', r'C:\tata_tck.fib',
#                              '-a', r'C:\t2.nii.gz',
#                              '-f', '-v'])

    input = args.input
    output = args.output
    anat = args.anat
    isForcing = args.isForce
    isVerbose = args.isVerbose

    if isVerbose:
        logging.basicConfig(level=logging.DEBUG)

    if input[-3:] not in FORMATS.keys():
        parser.error('Input file must be one of {0}!'.format(",".join(FORMATS.keys())))

    if not os.path.isfile(input):
        parser.error('"{0}" must be an existing file!'.format(input))

    if output[-3:] not in FORMATS.keys():
        parser.error('Output file must be one of {0}!'.format(",".join(FORMATS.keys())))

    if os.path.isfile(output):
        if isForcing:
            logging.info('Overwriting "{0}".'.format(output))
        else:
            parser.error('"{0}" already exist! Use -f to overwrite it.'.format(output))

    if input[-3:] == output[-3:]:
        parser.error('Input and output must be from different types!'.format(",".join(FORMATS.keys())))

    if anat is not None:
        if not any(map(anat.endswith, EXT_ANAT.split('|'))):
            if isForcing:
                logging.info('Reading "{0}" as a {1} file.'.format(anat.split("/")[-1], EXT_ANAT))
            else:
                parser.error('Anatomy file must be one of {1}!'.format(EXT_ANAT))

        if not os.path.isfile(anat):
            parser.error('"{0}" must be an existing file!'.format(anat))

    convert(input, output, anat)

if __name__ == "__main__":
    main()
