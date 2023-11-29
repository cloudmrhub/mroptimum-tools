from cloudmrhub.cm2D import *
import cloudmrhub.cm as cm
import multiprocessing as mlp
from pynico_eros_montin import pynico as pn

VERSION="1.0.0"
def saveImage(x,origin=None,spacing=None,direction=None,fn=None):
    if not(direction is None):
        x.setImageDirection(direction)
    if not(spacing  is None):
        x.setImageSpacing(spacing)
    if not(direction  is None):
        x.setImageOrigin(origin)
    x.writeImageAs(fn)






def customizerecontructor(reconstructor,O={}):
    signal=O["signal"]
    noise=O["noise"]
    noisecovariance=O["noisecovariance"]
    reference=O["reference"]
    mimic=O["mimic"]
    acceleration=O["acceleration"]
    autocalibration=O["autocalibration"]
    grappakernel=O["grappakernel"]
    try:
        LOG=reconstructor.LOG
    except:
        LOG=[]

    reconstructor.complexType=np.singlecomplex
    #signal
    if reconstructor.HasAcceleration:
        if mimic:
            signal,reference=cm.mimicAcceleration2D(signal,acceleration,autocalibration)
            LOG.append(f'Mimicked an accelaration of {acceleration}')
        else:
            signal=fixAccelratedKSpace2D(signal)
            reference=fixAccelratedKSpace2D(reference)
        reconstructor.setAcceleration(acceleration)
        reconstructor.setAutocalibrationLines(autocalibration)
        LOG.append(f'Acceleration set to {acceleration}' )
    reconstructor.setSignalKSpace(signal)

    
    #reference
    if reconstructor.HasSensitivity or reconstructor.HasAcceleration:
        reconstructor.setReferenceKSpace(reference)

    #noise
    if noise is not None:
        reconstructor.setNoiseKSpace(noise)
        
    elif noisecovariance is not None:
        reconstructor.setNoiseCovariance(noisecovariance)
    else:
        reconstructor.setPrewhitenedSignal(signal)
        reconstructor.setNoiseCovariance(np.eye(signal.shape[-1]))
        LOG.append(f'no Noise informations images will not be prewhitened' )
    
    if ((reconstructor.HasAcceleration) and (not reconstructor.HasSensitivity)):
        # this is grappa:
        if grappakernel is not None:
            reconstructor.setGRAPPAKernel(grappakernel)
        else:
            reconstructor.setGRAPPAKernel([x+1 for x in acceleration])
        LOG.append(f'GRAPPA Kernel set to {reconstructor.GRAPPAKernel}' )
        
    return reconstructor
