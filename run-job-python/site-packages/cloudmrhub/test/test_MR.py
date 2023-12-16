import cloudmrhub.cm2D as cm2D
import numpy as np
import matplotlib.pyplot as plt
from pynico_eros_montin import pynico as pn
import twixtools

s="/data/MYDATA/siemensrawdataexamples/15042019_MR/meas_MID00036_FID188190_Multislice_100_REPLICAS.dat"

twix=twixtools.map_twix(s)
im_array = twix[0]['image']
im_array.flags['remove_os'] = True  # activate automatic os removal
im_array.flags['average']['Rep'] = False  # average all repetitions
im_array.flags['average']['Ave'] = True  # average all repetitions
SL=0
S=np.transpose(im_array[0,0,0,0,0,0,0,:,0,0,0,SL,0,:,:,:],[0,3,1,2])



L=cm2D.cm2DSignalToNoiseRatioMultipleReplicas()
L.reconstructor=cm2D.cm2DReconRSS()
for r in range(S.shape[-1]):
    L.reconstructor.setPrewhitenedSignal(S[r])
    L.add2DImage(L.reconstructor.getOutput())


plt.subplot(221)
plt.imshow(L.getOutput())
plt.title('SNR',pad=0)
plt.colorbar()
plt.axis('off')
plt.tick_params(axis='both', which='both', bottom=False, top=False, labelbottom=False, right=False, left=False, labelleft=False)
plt.subplot(222)
plt.imshow(L.getImageArrayMean())
plt.title('Mean',pad=0)
plt.colorbar()
plt.axis('off')
plt.tick_params(axis='both', which='both', bottom=False, top=False, labelbottom=False, right=False, left=False, labelleft=False)

plt.subplot(223)
plt.imshow(L.getImageArraySTD())
plt.title('STD',pad=0)
plt.colorbar()
plt.axis('off')
plt.tick_params(axis='both', which='both', bottom=False, top=False, labelbottom=False, right=False, left=False, labelleft=False)

plt.subplot(224)
plt.imshow(L.getImageArrayMax())
plt.title('Max',pad=0)
plt.colorbar()
plt.axis('off')
plt.tick_params(axis='both', which='both', bottom=False, top=False, labelbottom=False, right=False, left=False, labelleft=False)

plt.show()

