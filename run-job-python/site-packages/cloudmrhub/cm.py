import twixtools
import json
from pynico_eros_montin import pynico as pn
import numpy as np
import scipy



import pygrappa

def getGRAPPAKspace(rawdata, acs, ksize):
    """_summary_
    acs: [acl,acl,c]
    ksize: [kx,ky]
    """
    O=pygrappa.cgrappa(rawdata.astype(np.complex128), acs.astype(np.complex128), kernel_size=ksize)
    return O




def getPackagesVersion():
    PKG=['cloudmrhub','pynico_eros_montin','cmrawspy','pygrappa','twixtools','numpy','scipy','matplotlib','pydicom','SimpleITK','PIL','pyable_eros_montin']
    
    return pn.getPackagesVersion(PKG)
class i2d:
    """
    A 2D image class to use in CloudMR
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
    """
    A 3D image class to use in CloudMR
    """
    def __init__(self, k=None):
        super().__init__(k)
    def getnumberOfImages(self):
        return self.k.shape[-1]
    


try:
    import cm2D #dev
except:
    import cloudmrhub.cm2D as cm2D #runtime
    
import matplotlib.pyplot as plt
class k2d(i2d):
    """
    A 2d Kspace class to use in CloudMR
    complex number [freq,phase,c]
    """
    def __init__(self, k=None):
        super().__init__(k)
    def getNCoils(self):
        return self.k.shape[-1]
    def plot(self):
        if not self.isEmpty():
            R=cm2D.cm2DReconRSS()
            R.setPrewhitenedSignal(self.k)
            plt.imshow(np.abs(R.getOutput()))
            plt.colorbar()
            plt.show()
    
class sk2d(i2d):
    """
    Stack of 2D images class to use in CloudMR
    """
    def __init__(self, k=None):
        super().__init__(k)
    def getnumberOfImages(self):
        return self.k.shape[-1]
    
from scipy.ndimage import binary_fill_holes
from scipy.ndimage import label, sum
from scipy.ndimage.morphology import binary_fill_holes, binary_erosion, binary_dilation
from scipy.ndimage import generate_binary_structure
def calculateCoilsSensitivityMask2D(mask,ref_img,K):
    """_summary_

    Args:
    
        mask (_type_): can be _ref_ (mean of ref_img) or a dictionary with the following keys:
            - method: _threshold_ (hard threshold on the ref_img) or _percentage_ (percentage of th max kspace value) or _percentagemean_ (percentage of the mean of the kspace)    
            - value: _float_ or _int_

        ref_img (_type_): _description_
        dimension (_type_): kspace dimension 2 or 3 (2d,3D)
    """
    ref_img = np.abs(ref_img)
    sensmask = np.ones((ref_img.shape[0],ref_img.shape[1]))
    print("calculateCoilsSensitivityMask2D",end=" ")
    ncoils=K.shape[-1]
    FILLHOLES=False
    if isinstance(mask,str):  #will be removed
        if mask.lower()=='reference':
            sensmask = ref_img > np.mean(ref_img)-np.std(ref_img)
            print("reference ")
            FILLHOLES=True
        if mask.lower()=='espirit':
            print("espirit")
            k=8
            r=24
            t=0.01
            c=0.9925
            debug=False
            sensmask = sensitivitiesEspirit2D(K, k, r,t,c,debug)       
            sensmask=np.squeeze(sensmask)
            sensmask=np.abs(sensmask.sum(axis=-1))>0
            FILLHOLES=True
    if isinstance(mask,dict):
            if mask["method"].lower()=='threshold':
                sensmask = ref_img > mask["value"]
                print("threshold")
                FILLHOLES=True
            if mask["method"].lower()=='percentagemean':
                sensmask = ref_img > (np.mean(ref_img)*mask["value"])
                print("percentagemean")
                FILLHOLES=True
            if mask["method"].lower()=='percentage':
                sensmask = ref_img > (np.max(ref_img)*float(mask["value"])/100.0)
                print("percentage")
                FILLHOLES=True
            if mask["method"].lower()=='reference':
                sensmask = ref_img > np.mean(ref_img)-np.std(ref_img)
                print("reference ")
                FILLHOLES=True
            if mask["method"].lower()=='upload':
                read=ima.Imaginable(mask["file"])
                sensmask = read.getImageAsNumpy()
                sensmask = sensmask > 0
                FILLHOLES=False
            if (mask["method"].lower()=='no') or (mask["method"].lower()=='zero'):
                sensmask = np.ones((ref_img.shape[0],ref_img.shape[1]))
                FILLHOLES=False
            if mask["method"].lower()=='espirit':
                print("espirit")
                k=6
                r=24
                t=0.01
                c=0.9925
                debug=False
                for ke,v in mask.items():
                    if ke.lower()=='k':
                        k=v
                    if ke.lower()=='r':
                        r=v
                    if ke.lower()=='t':
                        t=v
                    if ke.lower()=='c':
                        c=v
                    if ke.lower()=='debug':
                        debug=v
                sensmask = sensitivitiesEspirit2D(K, k, r,t,c,debug)       
                sensmask=np.squeeze(sensmask)
                sensmask=np.abs(sensmask.sum(axis=-1))>0
                FILLHOLES=True
            if mask["method"].lower()=='numpy':
                sensmask = mask["matrix"]
                FILLHOLES=False
                
    if isinstance(mask,np.ndarray): #will be removed
        sensmask = mask
        print("mask from ndarray")
    #if sensmask doesn't exists
    if not 'sensmask' in locals():
        sensmask = np.ones((ref_img.shape[0],ref_img.shape[1]))
        print("default")
    if FILLHOLES:
        sensmask=binary_fill_holes(sensmask)
        struct = generate_binary_structure(2, 2)  # Generate a 5x5 structuring element
        image_dilated = binary_dilation(sensmask, structure=struct)
        image_filled = binary_fill_holes(image_dilated)
        sensmask = binary_erosion(image_filled, structure=struct)

    if len(sensmask.shape)==2:            
            TILE=[1]*2
            TILE.append(ncoils)
            sensmask = np.tile(np.expand_dims(sensmask,axis=-1), TILE)

    return sensmask.astype(np.uint8)
        
class cmOutput:
    def __init__(self,message=None):
        self.Exporter = []
        self.Log = pn.Log(message)
        self.Type = "general"
        self.SubType = "zero"
        self.OUTPUTLOGFILENAME = None
        self.OUTPUTFILENAME = None

    def addToExporter(self, type, name, value):
        self.Exporter.append([type, name, value])

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
    L = np.linalg.cholesky(psi).astype(signalrawdata.dtype)
    L_inv = np.linalg.inv(L).astype(signalrawdata.dtype)
    
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



def calculate_covariance_coefficient_matrix(cov):
    coeff = np.zeros(cov.shape)
    for itemp in range(cov.shape[0]):
        for jtemp in range(cov.shape[1]):
            coeff[itemp,jtemp] = cov[itemp,jtemp]/np.sqrt(cov[itemp,itemp]*cov[jtemp,jtemp])
    return coeff
import PIL

def getMRoptimumTestData(nc=None,figure='./eros.jpg'):
    """Create some fake data to test reconstructions
    Args:
        path: The path to the image file.
    Returns:
        Kspace signal, noise data and nc.
    """
    image = PIL.Image.open(figure)
    K = MRfft(np.array(image),[0,1])
    
    # Create a fake noise covariance matrix
    if nc is None:
        nc = np.eye(K.shape[-1]) * np.random.rand(3) / 1000000

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

def calculate_simple_sense_sensitivitymaps2D(K,mask=None):
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
    sensmask=np.array([])
    if isinstance(mask,np.ndarray):
        c=mask
        mask={"matrix":c, "method":"numpy"}
        
    if (mask is False) or (mask is None):
        mask={"method":"no","value":0}
        
    D=len(K.shape)-1
    sensmask = calculateCoilsSensitivityMask2D(mask,ref_img,K)
    coilsens_set = coilsens_set * sensmask
    return coilsens_set, sensmask

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
    scipy.io.savemat(fn, {"export":var})


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


def getAutocalibrationsLines2DKSpaceZeroPadded(K,Autocalibration=[1,2]):
    """return a 2D multicoil Kspace data zeropadded with inside the KSpace in the ACL

    Args:
        K (nd.array(f,p,c)): Kspace
        AutocalibrationF (int): Number of Autocalibration in the Frequency
        AutocalibrationP (int): Number of Autocalibration in the Phase
    Returns:
        OK: np.array([f,p,c])
    """
    return  getAutocalibrationsLines2DKSpace(K,Autocalibration
                                             ,padded=True)


def getAutocalibrationsLines2DKSpace(K,Autocalibration=[1,2]):
    """return a 2D multicoil Kspace data zeropadded with inside the KSpace in the ACL

    Args:
        K (nd.array(f,p,c)): Kspace
        AutocalibrationF (int): Number of Autocalibration in the Frequency
        AutocalibrationP (int): Number of Autocalibration in the Phase
    Returns:
        OK: np.array([fac,pac,c])
    """
    return retrieveAutocalibrationsLines2DKSpace(K,Autocalibration,padded=False)

def retrieveAutocalibrationsLines2DKSpace(K,Autocalibration=[1,2],padded=True):
    """return a 2D multicoil Kspace data zeropadded with inside the KSpace in the ACL

    Args:
        K (nd.array(f,p,c)): Kspace
        AutocalibrationF (int): Number of Autocalibration in the Frequency
        AutocalibrationP (int): Number of Autocalibration in the Phase
    Returns:
        OK: np.array([f,p,c])
    """
    x,y=getACLGrids(K,Autocalibration)
    OK=np.zeros_like(K)
    for _x in x:
        for _y in y:
            OK[_x,_y]=K[_x,_y]

    if padded:
        return OK
    else:
        return OK[np.min(x):np.max(x),np.min(y):np.max(y)]
        

#defiined in mro
def fixAccelratedKSpace2D(s,acceleration):
    MOD=np.mod(s.shape[1],acceleration)
    if MOD>0:
        G=np.zeros((s.shape[0],MOD,s.shape[2]))
        s=np.concatenate((s,G),axis=1)
    return s


def resizeIM2D(IM,new_size):
    """resize a 2d image on the new size

    Args:
        IM (np.array([x,y])): the image
        new_size (np.array([sx,sy])): the new size

    Returns:
        _type_: _description_
    """
    if np.iscomplexobj(IM):
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

try:
    import espirit
except:
    import cloudmrhub.espirit as espirit
    
def sensitivitiesEspirit2D(ref, k=6, r=24,t=0.01, c=0.9925,debug=False):
    #it's 2d so i have t add a new axis to the ref kspace
    ref = np.expand_dims(ref,axis=0)
    esp = espirit.espirit(ref, k, r, t,c)
    esp=np.squeeze(esp)
    if debug:
        return esp
    else:
        return esp[...,0]

def needs_regridding(K, acceleration):
    """
    Checks if the input array needs to be regridded.

    Args:
    K: The input array.
    acc: acceleration frequency and phase


    Returns:
    True if the array needs to be regridded, False otherwise.
    """
    accf, accp = acceleration
    S = K.shape
    return sum(np.mod(S[1:2], [accf, accp])) != 0

   
def getACLGrids(K,acl=[20,20]):
    nX, nY, nCoils = K.shape
    frequencyautocalibration, phaseautocalibration=acl

    if phaseautocalibration > nY or frequencyautocalibration > nX:
        raise Exception('The Number of requested Autocalibrations lines is greater than the kspace size')
    # Ysamp_u = np.arange(0, nY, phaseacceleration)
    # Ysamp_ACL = np.arange(nY // 2 - phaseautocalibration // 2 ,
    #                         nY // 2 + phaseautocalibration // 2)
    if phaseautocalibration>0:
        Ysamp_ACL = np.arange(nY//2-phaseautocalibration//2+1 , np.floor(nY/2)+phaseautocalibration//2,dtype=int)
    else:
        Ysamp_ACL =np.array([],dtype=int)

    if frequencyautocalibration>0:
        Xsamp_ACL = np.arange(nX//2-frequencyautocalibration//2+1 , np.floor(nX/2)+frequencyautocalibration//2,dtype=int)
    else:
        Xsamp_ACL =np.array([],dtype=int)

    # Xsamp = np.union1d(Xsamp_u, Xsamp_ACL)
    return Xsamp_ACL,Ysamp_ACL

def getUndersampleGrids(K, acceleration=[1,2]):
    nX, nY, nCoils = K.shape
    frequencyacceleration, phaseacceleration=acceleration
    Ysamp = np.arange(0, nY, phaseacceleration)    
    Xsamp = np.arange(0, nX, frequencyacceleration)
    return Xsamp,Ysamp

def mimicAcceleration2D(K, acceleration=[1,2],ACL=[np.nan,20]):
    """return a 2D multicoil Kspace data zeropadded with inside the KSpace in the ACL
    plae a np.nan in case you want all the lines in a direction
    """
    for i,a in enumerate(ACL):
        if np.isnan(a):
            ACL[i]=K.shape[i]
    
    x,y=getUndersampleGrids(K,acceleration=acceleration)
    SIGNAL=np.zeros_like(K)
    for _x in x:
        for _y in y:
            SIGNAL[_x,_y,:]=K[_x,_y,:]
    
    REFERENCE=np.zeros_like(K)
    x,y=getACLGrids(K,acl=ACL)
    for _x in x:
        for _y in y:
            REFERENCE[_x,_y,:]=K[_x,_y,:]
    
    return SIGNAL, REFERENCE

def shrinkToAliasedMatrix2D(K,acceleration):
    frequencyacceleration, phaseacceleration=acceleration
    S=np.array(K.shape)//np.array([frequencyacceleration,phaseacceleration,1])
    #get numpy type

    OK=np.zeros(S,dtype=K.dtype)
    x=np.arange(0,S[0])
    y=np.arange(0,S[1])
    for i,_x in enumerate(x):
        for j,_y in enumerate(y):
            OK[i,j,:]=K[_x,_y,:]
    return OK



# def calculate_simple_sense_sensitivitymaps_acl(K,autocalibrationF,autocalibrationP,mask=None):
#     """Calculates the coil sensitivity maps using the simple SENSE method on undersampled Kspace.

#     Args:
#         K: freq,phase,coil numpy array of the kspace 


#     Returns:
#         The coil sensitivity matrix.
#     """
#     return calculate_simple_sense_sensitivitymaps(getAutocalibrationsLines2DKSpaceZeroPadded(K,autocalibrationF,autocalibrationP),mask)
