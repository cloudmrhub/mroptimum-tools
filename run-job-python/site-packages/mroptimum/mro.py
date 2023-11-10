from cloudmrhub.cm2D import *
import cloudmrhub.cm as cm
import multiprocessing as mlp
from pynico_eros_montin import pynico as pn

VERSION="0.0.5"
def saveImage(x,origin=None,spacing=None,direction=None,fn=None):
    if not(direction is None):
        x.setImageDirection(direction)
    if not(spacing  is None):
        x.setImageSpacing(spacing)
    if not(direction  is None):
        x.setImageOrigin(origin)
    x.writeImageAs(fn)


RECON_classes=[cm2DReconRSS,cm2DReconB1,cm2DReconmSense,cm2DReconGrappa]
KELLMAN_classes=[cm2DKellmanRSS,cm2DKellmanB1,cm2DKellmanmSense,None]
G_classes=[None,None,cm2DGfactorSense,cm2DGfactormSense,None]
SNR_classes=[None,cm2DSignalToNoiseRatioMultipleReplicas,cm2DSignalToNoiseRatioPseudoMultipleReplicas,cm2DSignalToNoiseRatioPseudoMultipleReplicasWen]
RECON=["rss","b1","sense","grappa"]
SNR=["ac","mr","pmr","cr"]


def undersample(K,recon):
    N=recon["name"].lower()
    if N=='sense':
        return cm.undersample2DDataSENSE(K, frequencyacceleration=recon["options"]["accelerations"][0],phaseacceleration=recon["options"]["accelerations"][1]),True
    # if N=="msense":
    #     return cm.undersample2DDatamSENSE(K, frequencyacceleration=recon["options"]["accelerations"][0],phaseacceleration=recon["options"]["accelerations"][1],phaseACL=recon["options"]["acl"][1]),True
    if N=="grappa":
        return cm.undersample2DDatamGRAPPA(K, frequencyacceleration=recon["options"]["accelerations"][0],phaseacceleration=recon["options"]["accelerations"][1],frequencyACL=recon["options"]["acl"][0],phaseACL=recon["options"]["acl"][1]),True



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

def getSiemensKSpace2DInformation(s,signal=True):
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

    K=getSiemensKSpace2D(N.getPosition(),noise=False,slice='all',raid=raid)
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







def getSiemensKSpace2D(n,noise=False,aveRepetition=True,slice=0,raid=0):
    
    twix=twixtools.map_twix(n)
    im_array = twix[raid]['image']
    im_array.flags['remove_os'] = not noise  # activate automatic os removal

    if noise:
        im_array.flags['average']['Rep'] = False  # average all repetitions
        im_array.flags['average']['Ave'] = False # average all repetitions
    else:
        im_array.flags['average']['Rep'] = aveRepetition  # average all repetitions
        im_array.flags['average']['Ave'] = True # average all repetitions
    SL=11
    if isinstance(slice,str):
        if slice.lower()=='all':
            K=[]
            for sl in range(im_array.shape[SL]):
                # print(sl)
                K.append(np.transpose(im_array[0,0,0,0,0,0,0,0,0,0,0,sl,0,:,:,:],[2,0,1])   )    
        return K  
    return np.transpose(im_array[0,0,0,0,0,0,0,0,0,0,0,slice,0,:,:,:],[2,0,1])

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



def fixAccelratedKSpace2D(s):
    if np.mod(s.shape[1],2)>0:
        G=np.zeros((s.shape[0],1,s.shape[2]))
        s=np.concatenate((s,G),axis=1)
    return s

