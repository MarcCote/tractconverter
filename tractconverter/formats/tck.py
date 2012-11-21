# -*- coding: UTF-8 -*-

#Documentation available here:
#http://www.brain.org.au/software/mrtrix/appendix/mrtrix.html

import os
import numpy as np

from numpy import linalg
import nibabel
from tractconverter.formats.header import Header
from numpy.lib.index_tricks import c_, r_

class TCK:
    MAGIC_NUMBER = "mrtrix tracks"
    #self.hdr
    #self.filename
    #self.dtype
    #self.offset
    #self.FIBER_DELIMITER
    #self.END_DELIMITER
    #self.anat
    #self.M
    #self.invM
    
    #####
    #Static Methods
    ###
    @staticmethod
    def create(filename, hdr, anatFile):
        f = open(filename, 'wb')
        f.write(TCK.MAGIC_NUMBER + "\n")
        f.close()
        
        tck = TCK(filename, load=False)
        tck.hdr = hdr
        tck._calcTransform(anatFile)
        tck.writeHeader();

        return tck

    #####
    #Methods
    ###
    def __init__(self, filename, anatFile=None, load=True):
        self.filename = filename
        if not self._check():
            raise NameError("Not a TCK file.")
        
        self.hdr = {}
        if load:
            self._calcTransform(anatFile)
            self._load()
    
    def _check(self):
        f = open(self.filename, 'rb')
        
        magicNumber = f.readline()
        
        f.close()
        return magicNumber.strip() == self.MAGIC_NUMBER
    
    def _load(self):
        f = open(self.filename, 'rb')
        
        #Skip magic number
        buffer = f.readline()
        
        #####
        #Read header
        ###
        buffer = f.readline()
        while not buffer.rstrip().endswith("END"):
            buffer += f.readline()
        
        #Build dictionary from header (not used)
        hdr = dict(item.split(': ') for item in buffer.rstrip().split('\n')[:-1])
        
        #Set datatype
        self.dtype = np.dtype('>f4')
        if hdr['datatype'].endswith('LE'):
            self.dtype = np.dtype('<f4')
        
        #Seek to beginning of data
        self.offset = int(hdr['file'].split()[1])
        
        f.seek(self.offset)
        #Count number of NaN (i.e. numbers of fiber).
        self.hdr[Header.NB_FIBERS] = 0
        remainingBytes = os.path.getsize(self.filename) - self.offset
        while remainingBytes > 0:
            nbBytesToRead = min(remainingBytes, 1000*3*self.dtype.itemsize)
            buff = f.read(nbBytesToRead) #Read 100 triplets of coordinates (float)
            pts = np.frombuffer(buff, dtype=self.dtype) #Convert binary to float
            remainingBytes -= nbBytesToRead;
            
            pts = pts.reshape([-1, 3])
            self.hdr[Header.NB_FIBERS] += len(pts[np.isnan(pts[:,0])])
        
        f.close()


    FIBER_DELIMITER = np.array([[np.nan, np.nan, np.nan]], '<f4')
    END_DELIMITER = np.array([[np.inf, np.inf, np.inf]], '<f4')
        
    def writeHeader(self):
        f = open(self.filename, 'wb')
            
        lines = []
        lines.append(self.MAGIC_NUMBER)
        lines.append("count: {0}".format(self.hdr[Header.NB_FIBERS]))
        lines.append("datatype: Float32LE")
        lines.append("file: . ")
        out = "\n".join(lines)
        f.write(out)
        offset = len(out)+5 #+5 is for "\nEND\n", +1 is for the beginning of binary data
        self.offset = offset + len(str(offset))
        
        if len(str(self.offset)) != len(str(offset)):
            self.offset += 1
         
        f.write(str(self.offset) + "\n")
        f.write("END\n")
        f.close()
        
    def close(self):
        f = open(self.filename, 'ab')
        f.write(self.END_DELIMITER.tostring())
        f.close()

#    def __iadd__(self, fiber):
#        f = open(self.filename, 'ab')
#        f.write(fiber.tostring())
#        f.write(self.FIBER_DELIMITER.tostring())
#        f.close()
#        
#        return self
    
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
        anat = nibabel.load(anatFile)
        voxelSize = list(anat.get_header().get_zooms())[:3]

        M = anat.get_header().get_best_affine()
        idxDiag = np.diag(np.diag(M)) != 0;
        M[idxDiag] /= voxelSize + [1]
        self.M = M.T.astype('<f4')
        self.invM = linalg.inv(self.M)
    
    def __iadd__(self, p_fibers):
        if len(p_fibers) == 0:
            return self

        fibers = [r_[f,self.FIBER_DELIMITER] for f in p_fibers]
        fibers = np.concatenate(fibers)
        fibers = np.dot(c_[fibers, np.ones([len(fibers), 1], dtype='<f4')], self.M)[:,:-1]
        
        f = open(self.filename, 'ab')
        f.write(fibers.tostring())
        f.close()
        
        return self
        
    #TODO: 
    #    voxelSize = [0,0,0]
    #    if anatFile is not None:
    #        # The MrTrix fibers are defined in the same geometric reference
    #        # as the anatomical file. That is, the fibers coordinates are related to 
    #        # the anatomy in world space. The transformation from local to world space
    #        # for the anatomy is encoded in the m_dh->m_niftiTransform member.
    #        # Since we do not consider this tranform when loading the anatomy, we must 
    #        # bring back the fibers in the same reference, using the inverse of the 
    #        # local to world transformation. A further problem arises when loading an
    #        # anatomy that has voxels with dimensions differing from 1x1x1. The 
    #        # scaling factor is encoded in the transformation matrix, but we do not,
    #        # for the moment, use this scaling. Therefore, we must remove it from the
    #        # the transformation matrix before computing its inverse.
    #        anat = nibabel.load(anatFile)
    #        voxelSize = list(anat.get_header().get_zooms())
    #        
    #        M = anat.get_header().get_qform()
    #        idxDiag = np.diag(np.diag(M)) != 0;
    #        M[idxDiag] /= voxelSize + [1]
    #        M = linalg.inv(M)
    #        
    #        pts = np.dot(c_[pts, np.ones([len(pts), 1])], M.T)[:,:-1]
        
            
    #####
    #Iterate through fibers
    ###
    def __iter__(self):
        buff = ""
        idxNaN = []
        
        f = open(self.filename, 'rb')
        f.seek(self.offset)
        remainingBytes = os.path.getsize(self.filename) - self.offset
        
        while remainingBytes > 0:
            if remainingBytes > 0:
                nbBytesToRead = min(remainingBytes, 100*3*self.dtype.itemsize)
                buff += f.read(nbBytesToRead) #Read 100 triplets of coordinates (float)
                remainingBytes -= nbBytesToRead;
                    
            pts = np.frombuffer(buff, dtype=self.dtype) #Convert binary to float
            
            if self.dtype != '<f4':
                pts = pts.astype('<f4')

            pts = pts.reshape([-1, 3])
            idxNaN = np.arange(len(pts))[np.isnan(pts[:,0])]
                
            if len(idxNaN) == 0:
                continue
            
            nbPts = len(pts[:idxNaN[0],:])
            yield np.dot(c_[pts[:idxNaN[0],:], np.ones([nbPts, 1], dtype='<f4')], self.invM)[:,:-1] 
            
            #Remove pts plus the first triplet of NaN.
            nbBytesToRemove = (nbPts+1)*3*self.dtype.itemsize
            buff = buff[nbBytesToRemove:] 
            idxNaN = idxNaN[1:]
        
        f.close()
