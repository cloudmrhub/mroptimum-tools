import twixtools
import json
from pynico_eros_montin import pynico as pn
import numpy as np
import scipy

VERSION ='2.5'

import pygrappa
def getGRAPPAKspace(rawdata, acs, ksize):
    return pygrappa.grappa(rawdata, acs, kernel_size=ksize)

def printInfo():
    print('cloudmrhub {VERSION}')
class i2d:
    """
    A 2d image class to use in CloudMR
    """
    def __init__(self,k=None):
        self.k=np.array([])
        if k is not None:
            self.set(k)
    def getSize(self):
        return self.k.shape[0:2]
    def get(self):
        return self.k
    def set(self,k):
        self.k =k
    def isEmpty(self):
        return not np.sum(self.k.shape)>0
    def reset(self):
        self.k=np.array([])

class i3d(i2d):
    def __init__(self, k=None):
        super().__init__(k)
    def getnumberOfImages(self):
        return self.k.shape[-1]
    


class k2d(i2d):
    """
    A 2d Kspace class to use in CloudMR
    """
    def __init__(self, k=None):
        super().__init__(k)
    def getNCoils(self):
        return self.k.shape[-1]
    
class sk2d(i2d):
    def __init__(self, k=None):
        super().__init__(k)
    def getnumberOfImages(self):
        return self.k.shape[-1]
        
        
class cmOutput:
    def __init__(self,message=None):
        self.Exporter = []
        self.Log = pn.Log(message)
        self.Type = "general"
        self.SubType = "zero"
        self.OUTPUTLOGFILENAME = None
        self.OUTPUTFILENAME = None

    def addToExporter(self, type, name, value):
        self.Exporter.append([type, name, float(value)])

    def setOutputLogFileName(self, L):
        self.OUTPUTLOGFILENAME = pn.Pathable(L)

    def getOutputLogFileName(self):
        return self.OUTPUTLOGFILENAME.getPosition()

    def setOutputFileName(self, L):
        self.OUTPUTFILENAME = pn.Pathable(L)

    def getOutputFileName(self):
        return self.OUTPUTFILENAME.getPosition()

    def setLog(self, L):
        self.Log = L

    def getLog(self):
        return self.Log

    def setTypeOutput(self, L):
        self.Type = L

    def getTypeOutput(self):
        return self.Type

    def appendLog(self, L,t=None):
        self.logIt(L,t)

    def logIt(self, W, t=None):
        self.Log.append(W,t)

    def getResults(self):
        return self.exportResults()

    # def getResultsAsImages(self):
    #     return self.getImagesFromResuls(self.getResults())

    # def exportResults(self, fn):
    #     O = {}
    #     O["version"] = "20201223"
    #     O["author"] = "eros.montin@gmail.com"
    #     if self.Type == "":for t in range(len(self.Log)):
    #         print(self.Log[t])
    #         O["type"] = "DATA"
    #     else:
    #         O["type"] = self.Type
    #     if self.SubType == "":
    #         O["subtype"] = ""
    #     else:
    #         O["subtype"] = self.SubType
    #     for t in range(len(self.Exporter)):
    #         if self.Exporter[t][0] == "image2D":
    #             im = {}
    #             im["slice"] = self.image2DToJson(self.Exporter[t][2])
    #             im["imageName"] = self.Exporter[t][1]
    #             O["images"].append(im)
    #     if len(fn) > 0:
    #         with open(fn, "w") as f:
    #             json.dump(O, f)
    #     else:
    #         with open(self.getOutputFileName(), "w") as f:
    #             json.dump(O, f)

    def exportLog(self, fn=None):
        if fn==None:
            fn=self.getOutputFileName()
        
        self.Log.writeLogAs(fn)


    def whatHappened(self):
        print(self.Log.getWhatHappened())

    def errorMessage(self):
        self.logIt("ERROR", "error")

    def outputError(self, fn):
        self.errorMessage()
        self.exportLog(fn)



