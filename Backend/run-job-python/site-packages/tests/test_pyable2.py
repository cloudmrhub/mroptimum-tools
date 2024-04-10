
from pyable_eros_montin import imaginable
import SimpleITK as sitk

A=imaginable.SITKImaginable(filename='/data/MYDATA/TDCS/EROS_TDCS/Healthy/NC_sub14_20190117/POST_LCA_PHA_s10383653-0074-00001-000001-01.nii')


B=A.getDuplicate()

A.rotateImage(rotation=[5,0],interpolator=sitk.sitkNearestNeighbor)
A.writeImageAs('/data/ttFalse.nii.gz')

B.rotateImage(rotation=[5,0],interpolator=sitk.sitkNearestNeighbor,useNearestNeighborExtrapolator=True)
B.writeImageAs('/data/ttTrue.nii.gz')
