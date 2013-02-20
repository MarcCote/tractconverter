# -*- coding: UTF-8 -*-

import numpy as np
from tractconverter.formats.header import Header


class FIB:
    MAGIC_NUMBER = "fib"  # Not really one...
    # self.hdr
    # self.filename

    #####
    # Static Methods
    ###
    @staticmethod
    def create(filename, hdr, anatFile=None):
        f = open(filename, 'wb')
        f.write(FIB.MAGIC_NUMBER + "\n")
        f.close()

        fib = FIB(filename, load=False)
        fib.hdr = hdr
        fib.writeHeader()

        return fib

    #####
    # Methods
    ###
    def __init__(self, filename, anatFile=None, load=True):
        self.filename = filename
        if not self._check():
            raise NameError("Not a FIB file.")

        self.hdr = {}
        if load:
            self._load()

    def _check(self):
        return self.filename[-3:].lower() == self.MAGIC_NUMBER

    def _load(self):
        f = open(self.filename, 'rb')

        #####
        # Read header
        ###
        # Skip "magic number"
        f.readline()

        # Skip the 5 next lines
        f.readline()  # 4 min max mean var
        f.readline()  # 1
        f.readline()  # 4 0 0 0 0
        f.readline()  # 4 0 0 0 0
        f.readline()  # 4 0 0 0 0

        # Read number of fibers
        self.hdr[Header.NB_FIBERS] = int(f.readline().split()[0])
        self.hdr[Header.NB_POINTS] = len(f.readlines()) - 2 * self.hdr[Header.NB_FIBERS]

        f.close()

    def writeHeader(self):
        f = open(self.filename, 'wb')

        f.write("1 FA\n")
        f.write("4 min max mean var\n")
        f.write("1\n")
        f.write("4 0 0 0 0\n")
        f.write("4 0 0 0 0\n")
        f.write("4 0 0 0 0\n")
        f.write("{0} 0.5\n".format(self.hdr[Header.NB_FIBERS]))

        f.close()

    def close(self):
        pass

    #####
    # Append fiber to file
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

        for i in range(self.hdr[Header.NB_FIBERS]):
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
