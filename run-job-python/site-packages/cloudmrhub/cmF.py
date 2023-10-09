 
def getSNRScaling(self):
    return np.random.random(1)
def getNoiseCovarianceMatrix(self):
    if self.NoiseCovarianceMatrix is not None:
        return self.NoiseCovarianceMatrix
    else:  
        self.setNoiseCovarianceMatrix(self.__calculateNCM__(self.operator,self.solver))
        return self.NoiseCovarianceMatrix
        
def getSNR(self):
    if self.SNR.isImageSet():
        return self.SNR
    else:
        NC=self.E.getNoiseCovarianceMatrix()
        invPsi = np.linalg.inv(NC)
        B=self.H.getB1minus()
        X,Y,Z,C=B.getImageSize()
        scaling_snr=self.getSNRScaling()
        SNR=np.zeros((Z,Y,X),dtype=np.complex128)
        A=B.getImageArray() #[C,Z,Y,X]
        # I know i hate this kind of loops, i miss itk and its iterator classes :(
        for x in range(X):
            for y in range(Y):
                for z in range(Z):
                    Svox=np.matrix(A[:,z,y,x])
                    Svox=Svox.T
                    Spsiss=Svox.T*invPsi*Svox
                    SNR[z,y,x]=scaling_snr*np.sqrt(Spsiss)
        R=np.array(B.getImageSpacing())
        O=np.array(B.getImageOrigin())
        d=B.getImageDimension()
        D=np.reshape(np.array(B.getImageDirections()),[d, d])
        DO=D[0:3,0:3]
        SNR_SITK=im.createSITKImagefromArray(SNR,R[np.r_[0,1,2]],O[np.r_[0,1,2]],DO.flatten())
        O=im.Imaginable()
        O.setImage(SNR_SITK)
        self.EHSNR=O
        # self.Log.append("Calculating Fields SNR","ok")
        return O