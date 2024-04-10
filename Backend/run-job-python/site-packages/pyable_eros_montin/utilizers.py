import SimpleITK as sitk
from pynico_eros_montin import pynico as pn

from .imaginable import Roiable

class RoiComparison():
    """
    A class that compares 2 ROIable

    ...

    Attributes
    ----------
    ref : Roiable
        The reference ROIable
    test : ROIable
        The Roiable that you want to test
    """

    
    def __init__(self,ref=None,test=None):

        self.Reference=ref
        self.Test=test
        self.Overlap=None
        self.ComparisonArea=None
        
    def getReference(self):
        return self.Reference
    def getTest(self):
        return self.Test
    def setReference(self,reference):
        self.resetOverlap()
        self.Reference =reference

    # def setComparisonArea(self,comparison_area):
    #     self.resetOverlap()
    #     self.ComparisonArea =comparison_area

    # def getReferenceAndTest(self):
    #     if self.ComparisonArea:
    #         R=self.Reference.getDuplicate()
    #     self.resetOverlap()

    def setTest(self,test):
        self.resetOverlap()
        self.Test=test
    def setOverlapFilter(self,overlap):
        self.Overlap =overlap
    def resetOverlap(self):
        self.Overlap =None

    def getOverlapFilter(self):
        ov=self.Overlap
        if ov is None:
            R=self.getReference()
            T=self.getTest()
            t=T.getImage()
            r=R.getImage()
            if (r is not None) & (t is not None):
                ov=sitk.LabelOverlapMeasuresImageFilter()
                try:
                    ov.Execute(r, t)
                    
                except Exception as e:
                    if(e.__str__().find('Inputs do not occupy the same physical space!'))>0:
                        O=R.getDuplicate()
                        O.resampleOnTargetImage(T)
                        r=O.getImage()
                        ov.Execute(r, t)
                self.setOverlapFilter(ov)
                return ov
            else:
                return None

        else:
            return ov

    def getJaccard(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetJaccardCoefficient()
        else:
            return None
    
    def getDice(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetDiceCoefficient()
        else:
            return None

    def getSimilarity(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetVolumeSimilarity()
        else:
            return None
    
    def getFalseNegativeError(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetFalseNegativeError()
        else:
            return None
    
    def getFalsePostiveError(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetFalsePositiveError()
        else:
            return None
    
    def getHahusdorf(self):
        ov = sitk.HausdorffDistanceImageFilter()
        R=self.getReference()
        T=self.getTest()
        t=T.getImage()
        r=R.getImage()

        ov.Execute(r, t)
        if ov is not None:
            return ov.GetHausdorffDistance()
        else:
            return None

    def getVolmeSimilarity(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetVolumeSimilarity()
        else:
            return None

    def getMeanOverlap(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetMeanOverlap()
        else:
            return None

    def getSimilarity(self):
        ov = sitk.SimilarityIndexImageFilter()
        R=self.getReference()
        T=self.getTest()
        t=T.getImage()
        r=R.getImage()
        ov.Execute(r, t)
        if ov is not None:
            return ov.GetSimilarityIndex()
        else:
            return None

    def getOverlappedVoxels(self):
        O=self.getReference().getDuplicate()
        O.add(self.getTest())
        s=sitk.StatisticsImageFilter()
        s.Execute(O.getImage()==2)
        return s.GetSum()

    def getNonOverlappedVoxels(self):
        O=self.getReference().getDuplicate()
        O.add(self.getTest())
        s=sitk.StatisticsImageFilter()
        s.Execute(O.getImage()!=2)
        return s.GetSum()
    
    def getAllMetrics(self):
        O={
            "Hahusdorf":self.getHahusdorf(),
            "FNE":self.getFalseNegativeError(),
            "FPE":self.getFalsePostiveError(),
            "Dice":self.getDice(),
            "Jaccard":self.getJaccard(),
            "VolumeSimilarity":self.getVolmeSimilarity(),
            "MeanOverlap":self.getMeanOverlap(),
            "Similarity":self.getSimilarity(),
            "OverlappedVoxels":self.getOverlappedVoxels(),
            "NonOverlappedVoxels":self.getNonOverlappedVoxels(),
        }
        return O
    
    def printAllMetrics(self,json=None):
        if json:
            pn.Pathable(json).writeJson(self.getAllMetrics())
        else:
            print(self.getAllMetrics())




if __name__=="__main__":
    import numpy as np
    r=np.zeros((10,10,10),dtype=np.int16)
    r[0:8,0:8,0:8]=4
    t=np.zeros((20,20,20),dtype=np.int16)
    t[0:16,0:16,0:16]=1

    R=Roiable()
    R.setImageFromNumpy(r)
    R.roiValue=4
    R.setImageSpacing([2,2,2])
    R.viewAxial()
    T=Roiable()
    T.setImageFromNumpy(t)
    T.roiValue=1
    C=RoiComparison(R,T)
    print(C.getDice())
    # C.printAllMetrics()
