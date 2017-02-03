# -*- coding: UTF-8 -*-

# Documentation available here:
# http://www.vtk.org/VTK/img/file-formats.pdf

import os
import copy
import tempfile
import numpy as np

from tractconverter.formats import header
from tractconverter.formats.header import Header as H


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
    file_type = f.readline().strip()  # Type of the file BINARY or ASCII.

    f.seek(0, 0)  # Reset cursor to beginning of the file.

    return file_type.upper() == "BINARY"


def convertAsciiToBinary(original_filename):
    sections = get_sections(original_filename)

    f = open(original_filename, 'rb')

    # Skip the first header lines
    f.readline()  # Version (not used)
    f.readline()  # Description (not used)
    original_file_type = f.readline().strip()  # Type of the file BINARY or ASCII.
    f.readline()  # Data type (not used)

    if original_file_type.upper() != "ASCII":
        raise ValueError("BINARY file given to convertAsciiToBinary.")

    # Create a temporary file with a name. Delete is set to false to make sure
    # the file is not automatically deleted when closed.
    binary_file = tempfile.NamedTemporaryFile(delete=False)

    # Write header
    binary_file.write("# {0} DataFile Version {1}\n".format(VTK.MAGIC_NUMBER, VTK.VERSION))
    binary_file.write("converted from ASCII vtk by tractconverter\n")
    binary_file.write("BINARY\n")
    binary_file.write("DATASET POLYDATA\n")

    # Convert POINTS section from ASCII to binary
    f.seek(sections['POINTS'], os.SEEK_SET)
    line = f.readline()  # POINTS n float
    nb_coordinates = int(line.split()[1]) * 3
    binary_file.write(line)

    while nb_coordinates * 3 > 0:
        tokens = f.readline().split()

        #Skip empty lines
        if len(tokens) == 0:
            continue

        binary_file.write(np.array(tokens, dtype='>f4').tostring())
        nb_coordinates -= len(tokens)

    binary_file.write('\n')

    if 'LINES' in sections:
        # Convert LINES section from ASCII to binary
        f.seek(sections['LINES'], os.SEEK_SET)
        line = f.readline()  # LINES n size
        nb_lines = int(line.split()[1])
        binary_file.write(line)

        while nb_lines > 0:
            tokens = f.readline().split()

            #Skip empty lines
            if len(tokens) == 0:
                continue

            #Write number of points in the line
            binary_file.write(np.array([tokens[0]], dtype='>i4').tostring())
            #Write indices of points in the line
            binary_file.write(np.array(tokens[1:], dtype='>i4').tostring())
            nb_lines -= 1

    # TODO: COLORS, SCALARS

    binary_file.close()
    f.close()

    return binary_file.name

POLYDATA_SECTIONS = ['POINTS', 'VERTICES', 'LINES', 'POLYGONS', 'TRIANGLE_STRIPS']


def get_sections(filename):
    sections_found = {}
    nb_read_bytes = 0
    with open(filename, 'rb') as f:
        for line in f:
            for section in POLYDATA_SECTIONS:
                if line.upper().startswith(section):
                    if section in sections_found:
                        print "Warning multiple {0} sections!".format(section)

                    sections_found[section] = nb_read_bytes

            nb_read_bytes += len(line)

    return sections_found


