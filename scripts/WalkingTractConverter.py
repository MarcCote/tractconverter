#!/usr/bin/env python
'''
Created on 2012-02-10

@author: coteharn
'''
import os
import os.path as path

import tractconverter
import argparse
import logging

from tractconverter import FORMATS
from tractconverter import EXT_ANAT


def walkAndConvert(p_input, p_conversions, p_output=None, p_anatFile=None, p_isRecursive=False, p_overwrite=False):

    for root, dirs, allFiles in os.walk(p_input):
        logging.info('Processing "{0}"...'.format(root))
        root = root + "/"
        nbFiles = 0
        for k, v in p_conversions.items():
            #files = [f for f in allFiles if FORMATS[k]._check(root + f)]
            for i, f in enumerate(allFiles):
                logging.info('{0}/{1} files'.format(i, len(allFiles)))

                if not FORMATS[k]._check(root + f):
                    logging.info('Skip')
                    continue

                nbFiles += 1
                inFile = root + f

                if p_output is not None:
                    outFile = p_output + '/' + f[:-3] + v
                else:
                    outFile = inFile[:-3] + v

                if path.exists(outFile) and not p_overwrite:
                    logging.info(f + " : Already Done!!!")
                    continue

                input = FORMATS[k](inFile, p_anatFile)
                output = FORMATS[v].create(outFile, input.hdr, p_anatFile)
                tractconverter.convert(input, output)
                logging.info(inFile)

        logging.info('{0} skipped (none track files)'.format(len(allFiles) - nbFiles))
        if not p_isRecursive:
            break

    logging.info("Conversion finished!")

#####
# Script part
###

#Script description
DESCRIPTION = 'Convert streamlines files while walking down a path. ({0})'.format(",".join(FORMATS.keys()))


def buildArgsParser():
    p = argparse.ArgumentParser(description=DESCRIPTION)
    p.add_argument('-i', action='store', dest='input',
                   metavar='DIR', required=True,
                   help='path to walk')
    p.add_argument('-o', action='store', dest='output',
                   metavar='DIR',
                   help='output folder (if omitted, the walking folder is used)')
    p.add_argument('-a', action='store', dest='anat',
                   metavar='FILE', required=False,
                   help='anatomy file ({0})'.format(EXT_ANAT))

    #VTK
    p.add_argument('-vtk2tck', action='store_true', dest='vtk2tck',
                   help='convert .vtk to .tck (anatomy needed)')
    p.add_argument('-vtk2trk', action='store_true', dest='vtk2trk',
                   help='convert .vtk to .trk')
    p.add_argument('-vtk2fib', action='store_true', dest='vtk2fib',
                   help='convert .vtk to .fib')
    #FIB
    p.add_argument('-fib2tck', action='store_true', dest='fib2tck',
                   help='convert .fib to .tck (anatomy needed)')
    p.add_argument('-fib2trk', action='store_true', dest='fib2trk',
                   help='convert .fib to .trk')
    p.add_argument('-fib2vtk', action='store_true', dest='fib2vtk',
                   help='convert .fib to .vtk')
    #TCK
    p.add_argument('-tck2fib', action='store_true', dest='tck2fib',
                   help='convert .tck to .fib (anatomy needed)')
    p.add_argument('-tck2trk', action='store_true', dest='tck2trk',
                   help='convert .tck to .trk (anatomy needed)')
    p.add_argument('-tck2vtk', action='store_true', dest='tck2vtk',
                   help='convert .tck to .vtk (anatomy needed)')
    #TRK
    p.add_argument('-trk2tck', action='store_true', dest='trk2tck',
                   help='convert .trk to .tck (anatomy needed)')
    p.add_argument('-trk2fib', action='store_true', dest='trk2fib',
                   help='convert .trk to .fib')
    p.add_argument('-trk2vtk', action='store_true', dest='trk2vtk',
                   help='convert .trk to .vtk')

    p.add_argument('-R', action='store_true', dest='isRecursive',
                   help='make a recursive walk')
    p.add_argument('-f', action='store_true', dest='isForce',
                   help='force (pass extension check; overwrite output file)')
    p.add_argument('-v', action='store_true', dest='isVerbose',
                   help='produce verbose output')

    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()

    input = args.input
    output = args.output
    anat = args.anat
    vtk2tck = args.vtk2tck
    vtk2trk = args.vtk2trk
    vtk2fib = args.vtk2fib
    fib2tck = args.fib2tck
    fib2trk = args.fib2trk
    fib2vtk = args.fib2vtk
    trk2tck = args.trk2tck
    trk2fib = args.trk2fib
    trk2vtk = args.trk2vtk
    tck2trk = args.tck2trk
    tck2fib = args.tck2fib
    tck2vtk = args.tck2vtk
    isRecursive = args.isRecursive
    isForcing = args.isForce
    isVerbose = args.isVerbose

    if isVerbose:
        logging.basicConfig(level=logging.DEBUG)

    if not os.path.isdir(input):
        parser.error('"{0}" must be a folder!'.format(input))

    if output is not None:
        if not os.path.isdir(output):
            if isForcing:
                logging.info('Creating "{0}".'.format(output))
                os.makedirs(output)
            else:
                parser.error("Can't find the output folder")

    #TODO: Warn if duplicate conversion (i.e. tck2X, tck2Y)
    #TODO: Find better way to add multiple conversions.
    conversions = {}
    if vtk2tck:
        conversions['vtk'] = 'tck'
    if vtk2trk:
        conversions['vtk'] = 'trk'
    if vtk2fib:
        conversions['vtk'] = 'fib'
    if fib2tck:
        conversions['fib'] = 'tck'
    if fib2trk:
        conversions['fib'] = 'trk'
    if fib2vtk:
        conversions['fib'] = 'vtk'
    if trk2tck:
        conversions['trk'] = 'tck'
    if trk2fib:
        conversions['trk'] = 'fib'
    if trk2vtk:
        conversions['trk'] = 'vtk'
    if tck2trk:
        conversions['tck'] = 'trk'
    if tck2fib:
        conversions['tck'] = 'fib'
    if tck2vtk:
        conversions['tck'] = 'vtk'

    if len(conversions) == 0:
        parser.error('Nothing to convert! Please specify at least one conversion.')

    if anat is not None:
        if not any(map(anat.endswith, EXT_ANAT.split('|'))):
            if isForcing:
                logging.info('Reading "{0}" as a {1} file.'.format(anat.split("/")[-1], EXT_ANAT))
            else:
                parser.error('Anatomy file must be one of {0}!'.format(EXT_ANAT))

        if not os.path.isfile(anat):
            parser.error('"{0}" must be an existing file!'.format(anat))

    walkAndConvert(input, conversions, output, anat, isRecursive, isForcing)

if __name__ == "__main__":
    main()
