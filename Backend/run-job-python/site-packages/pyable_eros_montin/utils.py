from pyable_eros_montin import imaginable


import numpy as np

# Input: expects 3xN matrix of points
# Returns R,t
# R = 3x3 rotation matrix
# t = 3x1 column vector

def rigid_transform_3D(A, B):
    assert A.shape == B.shape

    num_rows, num_cols = A.shape
    if num_rows != 3:
        raise Exception(f"matrix A is not 3xN, it is {num_rows}x{num_cols}")

    num_rows, num_cols = B.shape
    if num_rows != 3:
        raise Exception(f"matrix B is not 3xN, it is {num_rows}x{num_cols}")

    # find mean column wise
    centroid_A = np.mean(A, axis=1)
    centroid_B = np.mean(B, axis=1)

    # ensure centroids are 3x1
    centroid_A = centroid_A.reshape(-1, 1)
    centroid_B = centroid_B.reshape(-1, 1)

    # subtract mean
    Am = A - centroid_A
    Bm = B - centroid_B

    H = Am @ np.transpose(Bm)

    # sanity check
    #if linalg.matrix_rank(H) < 3:
    #    raise ValueError("rank of H = {}, expecting 3".format(linalg.matrix_rank(H)))

    # find rotation
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T

    # special reflection case
    if np.linalg.det(R) < 0:
        print("det(R) < R, reflection detected!, correcting for it ...")
        Vt[2,:] *= -1
        R = Vt.T @ U.T

    t = -R @ centroid_A + centroid_B

    return R, t

def getImaginableSlice(I,axis,index):
    if axis==0:
        slicer=I.getSliceNormalI
        # ratio=k[2]/k[1]
    elif axis==1:
        slicer=I.getSliceNormalJ
        # self.ratio=k[2]/k[0]
    elif axis==2:
        slicer=I.getSliceNormalK
        # self.ratio=k[1]/k[0]
    o=imaginable(image=slicer(index)).getImageAsNumpy()
    return o


from PIL import Image

import matplotlib
def saveSliceToImage(I,axis,index,fn,spacing=None):
    if spacing:
        I.changeImageSpacing(spacing)
    f=getImaginableSlice(I,axis=axis,index=index)
    matplotlib.image.imsave(fn, f,vmin=0.2,vmax=1,cmap='jet'  )

import pywt
def wlt(x=None,wtype='Haar'):
    return pywt.dwtn(x, wtype)




# if __name__=="__main__":

#     # P=pn.Pathable('/g/a/f.nii.gz')
#     # for p in P.getFilesInPathByExtension():
#     #     I=Imaginable(filename=p)
#     #     l=pn.Pathable(p)
#     #     l.changeExtension('png')
#     #     l.appendPath('f')
#     #     l.ensureDirectoryExistence()
#     #     for c,v in zip(range(3),[40,80,30]):
#     #         l.addPrefix(f'{c}_')
#     #         if not l.exists():
#     #             saveSliceToImage(I,axis=c,index=v,fn=l.getPosition())
#     #         l.undo()
        


   

#     # NEW=np.array([-0.9993099234645667, -6.385608658999428e-08, -0.037144005107034125, 1.898319864628949e-05, -0.9999998702797991, -0.0005089990447097432, -0.03714399688886282, -0.0005093529042066276, 0.9993097937099291]).reshape((3,3))
#     # ORIGINAL=np.eye(3)

#     # n=10
#     # t=np.array([[0],[0],[0]])
#     # A = np.random.rand(3, n)
#     # B = NEW@A + t

#     # ret_R, ret_t = rigid_transform_3D(A, B)
#     # print(ret_R)
#     # print(ret_t)
