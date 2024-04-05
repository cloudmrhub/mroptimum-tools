import numpy as np
try:
    import cm #dev
except:
    import cloudmrhub.cm as cm #runtime
    
import matplotlib.pyplot as plt
import scipy
from types import MethodType

import pkg_resources


class cm2DRecon(cm.cmOutput):
    """
    Python implementation of the cm2DRecon MATLAB class
   
    :author:
        Dr. Eros Montin, Ph.D. <eros.montin@gmail.com>
    :date:
        16/06/2023
    :note:
        This work was supported in part by the National Institute of Biomedical Imaging and Bioengineering (NIBIB) of the National Institutes of Health under Award Number R01 EB024536 and P41 EB017183. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.


    :Attributes:
        Dimension (int): The dimension of the reconstruction.

        SignalKSpace (cm.k2d): The signal k-space data.
        
        NoiseKSpace (cm.k2d): The noise k-space data.
                
        NoiseCovariance (np.ndarray): The noise covariance matrix.
        
        InverseNoiseCovariance (np.ndarray): The Inverse Noise Covariance matrix.
        
        SignalPrewhitened (np.ndarray): The prewhitened signal k-space data.
        
        HasSensitivity (bool): Whether the reconstruction contains sensitivity information.
        
        HasAcceleration (bool): Whether the reconstruction has accelerations.
        
        complexType (np.complex128): The complex type of the reconstruction.
   
    """
    def __init__(self):
        """
        Initializes the cm2DRecon object.
        """
        self.dimesion=2 
        self.SignalKSpace = cm.k2d()        
        self.NoiseKSpace = cm.k2d()
        self.NoiseCovariance = np.array([])
        self.InverseNoiseCovariance = np.array([])
        self.SignalPrewhitened = cm.k2d()
        self.HasSensitivity = False
        self.HasAcceleration = False
        self.HasAutocalibration = False
        self.NoiseBandWidth = None
        self.complexType=np.complex128

    def checkKSpacePixelType(self,s):
        if s.dtype != self.complexType:
            s = s.astype(self.complexType)
        return s
    def setSignalKSpace(self, signalKSpace):
        """
        Sets the signal k-space data.
        
        :param signalkspace: The signal k-space data
        :type: np.ndarray
        """
        # check pixel type
        signalKSpace=self.checkKSpacePixelType(signalKSpace)
        self.SignalKSpace.set(signalKSpace)
        # i've set a new signal, so the prewhitened signal is not valid anymore
        self.SignalPrewhitened.reset()

    def getSignalKSpace(self):
        """
        Gets the signal k-space data.
        
        Returns:
            _type_: nd.array(f,p,c)
        """
        return self.SignalKSpace.get()
    def getSignalKSpaceSize(self):
        """
        Gets the signal k-space size.
        
        Returns:
            NoiseKspace: nd.array(f,p,c)
        """
        return self.SignalKSpace.getSize()
    def getSignalNCoils(self):
        """
        Gets the number of coils in the signal k-space data.
        
        Returns:
            int: ncoils
        """
        return self.SignalKSpace.getNCoils()
    def setNoiseKSpace(self, noiseKSpace):
        """ Sets the noise k-space data.

        :param noiseKspace: The noise k-space data
        :type: np.ndarray(f,p,c)
        """
        noiseKSpace=self.checkKSpacePixelType(noiseKSpace)
        self.NoiseKSpace.set(noiseKSpace)

    def getNoiseKSpace(self):
        """
        Gets the noise k-space data.
        
        Returns:
            NoiseKspace: nd.array(f,p)
        """
        return self.NoiseKSpace.get()
    def getNoiseKSpaceSize(self):
        """
        Gets the noise k-space size.
        
        Returns:
            NoiseKspace: nd.array(f,p)
        """
        return self.NoiseKSpace.getSize()
    def getNoiseNCoils(self):
        """
        Gets the number of coils in the noise k-space data.
        
        Returns:
            int: ncoils
        """
        return self.NoiseKSpace.getNCoils()
    
    def getNoiseBandWidth(self):
            if(self.NoiseBandWidth is None):
                noise_bandwidth = cm.mrir_noise_bandwidth(self.getNoiseKSpace());
                self.NoiseBandWidth=noise_bandwidth
            try:
                return  self.NoiseBandWidth
            except:
                print("---problem in the noisebadwidth----")
                self.appendLog("---problem in the noisebadwidth----","warning")
                return  1.0
            
    def getInverseNoiseCovariancePrewhitened(self):
        """when prewhitened the correlation is an eye

        """
        return np.eye(self.getSignalNCoils())
    def setNoiseCovariance(self, noiseCovariance):
        """
        Sets the noise covariance matrix.

        :param noiseCovariance: The noise covariance matrix.
        :type: mp.ndarray(c,c)

        """
        noiseCovariance=self.checkKSpacePixelType(noiseCovariance)

        self.NoiseCovariance = noiseCovariance
        self.InverseNoiseCovariance = np.linalg.inv(noiseCovariance)
    def getNoiseCovariance(self):
        """
        Return the covariance matrix
        
        Returns:
            np.ndarray(c,c): Covariance Matrix
        """
        if not self.NoiseCovariance.any():
            self.NoiseCovariance = cm.calculate_covariance_matrix(
                self.getNoiseKSpace(),self.getNoiseBandWidth()
                )
        return self.NoiseCovariance

    def getNoiseCovarianceCoefficients(self):
        noise_covariance=self.getNoiseCovariance()
        return cm.calculate_covariance_coefficient_matrix(noise_covariance)  

    def getInverseNoiseCovariance(self):
        """
        Gets the inverse noise covariance matrix.

        Returns:
            np.ndarray(c,c): inverse of the covariance matrix
        """
        return self.InverseNoiseCovariance

    def getPrewhitenedSignal(self):
        """
        Gets the prewhitened signal.

        Returns:
            np.ndarray(f,p,c): prewhitened signal
        """
        if self.SignalPrewhitened.isEmpty():
            self.SignalPrewhitened.set(cm.prewhiteningSignal(self.getSignalKSpace(), self.getNoiseCovariance()))
        return self.SignalPrewhitened.get()

    def setPrewhitenedSignal(self, prewhitenedSignal):
        
        prewhitenedSignal=self.checkKSpacePixelType(prewhitenedSignal)

        self.SignalPrewhitened.set(prewhitenedSignal)

    def plotImageAfterTest(self,IM,tit):
        # Create the figure and subplots
        fig, axarr = plt.subplots(2, 1)
        axarr[0].imshow(IM)
        axarr[0].set_title(tit)
        axarr[1].imshow(abs(IM))
        axarr[1].set_title(tit + ' abs')

        ha = plt.axes([0, 0, 1, 1], frameon=False, visible=False,
              xlim=[0, 1], ylim=[0, 1], aspect='equal')
        # Add text to the axes object
        text = ha.text(0.5, 0.98, f'{IM.shape[0]}x{IM.shape[1]}',
                    transform=ha.transAxes, horizontalalignment='center',
                    verticalalignment='top')
        plt.show()
    def test(self):
        TEST = self.testrecon()
        self.plotImageAfterTest(TEST.getOutput(), "recon")
        return TEST
    def get2DKSIFFT(self,K=None):
        if K is None:
            K=self.getPrewhitenedSignal()
        SC=np.sqrt(np.prod(np.array(K.shape[0:2])))
        return cm.MRifft(K,[0,1])*SC
    def getOutput(self):
        pass
    def resetAfterSignal(self):
        self.SignalPrewhitened.reset()
    def resetAfterNoise(self):
        if not isinstance(self.NoiseBandWidth,str):
            self.NoiseBandWidth=None
            print('reset the NBW')
        self.NoiseCovariance = np.array([])
        self.InverseNoiseCovariance = np.array([])
        self.SignalPrewhitened.reset()

        

