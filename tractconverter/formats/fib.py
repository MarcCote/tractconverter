# -*- coding: UTF-8 -*-

import copy
import numpy as np
from tractconverter.formats.header import Header as H
from vtk import VTK


class FIB:
    MAGIC_NUMBER = "fib"  # Not really one...
    # self.hdr
    # self.filename

    #####
    # Static Methods
    ###
    @staticmethod
    def _check(filename):
        if VTK._check(filename):
            return False

        return filename[-3:].lower() == FIB.MAGIC_NUMBER

    @staticmethod
    def create(filename, hdr=None, anatFile=None):
        f = open(filename, 'wb')
        f.write(FIB.MAGIC_NUMBER + "\n")
        f.close()

        if hdr is None:
            hdr = VTK.get_empty_header()
        else:
            hdr = copy.deepcopy(hdr)

        fib = FIB(filename, load=False)
        fib.hdr = hdr
        fib.writeHeader()

        return fib

    #####
    # Methods
    ###
    def __init__(self, filename, anatFile=None, load=True):
        if not FIB._check(filename):
            raise NameError("Not a FIB file.")

        self.filename = filename
        self.hdr = {}
        if load:
            self._load()

    def _load(self):
        f = open(self.filename, 'rb')

        #####
        # Read header
        ###
        # Skip pseudo "magic number"
        f.readline()

        # Skip the 5 next lines
        f.readline()  # 4 min max mean var
        f.readline()  # 1
        f.readline()  # 4 0 0 0 0
        f.readline()  # 4 0 0 0 0
        f.readline()  # 4 0 0 0 0

        # Read number of fibers
        self.hdr[H.NB_FIBERS] = int(f.readline().split()[0])
        self.hdr[H.NB_POINTS] = len(f.readlines()) - 2 * self.hdr[H.NB_FIBERS]

        f.close()

    @classmethod
    def get_empty_header(cls):
        hdr = {}

        #Default values
        hdr[H.NB_FIBERS] = 0

        return hdr

    def writeHeader(self):
        f = open(self.filename, 'wb')

        f.write("1 FA\n")
        f.write("4 min max mean var\n")
        f.write("1\n")
        f.write("4 0 0 0 0\n")
        f.write("4 0 0 0 0\n")
        f.write("4 0 0 0 0\n")
        f.write("{0} 0.5\n".format(self.hdr[H.NB_FIBERS]))

        f.close()

    def close(self):
        pass

    #####
    # Append fiber to file
    # TODO: make it really dynamic if possible (like trk and tck).
    ###
    def __iadd__(self, fibers):
        f = open(self.filename, 'ab')

        for fib in fibers:
            lines = []
            lines.append("0 {0}".format(len(fib)))
            lines.append("1")
            lines += [" ".join(map(str, pts)) + " 0" for pts in fib]

            f.write("\n".join(lines) + "\n")
        f.close()

        return self

    #####
    # Iterate through fibers from file
    ###
    def __iter__(self):

        f = open(self.filename, 'rb')

        # Skip header
        for i in range(7):
            f.readline()

        for i in range(self.hdr[H.NB_FIBERS]):
            line = f.readline()
            nbBackward, nbForward = map(int, line.split())
            f.readline()  # Skip (unused)
            # nbPoints = nbBackward + nbForward - int(nbBackward > 0 and nbForward > 0)
            pts = []
            for j in range(nbBackward):
                pts.append(f.readline().split()[:3])

            pts = pts[::-1]
            if nbForward > 0 and nbBackward > 0:
                f.readline()  # Skip redundant points
                nbForward -= 1

            for j in range(nbForward):
                pts.append(f.readline().split()[:3])

            pts = np.array(pts, "<f4")

            yield pts

        f.close()

    def load_all(self):
        # TODO: make it more efficient, load everything in memory first
        #       and to processing afterward.
        return [s for s in self]