def calcPseudoMultipleReplicasSNR(O): 
    reconstructor=O["reconstructor"]
    NR=O["NR"]

    OUT={"slice":O["slice"],"images":{}}
    
 

    L2=cm2DSignalToNoiseRatioPseudoMultipleReplicas()            
    if NR:
        L2.numberOfReplicas=NR
    reconstructor =customizerecontructor(reconstructor,O) 
    L2.reconstructor=reconstructor
    
    SNR=L2.getOutput()
    OUT["images"]["SNR"]={"id":0,"dim":3,"name":"SNR","data":SNR,"filename":'data/SNR.nii.gz',"type":'output',"numpyPixelType":SNR.dtype.name}

    if reconstructor.HasSensitivity and O["savecoilsens"]:
        CS=reconstructor.getCoilSensitivityMatrix()
        for a in range(CS.shape[-1]):
            OUT["images"][f"SENSITIVITY_{a:02d}"]={"id":10+a,"dim":3,"name":f"Coils Sensitivity {a:02d}","data":CS[:,:,a],"filename":f'data/sensitivity_{a:02d}.nii.gz',"type":'accessory',"numpyPixelType":CS.dtype.name}
        
    if isinstance(reconstructor,cm2DReconSENSE) and O["savegfactor"]:
        reconstructor.__class__=cm2DGFactorSENSE
        OUT["images"]["GFactor"]={"id":4,"dim":3,"name":"G Factor","data":reconstructor.getOutput(),"filename":'data/G.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
        OUT["images"]["InverseGFactor"]={"id":3,"dim":3,"name":"Inverse G Factor","data":1.0/reconstructor.getOutput(),"filename":'data/IG.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 

    return OUT
def calcPseudoMultipleReplicasSNRWien(O):    
    reconstructor=O["reconstructor"]
    NR=O["NR"]
    boxSize=O["boxSize"]
    OUT={"slice":O["slice"],"images":{}}
    
 

    L2=cm2DSignalToNoiseRatioPseudoMultipleReplicasWein()            
    if NR:
        L2.numberOfReplicas=NR
    if boxSize:
        L2.boxSize=boxSize

    reconstructor =customizerecontructor(O) 
    SNR=L2.getOutput()
    OUT["images"]["SNR"]={"id":0,"dim":3,"name":"SNR","data":SNR,"filename":'data/SNR.nii.gz',"type":'output',"numpyPixelType":SNR.dtype.name}

    if reconstructor.HasSensitivity and O["savecoilsens"]:
        CS=reconstructor.getCoilSensitivityMatrix()
        for a in range(CS.shape[-1]):
            OUT["images"][f"SENSITIVITY_{a:02d}"]={"id":10+a,"dim":3,"name":f"Coils Sensitivity {a:02d}","data":CS[:,:,a],"filename":f'data/sensitivity_{a:02d}.nii.gz',"type":'accessory',"numpyPixelType":CS.dtype.name}
        
    if isinstance(reconstructor,cm2DReconSENSE) and O["savegfactor"]:
        reconstructor.__class__=cm2DGFactorSENSE
        OUT["images"]["GFactor"]={"id":4,"dim":3,"name":"G Factor","data":reconstructor.getOutput(),"filename":'data/G.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
        OUT["images"]["InverseGFactor"]={"id":3,"dim":3,"name":"Inverse G Factor","data":1.0/reconstructor.getOutput(),"filename":'data/IG.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
    return OUT



def calcKellmanSNR(O):
    reconstructor=O["reconstructor"]
    OUT={"slice":O["slice"],"images":{}}
 

    
    reconstructor =customizerecontructor(reconstructor,O) 
    #only difference is here
    SNR=reconstructor.getOutput()
    OUT["images"]["SNR"]={"id":0,"dim":3,"name":"SNR","data":SNR,"filename":'data/SNR.nii.gz',"type":'output',"numpyPixelType":SNR.dtype.name}
    if reconstructor.HasSensitivity and O["savecoilsens"]:
        CS=reconstructor.getCoilSensitivityMatrix()
        for a in range(CS.shape[-1]):
            OUT["images"][f"SENSITIVITY_{a:02d}"]={"id":10+a,"dim":3,"name":f"Coils Sensitivity {a:02d}","data":CS[:,:,a],"filename":f'data/sensitivity_{a:02d}.nii.gz',"type":'accessory',"numpyPixelType":CS.dtype.name} 
        
        
    if isinstance(reconstructor,cm2DReconSENSE) and O["savegfactor"]:
        reconstructor.__class__=cm2DGFactorSENSE
        OUT["images"]["GFactor"]={"id":4,"dim":3,"name":"G Factor","data":reconstructor.getOutput(),"filename":'data/G.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
        OUT["images"]["InverseGFactor"]={"id":3,"dim":3,"name":"Inverse G Factor","data":1.0/reconstructor.getOutput(),"filename":'data/IG.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
    return OUT

def calcMultipleReplicasSNR(O):    
    reconstructor=O["reconstructor"]
    
    #freq,phase,coil,number of replicas
    signal=O["signal"]
    noise=O["noise"]
    noisecovariance=O["noisecovariance"]
    # fake one just to homogeneous the code
    # we are chaning the signal in the loop
    O["signal"]=signal[...,0]
    
    OUT={"slice":O["slice"],"images":{}}

 

    L2=cm2DSignalToNoiseRatioMultipleReplicas()

    reconstructor =customizerecontructor(reconstructor,O) 
    L2.reconstructor=reconstructor
    for r in range(signal.shape[-1]):
        _S=signal[...,r]
        _R=signal[...,r]
        if reconstructor.HasAcceleration:
            if O["mimic"]:
                _S,_R=cm.mimicAcceleration2D(_S,O["acceleration"],O["autocalibration"]) 
            # if there's a noise information 
            else:
                _S=fixAccelratedKSpace2D(_S)
                _R=fixAccelratedKSpace2D(_R)
        if (noise is not None) or (noisecovariance is not None):
            L2.reconstructor.setSignalKSpace(_S)
            if reconstructor.HasSensitivity or reconstructor.HasAcceleration:   
                L2.reconstructor.setReferenceKSpace(_R)
        #otherwise we are using the prewhitened signal                
        else:
            L2.reconstructor.setPrewhitenedSignal(_S)
            if reconstructor.HasSensitivity or reconstructor.HasAcceleration:
                L2.reconstructor.setPrewhitenedReferenceKSpace(_R)
        L2.add2DImage(L2.reconstructor.getOutput())
    
    SNR=L2.getOutput()
    OUT["images"]["SNR"]={"id":0,"dim":3,"name":"SNR","data":SNR,"filename":'data/SNR.nii.gz',"type":'output',"numpyPixelType":SNR.dtype.name}

    if reconstructor.HasSensitivity and O["savecoilsens"]:
        CS=reconstructor.getCoilSensitivityMatrix()
        for a in range(CS.shape[-1]):
            OUT["images"][f"SENSITIVITY_{a:02d}"]={"id":10+a,"dim":3,"name":f"Coils Sensitivity {a:02d}","data":CS[:,:,a],"filename":f'data/sensitivity_{a:02d}.nii.gz',"type":'accessory',"numpyPixelType":CS.dtype.name}
        
    if isinstance(reconstructor,cm2DReconSENSE) and O["savegfactor"]:
        reconstructor.__class__=cm2DGFactorSENSE
        OUT["images"]["GFactor"]={"id":4,"dim":3,"name":"G Factor","data":reconstructor.getOutput(),"filename":'data/G.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
        OUT["images"]["InverseGFactor"]={"id":3,"dim":3,"name":"Inverse G Factor","data":1.0/reconstructor.getOutput(),"filename":'data/IG.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
    return OUT


RECON=["rss","b1","sense","grappa"]
RECON_classes=[cm2DReconRSS,cm2DReconB1,cm2DReconSENSE,cm2DReconGRAPPA]
SNR=["ac","mr","pmr","cr"]
KELLMAN_classes=[cm2DKellmanRSS,cm2DKellmanB1,cm2DKellmanSENSE,None]
SNR_calculator=[calcKellmanSNR,
                calcMultipleReplicasSNR,
                calcPseudoMultipleReplicasSNR,
                calcPseudoMultipleReplicasSNRWien]

class manalitical:
    def __init__(self,reconstructor,counter=0) -> None:
        self.reconstructor=reconstructor
        self.counter=counter

    
    def getOutput(self):
        return self.reconstructor.getOutput(),self.counter


class mreplicas:
    def __init__(self,reconstructor,snrmethod,NR=None,boxsize=None,counter=0) -> None:
        self.reconstructor=reconstructor
        self.snrmethod=snrmethod
        self.NR=NR
        self.boxsize=boxsize
        self.counter=counter

    
    def getOutput(self):
        return replicas(self.reconstructor,self.snrmethod,self.NR,self.boxsize),self.counter
        
        
def replicas(reconstructor,snrmethod,NR=None,boxsize=None):
    L2=snrmethod
    if NR:
        L2.numberOfReplicas=NR
    if boxsize:
        L2.boxSize=10
    L2.reconstructor=reconstructor
    O=L2.getOutput()
    return O

def rT(t,counter=None):
    return t.getOutput()


import boto3

s3 = boto3.client('s3')


def getFile(s):
    """
    
    Args:
        s (_type_): _description_
    
    Returns:
      fn (str): position of the file in the local filesystem

    """
    if (s["type"].lower()=='local'):
        return s["filename"]
    elif (s["type"].lower()=='s3'):
        T=pn.createRandomTemporaryPathableFromFileName(s["filename"])
        with open(T, 'wb') as f:
            s3.download_fileobj(s["bucket"],s["key"], f)
        return T
    else:
        raise Exception("I can't get this file modality")

import twixtools
import numpy as np
from raider_eros_montin import raider

def getSiemensKSpace2DInformation(s,signal=True,MR=False):
    N=pn.Pathable(getFile(s["options"]))
    n=N.getPosition()
    twix=twixtools.map_twix(n)
    if signal:
        raid =len(twix)-1
    H=twix[raid]["hdr"]
    SA=H["Phoenix"]['sSliceArray']
 
    C=H["Config"]
    KS=[int(a) for a in [C['BaseResolution'],C['PhaseEncodingLines']]]
    slices=[]
    SL=SA["asSlice"]

    K=getSiemensKSpace2D(N.getPosition(),noise=False,slice='all',raid=raid,MR=MR)
    try:
        SLORDER=[int(a) for a in C["relSliceNumber"].replace('-1','').replace(' ','')]
    except:
        SLORDER=range(len(SL))
    if len(K)==1:
        CC=[0]
    else:
        CC=SLORDER
    for t in CC:
        sl=SL[t]
        slp=SL[t]['sPosition']
        try:
            ORIGIN=[slp["dSag"],slp["dCor"],slp["dTra"]]
        except:
            ORIGIN=[0]*3
            print("wasn't able to get the origin of this slice")
        o={
            "fov":[sl["dReadoutFOV"],sl["dPhaseFOV"],sl["dThickness"]*SA["lSize"]],
            "spacing":[sl["dReadoutFOV"]/KS[0],sl["dPhaseFOV"]/KS[1],sl["dThickness"]],
            
            "origin":ORIGIN,
            "size":[*KS,1],
            "KSpace":K[t]
        }
        if sl['sNormal']["dTra"]:
            o["direction"]=-np.eye(3)
            o["direction"][-1:-1]=-sl['sNormal']["dTra"]
        slices.append(o)
    return slices





def fixReferenceSiemens(ref_,signal_acceleration_realsize):
    s_ref=list(ref_.shape)
    #non accelerated_size
    s_ref[1]=signal_acceleration_realsize
    ref=np.zeros((s_ref),dtype=ref_.dtype)
    n_ref=ref_.shape[1]
    ref[:,0:n_ref]=ref_
    return ref

def getSiemensReferenceKSpace2D(s,signal_acceleration_realsize,slice=0,raid=1):
    N=pn.Pathable(getFile(s["options"]))
    n=N.getPosition()
    twix=twixtools.map_twix(n)
    r_array = twix[raid]['refscan']
    r_array.flags['remove_os'] = True  # activate automatic os removal
    r_array.flags['average']['Rep'] = True  # average all repetitions
    r_array.flags['average']['Ave'] = True # average all repetitions

    SL=11
    if isinstance(slice,str):
        if slice.lower()=='all':
            K=[]
            for sl in range(r_array.shape[SL]):
                ref=fixReferenceSiemens(np.transpose(r_array[0,0,0,0,0,0,0,0,0,0,0,sl,0,:,:,:],[2,0,1]),signal_acceleration_realsize)
                K.append(ref)
        return K  
    
    sl=0
    return fixReferenceSiemens(np.transpose(r_array[0,0,0,0,0,0,0,0,0,0,0,sl,0,:,:,:],[2,0,1]),signal_acceleration_realsize)


def getSiemensKSpace2D(n,noise=False,aveRepetition=True,slice=0,raid=0,MR=False):
    
    twix=twixtools.map_twix(n)
    im_array = twix[raid]['image']
    im_array.flags['remove_os'] = not noise  # activate automatic os removal

    if noise:
        im_array.flags['average']['Rep'] = False  # average all repetitions
        im_array.flags['average']['Ave'] = False # average all repetitions
    else:
        if not MR:
            #if it' not mr
            im_array.flags['average']['Rep'] = aveRepetition  # average all repetitions
            im_array.flags['average']['Ave'] = True # average all repetitions
        else:
            #if it's mr
            im_array.flags['average']['Rep'] = False
            im_array.flags['average']['Ave'] = True
    SL=11
    if isinstance(slice,str):
        if slice.lower()=='all':
            K=[]
            for sl in range(im_array.shape[SL]):
                # print(sl)
                if MR:
                    K.append(np.transpose(im_array[0,0,0,0,0,0,0,:,0,0,0,sl,0,:,:,:],[3,1,2,0]))    
                else:
                    K.append(np.transpose(im_array[0,0,0,0,0,0,0,0,0,0,0,sl,0,:,:,:],[2,0,1])   )
                    
        return K  
    else:
        if MR:
            K=np.transpose(im_array[0,0,0,0,0,0,0,:,0,0,0,sl,0,:,:,:],[3,1,2,0])
        else:
            K=np.transpose(im_array[0,0,0,0,0,0,0,0,0,0,0,sl,0,:,:,:],[2,0,1])
        
        return K

def getNoiseKSpace(s,slice=0):
    """
    
    Args:
        s (_type_): _description_
    
    Returns:
      fn (str): position of the file in the local filesystem

    """
    N=pn.Pathable(getFile(s["options"]))

    if N.getExtension() == 'dat':
        if (s["options"]["multiraid"]):
                # K=getSiemensKSpace2D(N.getPosition(),noise=True,slice=slice,raid=0)
                K=raider.readMultiRaidNoise(N.getPosition(),slice=slice,raid=0)
                return K
        else: 
            return getSiemensKSpace2D(N.getPosition(),noise=True,slice=slice)
    else:
        raise Exception("I can't get the noise")


def getKSpace(s,slice=0):
    """
    
    Args:
        s (_type_): _description_
    
    Returns:
      fn (str): position of the file in the local filesystem

    """
    N=pn.Pathable(getFile(s["options"]))

    if N.getExtension() == 'dat':
        if (s["options"]["multiraid"]):
                K=getSiemensKSpace2D(N.getPosition(),noise=False,slice=slice,raid=1)
                return K
        else: 
            return getSiemensKSpace2D(N.getPosition(),noise=False,slice=slice)
    else:
        raise Exception("I can't get the noise")




import cloudmrhub.cm2D as cm2D    
def calculteNoiseCovariance(NOISE,verbose=False):
    # N is an array of 2d slices f,p,c
    NN=cm2D.cm2DRecon()
    for tn in range(0,len(NOISE)):
        if tn==0:
            BN=NOISE[tn]
        else:
            BN=np.concatenate((BN,NOISE[tn]),axis=1)
    NN.setNoiseKSpace(BN)
    NC=NN.getNoiseCovariance()
    NCC=NN.getNoiseCovarianceCoefficients()
    if verbose:
       plt.figure()
       plt.subplot(121)
       plt.imshow(np.abs(NC))
       plt.title('Noise Covariance Matrix')
       plt.subplot(122)
       plt.imshow(np.abs(NCC))
       plt.title('Noise Coefficient Matrix')
    return NC,NCC
def fixAccelratedKSpace2D(s):
    if np.mod(s.shape[1],2)>0:
        G=np.zeros((s.shape[0],1,s.shape[2]))
        s=np.concatenate((s,G),axis=1)
    return s

