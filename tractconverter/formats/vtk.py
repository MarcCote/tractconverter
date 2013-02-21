# -*- coding: UTF-8 -*-

# Documentation available here:
# http://www.vtk.org/VTK/img/file-formats.pdf

import os
import numpy as np
from pdb import set_trace as dbg

from tractconverter.formats.header import Header


def readBinaryBytes(f, nbBytes, dtype):
    buff = f.read(nbBytes * dtype.itemsize)
    return np.frombuffer(buff, dtype=dtype)


def readAcsiiBytes(f, nbWords, dtype):
    words = []
    buff = ""
    while len(words) < nbWords:
        c = f.read(1)
        if c == " " or c == '\n':
            if len(buff) > 0:
                words.append(buff)
                buff = ""
        else:
            buff += c

    return np.array(' '.join(words).split(), dtype=dtype)


class VTK:
    MAGIC_NUMBER = "vtk"
    VERSION = "3.0"

    #####
    # Static Methods
    ###
    @staticmethod
    def create(filename, hdr, anatFile=None):
        f = open(filename, 'wb')
        f.write(VTK.MAGIC_NUMBER + "\n")
        f.close()

        vtk = VTK(filename, load=False)
        vtk.hdr = hdr
        vtk.writeHeader()

        return vtk

    #####
    # Methods
    ###
    def __init__(self, filename, anatFile=None, load=True):
        self.filename = filename
        if not self._check():
            raise NameError("Not a TRK file.")

        self.hdr = {}
        if load:
            self._load()

    def _check(self):
        f = open(self.filename, 'rb')
        magicNumber = f.readline()
        f.close()
        return VTK.MAGIC_NUMBER in magicNumber

    def _load(self):
        f = open(self.filename, 'rb')

        #####
        # Read header
        ###
        f.readline()  # Version (not used)
        f.readline()  # Description (not used)
        self.fileType = f.readline()  # Type of the file BINARY or ASCII.
        f.readline()  # Data type (not used)

        self.offset = f.tell()  # Store offset to the beginning of data.

        self.hdr[Header.NB_POINTS] = int(f.readline().split()[1])  # POINTS n float
        self.offset_points = f.tell()
        f.seek(self.hdr[Header.NB_POINTS] * 3 * 4, 1)  # Skip nb_points * 3 (x,y,z) * 4 bytes

        # Skip newline
        f.readline()

        infos = f.readline().split()  # LINES n size
        self.hdr[Header.NB_FIBERS] = int(infos[1])
        size = int(infos[2])

        if size != self.hdr[Header.NB_FIBERS] + self.hdr[Header.NB_POINTS]:
            print "ERROR!!!!"

        self.offset_lines = f.tell()
        f.seek(size * 4, 1)  # Skip nb_lines + nb_points * 4 bytes

        if self.fileType == "ASCII\n":
            # Skip newline
            f.readline()

        # TODO: Read infos about COLORS, SCALARS, ...

        f.close()

    def writeHeader(self):
        f = open(self.filename, 'wb')
        f.write("# {0} DataFile Version {1}\n".format(VTK.MAGIC_NUMBER, VTK.VERSION))
        f.write("vtk comments\n")
        f.write("BINARY\n")  # Support only binary file for saving.
        f.write("DATASET POLYDATA\n")

        # POINTS
        f.write("POINTS {0} float\n".format(self.hdr[Header.NB_POINTS]))
        self.offset = f.tell()
        self.offset_points = f.tell()
        f.write(np.zeros((self.hdr[Header.NB_POINTS], 3), dtype='>f4'))

        f.write('\n')

        # LINES
        size = self.hdr[Header.NB_FIBERS] + self.hdr[Header.NB_POINTS]
        f.write("LINES {0} {1}\n".format(self.hdr[Header.NB_FIBERS], size))
        self.offset_lines = f.tell()
        f.write(np.zeros(size, dtype='>i4'))

        # TODO: COLORS, SCALARS

        f.close()

    def close(self):
        pass

    def __iadd__(self, fibers):
        f = open(self.filename, 'r+b')
        f.seek(self.offset_points, 0)

        nb_points = (self.offset_points - self.offset) / 3 / 4
        for fib in fibers:
            f.write(fib.astype('>f4').tostring())

        self.offset_points = f.tell()

        f.seek(self.offset_lines, 0)
        for fib in fibers:
            f.write(np.array([len(fib)], dtype='>i4').tostring())
            f.write(np.arange(nb_points, nb_points + len(fib), dtype='>i4').tostring())
            nb_points += len(fib)

        self.offset_lines = f.tell()

        f.close()

        return self

    #####
    # Iterate through fibers
    # TODO: Use a buffer instead of reading one streamline at the time.
    ###
    def __iter__(self):
        f = open(self.filename, 'rb')

        readFct = readAcsiiBytes
        if self.fileType == "BINARY\n":
            readFct = readBinaryBytes

        for i in range(self.hdr[Header.NB_FIBERS]):
            f.seek(self.offset_lines, 0)  # Seek from beginning of the file

            # Read indices of next streamline
            nbIdx = readFct(f, 1, np.dtype('>i4'))[0]
            ptsIdx = readFct(f, nbIdx, np.dtype('>i4'))
            self.offset_lines = f.tell()

            # Read points according to indices previously read
            startPos = np.min(ptsIdx) * 3  # Minimum index * 3 (x,y,z)
            endPos = (np.max(ptsIdx) + 1) * 3  # After maximum index * 3 (x,y,z)
            f.seek(self.offset_points + startPos * 4, 0)  # Seek from beginning of the file

            points = readFct(f, endPos - startPos, np.dtype('>f4'))
            points = points.reshape([-1, 3])  # Matrix dimension: Nx3

            # TODO: Read COLORS, SCALARS, ...

            streamline = points[ptsIdx - np.min(ptsIdx)]
            yield streamline

        f.close()