class cm2DReconRSS(cm2DRecon):
    """
    Python implementation of the cm2DReconRSS MATLAB class
   
    :author:
        Dr. Eros Montin, Ph.D. <eros.montin@gmail.com>
    :date:
        16/06/2023
    :note:
        This work was supported in part by the National Institute of Biomedical Imaging and Bioengineering (NIBIB) of the National Institutes of Health under Award Number R01 EB024536 and P41 EB017183. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.
    """
    
    def __init__(self):
        """
        Initializes the RSS reconstruction.
        
        """
        super().__init__()
        self.HasAcceleration= False
        self.HasSensitivity=False
        self.HasAutocalibration=False

    def getOutput(self):
        img_matrix = self.get2DKSIFFT()
        im = np.sqrt(np.sum(np.abs(img_matrix)**2,axis=-1))
        return im

    @staticmethod
    def testrecon():
        TEST = cm2DReconRSS()
        [K, N, nc] = cm.getMRoptimumTestData()
        TEST.setSignalKSpace(K)
        TEST.setNoiseCovariance(nc)
        return TEST

class cm2DReconSS(cm2DReconRSS):
    """
    Python implementation of the cm2DReconSS MATLAB class
   
    :author:
        Dr. Eros Montin, Ph.D. <eros.montin@gmail.com>
    :date:
        16/06/2023
    :note:
        This work was supported in part by the National Institute of Biomedical Imaging and Bioengineering (NIBIB) of the National Institutes of Health under Award Number R01 EB024536 and P41 EB017183. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.
    """
    
    def getOutput(self):
        img_matrix = self.get2DKSIFFT()
        im = np.sum(img_matrix**2,axis=-1)
        return im

    @staticmethod
    def testrecon():
        TEST = cm2DReconSS()
        [K, N, nc] = cm.getMRoptimumTestData()
        TEST.setSignalKSpace(K)
        TEST.setNoiseCovariance(nc)
        return TEST
class cm2DReconRSSunAbs(cm2DReconSS):
    """
    Python implementation of the cm2DReconRSSunAbs MATLAB class
   
    :author:
        Dr. Eros Montin, Ph.D. <eros.montin@gmail.com>
    :date:
        16/06/2023
    :note:
        This work was supported in part by the National Institute of Biomedical Imaging and Bioengineering (NIBIB) of the National Institutes of Health under Award Number R01 EB024536 and P41 EB017183. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.
    """
    def getOutput(self):
        im = np.sqrt(super().getOutput())
        return im

    @staticmethod
    def testrecon():
        TEST = cm2DReconRSSunAbs()
        [K, N, nc] = cm.getMRoptimumTestData()
        TEST.setSignalKSpace(K)
        TEST.setNoiseCovariance(nc)
        return TEST


