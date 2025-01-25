from cmtools.cm2D import *
import cmtools.cm as cm
import multiprocessing as mlp
from pynico_eros_montin import pynico as pn


from cmtools.cm2D import cm2DKellmanRSS as mroArrayCombiningRSS
from cmtools.cm2D import cm2DKellmanB1 as mroArrayCombiningB1
from cmtools.cm2D import cm2DKellmanSENSE as mroArrayCombiningSENSE

from cmtools.cm2D import cm2DSignalToNoiseRatioMultipleReplicas as mroMultipleReplicas
from cmtools.cm2D import cm2DSignalToNoiseRatioPseudoMultipleReplicas as mroPseudoMultipleReplicas
from cmtools.cm2D import cm2DSignalToNoiseRatioPseudoMultipleReplicasWein as mroGeneralizedPseudoMultipleReplicas



def saveImage(x,origin=None,spacing=None,direction=None,fn=None):
    if not(direction is None):
        x.setImageDirection(direction)
    if not(spacing  is None):
        x.setImageSpacing(spacing)
    if not(direction  is None):
        x.setImageOrigin(origin)
    x.writeImageAs(fn)



PKG=['mrotools','cmtools','pynico_eros_montin','pygrappa','twixtools','numpy','scipy','matplotlib','pydicom','SimpleITK','PIL','pyable_eros_montin','multiprocessing']

