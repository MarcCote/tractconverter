# -*- coding: UTF-8 -*-

# Documentation available here:
# http://www.trackvis.org/docs/?subsect=fileformat

import io
import os
import copy
import logging
import numpy as np

from tractconverter.formats import header
from tractconverter.formats.header import Header as H


def readBinaryBytes(f, nbBytes, dtype):
    buff = f.read(nbBytes * dtype.itemsize)
    return np.frombuffer(buff, dtype=dtype)


class TRK:
    MAGIC_NUMBER = "TRACK"
    COUNT_OFFSET = 988
    OFFSET = 1000
    # self.hdr
    # self.filename
    # self.hdr[H.ENDIAN]
    # self.FIBER_DELIMITER
    # self.END_DELIMITER

    #####
    # Static Methods
    ###
    @staticmethod
    def _check(filename):
        f = open(filename, 'rb')
        magicNumber = f.read(5)
        f.close()
        return magicNumber == TRK.MAGIC_NUMBER

    @staticmethod
    def create(filename, hdr=None, anatFile=None):
        f = open(filename, 'wb')
        f.write(TRK.MAGIC_NUMBER + "\n")
        f.close()

        if hdr is None:
            hdr = TRK.get_empty_header()
        else:
            hdr = copy.deepcopy(hdr)

        hdr[H.NB_FIBERS] = 0  # NB_FIBERS will be updated when using iadd().

        trk = TRK(filename, load=False)
        trk.hdr = hdr
        trk.writeHeader()

        return trk

    #####
    # Methods
    ###
    def __init__(self, filename, anatFile=None, load=True):
        if not TRK._check(filename):
            raise NameError("Not a TRK file.")

        self.filename = filename
        self.hdr = {}
        if load:
            self._load()
            self.hdr = header.get_header_from_anat(anatFile, self.hdr)

    def _load(self):
        f = open(self.filename, 'rb')

        #####
        # Read header
        ###
        self.hdr[H.MAGIC_NUMBER] = f.read(6)
        self.hdr[H.DIMENSIONS] = np.frombuffer(f.read(6), dtype='<i2')
        self.hdr[H.VOXEL_SIZES] = np.frombuffer(f.read(12), dtype='<f4')
        self.hdr[H.ORIGIN] = np.frombuffer(f.read(12), dtype='<f4')
        self.hdr[H.NB_SCALARS_BY_POINT] = np.frombuffer(f.read(2), dtype='<i2')[0]
        self.hdr['scalar_name'] = [f.read(20) for i in range(10)]
        self.hdr[H.NB_PROPERTIES_BY_TRACT] = np.frombuffer(f.read(2), dtype='<i2')[0]
        self.hdr['property_name'] = [f.read(20) for i in range(10)]

        self.hdr[H.VOXEL_TO_WORLD] = np.frombuffer(f.read(64), dtype='<f4').reshape(4, 4)
        self.hdr[H.WORLD_ORDER] = "RAS"

        # Skip reserved bytes
        f.seek(444, os.SEEK_CUR)

        self.hdr[H.VOXEL_ORDER] = f.read(4)
        self.hdr["pad2"] = f.read(4)
        self.hdr["image_orientation_patient"] = np.frombuffer(f.read(24), dtype='<f4')
        self.hdr["pad1"] = f.read(2)

        self.hdr["invert_x"] = f.read(1) == '\x01'
        self.hdr["invert_y"] = f.read(1) == '\x01'
        self.hdr["invert_z"] = f.read(1) == '\x01'
        self.hdr["swap_xy"] = f.read(1) == '\x01'
        self.hdr["swap_yz"] = f.read(1) == '\x01'
        self.hdr["swap_zx"] = f.read(1) == '\x01'

        self.hdr[H.NB_FIBERS] = np.frombuffer(f.read(4), dtype='<i4')
        self.hdr["version"] = np.frombuffer(f.read(4), dtype='<i4')
        self.hdr["hdr_size"] = np.frombuffer(f.read(4), dtype='<i4')

        # Check if little or big endian
        self.hdr[H.ENDIAN] = '<'
        if self.hdr["hdr_size"] != self.OFFSET:
            self.hdr[H.ENDIAN] = '>'
            self.hdr[H.NB_FIBERS] = self.hdr[H.NB_FIBERS].astype('>i4')
            self.hdr["version"] = self.hdr["version"].astype('>i4')
            self.hdr["hdr_size"] = self.hdr["hdr_size"].astype('>i4')

        nb_fibers = 0
        self.hdr[H.NB_POINTS] = 0

        #Either verify the number of streamlines specified in the header is correct or
        # count the actual number of streamlines in case it is not specified in the header.
        remainingBytes = os.path.getsize(self.filename) - self.OFFSET
        while remainingBytes > 0:
            # Read points
            nbPoints = readBinaryBytes(f, 1, np.dtype(self.hdr[H.ENDIAN] + "i4"))[0]
            self.hdr[H.NB_POINTS] += nbPoints
            # This seek is used to go to the next points number indication in the file.
            f.seek((nbPoints * (3 + self.hdr[H.NB_SCALARS_BY_POINT])
                   + self.hdr[H.NB_PROPERTIES_BY_TRACT]) * 4, 1)  # Relative seek
            remainingBytes -= (nbPoints * (3 + self.hdr[H.NB_SCALARS_BY_POINT])
                               + self.hdr[H.NB_PROPERTIES_BY_TRACT]) * 4 + 4
            nb_fibers += 1

        if self.hdr[H.NB_FIBERS] != nb_fibers:
            logging.warn(('The number of streamlines specified in header ({0}) does not match '
                         'the actual number of streamlines contained in this file ({1}). '
                         'The latter will be used.').format(self.hdr[H.NB_FIBERS], nb_fibers))

        self.hdr[H.NB_FIBERS] = nb_fibers

        f.close()

    @classmethod
    def get_empty_header(cls):
        hdr = {}

        #Default values
        hdr[H.MAGIC_NUMBER] = cls.MAGIC_NUMBER
        hdr[H.VOXEL_SIZES] = (1, 1, 1)
        hdr[H.DIMENSIONS] = (1, 1, 1)
        hdr[H.VOXEL_TO_WORLD] = np.eye(4)
        hdr[H.VOXEL_ORDER] = 'LPS'  # Trackvis's default is LPS
        hdr[H.NB_FIBERS] = 0
        hdr['version'] = 2
        hdr['hdr_size'] = cls.OFFSET

        return hdr

    def writeHeader(self):
        # Get the voxel size and format it as an array.
        voxel_sizes = np.asarray(self.hdr.get(H.VOXEL_SIZES, (1.0, 1.0, 1.0)), dtype='<f4')
        dimensions = np.asarray(self.hdr.get(H.DIMENSIONS, (0, 0, 0)), dtype='<i2')
        voxel2world = np.asarray(self.hdr.get(H.VOXEL_TO_WORLD, np.eye(4)), dtype='<f4')
        voxel_order = np.asarray(self.hdr.get(H.VOXEL_ORDER, 'LPS'), dtype='S4')  # Trackvis's default is LPS

        f = open(self.filename, 'wb')
        f.write(self.MAGIC_NUMBER + "\0")   # id_string
        f.write(dimensions)                 # dim
        f.write(voxel_sizes)                # voxel_size
        f.write(np.zeros(12, dtype='i1'))   # origin
        f.write(np.zeros(2, dtype='i1'))    # n_scalars
        f.write(np.zeros(200, dtype='i1'))  # scalar_name
        f.write(np.zeros(2, dtype='i1'))    # n_properties
        f.write(np.zeros(200, dtype='i1'))  # property_name
        f.write(voxel2world)                # vos_to_ras
        f.write(np.zeros(444, dtype='i1'))  # reserved
        f.write(voxel_order)                # voxel_order
        f.write(np.zeros(4, dtype='i1'))    # pad2
        f.write(np.zeros(24, dtype='i1'))   # image_orientation_patient
        f.write(np.zeros(2, dtype='i1'))    # pad1
        f.write(np.zeros(1, dtype='i1'))    # invert_x
        f.write(np.zeros(1, dtype='i1'))    # invert_y
        f.write(np.zeros(1, dtype='i1'))    # invert_z
        f.write(np.zeros(1, dtype='i1'))    # swap_xy
        f.write(np.zeros(1, dtype='i1'))    # swap_yz
        f.write(np.zeros(1, dtype='i1'))    # swap_zx
        f.write(np.array(self.hdr[H.NB_FIBERS], dtype='<i4'))
        f.write(np.array([2], dtype='<i4'))  # version
        f.write(np.array(self.OFFSET, dtype='<i4'))  # hdr_size, should be 1000
        f.close()

    def close(self):
        pass

    def __iadd__(self, fibers):
        f = open(self.filename, 'ab')

        self.hdr[H.NB_FIBERS] += len(fibers)
        for fib in fibers:
            f.write(np.array([len(fib)], '<i4').tostring())
            f.write(fib.astype("<f4").tostring())
        f.close()

        f = open(self.filename, 'r+b')
        f.seek(TRK.COUNT_OFFSET, os.SEEK_SET)
        f.write(np.array(self.hdr[H.NB_FIBERS], dtype='<i4'))
        f.close()

        return self

    #####
    # Iterate through fibers
    ###
    def __iter__(self):
        if self.hdr[H.NB_FIBERS] == 0:
            return

        f = open(self.filename, 'rb')
        f.seek(self.OFFSET)

        remainingBytes = os.path.getsize(self.filename) - self.OFFSET

        cpt = 0
        while cpt < self.hdr[H.NB_FIBERS] or remainingBytes > 0:
            # Read points
            nbPoints = readBinaryBytes(f, 1, np.dtype(self.hdr[H.ENDIAN] + "i4"))[0]
            ptsAndScalars = readBinaryBytes(f,
                                            nbPoints * (3 + self.hdr[H.NB_SCALARS_BY_POINT]),
                                            np.dtype(self.hdr[H.ENDIAN] + "f4"))

            # If there are some properties, ignore them for now.
            properties = readBinaryBytes(f,
                                         self.hdr[H.NB_PROPERTIES_BY_TRACT],
                                         np.dtype(self.hdr[H.ENDIAN] + "f4"))

            newShape = [-1, 3 + self.hdr[H.NB_SCALARS_BY_POINT]]
            ptsAndScalars = ptsAndScalars.reshape(newShape)

            pointsWithoutScalars = ptsAndScalars[:, 0:3]
            yield pointsWithoutScalars

            remainingBytes -= 4  # Number of points
            remainingBytes -= nbPoints * (3 + self.hdr[H.NB_SCALARS_BY_POINT]) * 4
            # For now, we do not process the tract properties, so just skip over them.
            remainingBytes -= self.hdr[H.NB_PROPERTIES_BY_TRACT] * 4
            cpt += 1

        f.close()

    def load_all(self):
        if self.hdr[H.NB_FIBERS] == 0:
            return []

        with open(self.filename, 'rb') as f:
            f.seek(self.OFFSET)
            buff = io.BytesIO(f.read())

        remainingBytes = os.path.getsize(self.filename) - self.OFFSET

        streamlines = []
        cpt = 0
        while cpt < self.hdr[H.NB_FIBERS] or remainingBytes > 0:
            # Read points
            nbPoints = readBinaryBytes(buff, 1, np.dtype(self.hdr[H.ENDIAN] + "i4"))[0]
            ptsAndScalars = readBinaryBytes(buff,
                                            nbPoints * (3 + self.hdr[H.NB_SCALARS_BY_POINT]),
                                            np.dtype(self.hdr[H.ENDIAN] + "f4"))

            # If there are some properties, ignore them for now.
            properties = readBinaryBytes(buff,
                                         self.hdr[H.NB_PROPERTIES_BY_TRACT],
                                         np.dtype(self.hdr[H.ENDIAN] + "f4"))

            newShape = [-1, 3 + self.hdr[H.NB_SCALARS_BY_POINT]]
            ptsAndScalars = ptsAndScalars.reshape(newShape)

            pointsWithoutScalars = ptsAndScalars[:, 0:3]
            streamlines.append(pointsWithoutScalars)

            remainingBytes -= 4  # Number of points
            remainingBytes -= nbPoints * (3 + self.hdr[H.NB_SCALARS_BY_POINT]) * 4
            # For now, we do not process the tract properties, so just skip over them.
            remainingBytes -= self.hdr[H.NB_PROPERTIES_BY_TRACT] * 4
            cpt += 1

        return streamlines

    def __str__(self):
        text = ""
        text += "MAGIC NUMBER: {0}".format(self.hdr[H.MAGIC_NUMBER])
        text += "\nv.{0}".format(self.hdr['version'])
        text += "\ndim: {0}".format(self.hdr[H.DIMENSIONS])
        text += "\nvoxel_sizes: {0}".format(self.hdr[H.VOXEL_SIZES])
        text += "\norigin: {0}".format(self.hdr[H.ORIGIN])
        text += "\nnb_scalars: {0}".format(self.hdr[H.NB_SCALARS_BY_POINT])
        text += "\nscalar_name:\n{0}".format("\n".join(self.hdr['scalar_name']))
        text += "\nnb_properties: {0}".format(self.hdr[H.NB_PROPERTIES_BY_TRACT])
        text += "\nproperty_name:\n{0}".format("\n".join(self.hdr['property_name']))
        text += "\nvox_to_world:\n{0}".format(self.hdr[H.VOXEL_TO_WORLD])
        text += "\nworld_order: {0}".format(self.hdr[H.WORLD_ORDER])
        text += "\nvoxel_order: {0}".format(self.hdr[H.VOXEL_ORDER])
        text += "\nimage_orientation_patient: {0}".format(self.hdr['image_orientation_patient'])
        text += "\npad1: {0}".format(self.hdr['pad1'])
        text += "\npad2: {0}".format(self.hdr['pad2'])
        text += "\ninvert_x: {0}".format(self.hdr['invert_x'])
        text += "\ninvert_y: {0}".format(self.hdr['invert_y'])
        text += "\ninvert_z: {0}".format(self.hdr['invert_z'])
        text += "\nswap_xy: {0}".format(self.hdr['swap_xy'])
        text += "\nswap_yz: {0}".format(self.hdr['swap_yz'])
        text += "\nswap_zx: {0}".format(self.hdr['swap_zx'])
        text += "\nn_count: {0}".format(self.hdr[H.NB_FIBERS])
        text += "\nhdr_size: {0}".format(self.hdr['hdr_size'])
        text += "\nendianess: {0}".format(self.hdr[H.ENDIAN])

        return text