class cm2DKellmanRSS(cm2DReconRSS):
    def __init__(self):
        super().__init__()
    def getOutput(self):
        nf,nph =self.getSignalKSpaceSize()
        img_matrix = self.get2DKSIFFT()
        snr = np.zeros((nf,nph),self.complexType)
        for irow in range(nf):
            for icol in range(nph):
                        B=np.expand_dims(img_matrix[irow,icol],axis=-1)
                        A=B.conj().T
                        snr[irow,icol] = np.abs(np.sqrt(2*(A @ B)))
        return snr
    


class cm2DReconWithSensitivity(cm2DRecon):
    """
    Python implementation of the cm2DReconWithSensitivity MATLAB class
   
    :author:
        Dr. Eros Montin, Ph.D. <eros.montin@gmail.com>
    :date:
        16/06/2003
    :note:
        This work was supported in part by the National Institute of Biomedical Imaging and Bioengineering (NIBIB) of the National Institutes of Health under Award Number R01 EB024536 and P41 EB017183. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.
    """
    
    def __init__(self):
        """
        Initializes the reconstruction.
        
        """
        super().__init__()
        self.HasAcceleration= False
        self.HasSensitivity=True
        self.HasAutocalibration=False
        self.CoilSensitivityMatrix=cm.k2d()
        self.ReferenceKSpace=cm.k2d()
        self.PrewhitenedReferenceKSpace=cm.k2d()
        self.MaskCoilSensitivityMatrix='reference'
        self.outputMask=cm.k2d()

    def setNoMask(self):
        # self.setMaskCoilSensitivityMatrix(False)
        O={"method":"no"}
        self.setMaskCoilSensitivityMatrix(O)
        
        

    def setMaskCoilSensitivityMatrixBasedOnEspirit(self,k=8,r=24,t=0.01,c=0.997):
        O={"method":"espirit","k":k,"r":r,"t":t,"c":c}
        self.setMaskCoilSensitivityMatrix(O)
    
    def setMaskCoilSensitivityMatrixDefault(self):
        self.setMaskCoilSensitivityMatrix('reference')
    
    def setCoilSensitivityMatrix(self, S):
        self.CoilSensitivityMatrix.set(S)

    def resetCoilSensitivityMatrix(self):
        self.CoilSensitivityMatrix.reset()
    def getCoilSensitivityMatrix(self):
        # if a coil sensitivity matrix has not yet been set
        if self.CoilSensitivityMatrix.isEmpty():
            coilsens_set, mask = cm.calculate_simple_sense_sensitivitymaps2D(
                self.getPrewhitenedReferenceKSpace(),self.MaskCoilSensitivityMatrix)
            self.outputMask.set(mask)
            self.setCoilSensitivityMatrix(coilsens_set)
        return self.CoilSensitivityMatrix.get()

    def setPrewhitenedReferenceKSpace(self, x):
        self.PrewhitenedReferenceKSpace.set(x)

    
    def getReferenceKSpace(self):
        return self.ReferenceKSpace.get()
    
    def getReferenceKSpaceSize(self):
        return self.ReferenceKSpace.getSize()
    
    def getReferenceKSpaceNCoils(self):
        return self.ReferenceKSpace.getNCoils()
    
    def getPrewhitenedReferenceKSpace(self):
        if self.PrewhitenedReferenceKSpace.isEmpty():
            S = self.getReferenceKSpace()
            Rn = self.getNoiseCovariance()
            pw_S = cm.prewhiteningSignal(S, Rn)
            self.setPrewhitenedReferenceKSpace(pw_S)
        else:
            pw_S = self.PrewhitenedReferenceKSpace.get()
        return pw_S

    def setReferenceKSpace(self, IM):
        IM=self.checkKSpacePixelType(IM)
        self.ReferenceKSpace.set(IM)
        self.PrewhitenedReferenceKSpace.reset()

    def setMaskCoilSensitivityMatrix(self, x):
        self.MaskCoilSensitivityMatrix = x

    def getMaskCoilSensitivityMatrix(self):
        return self.MaskCoilSensitivityMatrix

    
    def resetAfterSignal(self):
        #triggered after setting the signal
        super().resetAfterSignal()       

        
    def resetAfterNoise(self):
        #triggered after setting the signal
        super().resetAfterNoise()
        # the noise covariance changes and therwfore the prewhitening are not valid anymore
        self.CoilSensitivityMatrix.reset()
        self.PrewhitenedReferenceKSpace.reset()
    
    def prepareCoilSensitivityMatrixPlot(self,title='Coil Sensitivity Maps',newplot=True):
        if newplot:
            plt.figure()
        S=self.getCoilSensitivityMatrix()
        NC=S.shape[-1]
        SNC=int(np.ceil(np.sqrt(NC)))
        for t in range(NC):
            #place the subplot closer to each other
            plt.subplot(SNC,SNC,t+1)
            plt.imshow(np.abs(S[:,:,t]))
            # set title padding to 0
            plt.title('Coil '+str(t),fontdict={'fontsize': 7},pad =0)
            #remove axis
            plt.axis('off')
            #remove ticks
            plt.tick_params(axis='both', which='both', bottom=False, top=False, labelbottom=False, right=False, left=False, labelleft=False)
        # add a common colorbar for all the subplots in the left side of the figure
        plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        plt.colorbar(plt.gcf().axes[0].images[0], ax=plt.gcf().axes)
        # add a title for the figure
        plt.suptitle(title, fontsize=16)


    def plotCoilSensitivityMatrix(self,fn=None, title_addition='',newplot=True):
        self.prepareCoilSensitivityMatrixPlot(title='Coil Sensitivity Maps '+title_addition,newplot=newplot)
        if fn is not None:
            plt.savefig(fn)
        else:
            plt.show()


    