def prewhiteningSignal(signalrawdata, psi):
    L = np.linalg.cholesky(psi).astype(complex)
    L_inv = np.linalg.inv(L).astype(complex)
    
    nc = signalrawdata.shape[-1]
    nf = signalrawdata.shape[0]
    nph = signalrawdata.shape[1]
    pw_signalrawdata = pw_signalrawdata = np.transpose(signalrawdata, [2, 1,0])  # [ncoil nfreq, nphasex]
    shape= pw_signalrawdata.shape
    output=pw_signalrawdata.reshape(shape[0],shape[1]*shape[2],order='F')
    pw_signalrawdata = np.matmul(L_inv, output)
    pw_signalrawdata = np.reshape(pw_signalrawdata, [nc, nph, nf],order='F')
    pw_signalrawdata = np.transpose(pw_signalrawdata, [2, 1, 0])  # [nfreq nphase ncoil]
    return pw_signalrawdata

def calculate_covariance_matrix(noise, bandwidth=1):
    """Calculates the covariance matrix of noise.
       update 09/24/2020 Prof. Riccardo Lattanzi, Ph.D.

    Args:
        noise: The noise as a NumPy array.
        bandwidth: The bandwidth of the noise.
    Returns:
        The covariance matrix of the noise.
    """
    
    nf,nph,nchan = noise.shape
    Rn = np.zeros((nchan, nchan))
    noise_samples = np.swapaxes(noise.reshape((nph*nf,nchan)),0,1) # non complex conj
    Rn = ( noise_samples @ noise_samples.conj().T)/ (2.0 * float(nf)*float(nph))
    Rn = Rn / float(bandwidth)
    return Rn

import PIL

def getMRoptimumTestData(nc=None):
    """Create some fake data to test reconstructions
    Args:
        path: The path to the image file.
    Returns:
        Kspace singal data and nc.
    """
    image = PIL.Image.open('./eros.jpg')
    K = MRfft(np.array(image),[0,1])
    
    # Create a fake noise covariance matrix
    if nc is None:
        nc = np.eye(3) * np.random.rand(3) / 1000000

    KN=create_fake_noise_kspace_data(shape=K.shape,correlation_matrix=nc)
    return K, KN, nc
    


def get_pseudo_noise(msize, corr_noise_factor):
    """
    msize (freq,phase,coil)
    """
    N = np.sqrt(0.5) * (np.random.randn(*msize) + 1j * np.random.randn(*msize))
    nrow = msize[0]
    ncol = msize[1]
    nchan = msize[2]
    gaussian_whitenoise = np.reshape(N, (nrow * ncol, nchan))
    gaussian_whitenoise = np.matmul(corr_noise_factor,gaussian_whitenoise.T)
    gaussian_whitenoise = np.reshape(gaussian_whitenoise.T, (nrow, ncol, nchan))

    return gaussian_whitenoise
def get_correlation_factor(correlation_matrix):
    D,V = np.linalg.eigh(correlation_matrix, UPLO='U')
    return V @ np.sqrt(np.diag(D)) @ np.linalg.inv(V)  # 1 i
def create_fake_noise_kspace_data(shape, correlation_matrix=None):
    """Creates a fake noise matrix with some correlations between the channels.

    Args:
        shape: The shape of the matrix.
        correlation_matrix: The correlation matrix between the channels.

    Returns:
        The noise matrix.
    """
    if correlation_matrix is None:
        correlation_matrix=np.eye(len(shape))
    corr_noise_factor=get_correlation_factor(correlation_matrix)
    return get_pseudo_noise(shape, corr_noise_factor)


def MRifft(k,dim):
    """
    Reconstruct individual coils' images and apply FFT scale factor
    iFFT scales data by 1/sqrt(N), so I need to scale back, as the noise covariance
    matrix is calculated in k-space (not Fourier transformed)

    Args:
        k: The k-space data

    Returns:
        o: The reconstructed images
    """
    tmp = np.fft.ifftshift(k)
    for idim in dim:
        tmp = np.fft.ifft(tmp, axis=idim)
    output = np.fft.ifftshift(tmp)
    return output


