
import twixtools

import ismrmrd
from ismrmrdtools import simulation, transform
from ismrmrd import Dataset,Acquisition
from ismrmrd.xsd import CreateFromDocument as parse_ismrmd_header
import ismrmrd.xsd
from ismrmrd.constants import *
import numpy as np
import os

def KSpace2DtoISMRMRD(K,filename,resolution):
    #K is (rep,nPhase,nCoils,nFreq)
  
    try:
        os.unlink(filename)
    except:
         pass
        
        
    dset = Dataset(filename)
    # Create an acquisition block
    nReps,nY,nCoils,nX=K.shape
    # Fill the xml header
    header = ismrmrd.xsd.ismrmrdHeader()
 # Experimental Conditions
    exp = ismrmrd.xsd.experimentalConditionsType()
    exp.H1resonanceFrequency_Hz = 128000000
    header.experimentalConditions = exp
    
    # Acquisition System Information
    sys = ismrmrd.xsd.acquisitionSystemInformationType()
    sys.receiverChannels = nCoils
    header.acquisitionSystemInformation = sys

    oversampling =2
    # Encoding
    encoding = ismrmrd.xsd.encodingType()
    encoding.trajectory = ismrmrd.xsd.trajectoryType.CARTESIAN
    
    # encoded and recon spaces
    efov = ismrmrd.xsd.fieldOfViewMm()
    efov.x = nX*resolution[0]
    efov.y = nY *resolution[1]
    efov.z = resolution[2]

    rfov = ismrmrd.xsd.fieldOfViewMm()
    rfov.x = nX // oversampling*resolution[0]
    rfov.y = nY *resolution[1]
    rfov.z = resolution[2]

    ematrix = ismrmrd.xsd.matrixSizeType()
    ematrix.x = nX
    ematrix.y = nY
    ematrix.z = 1
    rmatrix = ismrmrd.xsd.matrixSizeType()
    rmatrix.x = int(nX // oversampling)
    rmatrix.y = nY
    rmatrix.z = 1
    
    espace = ismrmrd.xsd.encodingSpaceType(ematrix,efov)

    rspace = ismrmrd.xsd.encodingSpaceType(rmatrix,rfov)

      # Set encoded and recon spaces
    encoding.encodedSpace = espace
    encoding.reconSpace = rspace
    
    # Encoding limits
    limits = ismrmrd.xsd.encodingLimitsType()
    
    limits1 = ismrmrd.xsd.limitType()
    limits1.minimum = 0
    limits1.center = round(nY/2)
    limits1.maximum = nY - 1
    limits.kspace_encoding_step_1 = limits1
    
    limits_rep = ismrmrd.xsd.limitType()
    limits_rep.minimum = 0
    limits_rep.center = round(nReps / 2)
    limits_rep.maximum = nReps - 1
    limits.repetition = limits_rep
    
    limits_rest = ismrmrd.xsd.limitType()
    limits_rest.minimum = 0
    limits_rest.center = 0
    limits_rest.maximum = 0
    limits.kspace_encoding_step_0 = limits_rest
    limits.slice = limits_rest    
    limits.average = limits_rest
    limits.contrast = limits_rest
    limits.kspaceEncodingStep2 = limits_rest
    limits.phase = limits_rest
    limits.segment = limits_rest
    limits.set = limits_rest
    
    encoding.encodingLimits = limits
    header.encoding.append(encoding)
    
    dset.write_xml_header(header.toXML('utf-8'))      

 # Create an acquistion and reuse it
    acq = ismrmrd.Acquisition()
    acq.resize(nX, nCoils)
    acq.version = 1
    acq.available_channels = nCoils
    acq.center_sample = round(nX/2)
    acq.read_dir[0] = 1.0
    acq.phase_dir[1] = 1.0
    acq.slice_dir[2] = 1.0

    # Initialize an acquisition counter
    counter = 0
    
    for rep in range(nReps):
        acq.idx.repetition = rep
        for line in range(nY):
            # set some fields in the header
            acq.scan_counter = counter
            acq.idx.kspace_encode_step_1 = line
            acq.clearAllFlags()
            if line == 0:
                    acq.setFlag(ismrmrd.ACQ_FIRST_IN_ENCODE_STEP1)
                    acq.setFlag(ismrmrd.ACQ_FIRST_IN_SLICE)
                    acq.setFlag(ismrmrd.ACQ_FIRST_IN_REPETITION)
            elif line == nY - 1:
                    acq.setFlag(ismrmrd.ACQ_LAST_IN_ENCODE_STEP1)
                    acq.setFlag(ismrmrd.ACQ_LAST_IN_SLICE)
                    acq.setFlag(ismrmrd.ACQ_LAST_IN_REPETITION)
            # set the data and append
            acq.data[:] = K[rep,line,:,:]
            dset.append_acquisition(acq)
            counter += 1
    dset.write_acquisition
    # Clean up
    dset.close()



def readMultiRaidNoise(filename,raid=0,avgrep=False,avgave=False,knoise_dwelltime = 5000,slice=0):
    twix = twixtools.map_twix(filename)
    L=twix[raid]['noise']
    L.flags['average']['Rep'] = avgrep
    L.flags['average']['Ave'] = avgave 
    SL=11
    # print(K.shape)
# %                     theres's a dweltime also for noise but we decided to
# %                      set it to value = 5000 Riccardo 
#                        Riccardo Lattanzi on 05/23/2020
# %                      knoise_dwelltime=DATA{x}.hdr.Meas.RealDwellTime(2);
# %                      
    kdata_dwelltim=np.max(twix[raid]["hdr"]["Meas"]["alDwellTime"])
    correction_factor = np.sqrt(knoise_dwelltime/kdata_dwelltim)
    
    if isinstance(slice,str):
        K=[]
        if slice.lower()=='all':
            K=[]
            for sl in range(L.shape[SL]):
                print(sl)
                K.append(np.transpose(L[0,0,0,0,0,0,0,0,0,0,0,sl,0,:,:,:],[2,0,1])*correction_factor   )    
        return K  
    return np.transpose(L[0,0,0,0,0,0,0,0,0,0,0,slice,0,:,:,:],[2,0,1])




def exportNoiseFromRaid(filename,outputname,resolution=[1,1,1]):
    K=readMultiRaidNoise(filename,False,False)
    KSpace2DtoISMRMRD(K,outputname,resolution)
    


if __name__=="__main__":
     K=readMultiRaidNoise('/data/MYDATA/SNR_rawdata_examples/2018-07-31_BRAINO_scan/MULTI-RAID-FILE/meas_MID02317_FID373207_AXIAL_2D_GRE_1SL.dat',0,False,False)
    