class cm2DReconB1(cm2DReconWithSensitivity):
    """
    Python implementation of the cm2DReconB1 MATLAB class
   
    :author:
        Dr. Eros Montin, Ph.D. <eros.montin@gmail.com>
    :date:
        16/06/2003
    :note:
        This work was supported in part by the National Institute of Biomedical Imaging and Bioengineering (NIBIB) of the National Institutes of Health under Award Number R01 EB024536 and P41 EB017183. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.
    """
    
    def __init__(self):
        """
        Initializes the RSS reconstruction.
        
        """
        super().__init__()
        self.HasAcceleration= False
        self.HasSensitivity=True
        self.HasAutocalibration=False
        
    def getOutput(self):
        img_matrix = self.get2DKSIFFT()
        pw_sensmap=self.getCoilSensitivityMatrix()
        invRn=self.getInverseNoiseCovariancePrewhitened()
        nf,nph =self.getSignalKSpaceSize()
        im = np.zeros((nf,nph),dtype=self.complexType)
        for irow in range(nf):
            for icol in range(nph):
                        s_matrix=pw_sensmap[irow,icol,:]
                        if s_matrix.sum() !=0:
                            im[irow,icol] = s_matrix.conj().T @ invRn @ img_matrix[irow,icol,:]
        return im
    

    @staticmethod
    def testrecon():
        TEST = cm2DReconB1()
        [K, N, nc] = cm.getMRoptimumTestData()
        TEST.setSignalKSpace(K)
        TEST.setNoiseCovariance(nc)
        return TEST

class cm2DKellmanB1(cm2DReconB1):
    """
    Python implementation of the cm2DReconB1 MATLAB class
   
    :author:
        Dr. Eros Montin, Ph.D. <eros.montin@gmail.com>
    :date:
        16/06/2003
    :note:
        This work was supported in part by the National Institute of Biomedical Imaging and Bioengineering (NIBIB) of the National Institutes of Health under Award Number R01 EB024536 and P41 EB017183. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.
    """
    
    def getOutput(self):
        img_matrix = self.get2DKSIFFT()
        pw_sensmap=self.getCoilSensitivityMatrix()
        invRn=self.getInverseNoiseCovariancePrewhitened()
        nf,nph =self.getSignalKSpaceSize()
        im = np.zeros((nf,nph),dtype=self.complexType)
        SR=np.sqrt(2.0)
        for irow in range(nf):
            for icol in range(nph):
                        s_matrix=pw_sensmap[irow,icol,:]
                        if s_matrix.sum() !=0:
                            S=s_matrix
                            ST=s_matrix.conj().T
                            I=img_matrix[irow,icol,:]
                            num=np.dot(SR,np.abs(ST @ invRn @ I))
                            den=np.sqrt(np.abs(ST @ invRn @ S))
                            im[irow,icol] = np.divide(num,den)
        return im