def MRfft(k,dim):
    """
    Reconstruct individual coils' images and apply FFT scale factor
    iFFT scales data by 1/sqrt(N), so I need to scale back, as the noise covariance
    matrix is calculated in k-space (not Fourier transformed)

    Args:
        k: The k-space data

    Returns:
        o: The reconstructed images
    """
    tmp = np.fft.ifftshift(k)
    for idim in dim:
        tmp = np.fft.fft(tmp, axis=idim)
    output = np.fft.ifftshift(tmp)
    return output

def calculate_simple_sense_sensitivitymaps(K,mask=None):
    """Calculates the coil sensitivity maps using the simple SENSE method.

    Args:
        K: freq,phase,coil numpy array of the kspace 

    Returns:
        The coil sensitivity matrix.
    """
    dims=K.shape
    sensmap_temp = MRifft(K,[0,1])
    ref_img = np.sqrt(np.sum(np.abs(sensmap_temp)**2, axis=-1))
    coilsens_set = sensmap_temp / np.tile(np.expand_dims(ref_img,axis=-1), [1, 1, dims[2]])
    if mask:
        if isinstance(mask,str):
            if mask.lower()=='ref':
                sensmask = ref_img > np.mean(ref_img)        
        elif isinstance(mask,np.ndarray):
            sensmask = ref_img > np.mean(ref_img)
        if len(sensmask.shape)==2:            
            sensmaskrep = np.tile(np.expand_dims(sensmask,axis=-1), [1, 1, dims[2]])
        coilsens_set = coilsens_set * sensmaskrep
    return coilsens_set

def get_wien_noise_image(noiseonly, box):
    """
    Calculates the Wiener noise image from the noiseonly image.

    Args:
        noiseonly: The noiseonly image.
        box: The size of the box.

    Returns:
        The Wiener noise image.
    """
    NC, NR = noiseonly.shape
    kx = box
    ky = box
    NOISE = np.zeros((NC, NR))
    NOISE.fill(np.nan)
    PADDEDNOISE = np.pad(noiseonly, [(kx, kx), (ky, ky)], 'constant', constant_values=np.nan)
    for ic in range(NC):
        for ir in range(NR):
            pic = kx + ic + np.arange(-kx, kx + 1)
            pir = ky + ir + np.arange(-ky, ky + 1)
            try:
                NOISE[ic, ir] = np.nanstd(PADDEDNOISE[np.min(pic):np.max(pic)+1,np.min(pir):np.max(pir)+1],ddof=1)
            except:
                pass
    return NOISE

    