def getPackagesVersion():
    return pn.getPackagesVersion(PKG)


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


    reconstructor.complexType=np.complex64
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

    
    #mask
    if reconstructor.HasSensitivity or reconstructor.HasAcceleration:
        reconstructor.setReferenceKSpace(reference)
        if "mask" in O.keys():
            # if O["mask"] == False or O["mask"]=="no":
            #     reconstructor.setNoMask()
            #     LOG.append(f'No mask will be used' )
            # else:
                # reconstructor.setMaskCoilSensitivityMatrix(O["mask"])
            reconstructor.setMaskCoilSensitivityMatrix(O["mask"])
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
        M=reconstructor.outputMask.get()
        for a in range(CS.shape[-1]):
            OUT["images"][f"SENSITIVITY_{a:02d}"]={"id":10+a,"dim":3,"name":f"Coils Sensitivity {a:02d}","data":CS[:,:,a],"filename":f'data/sensitivity_{a:02d}.nii.gz',"type":'accessory',"numpyPixelType":CS.dtype.name}
        if not reconstructor.outputMask.isEmpty():
            a=0
            OUT["images"][f"MASK_{a:02d}"]={"id":100+a,"dim":3,"name":f"Coil Sensitivity Mask {a:02d}","data":M[:,:,a],"filename":f'data/mask_{a:02d}.nii.gz',"type":'mask',"numpyPixelType":M.dtype.name}
        
    if isinstance(reconstructor,cm2DReconSENSE) and O["savegfactor"]:
        reconstructor.__class__=cm2DGFactorSENSE
        G=reconstructor.getOutput()
        IGF=1/G
        IGF[np.isinf(IGF)]=0        
        OUT["images"]["GFactor"]={"id":4,"dim":3,"name":"G Factor","data":G,"filename":'data/G.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
        OUT["images"]["InverseGFactor"]={"id":3,"dim":3,"name":"Inverse G Factor","data":IGF,"filename":'data/IG.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 

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

    reconstructor =customizerecontructor(reconstructor,O) 

    L2.reconstructor=reconstructor
    SNR=L2.getOutput()
    OUT["images"]["SNR"]={"id":0,"dim":3,"name":"SNR","data":SNR,"filename":'data/SNR.nii.gz',"type":'output',"numpyPixelType":SNR.dtype.name}

    if reconstructor.HasSensitivity and O["savecoilsens"]:
        CS=reconstructor.getCoilSensitivityMatrix()
        M=reconstructor.outputMask.get()
        for a in range(CS.shape[-1]):
            OUT["images"][f"SENSITIVITY_{a:02d}"]={"id":10+a,"dim":3,"name":f"Coils Sensitivity {a:02d}","data":CS[:,:,a],"filename":f'data/sensitivity_{a:02d}.nii.gz',"type":'accessory',"numpyPixelType":CS.dtype.name}
        if not reconstructor.outputMask.isEmpty():
            a=0
            OUT["images"][f"MASK_{a:02d}"]={"id":100+a,"dim":3,"name":f"Coil Sensitivity Mask {a:02d}","data":M[:,:,a],"filename":f'data/mask_{a:02d}.nii.gz',"type":'mask',"numpyPixelType":M.dtype.name}

    if isinstance(reconstructor,cm2DReconSENSE) and O["savegfactor"]:
        reconstructor.__class__=cm2DGFactorSENSE
        G=reconstructor.getOutput()
        IGF=1/G
        IGF[np.isinf(IGF)]=0        
        OUT["images"]["GFactor"]={"id":4,"dim":3,"name":"G Factor","data":G,"filename":'data/G.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
        OUT["images"]["InverseGFactor"]={"id":3,"dim":3,"name":"Inverse G Factor","data":IGF,"filename":'data/IG.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
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

        M=reconstructor.outputMask.get()    
        for a in range(CS.shape[-1]):
            OUT["images"][f"SENSITIVITY_{a:02d}"]={"id":10+a,"dim":3,"name":f"Coils Sensitivity {a:02d}","data":CS[:,:,a],"filename":f'data/sensitivity_{a:02d}.nii.gz',"type":'accessory',"numpyPixelType":CS.dtype.name} 
        if not reconstructor.outputMask.isEmpty():
            a=0
            OUT["images"][f"MASK_{a:02d}"]={"id":100+a,"dim":3,"name":f"Coil Sensitivity Mask {a:02d}","data":M[:,:,a],"filename":f'data/mask_{a:02d}.nii.gz',"type":'mask',"numpyPixelType":M.dtype.name}

        
    if isinstance(reconstructor,cm2DReconSENSE) and O["savegfactor"]:
        reconstructor.__class__=cm2DGFactorSENSE
        G=reconstructor.getOutput()
        IGF=1/G
        IGF[np.isinf(IGF)]=0        
        OUT["images"]["GFactor"]={"id":4,"dim":3,"name":"G Factor","data":G,"filename":'data/G.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
        OUT["images"]["InverseGFactor"]={"id":3,"dim":3,"name":"Inverse G Factor","data":IGF,"filename":'data/IG.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
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
        # mask
        if reconstructor.HasSensitivity or reconstructor.HasAcceleration:
            if "mask" in O.keys():
                # if O["mask"] == False or O["mask"]=="no":
                #     reconstructor.setNoMask()
                # else:
                    # reconstructor.setMaskCoilSensitivityMatrix(O["mask"])
                reconstructor.setMaskCoilSensitivityMatrix(O["mask"])
 
        L2.add2DImage(L2.reconstructor.getOutput())
    
    SNR=L2.getOutput()
    OUT["images"]["SNR"]={"id":0,"dim":3,"name":"SNR","data":SNR,"filename":'data/SNR.nii.gz',"type":'output',"numpyPixelType":SNR.dtype.name}

    if reconstructor.HasSensitivity and O["savecoilsens"]:
        CS=reconstructor.getCoilSensitivityMatrix()
        M=reconstructor.outputMask.get()
        for a in range(CS.shape[-1]):
            OUT["images"][f"SENSITIVITY_{a:02d}"]={"id":10+a,"dim":3,"name":f"Coils Sensitivity {a:02d}","data":CS[:,:,a],"filename":f'data/sensitivity_{a:02d}.nii.gz',"type":'accessory',"numpyPixelType":CS.dtype.name}
        if not reconstructor.outputMask.isEmpty():
            a=0
            OUT["images"][f"MASK_{a:02d}"]={"id":100+a,"dim":3,"name":f"Coil Sensitivity Mask {a:02d}","data":M[:,:,a],"filename":f'data/mask_{a:02d}.nii.gz',"type":'mask',"numpyPixelType":M.dtype.name}
    
    if isinstance(reconstructor,cm2DReconSENSE) and O["savegfactor"]:
        reconstructor.__class__=cm2DGFactorSENSE
        G=reconstructor.getOutput()
        IGF=1/G
        IGF[np.isinf(IGF)]=0
        
        OUT["images"]["GFactor"]={"id":4,"dim":3,"name":"G Factor","data":G,"filename":'data/G.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
        OUT["images"]["InverseGFactor"]={"id":3,"dim":3,"name":"Inverse G Factor","data":IGF,"filename":'data/IG.nii.gz',"type":'accessory',"numpyPixelType":reconstructor.getOutput().dtype.name} 
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

import cmtools.cm as cm
import cmtools.cmaws as cmaws
def getFile(s,s3=None):
    return cmaws.getCMRFile(s,s3)

import twixtools
import numpy as np
from raider_eros_montin import raider
import copy
def getSiemensKSpace2DInformation(s,signal=True,MR=False):
    N=pn.Pathable(getFile(s))
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
    
    # theoutput is a list of 2d slices, if is MR but without replicas the output will be no MR data
    if isinstance(K,str):
        return K
    try:
        SLORDER=[int(a) for a in C["relSliceNumber"].replace('-1','').replace(' ','')]
    except:
        SLORDER=range(len(SL))
    if len(K)==1:
        CC=[0]
    else:
        CC=SLORDER
    for j,ft in enumerate(CC):
        t=SLORDER.index(j)
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
        

        o["direction"] = np.eye(3)  # Initialize with default identity matrix flipped.

        # Update specific components based on the scalar values in sl['sNormal']
        if "dTra" in sl['sNormal']:
            o["direction"][2, 2] = -sl['sNormal']["dTra"]  # Update the z-axis (axial) direction

        if "dSag" in sl['sNormal']:
            o["direction"][0, 0] = -sl['sNormal']["dSag"]  # Update the x-axis (sagittal) direction

        if "dCor" in sl['sNormal']:
            o["direction"][1, 1] = -sl['sNormal']["dCor"]  # Update the y-axis (coronal) direction

           
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
    N=pn.Pathable(getFile(s))
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
    _MR=7
    if noise:
        im_array.flags['average']['Rep'] = False  # average all repetitions
        im_array.flags['average']['Ave'] = False # average all repetitions
    else:
        if not MR:
            #if it's not mr
            im_array.flags['average']['Rep'] = aveRepetition  # average all repetitions
            im_array.flags['average']['Ave'] = True # average all repetitions
        else:
            #if it's mr
            if not im_array.shape[_MR]>1:
                return "No Multiple Replicas Data"
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
    N=pn.Pathable(getFile(s))

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




import cmtools.cm2D as cm2D    
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

