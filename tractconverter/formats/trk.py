# -*- coding: UTF-8 -*-

# Documentation available here:
# http://www.trackvis.org/docs/?subsect=fileformat

import os
import logging
import numpy as np

from tractconverter.formats.header import Header as H


def readBinaryBytes(f, nbBytes, dtype):
    buff = f.read(nbBytes * dtype.itemsize)
    return np.frombuffer(buff, dtype=dtype)


class TRK:
    MAGIC_NUMBER = "TRACK"
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
    def create(filename, hdr, anatFile=None):
        f = open(filename, 'wb')
        f.write(TRK.MAGIC_NUMBER + "\n")
        f.close()

        trk = TRK(filename, load=False)
        trk.hdr = hdr
        trk.writeHeader()

        return trk

    def infos(self):
        f = open(self.filename, 'rb')

        #####
        # Read header
        ###
        id_string = f.read(6)
        buffer = f.read(6)
        dimensions = np.frombuffer(buffer, dtype='<i2')

        buffer = f.read(12)
        voxel_sizes = np.frombuffer(buffer, dtype='<f4')
        self.hdr[H.VOXEL_SIZES] = tuple(voxel_sizes)

        buffer = f.read(12)
        origin = np.frombuffer(buffer, dtype='<f4')

        buffer = f.read(2)
        nb_scalars = np.frombuffer(buffer, dtype='<i2')[0]
        self.hdr[H.NB_SCALARS_BY_POINT] = nb_scalars

        scalar_name = [f.read(20) for i in range(10)]

        buffer = f.read(2)
        nb_properties = np.frombuffer(buffer, dtype='<i2')[0]
        self.hdr[H.NB_PROPERTIES_BY_TRACT] = nb_properties

        property_name = [f.read(20) for i in range(10)]

        buffer = f.read(64)
        vox_to_ras = np.frombuffer(buffer, dtype='<f4').reshape(4, 4)

        # Skip reserved bytes
        f.seek(444, os.SEEK_CUR)

        voxel_order = f.read(4)
        pad2 = f.read(4)

        buffer = f.read(24)
        image_orientation_patient = np.frombuffer(buffer, dtype='<f4')

        pad1 = f.read(2)

        invert_x = f.read(1) == '\x01'
        invert_y = f.read(1) == '\x01'
        invert_z = f.read(1) == '\x01'
        swap_xy = f.read(1) == '\x01'
        swap_yz = f.read(1) == '\x01'
        swap_zx = f.read(1) == '\x01'

        buffer = f.read(4 + 4 + 4)
        infos = np.frombuffer(buffer, dtype='<i4')

        print infos

        # Check if little or big endian
        self.hdr[H.ENDIAN] = '<'
        if infos[2] != 1000:
            infos = np.frombuffer(buffer, dtype='>i4')
            self.hdr[H.ENDIAN] = '>'

        n_count = infos[0]
        version = infos[1]
        hdr_size = infos[2]

        f.close()

        #Display infos
        print "MAGIC NUMBER: {0}".format(id_string)
        print "v.{0}".format(version)
        print "dim: {0}".format(dimensions)
        print "voxel_sizes: {0}".format(voxel_sizes)
        print "orgin: {0}".format(origin)
        print "nb_scalars: {0}".format(nb_scalars)
        print "scalar_name:\n {0}".format("\n".join(scalar_name))
        print "nb_properties: {0}".format(nb_properties)
        print "property_name:\n {0}".format("\n".join(property_name))
        print "vox_to_ras: {0}".format(vox_to_ras)
        print "voxel_order: {0}".format(voxel_order)
        print "image_orientation_patient: {0}".format(image_orientation_patient)
        print "pad1: {0}".format(pad1)
        print "pad2: {0}".format(pad2)
        print "invert_x: {0}".format(invert_x)
        print "invert_y: {0}".format(invert_y)
        print "invert_z: {0}".format(invert_z)
        print "swap_xy: {0}".format(swap_xy)
        print "swap_yz: {0}".format(swap_yz)
        print "swap_zx: {0}".format(swap_zx)
        print "n_count: {0}".format(n_count)
        print "hdr_size: {0}".format(hdr_size)
        print "endianess: {0}".format(self.hdr[H.ENDIAN])

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
            logging.warn('The number of streamlines specified in header ({1}) does not match ' +
                         'the actual number of streamlines contained in this file ({1}). ' +
                         'The latter will be used.'.format(self.hdr[H.NB_FIBERS], nb_fibers))

            self.hdr[H.NB_FIBERS] = nb_fibers

        f.close()

    def writeHeader(self):
        # Get the voxel size and format it as an array.
        voxel_sizes = np.asarray(self.hdr.get(H.VOXEL_SIZES, (1.0, 1.0, 1.0)), dtype='<f4')
        dimensions = np.asarray(self.hdr.get(H.DIMENSIONS, (0, 0, 0)), dtype='<i2')

        f = open(self.filename, 'wb')
        f.write(self.MAGIC_NUMBER + "\0")  # id_string
        f.write(dimensions)  # dim
        f.write(voxel_sizes)  # voxel_size
        f.write(np.zeros(12, dtype='i1'))  # origin
        f.write(np.zeros(2, dtype='i1'))  # n_scalars
        f.write(np.zeros(200, dtype='i1'))  # scalar_name
        f.write(np.zeros(2, dtype='i1'))  # n_properties
        f.write(np.zeros(200, dtype='i1'))  # property_name
        f.write(np.eye(4, dtype='<f4'))  # vos_to_ras
        f.write(np.zeros(444, dtype='i1'))  # reserved
        f.write(np.zeros(4, dtype='i1'))  # voxel_order
        f.write(np.zeros(4, dtype='i1'))  # pad2
        f.write(np.zeros(24, dtype='i1'))  # image_orientation_patient
        f.write(np.zeros(2, dtype='i1'))  # pad1
        f.write(np.zeros(1, dtype='i1'))  # invert_x
        f.write(np.zeros(1, dtype='i1'))  # invert_y
        f.write(np.zeros(1, dtype='i1'))  # invert_z
        f.write(np.zeros(1, dtype='i1'))  # swap_xy
        f.write(np.zeros(1, dtype='i1'))  # swap_yz
        f.write(np.zeros(1, dtype='i1'))  # swap_zx
        f.write(np.array(self.hdr[H.NB_FIBERS], dtype='<i4'))
        f.write(np.array([2], dtype='<i4'))  # version
        f.write(np.array(self.OFFSET, dtype='<i4'))  # hdr_size, should be 1000
        f.close()

    def close(self):
        pass

    def __iadd__(self, fibers):
        f = open(self.filename, 'ab')
        for fib in fibers:
            f.write(np.array([len(fib)], '<i4').tostring())
            f.write(fib.astype("<f4").tostring())
        f.close()

        return self

    #####
    # Iterate through fibers
    ###
    def __iter__(self):
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

            newShape = [-1, 3 + self.hdr[H.NB_SCALARS_BY_POINT]]
            ptsAndScalars = ptsAndScalars.reshape(newShape)

            pointsWithoutScalars = ptsAndScalars[:, 0:3]
            yield pointsWithoutScalars

            # For now, we do not process the tract properties, so just skip over them.
            remainingBytes -= nbPoints * (3 + self.hdr[H.NB_SCALARS_BY_POINT]) * 4 + 4
            remainingBytes -= self.hdr[H.NB_PROPERTIES_BY_TRACT] * 4
            cpt += 1

        f.close()