def writeResultsAsCmJSONOutput(results,filename,info=None):
    """_summary_

    Args:
        images (_type_): array of [type,name,imaginable,outputName]
        filename (_type_): oyutput filename
        info (_type_, optional): type, subType. Defaults to None.
    """
    OUTPUT={'version':'20220314',
    'language':'python',
    'type':'CMOutput',
    'subType':"default",
    'author':'eros.montin@gmail.com',
            }

        
    if info is not None:
        if info["type"] is not  None:
            OUTPUT["type"]=info['type']
        if info['subType'] is not None:
            OUTPUT["subType"]=info['subType']
    IMAGES=[]
    for r in results:
        if r['type']=='imaginable2D':
            if ((isinstance(r['imaginable'],im.Imaginable))):
                theim=r['imaginable']
            elif isinstance(r['imaginable'],sitk.Image):
                theim=im.Imaginable()
                theim.setImage(r['imaginable'])
            else:
                try:
                    if r['imaginable'].isImaginable():
                        theim=r['imaginable']
                    else:
                        return False
                except:
                    return False


            
            getSlice=theim.getAxialSlice
            orientation=2
            try:
                if r['orientation']==1:
                    getSlice=theim.getSagittalSlice
                    print('sagittal slices:)')
                elif r['orientation']==0:
                    getSlice=theim.getCoronalSlice
                    print('corona; slices:)')
                orientation=r['orientation']
                
            except:
                print('axial slices:)')
            
            S=theim.getImageSize()

            SL=[]
            for s in range(S[orientation]):
                o={"type":"double complex"}
                sl=getSlice(s)
                o['w'],o['h']=sl.GetSize()
                o['s']=sl.GetSpacing()
                o['o']=sl.GetOrigin()
                o['d']=sl.GetDirection()
                nda = sitk.GetArrayFromImage(sl) #YX
                s=nda.flatten('F').astype(complex)
                o['Vi']=s.imag.tolist()
                o['Vr']=s.real.tolist()
                SL.append(o)
            R={
                "slice":SL, # this should be slices... i know
                "imageName":r["name"]
            }
            
            try:
                R["imageOutputName"]=r["outputName"]
            except:
                R["imageOutputName"]=r["name"]
            
            IMAGES.append(R)
    
    OUTPUT["images"]=IMAGES

    if filename is None:
        return OUTPUT
    else:

        # create json object from dictionary
        js = json.dumps(OUTPUT)

        # open file for writing, "w" 
        f = open(filename,"w")

        # write json object to file
        f.write(js)

        # close file
        f.close()
        return True
    
def get_noise_for(file):
    multi_twix = twixtools.read_twix(file)

    noise_data = []

    for meas in multi_twix:
        if type(meas) is not dict:
            continue
        mdb_list = [x for x in meas['mdb'] if x.is_flag_set('NOISEADJSCAN')]
        if len(mdb_list) == 0:
            continue
        nLin = 1 + max([mdb.cLin for mdb in mdb_list])
        nAcq = 1 + max([mdb.cAcq for mdb in mdb_list])
        nCha, nCol = mdb_list[0].data.shape
        out = np.zeros([nAcq, nLin, nCha, nCol], dtype=np.complex64)
        for mdb in mdb_list:
            out[mdb.cAcq, mdb.cLin] = mdb.data
        noise_data.append(out)
    return np.asarray(noise_data)
	
import scipy
def savemat(fn,var):
    scipy.io.savemat(fn, {"var":var})


import matplotlib.pyplot as plt

