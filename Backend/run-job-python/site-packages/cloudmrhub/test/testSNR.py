import numpy as np
import cloudmrhub.cm2D as cm2D

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

L2=cm2D.cm2DSignalToNoiseRatioPseudoMultipleReplicas()
L=cm2D.cm2DReconRSS()
L2.numberOfReplicas=100
L.setNoiseKSpace(N)
L.setSignalKSpace(S)
L2.reconstructor=L

plt.subplot(221)
plt.imshow(np.abs(L2.getOutput()))
plt.tick_params(axis='both', which='both', bottom=False, top=False, labelbottom=False, right=False, left=False, labelleft=False)
plt.title('PMR')


R2=cm2D.cm2DSignalToNoiseRatioPseudoMultipleReplicasWein()
R=cm2D.cm2DReconRSS()
R2.numberOfReplicas=3
R2.boxSize=10
R.setNoiseKSpace(N)
R.setSignalKSpace(S)
R2.reconstructor=R



plt.subplot(222)
plt.imshow(np.abs(R2.getOutput()))
plt.tick_params(axis='both', which='both', bottom=False, top=False, labelbottom=False, right=False, left=False, labelleft=False)
plt.title('CR')


R=cm2D.cm2DKellmanRSS()
R.setNoiseKSpace(N)
R.setSignalKSpace(S)
plt.subplot(223)
plt.imshow(np.abs(R.getOutput()))
plt.tick_params(axis='both', which='both', bottom=False, top=False, labelbottom=False, right=False, left=False, labelleft=False)
plt.title('Kellman')

plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
plt.colorbar(plt.gcf().axes[0].images[0], ax=plt.gcf().axes)
# add a title for the figure
plt.suptitle("SNR", fontsize=16)


plt.show()