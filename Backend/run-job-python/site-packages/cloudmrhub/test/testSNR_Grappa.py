import numpy as np
import cloudmrhub.cm2D as cm2D
import cloudmrhub.cm as cm
import matplotlib.pyplot as plt
import  twixtools

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



FA=1
PA=2
ACLF=20
ACLP=20
GK=[3,2]

L=cm2D.cm2DReconGRAPPA()
L.AccelerationF=FA
L.AccelerationP=PA
L.AutocalibrationF=ACLF
L.AutocalibrationP=ACLP
US=cm.undersample2DDatamGRAPPA(S,frequencyacceleration=FA,phaseacceleration=PA,frequencyACL=ACLF,phaseACL=ACLP)
L.setSignalKSpace(US)
L.setNoiseKSpace(N)
L.setGrappaKernel(GK)


L2=cm2D.cm2DSignalToNoiseRatioPseudoMultipleReplicas()

L2.numberOfReplicas=100
L2.reconstructor=L

plt.subplot(121)
plt.imshow(L2.getOutput(),vmax=250)
plt.title('PMR')
plt.colorbar()

R2=cm2D.cm2DSignalToNoiseRatioPseudoMultipleReplicasWen()
R=cm2D.cm2DReconRSS()
R2.numberOfReplicas=5
R2.boxSize=10
R.setNoiseKSpace(N)
R.setSignalKSpace(S)
R2.reconstructor=R






plt.subplot(122)
plt.imshow(R2.getOutput(),vmax=250)
plt.title('CR')
plt.colorbar()



plt.show()