class cm2DReconWithSensitivityAutocalibrated(cm2DReconWithSensitivity):
    """
    Python implementation of the m2DReconWithSensitivityAutocalibrated MATLAB class
   
    :author:
        Dr. Eros Montin, Ph.D. <eros.montin@gmail.com>
    :date:
        16/06/2003
    :note:
        This work was supported in part by the National Institute of Biomedical Imaging and Bioengineering (NIBIB) of the National Institutes of Health under Award Number R01 EB024536 and P41 EB017183. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.
    """
    
    def __init__(self):
        """
        Initializes the reconstruction.
        
        """
        super().__init__()
        self.HasAcceleration= True
        self.HasSensitivity=True
        self.HasAutocalibration=True
        self.Autocalibration=[np.nan]*self.dimesion
        self.Acceleration=[1]*self.dimesion

    def setAutocalibrationLines(self,ACL):
        # if acl is a tuple or list
        if isinstance(ACL, (list, tuple)):
            self.Autocalibration=ACL
        else:
            self.Autocalibration=[np.NaN,ACL]

        s=self.getSignalKSpaceSize()

        for i,a in enumerate(self.Autocalibration):
            if np.isnan(a):
                self.Autocalibration[i]=s[i]

    def getAccelerationPattern2D(self):
        ACC=self.Acceleration
        ACL=self.Autocalibration
        S=self.getSignalKSpaceSize()
        nc=self.getSignalNCoils()
        O,_=cm.mimicAcceleration2D(np.ones((*S,nc)),ACC,ACL)
        return  O
    
    def applyAccelerationPattern2D(self,K):
        P,_ = self.getAccelerationPattern2D()
        return K*P
    def setAcceleration(self,ACL):
        # if acceleration is a tuple or list
        if isinstance(ACL, (list, tuple)):
            self.Acceleration=ACL
        else:
            self.Acceleration=[1,ACL]




    # def getCoilSensitivityMatrixSimpleSenseACL(self):
    #     # MASK 
    #     if self.CoilSensitivityMatrix.isEmpty():       
    #         if self.ReferenceKSpace.isEmpty():
    #             s=self.getSignalKSpace()
    #         else:
    #             s=self.getReferenceKSpace()
    #         self.setCoilSensitivityMatrix(cm.prewhiteningSignal(cm.calculate_simple_sense_sensitivitymaps(s,self.MaskCoilSensitivityMatrix), self.getNoiseCovariance() ))
    #     return self.CoilSensitivityMatrix.get()
    
    def getCoilSensitivityMatrixReferenceKSpace(self):
        # MASK 
        
        if self.CoilSensitivityMatrix.isEmpty():       
            s= self.getReferenceKSpace()
            sensmap,mask=cm.calculate_simple_sense_sensitivitymaps2D(s,self.MaskCoilSensitivityMatrix)
            self.setCoilSensitivityMatrix(cm.prewhiteningSignal(sensmap, self.getNoiseCovariance() ))
            self.outputMask.set(mask)
        return self.CoilSensitivityMatrix.get()


    # def __selectCoilSensitivityMapMethod__(self):
    #     s=None
    #     s=super().__selectCoilSensitivityMapMethod__()
    #     if s is None:
    #         if ((self.getCoilSensitivityMatrixCalculationMethod() == 'simplesenseacl') or (self.getCoilSensitivityMatrixCalculationMethod() =='inneracl')):
    #             s=self.getCoilSensitivityMatrixSimpleSenseACL
    #         if (self.getCoilSensitivityMatrixCalculationMethod() == 'reference'):
    #             s=self.getCoilSensitivityMatrixReferenceKSpace
                
    #     return s

    # def getCoilSensitivityMatrixSimpleSenseACL(self):
    #     # MASK 
    #     if self.CoilSensitivityMatrix.isEmpty():       
    #         if self.ReferenceKSpace.isEmpty():
    #             s=self.getSignalKSpace()
    #         else:
    #             s=self.getReferenceKSpace()
    #         self.setCoilSensitivityMatrix(cm.prewhiteningSignal(cm.calculate_simple_sense_sensitivitymaps_acl(s,self.AutocalibrationF,self.AutocalibrationP,self.MaskCoilSensitivityMatrix), self.getNoiseCovariance() ))
    #     return self.CoilSensitivityMatrix.get()




