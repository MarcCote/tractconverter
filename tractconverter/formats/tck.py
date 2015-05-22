# -*- coding: UTF-8 -*-

# Documentation available here:
# http://www.brain.org.au/software/mrtrix/appendix/mrtrix.html#tracks

import os
import copy
import numpy as np

from numpy import linalg
import nibabel

from tractconverter.formats.header import Header as H
from tractconverter.formats import header
from numpy.lib.index_tricks import c_, r_


class TCK:
    MAGIC_NUMBER = "mrtrix tracks"
    COUNT_OFFSET = len(MAGIC_NUMBER)+1
    BUFFER_SIZE = 1000000

    FIBER_DELIMITER = np.array([[np.nan, np.nan, np.nan]], '<f4')
    EOF_DELIMITER = np.array([[np.inf, np.inf, np.inf]], '<f4')

    # self.hdr
    # self.filename
    # self.dtype
    # self.offset
    # self.FIBER_DELIMITER
    # self.EOF_DELIMITER
    # self.anat
    # self.M
    # self.invM

    #####
    # Static Methods
    ###
    @staticmethod
    def _check(filename):
        f = open(filename, 'rb')
        magicNumber = f.readline()
        f.close()
        return magicNumber.strip() == TCK.MAGIC_NUMBER

    @staticmethod
    def create(filename, hdr=None, anatFile=None):
        f = open(filename, 'wb')
        f.write(TCK.MAGIC_NUMBER + "\n")
        f.close()

        if hdr is None:
            hdr = TCK.get_empty_header()
        else:
            hdr = copy.deepcopy(hdr)

        hdr[H.NB_FIBERS] = 0  # NB_FIBERS will be updated when using iadd().

        tck = TCK(filename, load=False)
        tck.hdr = hdr
        tck._calcTransform(anatFile)
        tck.writeHeader()

        return tck

    #####
    # Methods
    ###
    def __init__(self, filename, anatFile=None, load=True):
        if not TCK._check(filename):
            raise NameError("Not a TCK file.")

        self.filename = filename
        self.hdr = {}
        if load:
            self._calcTransform(anatFile)
            self.hdr = header.get_header_from_anat(anatFile)
            self._load()

    def _load(self):
        f = open(self.filename, 'rb')

        # Skip magic number
        buffer = f.readline()

        #####
        # Read header
        ###
        buffer = f.readline()
        while not buffer.rstrip().endswith("END"):
            buffer += f.readline()

        # Build dictionary from header (not used)
        hdr = dict(item.split(': ') for item in buffer.rstrip().split('\n')[:-1])

        # Set datatype
        self.dtype = np.dtype('>f4')
        if hdr['datatype'].endswith('LE'):
            self.dtype = np.dtype('<f4')

        # Seek to beginning of data
        self.offset = int(hdr['file'].split()[1])

        f.seek(self.offset)
        # Count number of NaN (i.e. numbers of fiber).
        self.hdr[H.NB_FIBERS] = 0
        self.hdr[H.NB_POINTS] = 0
        remainingBytes = os.path.getsize(self.filename) - self.offset
        while remainingBytes > 0:
            nbBytesToRead = min(remainingBytes, TCK.BUFFER_SIZE * 3 * self.dtype.itemsize)
            buff = f.read(nbBytesToRead)  # Read TCK.BUFFER_SIZE triplets of coordinates (float)
            pts = np.frombuffer(buff, dtype=self.dtype)  # Convert binary to float
            remainingBytes -= nbBytesToRead

            pts = pts.reshape([-1, 3])
            nbNaNs = np.isnan(pts[:, 0]).sum()
            self.hdr[H.NB_FIBERS] += nbNaNs
            self.hdr[H.NB_POINTS] += len(pts) - nbNaNs

        # Because the file might end with a serie of 'inf'
        self.hdr[H.NB_POINTS] -= np.isinf(pts[:, 0]).sum()
        f.close()

    @classmethod
    def get_empty_header(cls):
        hdr = {}

        #Default values
        hdr[H.MAGIC_NUMBER] = cls.MAGIC_NUMBER
        hdr[H.NB_FIBERS] = 0

        return hdr

    def writeHeader(self):
        f = open(self.filename, 'wb')

        lines = []
        lines.append(TCK.MAGIC_NUMBER)
        lines.append("count: {0:010}".format(self.hdr[H.NB_FIBERS]))
        lines.append("datatype: Float32LE")
        lines.append("file: . ")
        out = "\n".join(lines)
        f.write(out)
        offset = len(out) + 5  # +5 is for "\nEND\n", +1 is for the beginning of binary data
        self.offset = offset + len(str(offset))

        if len(str(self.offset)) != len(str(offset)):
            self.offset += 1

        f.write(str(self.offset) + "\n")
        f.write("END\n")
        f.write(self.EOF_DELIMITER.tostring())
        f.close()

    def close(self):
        pass

    def _calcTransform(self, anatFile):
        # The MrTrix fibers are defined in the same geometric reference
        # as the anatomical file. That is, the fibers coordinates are related to
        # the anatomy in world space. The transformation from local to world space
        # for the anatomy is encoded in the m_dh->m_niftiTransform member.
        # Since we do not consider this tranform when loading the anatomy, we must
        # bring back the fibers in the same reference, using the inverse of the
        # local to world transformation. A further problem arises when loading an
        # anatomy that has voxels with dimensions differing from 1x1x1. The
        # scaling factor is encoded in the transformation matrix, but we do not,
        # for the moment, use this scaling. Therefore, we must remove it from the
        # the transformation matrix before computing its inverse.
        if anatFile is None:
            self.M = np.identity(4, dtype='<f4')
            self.invM = np.identity(4, dtype='<f4')
            return

        anat = nibabel.load(anatFile)
        voxelSize = list(anat.get_header().get_zooms())[:3]

        scaleMat = np.diag(np.divide(1.0, voxelSize))
        M = anat.get_header().get_best_affine()

        # Affine matrix without scaling, i.e. diagonal is 1
        M[:3, :3] = np.dot(scaleMat, M[:3, :3])

        self.M = M.T.astype('<f4')
        self.invM = linalg.inv(self.M)

    def __iadd__(self, p_fibers):
        if len(p_fibers) == 0:
            return self

        self.hdr[H.NB_FIBERS] += len(p_fibers)
        fibers = [r_[f.astype('<f4'), self.FIBER_DELIMITER] for f in p_fibers]
        fibers = np.concatenate(fibers)
        fibers = np.dot(c_[fibers, np.ones([len(fibers), 1], dtype='<f4')], self.M)[:, :-1]

        f = open(self.filename, 'r+b')
        f.seek(self.COUNT_OFFSET, os.SEEK_SET)
        f.write("count: {0:010}\n".format(self.hdr[H.NB_FIBERS]))

        f.seek(-len(self.EOF_DELIMITER.tostring()), os.SEEK_END)
        f.write(fibers.tostring())
        f.write(self.EOF_DELIMITER.tostring())
        f.close()

        return self

    #####
    # Iterate through fibers
    ###
    def __iter__(self):
        if self.hdr[H.NB_FIBERS] == 0:
            return

        buff = ""
        pts = []

        f = open(self.filename, 'rb')
        f.seek(self.offset)
        remainingBytes = os.path.getsize(self.filename) - self.offset
        while remainingBytes > 0 or not np.all(np.isinf(pts)):
            if remainingBytes > 0:
                nbBytesToRead = min(remainingBytes, TCK.BUFFER_SIZE * 3 * self.dtype.itemsize)
                buff += f.read(nbBytesToRead)  # Read BUFFER_SIZE triplets of coordinates (float)
                remainingBytes -= nbBytesToRead
