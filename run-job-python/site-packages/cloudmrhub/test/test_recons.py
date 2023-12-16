from cloudmrhub.cm2D import cm2DKellmanRSS, cm2DReconRSS, cm2DKellmanB1,cm2DReconB1,cm2DReconSENSE,cm2DKellmanSENSE,cm2DGFactorSENSE,cm2DReconGRAPPA
import cloudmrhub.cm as cm

import twixtools
import numpy as np
import matplotlib.pyplot as plt

s='cloudmrhub/data/meas_MID00024_FID188178_Multislice.dat'
n='cloudmrhub/data/meas_MID00027_FID188181_Multislice_no_RF.dat'

twix=twixtools.map_twix(s)
im_array = twix[0]['image']
im_array.flags['remove_os'] = True  # activate automatic os removal
im_array.flags['average']['Rep'] = True  # average all repetitions
im_array.flags['average']['Ave'] = True  # average all repetitions
S=np.transpose(im_array[0,0,0,0,0,0,0,0,0,0,0,0,0,:,:,:],[2,0,1])


twix=twixtools.map_twix(n)
im_array = twix[0]['image']
im_array.flags['remove_os'] = False  # activate automatic os removal
im_array.flags['average']['Rep'] = False  # average all repetitions
im_array.flags['average']['Ave'] = False # average all repetitions
N=np.transpose(im_array[0,0,0,0,0,0,0,0,0,0,0,0,0,:,:,:],[2,0,1])



L=cm2DReconRSS()
L.setSignalKSpace(S)
L.setNoiseKSpace(N)

NBW=L.getNoiseBandWidth()

nc2=L.getNoiseCovariance()
plt.figure()
plt.subplot(121)
plt.imshow(np.abs(nc2))
plt.colorbar()
plt.title(f'Noise Covariance Matrix BW:{NBW:03f}')

plt.subplot(122)
plt.imshow(np.abs(L.getNoiseCovarianceCoefficients()))
plt.colorbar()
plt.title(f'Noise Coefficient Matrix BW:{NBW:03f}')


p=L.getPrewhitenedSignal()
plt.figure()
plt.imshow(np.abs(p[:,:,0]))
plt.colorbar()
plt.title('Prewhitened Kspace First Coil')

im=L.getOutput()

import matplotlib.pyplot as plt

plt.imshow(im)
plt.colorbar()
plt.title('RSS Recon')

L=cm2DReconB1()
L.setSignalKSpace(S)
L.setNoiseKSpace(N)
L.setReferenceKSpace(S)
L.prepareCoilSensitivityMatrixPlot(title='B1 Coil Sensitivity Maps')
plt.figure()
plt.imshow(np.abs(L.getOutput()))
plt.title('B1 Recon')



# acceleration frequency and phase
FA=1
PA=2
# autocalibrationlines
ACL=20
L=cm2DReconSENSE()
L.setAcceleration([FA,PA])
US,REF=cm.mimicAcceleration2D(S,[FA,PA],ACL=[np.nan,ACL])

L.setSignalKSpace(US)
L.setNoiseKSpace(N)
L.setReferenceKSpace(REF)
L.setAutocalibrationLines(ACL)

L.prepareCoilSensitivityMatrixPlot(title='SENSE Coil Sensitivity Maps')

plt.figure()
plt.imshow(np.abs(L.getOutput()))
plt.title('SENSE Recon')



# transform in Kellman!!!
L.__class__=cm2DGFactorSENSE
plt.figure()
plt.imshow(np.abs(L.getOutput()),vmin=0,vmax=2)
plt.colorbar()
plt.title('GFactor')



FA=1
PA=4
ACLF=20
ACLP=20
GK=[2,5]

US,REF=cm.mimicAcceleration2D(S,[FA,PA],[ACLF,ACLP])
L=cm2DReconGRAPPA()
L.setSignalKSpace(US)
L.setAcceleration([FA,PA])
L.setAutocalibrationLines([ACLF,ACLP])
L.setNoiseKSpace(N)
L.setGRAPPAKernel(GK)
L.setReferenceKSpace(REF)

plt.figure()
plt.imshow(np.abs(L.getOutput()))
plt.colorbar()
plt.title('GRAPPA Recon')
plt.show()