class VTK:
    MAGIC_NUMBER = "vtk"
    VERSION = "3.0"
    BUFFER = 10000

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
        magicNumber = f.readline().strip()
        f.close()
        return VTK.MAGIC_NUMBER in magicNumber

    @staticmethod
    def create(filename, hdr=None, anatFile=None):
        f = open(filename, 'wb')
        f.write(VTK.MAGIC_NUMBER + "\n")
        f.close()

        if hdr is None:
            hdr = VTK.get_empty_header()
        else:
            hdr = copy.deepcopy(hdr)

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
            self.hdr = header.get_header_from_anat(anatFile)
            self._load()

    def __del__(self):
        self.cleanTempFile()

    def _load(self):
        f = open(self.filename, 'rb')

        #####
        # Read header
        ###
        info = f.readline().split()
        self.hdr[H.MAGIC_NUMBER] = info[1]
        self.hdr["version"] = info[-1]
        self.hdr["description"] = f.readline().strip()
        self.hdr["file_type"] = f.readline().strip()

        #####
        # If in ASCII format, create a temporary Binary file. This
        # will avoid lots of problems when reading.
        # We will always read a binary file, converted or not.
        #####
        if "BINARY" != self.hdr["file_type"].upper():
            f.close()
            binary_filename = convertAsciiToBinary(self.filename)
            self.filename = binary_filename

        self.sections = get_sections(self.filename)

        #TODO: Check number of scalars and properties
        self.hdr[H.NB_SCALARS_BY_POINT] = "N/A"
        self.hdr[H.NB_PROPERTIES_BY_TRACT] = "N/A"

        f = open(self.filename, 'rb')

        #####
        # Read header
        ###
        f.readline()  # Version (not used)
        f.readline()  # Description (not used)
        self.fileType = f.readline().strip()  # Type of the file BINARY or ASCII.
        f.readline()  # Data type (not used)

        #self.offset = f.tell()  # Store offset to the beginning of data.

        f.seek(self.sections['POINTS'], os.SEEK_SET)
        self.hdr[H.NB_POINTS] = int(f.readline().split()[1])  # POINTS n float
        #self.offset_points = f.tell()

        #f.seek(self.hdr[H.NB_POINTS] * 3 * 4, 1)  # Skip nb_points * 3 (x,y,z) * 4 bytes
        # Skip newline, to bring to the line containing the LINES marker.
        #f.readline()

        self.hdr[H.NB_FIBERS] = 0
        if 'LINES' in self.sections:
            f.seek(self.sections['LINES'], os.SEEK_SET)
            infos = f.readline().split()  # LINES n size
            self.hdr[H.NB_FIBERS] = int(infos[1])
            #size = int(infos[2])

            #self.offset_lines = f.tell()
            #f.seek(size * 4, 1)  # Skip nb_lines + nb_points * 4 bytes

        # TODO: Read infos about COLORS, SCALARS, ...

        f.close()

    @classmethod
    def get_empty_header(cls):
        hdr = {}

        #Default values
        hdr[H.MAGIC_NUMBER] = cls.MAGIC_NUMBER
        hdr[H.NB_FIBERS] = 0
        hdr[H.NB_POINTS] = 0
        hdr[H.NB_SCALARS_BY_POINT] = 0
        hdr[H.NB_PROPERTIES_BY_TRACT] = 0

        return hdr

    def writeHeader(self):
        self.sections = {}
        f = open(self.filename, 'wb')
        f.write("# {0} DataFile Version {1}\n".format(VTK.MAGIC_NUMBER, VTK.VERSION))
        f.write("vtk comments\n")
        f.write("BINARY\n")  # Support only binary file for saving.
        f.write("DATASET POLYDATA\n")

        # POINTS
        self.sections['POINTS'] = f.tell()
        f.write("POINTS {0} float\n".format(self.hdr[H.NB_POINTS]))
        self.sections['POINTS_start'] = f.tell()
        self.sections['POINTS_current'] = f.tell()
        #self.offset = f.tell()
        f.write(np.zeros((self.hdr[H.NB_POINTS], 3), dtype='>f4'))

        f.write('\n')

        # LINES
        if self.hdr[H.NB_FIBERS] > 0:
            self.sections['LINES'] = f.tell()
            size = self.hdr[H.NB_FIBERS] + self.hdr[H.NB_POINTS]
            f.write("LINES {0} {1}\n".format(self.hdr[H.NB_FIBERS], size))
            self.sections['LINES_current'] = f.tell()
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

    # TODO: make it really dynamic if possible (like trk and tck).
    def __iadd__(self, fibers):
        if len(fibers) == 0:
            return self

        f = open(self.filename, 'r+b')
        f.seek(self.sections['POINTS_current'], os.SEEK_SET)

        nb_points = (self.sections['POINTS_current'] - self.sections['POINTS_start']) // 3 // 4
        for fib in fibers:
            f.write(fib.astype('>f4').tostring())

        self.sections['POINTS_current'] = f.tell()

        f.seek(self.sections['LINES_current'], os.SEEK_SET)
        for fib in fibers:
            f.write(np.array([len(fib)], dtype='>i4').tostring())
            f.write(np.arange(nb_points, nb_points + len(fib), dtype='>i4').tostring())
            nb_points += len(fib)

        self.sections['LINES_current'] = f.tell()

        f.close()

        return self

    #####
    # Iterate through fibers
    # TODO: Use a buffer instead of reading one streamline at the time.
    ###
    def __iter__(self):
        if self.hdr[H.NB_FIBERS] == 0:
            return

        f = open(self.filename, 'rb')

        #Keep important positions in the file.
        f.seek(self.sections['POINTS'], os.SEEK_SET)
        f.readline()
        self.sections['POINTS_current'] = f.tell()

        f.seek(self.sections['LINES'], os.SEEK_SET)
        f.readline()
        self.sections['LINES_current'] = f.tell()

        for i in range(0, self.hdr[H.NB_FIBERS], self.BUFFER):
            f.seek(self.sections['LINES_current'], os.SEEK_SET)  # Seek from beginning of the file

            # Read indices of next streamline
            nbIdx = []
            ptsIdx = []
            for k in range(min(self.hdr[H.NB_FIBERS], i+self.BUFFER) - i):
                nbIdx.append(readBinaryBytes(f, 1, np.dtype('>i4'))[0])
                ptsIdx.append(readBinaryBytes(f, nbIdx[-1], np.dtype('>i4')))

            self.sections['LINES_current'] = f.tell()

            # Read points according to indices previously read
            startPos = np.min(ptsIdx[0]) * 3  # Minimum index * 3 (x,y,z)
            endPos = (np.max(ptsIdx[-1]) + 1) * 3  # After maximum index * 3 (x,y,z)
            f.seek(self.sections['POINTS_current'] + startPos * 4, os.SEEK_SET)  # Seek from beginning of the file

            points = readBinaryBytes(f, endPos - startPos, np.dtype('>f4'))
            points = points.reshape([-1, 3])  # Matrix dimension: Nx3

            # TODO: Read COLORS, SCALARS, ...
            for pts_id in ptsIdx:
                yield points[pts_id - startPos/3]

        f.close()

    def load_all(self):
        # TODO: make it more efficient, load everything in memory first
        #       and to processing afterward.
        return [s for s in self]

    def __str__(self):
        text = ""
        text += "MAGIC NUMBER: {0}".format(self.hdr[H.MAGIC_NUMBER])
        text += "\nv.{0}".format(self.hdr['version'])
        text += "\nDescription: '{0}'".format(self.hdr['description'])
        text += "\nFile type: {0}".format(self.hdr['file_type'])
        text += "\nnb_scalars: {0}".format(self.hdr[H.NB_SCALARS_BY_POINT])
        text += "\nnb_properties: {0}".format(self.hdr[H.NB_PROPERTIES_BY_TRACT])
        text += "\nn_count: {0}".format(self.hdr[H.NB_FIBERS])

        return text