def mrir_noise_bandwidth(noise):
    """Calculates the noise bandwidth.

    Args:
        noise: The noise data.
        display: Whether to display the noise power spectrum.

    Returns:
        The noise bandwidth.
    """

    dims = noise.shape
    power_spectrum = np.abs(np.fft.fft(noise, axis=0))**2
    power_spectrum_chan = np.mean(power_spectrum, axis=1)
    N=np.concatenate([power_spectrum_chan[:dims[0] // 4],power_spectrum_chan[3*dims[0] // 4-1::]])
    power_spectrum_norm = np.mean(N, axis=0)
    norm_power_spectrum_chan = power_spectrum_chan / np.repeat(power_spectrum_norm[None, :], dims[0], axis=0)
    noise_bandwidth_chan = np.sum(norm_power_spectrum_chan, axis=0) / dims[0]
    noise_bandwidth = np.mean(noise_bandwidth_chan)

    return noise_bandwidth



from pyable_eros_montin import imaginable as ima


def getAutocalibrationsLines2DKSpaceZeroPadded(K,AutocalibrationF,AutocalibrationP):
    """return a 2D multicoil Kspace data zeropadded with inside the KSpace in the ACL

    Args:
        K (nd.array(f,p,c)): Kspace
        AutocalibrationF (int): Number of Autocalibration in the Frequency
        AutocalibrationP (int): Number of Autocalibration in the Phase
    Returns:
        OK: np.array([f,p,c])
    """
    x,y=getACLGrids(K,AutocalibrationF,AutocalibrationP)
    OK=np.zeros_like(K)
    for _x in x:
        for _y in y:
            OK[_x,_y]=K[_x,_y]
    return OK

def getAutocalibrationsLines2DKSpaceZeroPadded(K,AutocalibrationF,AutocalibrationP):
    """return a 2D multicoil Kspace data zeropadded with inside the KSpace in the ACL

    Args:
        K (nd.array(f,p,c)): Kspace
        AutocalibrationF (int): Number of Autocalibration in the Frequency
        AutocalibrationP (int): Number of Autocalibration in the Phase
    Returns:
        OK: np.array([f,p,c])
    """
    return getAutocalibrationsLines2DKSpace(K,AutocalibrationF,AutocalibrationP,padded=True)

def getAutocalibrationsLines2DKSpace(K,AutocalibrationF,AutocalibrationP):
    """return a 2D multicoil Kspace data zeropadded with inside the KSpace in the ACL

    Args:
        K (nd.array(f,p,c)): Kspace
        AutocalibrationF (int): Number of Autocalibration in the Frequency
        AutocalibrationP (int): Number of Autocalibration in the Phase
    Returns:
        OK: np.array([fac,pac,c])
    """
    return getAutocalibrationsLines2DKSpace(K,AutocalibrationF,AutocalibrationP,padded=False)

def getAutocalibrationsLines2DKSpace(K,AutocalibrationF,AutocalibrationP,padded=True):
    """return a 2D multicoil Kspace data zeropadded with inside the KSpace in the ACL

    Args:
        K (nd.array(f,p,c)): Kspace
        AutocalibrationF (int): Number of Autocalibration in the Frequency
        AutocalibrationP (int): Number of Autocalibration in the Phase
    Returns:
        OK: np.array([f,p,c])
    """
    x,y=getACLGrids(K,AutocalibrationF,AutocalibrationP)
    OK=np.zeros_like(K)
    for _x in x:
        for _y in y:
            OK[_x,_y]=K[_x,_y]

    if padded:
        return OK

    else:
        return OK[np.min(_x):np.max(_x),np.min(_y):np.max(_y)]
        



def resizeIM2D(IM,new_size):
    """resize a 2d image on the new size

    Args:
        IM (np.array([x,y])): the image
        new_size (np.array([sx,sy])): the new size

    Returns:
        _type_: _description_
    """
    if np.iscomplex(IM[0,0]):
        R=ima.numpyToImaginable(np.real(IM))
        I=ima.numpyToImaginable(np.imag(IM))
        R.changeImageSize(new_size)
        I.changeImageSize(new_size)
        return R.getImageAsNumpy() + 1j* I.getImageAsNumpy()
    else:
        R=ima.numpyToImaginable(IM)
        R.changeImageSize(new_size)
        return R.getImageAsNumpy()

    # if isinstance(IM[0,0],complex):
    #     R=ima.numpyToImaginable(np.real(IM))
    #     I=ima.numpyToImaginable(np.imag(IM))








def needs_regridding(K, accf, accp):
  """
  Checks if the input array needs to be regridded.

  Args:
    K: The input array.
    accf: The horizontal accuracy factor.
    accp: The vertical accuracy factor.

  Returns:
    True if the array needs to be regridded, False otherwise.
  """
 
  S = K.shape
  if sum(np.mod(S[1:2], [accf, accp])) != 0:
    return True
  else:
     return False

def getACLANDUndersampleGrids(K, frequencyacceleration, phaseacceleration, frequencyautocalibration=0, phaseautocalibration=0):
    ACLx,ACLy=getACLGrids(K, frequencyautocalibration, phaseautocalibration)
    Ux,Uy=getUndersampleGrids(K, frequencyacceleration, phaseacceleration)
    return np.union1d(ACLx,Ux),np.union1d(ACLy,Uy)
   
def getACLGrids(K, frequencyautocalibration, phaseautocalibration):
    nX, nY, nCoils = K.shape
    if phaseautocalibration > nY or frequencyautocalibration > nX:
        raise Exception('The Number of requested Autocalibrations lines is greater than the kspace size')
    # Ysamp_u = np.arange(0, nY, phaseacceleration)
    # Ysamp_ACL = np.arange(nY // 2 - phaseautocalibration // 2 ,
    #                         nY // 2 + phaseautocalibration // 2)
    if phaseautocalibration>0:
        Ysamp_ACL = np.arange(nY//2-phaseautocalibration//2+1 , np.floor(nY/2)+phaseautocalibration//2,dtype=int)
    else:
        Ysamp_ACL =np.array([],dtype=int)

    # Ysamp = np.union1d(Ysamp_u, Ysamp_ACL)
    # Xsamp_u = np.arange(0, nX, frequencyacceleration)
    if frequencyautocalibration>0:
        Xsamp_ACL = np.arange(nX//2-frequencyautocalibration//2+1 , np.floor(nX/2)+frequencyautocalibration//2,dtype=int)
    else:
        Xsamp_ACL =np.array([],dtype=int)

    # Xsamp = np.union1d(Xsamp_u, Xsamp_ACL)
    return Xsamp_ACL,Ysamp_ACL

def getUndersampleGrids(K, frequencyacceleration, phaseacceleration):
    nX, nY, nCoils = K.shape
    Ysamp = np.arange(0, nY, phaseacceleration)    
    Xsamp = np.arange(0, nX, frequencyacceleration)
    return Xsamp,Ysamp
def undersample2DDataSENSE(K, frequencyacceleration=1,phaseacceleration=1):
    x,y=getUndersampleGrids(K,frequencyacceleration=frequencyacceleration,phaseacceleration=phaseacceleration)
    OK=np.zeros((K.shape),dtype=complex)
    for _x in x:
        for _y in y:
            OK[_x,_y,:]=K[_x,_y,:]
    return OK
def undersample2DDatamSENSE(K, frequencyacceleration=1,phaseacceleration=1,phaseACL=1):
    x,y=getACLANDUndersampleGrids(K,frequencyacceleration=frequencyacceleration,phaseacceleration=phaseacceleration,phaseautocalibration=phaseACL)
    OK=np.zeros((K.shape),dtype=complex)
    for _x in x:
        for _y in y:
            OK[_x,_y]=K[_x,_y]
    return OK


def undersample2DDatamGRAPPA(K, frequencyacceleration=1,phaseacceleration=1,frequencyACL=1,phaseACL=1):
    x,y=getACLANDUndersampleGrids(K,frequencyacceleration=frequencyacceleration,phaseacceleration=phaseacceleration,frequencyautocalibration=frequencyACL,phaseautocalibration=phaseACL)
    OK=np.zeros((K.shape),dtype=complex)
    for _x in x:
        for _y in y:
            OK[_x,_y,:]=K[_x,_y,:]
    return OK

def shrinktoaliasedmatrix_2d(K,frequencyacceleration=1,phaseacceleration=1):
    S=np.array(K.shape)//np.array([frequencyacceleration,phaseacceleration,1])
    OK=np.zeros(S,dtype=complex)
    x=np.arange(0,S[0])
    y=np.arange(0,S[1])
    for i,_x in enumerate(x):
        for j,_y in enumerate(y):
            OK[i,j,:]=K[_x,_y,:]
    return OK



def calculate_simple_sense_sensitivitymaps_acl(K,autocalibrationF,autocalibrationP,mask=None):
    """Calculates the coil sensitivity maps using the simple SENSE method on undersampled Kspace.

    Args:
        K: freq,phase,coil numpy array of the kspace 


    Returns:
        The coil sensitivity matrix.
    """
    return calculate_simple_sense_sensitivitymaps(getAutocalibrationsLines2DKSpaceZeroPadded(K,autocalibrationF,autocalibrationP),mask)
