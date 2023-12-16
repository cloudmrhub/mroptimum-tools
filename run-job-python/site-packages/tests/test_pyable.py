
from pyable_eros_montin import imaginable as ima

A=ima.Imaginable('/data/MYDATA/HIPreconstructions/LeftRight111/input/Rightp10.nii.gz')
A.writeImageAs('/home/eros/Desktop/Segm/Rightp10.mha')
# import SimpleITK as sitk

# A=imaginable.SITKImaginable(filename='data/t.nii.gz')

# A.printImageInfo()


# B=A.getDuplicate()

# B.changeImageSpacing([5,5,5])
# B.changeImageOrigin([0,55,5])

# print(A.getVoxelVolume())
# print(B.getVoxelVolume())
# B.undo()
# B.changeImageSize([50,50,50],sitk.sitkBSpline)
# B.cropImage([0,0,0],[40,40,40])

# B.writeImageAs('/data/sa.nii.gz')
# B.whathappened()

# A.translateImage([5,0,0])
# A.writeImageAs('/data/tt.nii.gz')
# A.rotateImage([5,0,0])
# A.writeImageAs('/data/tr.nii.gz')
# A.scaleImage([0.8,0,0])
# A.writeImageAs('/data/ts.nii.gz')
# A.undo()
# A.writeImageAs('/data/tr2.nii.gz')
# A.cast(float)

# A.whathappened()



