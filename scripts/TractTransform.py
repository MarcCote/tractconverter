#!/usr/bin/env python
'''
Created on 2012-02-10

@author: coteharn
'''
import argparse
import logging
import os
import tractconverter.info as info
import nibabel as nib
import numpy as np

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
    p.add_argument(action='store', dest='input',
                   help='input track file ({0})'.format(",".join(FORMATS.keys())))
    p.add_argument(action='store', dest='output',
                   help='output track file ({0})'.format(",".join(FORMATS.keys())))
    p.add_argument('-ref', action='store', dest='ref',
                   metavar='FILE', required=False,
                   help='use affine from reference file ({0})'.format(EXT_ANAT))
    p.add_argument('-identity', action='store_true', dest='use_identity',
                   help='use identiy matrix as affine matrix')

    p.add_argument('-inverse', action='store_true', dest='is_inverse',
                   help='inverse affine matrix before tranforming')

    p.add_argument('-flip_x', action='store_true', dest='flip_x',
                   help='flip streamlines along X axis. (origin is infered by the affine matrix)')
    p.add_argument('-flip_y', action='store_true', dest='flip_y',
                   help='flip streamlines along Y axis. (origin is infered by the affine matrix)')
    p.add_argument('-flip_z', action='store_true', dest='flip_z',
                   help='flip streamlines along Z axis. (origin is infered by the affine matrix)')

    p.add_argument('-no_translate', action='store_false', dest='is_translate',
                   help='do not translate')
    p.add_argument('-no_scale', action='store_false', dest='is_scale',
                   help='do not scale')
    p.add_argument('-no_rotate', action='store_false', dest='is_rotate',
                   help='do not rotate')

    p.add_argument('-f', action='store_true', dest='is_force',
                   help='force (pass extension check; overwrite output file)')
    p.add_argument('-v', action='store_true', dest='is_verbose',
                   help='produce verbose output')
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()

    in_filename = args.input
    out_filename = args.output
    ref_filename = args.ref
    use_identity = args.use_identity

    is_inverse = args.is_inverse

    flip_x = args.flip_x
    flip_y = args.flip_y
    flip_z = args.flip_z
    is_translate = args.is_translate
    is_scale = args.is_scale
    is_rotate = args.is_rotate

    isForcing = args.is_force
    is_verbose = args.is_verbose

    if is_verbose:
        logging.basicConfig(level=logging.DEBUG)

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

    inFormat = tractconverter.detect_format(in_filename)
    outFormat = tractconverter.detect_format(out_filename)

    if ref_filename is not None:
        if not any(map(ref_filename.endswith, EXT_ANAT.split('|'))):
            if isForcing:
                logging.info('Reading "{0}" as a {1} file.'.format(ref_filename.split("/")[-1], EXT_ANAT))
            else:
                parser.error('Reference file must be one of {1}!'.format(EXT_ANAT))

        if not os.path.isfile(ref_filename):
            parser.error('"{0}" must be an existing file!'.format(ref_filename))

        affine = nib.load(ref_filename).get_affine()
    elif use_identity:
        affine = np.eye(4)
    else:
        # Enable command line history
        import readline
        readline.parse_and_bind('tab: complete')

        print "Enter the affine matrix to use (16 floats or 4x4 matrix):"
        affine = []
        while len(affine) < 16:
            txt = raw_input()
            affine += map(float, txt.split())

            if len(affine) > 16:
                affine = []
                print "You entered more than 16 floats!"
                print "Enter the affine matrix to use (16 floats or 4x4 matrix):"

        affine = np.array(affine[:16]).reshape((4, 4))

    if is_inverse:
        from numpy import linalg
        affine = linalg.inv(affine)

    if not is_translate:
        affine[:3, -1] = 0.0

    if not is_scale:
        affine[0, 0] /= affine[0, 0]
        affine[1, 1] /= affine[1, 1]
        affine[2, 2] /= affine[2, 2]

    if not is_rotate:
        affine[0, 1] = affine[0, 2] = 0.0
        affine[1, 0] = affine[1, 2] = 0.0
        affine[2, 0] = affine[2, 1] = 0.0

    if flip_x:
        affine[0, 0] = -affine[0, 0]

        # origin = affine[:3, -1]
        # M1 = np.eye(4)
        # M1[:3, -1] = -origin

        # M2 = np.eye(4)
        # M2[0, 0] = -affine[0, 0]

        # M3 = np.eye(4)
        # M3[:3, -1] = origin

        # M = np.dot(np.dot(M1, M2), M3)
        # affine[0, 0] = M[0, 0]
        # affine[0, -1] = M[0, -1]

    if flip_y:
        affine[1, 1] = -affine[1, 1]
        # origin = affine[:3, -1]
        # M1 = np.eye(4)
        # M1[:3, -1] = -origin

        # M2 = np.eye(4)
        # M2[1, 1] = -affine[1, 1]

        # M3 = np.eye(4)
        # M3[:3, -1] = origin

        # M = np.dot(np.dot(M1, M2), M3)
        # affine[1, 1] = M[1, 1]
        # affine[1, -1] = M[1, -1]

    if flip_z:
        affine[2, 2] = -affine[2, 2]
        # origin = affine[:3, -1]
        # M1 = np.eye(4)
        # M1[:3, -1] = -origin

        # M2 = np.eye(4)
        # M2[2, 2] = -affine[2, 2]

        # M3 = np.eye(4)
        # M3[:3, -1] = origin

        # M = np.dot(np.dot(M1, M2), M3)
        # affine[2, 2] = M[2, 2]
        # affine[2, -1] = M[2, -1]

    logging.info("Using affine matrix:\n" + str(affine))

    #Convert input to output
    input = inFormat(in_filename)
    output = outFormat.create(out_filename, input.hdr)
    tractconverter.transform(input, output, affine)

if __name__ == "__main__":
    main()