class cm2DReconSENSE(cm2DReconWithSensitivityAutocalibrated):
    """_summary_
    class to reconstruct 2D Kspace asSENSE.
    it works with a zeropadded signal and reference Kspace
    :author:
        Dr. Eros Montin, Ph.D. <eros.montin@gmail.com>
    :date:
        16/06/2023
    :note:
        This work was supported in part by the National Institute of Biomedical Imaging and Bioengineering (NIBIB) of the National Institutes of Health under Award Number R01 EB024536 and P41 EB017183. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.

    Args:
        cm2DReconWithSensitivityAutocalibrated (_type_): _description_
    Attributes:
        Acceleration [int,int]: Acceleration factor in the Frequency and Phase direction
        Autocalibration (int): Number of autocalibration lines in the Frequency and Phase direction
    
    

        
    """
    def __init__(self):
        super().__init__()
        self.HasAutocalibration=True
  
    def setSignalKSpace(self, signalKSpace):
        super().setSignalKSpace(signalKSpace)
        self.Autocalibration[0]=signalKSpace.shape[0]
        
    def getOutput(self):
        #if self.Acceleration is a tuple or a list
        if isinstance(self.Acceleration, (list, tuple)):
            R1,R2=self.Acceleration
        else:
            R1=1
            R2=self.Acceleration       
        Rtot = R1 * R2
        nc=self.getSignalNCoils()
        #preapre the matrix size
        nf,nph = self.getSignalKSpaceSize()
        # ideally after prewhiteninig the noise covariance matrix should be the identity    
        invRn=self.getInverseNoiseCovariancePrewhitened()
        # get the prewhitened signal
        pw_signalrawdata=self.getPrewhitenedSignal()     
        # get the image ifft (size is the size of the full image)
        img_matrix = self.get2DKSIFFT(pw_signalrawdata) * np.sqrt(Rtot)
        # now the image is folded
        imfold=cm.shrinkToAliasedMatrix2D(img_matrix,[R1,R2])

        pw_sensmap=self.getCoilSensitivityMatrix()

        MRimage = np.zeros((nf, nph),dtype=self.complexType)
        for irow in range(nf // R1):
            for icol in range(nph//R2):
                r1=np.arange(irow,nf,nf//R1)
                r2=np.arange(icol,nph,nph//R2)
                current_R1 = len(r1)
                current_R2 = len(r2)
                current_Rtot = current_R1 * current_R2
                s=np.zeros((current_R1,current_R2,nc),dtype=self.complexType)
                for i,_x in enumerate(r1):
                    for j,_y in enumerate(r2):
                        s[i,j,:] = pw_sensmap[_x,_y, :]
                s = s.reshape((current_Rtot, nc),order='F')
                s = np.transpose(s,[1,0])
                s[np.isnan(s)] = 0 + 1j*0
                u = np.linalg.pinv(s.conj().T @ invRn @ s) @ (s.conj().T @ invRn)
                u[np.isnan(u)] = 0 + 1j*0
                U=np.reshape(u @ imfold[irow,icol],(current_R1,current_R2),order='F')
                for i,_x in enumerate(r1):
                    for j,_y in enumerate(r2):
                        MRimage[_x,_y] = U[i,j]

        if (cm.needs_regridding(self.getSignalKSpace(),[R1,R2])):
            MRimage=cm.resizeIM2D(MRimage,self.getSignalKSpaceSize());
        return MRimage
                

class cm2DKellmanSENSE(cm2DReconSENSE):
       def getOutput(self):
        if isinstance(self.Acceleration, (list, tuple)):
            R1,R2=self.Acceleration
        else:
            R1=1
            R2=self.Acceleration
        Rtot = R1 * R2
        nc=self.getSignalNCoils()
        nf,nph = self.getSignalKSpaceSize()
        invRn=self.getInverseNoiseCovariancePrewhitened()
        pw_signalrawdata=self.getPrewhitenedSignal()     
        img_matrix = self.get2DKSIFFT(pw_signalrawdata) * np.sqrt(Rtot)
        imfold=cm.shrinkToAliasedMatrix2D(img_matrix,[R1,R2])
        
        pw_sensmap=self.getCoilSensitivityMatrix()
        Rn = np.eye(nc,dtype=self.complexType); #it's prewhitened
        MRimage = np.zeros((nf, nph),dtype=self.complexType)
        _c=np.sqrt(2.0)
        for irow in range(nf // R1):
            for icol in range(nph//R2):
                r1=np.arange(irow,nf,nf//R1)
                r2=np.arange(icol,nph,nph//R2)
                current_R1 = len(r1)
                current_R2 = len(r2)
                current_Rtot = current_R1 * current_R2
                s=np.zeros((current_R1,current_R2,nc),dtype=self.complexType)
                for i,_x in enumerate(r1):
                    for j,_y in enumerate(r2):
                        s[i,j,:] = pw_sensmap[_x,_y, :]
                s = s.reshape((current_Rtot, nc),order='F')
                s = np.transpose(s,[1,0])
                s[np.isnan(s)] = 0 + 1j*0
                u = np.linalg.pinv(s.conj().T @ invRn @ s) @ (s.conj().T @ invRn)
                u[np.isnan(u)] = 0 + 1j*0
                U=np.reshape(u @ imfold[irow,icol]/np.diag(np.sqrt(u @ Rn @ u.conj().T)),(current_R1,current_R2),order='F')
                for i,_x in enumerate(r1):
                    for j,_y in enumerate(r2):
                        MRimage[_x,_y] = _c*U[i,j]

        if (cm.needs_regridding(self.getSignalKSpace(),[R1,R2])):
            MRimage=cm.resizeIM2D(MRimage,self.getSignalKSpaceSize())
        return MRimage


import pygrappa

class cm2DGFactorv2(cm2DReconSENSE):
    def getOutput(self):
        if isinstance(self.Acceleration, (list, tuple)):
            R1,R2=self.Acceleration
        else:
            R1=1
            R2=self.Acceleration 
        pw_sensmap=self.getCoilSensitivityMatrix()
        MRimage = pygrappa.gfactor(pw_sensmap, R1, R2)

        if (cm.needs_regridding(self.getSignalKSpace(),[R1,R2])):
            MRimage=cm.resizeIM2D(MRimage,self.getSignalKSpaceSize())
        return MRimage
    
class cm2DGFactorSENSE(cm2DReconSENSE):
    def getOutput(self):
        if isinstance(self.Acceleration, (list, tuple)):
            R1,R2=self.Acceleration
        else:
            R1=1
            R2=self.Acceleration   
        nc=self.getSignalNCoils()
        nf,nph = self.getSignalKSpaceSize()
        invRn=self.getInverseNoiseCovariancePrewhitened()
        pw_sensmap=self.getCoilSensitivityMatrix()
        MRimage = np.zeros((nf, nph))
        _c=np.sqrt(2.0)
        for irow in range(nf // R1):
            for icol in range(nph//R2):
                r1=np.arange(irow,nf,nf//R1)
                r2=np.arange(icol,nph,nph//R2)
                current_R1 = len(r1)
                current_R2 = len(r2)
                current_Rtot = current_R1 * current_R2
                s=np.zeros((current_R1,current_R2,nc),dtype=self.complexType)
                for i,_x in enumerate(r1):
                    for j,_y in enumerate(r2):
                        s[i,j,:] = pw_sensmap[_x,_y, :]
                s = s.reshape((current_Rtot, nc),order='F')
                s = np.transpose(s,[1,0])
                s[np.isnan(s)] = 0 + 1j*0
                u1=s.conj().T @ invRn @ s
                u = np.diag(np.linalg.pinv(u1))*np.diag(u1)
                u[np.isnan(u)] = 0 + 1j*0
                U=np.reshape(u,(current_R1,current_R2),order='F')
                for i,_x in enumerate(r1):
                    for j,_y in enumerate(r2):
                        MRimage[_x,_y] = np.sqrt(np.abs(U[i,j]))

        if (cm.needs_regridding(self.getSignalKSpace(),[R1,R2])):
            MRimage=cm.resizeIM2D(MRimage,self.getSignalKSpaceSize())
        return MRimage
    





from pygrappa import sense1d,cgsense
class cm2DReconSENSEv1(cm2DReconSENSE):
    def getOutput(self):
        return sense1d(self.getPrewhitenedSignal(),self.getCoilSensitivityMatrix(), Ry=self.Acceleration, coil_axis=-1,imspace=False)
    
class cm2DReconCGSENSE(cm2DReconSENSE):
    def getOutput(self):
        return cgsense(self.getPrewhitenedSignal(),self.getCoilSensitivityMatrix(), coil_axis=-1)

class cm2DReconGRAPPA(cm2DReconWithSensitivityAutocalibrated):
    """GRAPPA REconstruction
    Args:
        cm2DReconWithSensitivityAutocalibrated (_type_): _description_
    """
    def __init__(self):
        super().__init__()
        self.HasSensitivity=False
        self.GRAPPAKernel=[3,2]
        self.PrewhitenedSignalKspaceACL=cm.k2d()
        self.reconstructor=cm2DReconRSS()

    
    def getPrewhitenedReferenceKSpaceACL(self):
        """
        Gets the prewhitened signalACL.

        Returns:
            np.ndarray(f,p,c): prewhitened signal
        """
        RF=self.getPrewhitenedReferenceKSpace()
        return cm.getAutocalibrationsLines2DKSpace(RF,self.Autocalibration)




    def setGRAPPAKernel(self,GK):
        self.GRAPPAKernel=GK
        
    
    def getR(this):
        SS = this.getSignalKSpaceSize()
        R = this.Acceleration[-1]
        np = SS[1]

        if np % R != 0:
            tempR = R
            while np % tempR != 0:
                tempR -= 1
            R = tempR
            ss = f'Acceleration R reduced to {R} ' \
                f', so the number of lines can be exactly divided by R'
            print(ss)
        return R


    def getOutput(self):
        grappa_kernel=self.GRAPPAKernel
        data_acs=self.getPrewhitenedReferenceKSpaceACL() #ACLxACxnc
        pw_signalrawdata=self.getPrewhitenedSignal() #fxpxc
        K=cm.getGRAPPAKspace(pw_signalrawdata,data_acs,grappa_kernel)
        K=self.checkKSpacePixelType(K)
        R=self.reconstructor
        R.setPrewhitenedSignal(K)
        return R.getOutput()



##MR PMR
class cm2DSignalToNoiseRatio(cm.cmOutput):
    def __init__(self, message=None):
        super().__init__(message)
        """
        the class expects a 3D matrix composed by a tile of 2D numpy images
        """
        self.appendLog("SNR Calculation started instantiated", "start")
        self.SNR = None
        self.Type = "MR"
        self.SubType = ""

def resetASPMR(self):
    """reset the SignalPrewhitened adter the signal is set"""
    self.SignalPrewhitened.reset()
def resetANPMR(self):
    """reset the SignalPrewhitened adter the noise is set"""
    if not isinstance(self.NoiseBandWidth,str):
        self.NoiseBandWidth=None
        print('reset the NBW')
    self.NoiseCovariance = np.array([])
    self.InverseNoiseCovariance = np.array([])
    self.SignalPrewhitened.reset()

        
    

class cm2DSignalToNoiseRatioMultipleReplicas(cm2DSignalToNoiseRatio):
    def __init__(self,x=None,message=None):
        """
        the class expects a 3D matrix composed by a tile of 2D images
        """
        super().__init__(message)
        self.imageArray=cm.i3d()
        self.Mean=None
        self.STD=None
        self.Max=None
        self.Type = "MR"
        self.reconstructor=None
        self.referenceImage=cm.i2d()

        
        if x is not None:
            self.add2DStackOfImages(x)
    def reset(self):
        self.Max=None
        self.Mean=None
        self.STD=None
        self.SNR=None
    def getReferenceImage(self):
        return self.referenceImage.get()
    def setReferenceImage(self,x):
        self.referenceImage.set(x)
    def add2DImage(self, x):
        self.reset()
        """
        add a 2D image to the class
        """
        if len(x.shape)==2:
            x=np.expand_dims(x,axis=-1)
        if self.imageArray.isEmpty():
            self.setImageArray(x)
        else:
            self.setImageArray(np.concatenate((self.getImageArray(), x), axis=-1))

    def add2DStackOfImages(self, x):
        """
        add a stack of 2D images to the class
        """
        self.add2DImage(x)

    def setSignalKSpace(self,signal):
        self.reconstructor.setSignalKSpace(signal)
        self.add2DImage(self.reconstructor.getOutput())
        
    def add2DKspace(self,signal):        
        self.reconstructor.setSignalKSpace(signal)
        self.add2DImage(self.reconstructor.getOutput())
    
    def setReconstructor(self,recon):
        """We dont' want to recalculate the Sensitivity map at every replica

        Args:
            recon (cm2dRecon): REconstructor class
        """
        self.reconstructor=recon
        self.reconstructor.resetAfterSignal=MethodType(resetASPMR,self.reconstructor)
        self.reconstructor.resetAfterNoise=MethodType(resetANPMR,self.reconstructor)

    def getReconstructor(self):
        return self.reconstructor
       
       
    def resetAfterNoise(self,keepsensitivity=False):
        super().resetAfterNoise()
        if not keepsensitivity:
            self.setCoilSensitivityMatrix.reset()


    def getImageArray(self):
        """
        return the image array
        """
        return self.imageArray.get()
    def setImageArray(self,x):
        """
        return the image array
        """
        self.imageArray.set(x)

    def getOutput(self):
        """
        calculate the mean and standard deviation of the image array
        """
        if self.SNR is None:
            self.SNR = np.divide(self.getImageArrayMean(), self.getImageArraySTD())
        return self.SNR
    def getImageArrayMean(self):
        """
        return the mean of the image array
        """
        if self.Mean is None:
            self.Mean=np.nanmean(np.abs(self.getImageArray()), axis=-1)
        return self.Mean
    def getImageArraySTD(self):
        """
        return the standard deviation of the image array
        """
        if self.STD is None:
            self.STD=np.nanstd(np.abs(self.getImageArray()), axis=-1,ddof=1) #matlab 0
        return self.STD
    def getImageArrayMax(self):
        """
        return the standard deviation of the image array
        """
        if self.Max is None:
            self.Max=np.nanmax(np.abs(self.getImageArray()), axis=-1) #matlab 0
        return self.Max
 
    def plotImageArray(self, p=0.5):
        """
        plot the image array
        """
        im = self.getImageArray()
        for t in range(im.shape[-1]):
            plt.subplot(121)
            plt.imshow(im[:, :, t])
            plt.colorbar()
            plt.title("Replicas number: " + str(t+1))
            if t>0:
                plt.subplot(122)
                plt.imshow(im[:, :, t]-im[:, :, t-1])
                plt.title(f'differerence {t+1} - {t}')
                plt.colorbar()
            plt.pause(interval=1)
            plt.show()

class cm2DSignalToNoiseRatioPseudoMultipleReplicas(cm2DSignalToNoiseRatioMultipleReplicas):
    def __init__(self, x=None, message=None):
        super().__init__(x, message)
        self.numberOfReplicas=20
        self.D=None # denumerator
    def createPseudoReplica(self,S,corr_noise_factor,acceleration_pattern=None):
        sh=self.reconstructor.getSignalKSpaceSize()
        N= cm.get_pseudo_noise(msize=[*sh, self.reconstructor.getSignalNCoils()],corr_noise_factor=corr_noise_factor)
        if self.reconstructor.HasAcceleration:
            if acceleration_pattern is None:
                N=self.reconstructor.applyAccelerationPattern2D(N)
            else:
                N=N*acceleration_pattern
        self.add2DKspace(S+N)
    def getSNRDenumerator(self):
        if self.D is None:
            D=np.nanstd(np.abs(self.getImageArray())+np.max(np.abs(self.getImageArrayMax())), axis=-1,ddof=1)
            D[D<=np.finfo(np.float64).eps]=1
            self.D=D
        return self.D
    def reset(self):
        super().reset()
        self.D=None
    
    def getOutput(self):
        # set the reference image
        # self.setReferenceImage(self.reconstructor.getOutput())
        corr_noise_factor=cm.get_correlation_factor(correlation_matrix=self.reconstructor.getNoiseCovariance())
        S=self.reconstructor.getSignalKSpace()
        acceleration_pattern=None
        if self.reconstructor.HasAcceleration:
            acceleration_pattern=self.reconstructor.getAccelerationPattern2D()
        for a in range(self.numberOfReplicas):
            #add in the queue
            self.createPseudoReplica(S,corr_noise_factor,acceleration_pattern=acceleration_pattern)
        if self.referenceImage.isEmpty():
            self.setReferenceImage(self.reconstructor.getOutput())
        D=self.getSNRDenumerator()
        SNR=np.divide(self.getReferenceImage(),D)
        return SNR

class cm2DSignalToNoiseRatioPseudoMultipleReplicasWein(cm2DSignalToNoiseRatioPseudoMultipleReplicas):
    def __init__(self, x=None, message=None):
        super().__init__(x, message)
        self.Type='CR'
        self.boxSize=2

    def getSNRDenumerator(self):
        if self.referenceImage.isEmpty():
            self.setReferenceImage(self.reconstructor.getOutput())
        r=self.getReferenceImage()-self.getImageArrayMean()
        return cm.get_wien_noise_image(r,self.boxSize)



