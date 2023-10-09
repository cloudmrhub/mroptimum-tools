try:
    from imaginable import *
except:
    from .imaginable import *
try:   
    from utils import wlt
except:
    from .utils import wlt

import numpy as np

class LabelMapable(Imaginable):
    def __init__(self, filename=None, image=None, verbose=False,labelsvalues=None):
        super().__init__(filename, image, verbose)
        self.dfltInterpolator=sitk.sitkNearestNeighbor
        self.dfltuseNearestNeighborExtrapolator=True
        self.labelsvalues=labelsvalues
        self.ROIS=[]
        if self.labelsvalues is None:
            self.labelsvalues=self.getImageUniqueValues(exclude=[0])

        for v in self.labelsvalues:
            self.ROIS.append(Roiable(filename,image,verbose,roivalue=v))
        

    def removeSmallObj(self,voxel_threshold=50,connectivity=26):
        for r in self.ROIS:
            r.removeSmallObj(voxel_threshold,connectivity)
        self.mergeLabels()
        return self

    def removeHoles(self,voxel_threshold=50,connectivity=26):
        for r in self.ROIS:
            r.removeHoles(voxel_threshold,connectivity)
        # self.mergeLabels()
        return self
    def keepBiggestObj(self,connectivity=26):
        for r in self.ROIS:
            r.keepBiggestObj(connectivity)
        # self.mergeLabels()
        return self

    def mergeLabels(self):
        for rd,v in zip(self.ROIS,self.labelsvalues):
            print(v)
            O=rd.getImageAsNumpy()
            try:
                LABELMAP[np.where(O==1)]=v    
            except NameError:
                LABELMAP=O
        self.setImageFromNumpy(LABELMAP,refimage=super().getImage())
        return self
    





from pynico_eros_montin import pynico as pn

if __name__=="__main__":
    # FN='/g/LeftRight111/input/Leftp03-1.nii.gz'
    FN='/g/LeftRight111/input/Leftp02.nii.gz'
    K=Imaginable(filename=FN)
    WT=K.getWavelet('db1')
    for t in WT:
        t["map"].writeImageAs(pn.Pathable(FN).addPrefix(f'new{t["name"]}').changePath('/g').getPosition())
        