#
            pts = np.frombuffer(buff, dtype=self.dtype)  # Convert binary to float

            if self.dtype != '<f4':
                pts = pts.astype('<f4')

            pts = pts.reshape([-1, 3])
            idxNaN = np.arange(len(pts))[np.isnan(pts[:, 0])]

            if len(idxNaN) == 0:
                continue

            nbPts_total = 0
            idx_start = 0
            for idx_end in idxNaN:
                nbPts = len(pts[idx_start:idx_end, :])
                nbPts_total += nbPts

                if nbPts > 0:
                    yield np.dot(c_[pts[idx_start:idx_end, :], np.ones([nbPts, 1], dtype='<f4')], self.invM)[:, :-1]

                idx_start = idx_end + 1

            # Remove pts plus the first triplet of NaN.
            nbBytesToRemove = (nbPts_total + len(idxNaN)) * 3 * self.dtype.itemsize
            buff = buff[nbBytesToRemove:]

        f.close()

    def load_all(self):
        if self.hdr[H.NB_FIBERS] == 0:
            return []

        with open(self.filename, 'rb') as f:
            f.seek(self.offset)
            buff = f.read()

        buff = buff[:-2 * 3 * self.dtype.itemsize]
        pts = np.frombuffer(buff, dtype=self.dtype)  # Convert binary to float

        # Convert big endian to little endian
        if self.dtype != '<f4':
            pts = pts.astype('<f4')

        pts = pts.reshape([-1, 3])
        idxNaN = np.arange(len(pts))[np.isnan(pts[:, 0])]
        pts = pts[np.isfinite(pts[:, 0])]
        idxNaN -= np.arange(len(idxNaN))

        streamlines = np.split(pts, idxNaN)
        return [np.dot(c_[s, np.ones(len(s), dtype='<f4')], self.invM)[:, :-1] for s in streamlines if s.shape[0] > 0]
