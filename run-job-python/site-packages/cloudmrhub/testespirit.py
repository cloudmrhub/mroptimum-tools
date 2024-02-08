import twixtools
import numpy as np
from pynico_eros_montin import pynico as pn

s='cloudmrhub/data/meas_MID00024_FID188178_Multislice.dat'
n='cloudmrhub/data/meas_MID00027_FID188181_Multislice_no_RF.dat'

twix=twixtools.map_twix(s)
im_array = twix[0]['image']
im_array.flags['remove_os'] = True  # activate automatic os removal
im_array.flags['average']['Rep'] = True  # average all repetitions
im_array.flags['average']['Ave'] = True  # average all repetitions
im_array.flags['squeeze_singletons'] = False
S=np.transpose(im_array[0,0,0,0,0,0,0,0,0,0,0,:,0,:,:,:],[3,1,0,2])
import cm
L=cm.sensitivitiesEspirit2D(S,k=4,r=24)
import espirit
import numpy as np
import matplotlib.pyplot as plt

T=pn.Timer()
#plot the first 8 maps

fig, axs = plt.subplots(2, 4, figsize=(20, 10))
for i in range(8):
    axs[i//4, i%4].imshow(np.abs(L[:,:,i]), cmap='gray')
    axs[i//4, i%4].set_title(f'Map {i+1}')
    axs[i//4, i%4].axis('off')
print(T.stop())
plt.show()
# Path: cloudmrhub/espirit.py

