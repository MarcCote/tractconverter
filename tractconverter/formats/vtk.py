# -*- coding: UTF-8 -*-

# Documentation available here:
# http://www.vtk.org/VTK/img/file-formats.pdf

import os
import tempfile
import numpy as np

from tractconverter.formats.header import Header

def readBinaryBytes(f, nbBytes, dtype):
    buff = f.read(nbBytes * dtype.itemsize)
    return np.frombuffer(buff, dtype=dtype)

def readAsciiBytes(f, nbWords, dtype):
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

# We assume the file cursor points to the beginning of the file.
def checkIfBinary(f):
    f.readline()  # Skip version
    f.readline()  # Skip description
    file_type = f.readline()  # Type of the file BINARY or ASCII.

    f.seek(0, 0)  # Reset cursor to beginning of the file.

    return file_type == "BINARY\n"

def convertAsciiToBinary(original_filename):
    f = open(original_filename, 'rb')

    # Skip the first header lines
    f.readline()  # Version (not used)
    f.readline()  # Description (not used)
    original_file_type = f.readline()  # Type of the file BINARY or ASCII.
    f.readline()  # Data type (not used)

    if original_file_type != "ASCII\n":
        raise ValueError("BINARY file given to convertAsciiToBinary.")

    # Create a temporary file with a name. Delete is set to false to make sure
    # the file is not automatically deleted when closed.
    binary_file = tempfile.NamedTemporaryFile(delete = False)

    # Write header
    binary_file.write("# {0} DataFile Version {1}\n".format(VTK.MAGIC_NUMBER, VTK.VERSION))
    binary_file.write("converted from ASCII vtk by tractconverter\n")
    binary_file.write("BINARY\n")
    binary_file.write("DATASET POLYDATA\n")

    temp_line = f.readline() # POINTS n float
    binary_file.write(temp_line)

    # Initialize for the loop.
    temp_line = f.readline()
    tokens = temp_line.split()

    # Write all the points up to the moment we find the LINES marker.
    while len(tokens) == 0 or (tokens[0] != "LINES" and tokens[0] != "VERTICES"):
        tokens_num = np.array(' '.join(tokens).split(), dtype='>f4')
        binary_file.write(tokens_num.astype('>f4').tostring())
        temp_line = f.readline()
        tokens = temp_line.split()
    
    # If we get the VERTICES token, we skip over it (for now) and iterate until
    # we find the LINES marker.
    if tokens[0] == "VERTICES":
        while len(tokens) == 0 or tokens[0] != "LINES":
            temp_line = f.readline()
            tokens = temp_line.split()

    # Write the line containing the LINES marker.
    binary_file.write('\n')
    binary_file.write(temp_line)

    # Write all the lines
    nb_lines = int(tokens[1])

    for line_idx in range(nb_lines):
        nb_pts = readAsciiBytes(f, 1, np.dtype('>i4'))[0]
        pts_idx = readAsciiBytes(f, nb_pts, np.dtype('>i4'))
        binary_file.write(np.array([nb_pts], dtype='>i4').tostring())
        binary_file.write(pts_idx.astype('>i4').tostring())

    # TODO: COLORS, SCALARS

    binary_file.close()
    f.close()

    return binary_file.name

class VTK:
    MAGIC_NUMBER = "vtk"
    VERSION = "3.0"
    # self.hdr
    # self.filename
    # self.endian
    # self.offset
    # self.FIBER_DELIMITER
    # self.END_DELIMITER

    #####
    # Static Methods
    ###
    @staticmethod
    def _check(filename):
        f = open(filename, 'rb')
        magicNumber = f.readline()
        f.close()
        return VTK.MAGIC_NUMBER in magicNumber

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
        if not VTK._check(filename):
            raise NameError("Not a VTK file.")

        self.filename = filename
        self.original_filename = filename

        self.hdr = {}
        if load:
            self._load()

    def __del__(self):
        self.cleanTempFile()

    def _load(self):
        f = open(self.filename, 'rb')

        #####
        # Check if file is in binary format or not.
        #####
        is_binary = checkIfBinary(f)

        #####
        # If in ASCII format, create a temporary Binary file. This
        # will avoid lots of problems when reading.
        # We will always read a binary file, converted or not.
        #####
        if not is_binary:
            f.close()
            binary_filename = convertAsciiToBinary(self.filename)
            self.filename = binary_filename

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
        # Skip newline, to bring to the line containing the LINES marker.
        f.readline()

        infos = f.readline().split()  # LINES n size
        self.hdr[Header.NB_FIBERS] = int(infos[1])
        size = int(infos[2])

        self.offset_lines = f.tell()
        f.seek(size * 4, 1)  # Skip nb_lines + nb_points * 4 bytes

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

    def cleanTempFile(self):
        # If the filenames differ, we converted an ASCII file to a binary file.
        # In this case, if the temporary binary file still exists, we need to clean up behind ourselves.
        if self.filename != self.original_filename and os.path.exists(self.filename):
            os.remove(self.filename)
            self.filename = self.original_filename

    def close(self):
        self.cleanTempFile()
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

        for i in range(self.hdr[Header.NB_FIBERS]):
            f.seek(self.offset_lines, 0)  # Seek from beginning of the file

            # Read indices of next streamline
            nbIdx = readBinaryBytes(f, 1, np.dtype('>i4'))[0]
            ptsIdx = readBinaryBytes(f, nbIdx, np.dtype('>i4'))
            self.offset_lines = f.tell()

            # Read points according to indices previously read
            startPos = np.min(ptsIdx) * 3  # Minimum index * 3 (x,y,z)
            endPos = (np.max(ptsIdx) + 1) * 3  # After maximum index * 3 (x,y,z)
            f.seek(self.offset_points + startPos * 4, 0)  # Seek from beginning of the file

            points = readBinaryBytes(f, endPos - startPos, np.dtype('>f4'))
            points = points.reshape([-1, 3])  # Matrix dimension: Nx3

            # TODO: Read COLORS, SCALARS, ...

            streamline = points[ptsIdx - np.min(ptsIdx)]
            yield streamline

        f.close()
