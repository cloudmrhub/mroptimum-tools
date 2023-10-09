import numbers
from pynico_eros_montin import pynico as pn
import SimpleITK as sitk
import numpy as np
import copy
import matplotlib.pyplot as plt

try:
    from .utils import wlt as uwlt
except:
    from utils import wlt as uwlt
from skimage import data, filters, measure, morphology

def getMaskedNunmpyArray(IM,ROI):
    """Return the values inside a region of interest
    Args:
      IM:
        Imaginable
      ROI:
        ROIable

    Returns:
      Numpy arrays aof values
    """
    o=IM.getImageAsNumpy()
    m=ROI.getImageAsNumpy()
    return o[np.where(m>0)]

def transform_point(P,transform):
    return transform.TransformPoint(P)


def getMatrixToPatientOrientationHF(L):
    #input is an imaginable
    
    transform=sitk.AffineTransform(L.getImageDimension())
    transform.SetMatrix(L.getImageDirection())
    O0= transform_point([0]*L.getImageDimension(),transform)
    O1= transform_point(L.getImageSize(),transform)
    
    
    L=[['Left','Right'],['Anterior','Posterior'],['Down','Up']]
    if O0[0]<O1[0]:
        L[0].reverse()   
    if O0[1]>O1[1]:
        L[1].reverse()   
    if O0[2]>O1[2]:
        L[2].reverse()   
    return L



def numpyToImaginable(x,ref=None,vector=False):
    T=Imaginable()
    T.setImageFromNumpy(x,refimage=ref,vector=vector)
    return T


def saveNumpy(x,fn,ref=None):
    T=numpyToImaginable(x,ref)
    T.writeImageAs(fn)
def getTransformFromFile(h):
    if not pn.isCollection(h):
        h=[h]
    o=[]
    for t in h:
        if isinstance(h,pn.Pathable):
            st=h.getPosition()
        else:
            st=t
        o.append(sitk.ReadTransform(st))
    return o    

def getSITKMetaInfo(image):
    o={}
    for key in image.GetMetaDataKeys():
            o[key]=image.GetMetaData(key)
    return o
def setSITKMetaInfo(image,m):
    for key,value in m.items():
            image.SetMetaData(key,value)
    return image
        
class IndexViewer(object):
        def __init__(self, ax, Ima,km=[True,True],normal=2,ind=None):
            self.ax = ax

            # ax.set_title('use scroll wheel to navigate the image size(' + str(X.shape) +')')
            self.slices=Ima.getImageSize(normal)
            self.ind=ind
            self.Ima=Ima
            k=list(Ima.getImageSpacing())
            if self.ind==None:
                self.ind = self.slices//2
                if normal==0:
                    self.slicer=self.Ima.getSliceNormalI
                    self.ratio=k[2]/k[1]
                elif normal==1:
                    self.slicer=self.Ima.getSliceNormalJ
                    self.ratio=k[2]/k[0]
                elif normal==2:
                    self.slicer=self.Ima.getSliceNormalK
                    self.ratio=k[1]/k[0]
            self.UD=not km[0]
            self.LR=not km[1]
            self.X=self.getTheX()
            self.im = ax.imshow(self.X)
            ax.set_aspect(self.ratio)
            self.update()
        def getTheX(self):
            o=SITKImaginable(image=self.slicer(self.ind)).getImageAsNumpyZYX()
            if self.UD:
                o=np.flipud(o)
            if self.LR:
                o=np.fliplr(o)
            return o

        def onscroll(self, event):
            if event.button == 'up':
                self.ind = (self.ind + 1) % self.slices
            else:
                self.ind = (self.ind - 1) % self.slices
            self.update()

        def update(self):
            self.X=self.getTheX()
            self.im.set_data(self.X)
            self.ax.set_ylabel('slice ' + str(self.ind)  + "/" +str(self.slices))
            self.im.axes.figure.canvas.draw()       
        def onclick(self,event):           
            if event.button == 2:
               print('you pressed', event.button, event.xdata, event.ydata)
               print('value %s' % self.X[int(np.floor(event.ydata)),int(np.floor(event.xdata))])



def getmeTheSimpleITKImage(x):
    if(issubclass(type(x),sitk.Image)):
        return x
    elif (issubclass(type(x),Imaginable)):
        return x.getImage()
    elif (isinstance(x,str)):
        return Imaginable(filename=x).getImage()
    else:
        raise Exception("I don't know this image tyoe!!! what shuld i do?? ask Eros eros.montin@gmail.com")
def copythethreeinfosonandsetthemtimage(source,reference):
    sp,o,d=getSITKImageInfo(reference)
    return setSITKImageInfo(source,sp,o,d)


def setSITKImageInforFromImage(nda,ima):
    # ORSP=nda.GetSpacing()
    REF=getmeTheSimpleITKImage(ima)
    nda=copythethreeinfosonandsetthemtimage(nda,REF)
    #if the resolution is identical no prob otherwise we need to fix the poition of the origin
    # if not np.array_equiv(ORSP,REF.GetSpacing()):
    #     nda=fixOriginOnResamping(nda,ima)
    return nda



def setSITKImageInfo(nda,spacing,origin,direction):
    if spacing:
        osp=nda.GetSpacing()
        Onda=copy.deepcopy(nda)
        nda.SetSpacing(spacing)
    if direction:
        nda.SetDirection(direction)
    if origin:
        nda.SetOrigin(origin)
        # if np.array_equiv(spacing,osp):
        #     nda=fixOriginOnResamping(nda,Onda)
    return nda
def getSITKImageInfo(nda):
    return nda.GetSpacing(),nda.GetOrigin(), nda.GetDirection()




class Imaginable:
    def __init__(self,filename=None,image=None,verbose=False):
        self.verbose=verbose
        self.dfltInterpolator=sitk.sitkLinear
        self.dfltuseNearestNeighborExtrapolator=False
        self.imageStack =pn.Stack()    
        self.log=pn.Log()
        self.settings={
            "spacingMinSize":2 #max number of digit 
            }

        if ((filename) and (image)):
            if(pn.Pathable(filename).exists()):
                raise Exception("you can't put an existing filename and an image")
        if filename:
            self.setInputFileName(filename)
        if image:
            self.setImage(getmeTheSimpleITKImage(image),'image set as simpeitk image at class initialization')
            if not self.getInputFileName():
                self.InputFileName=pn.createRandomTemporaryPathableFromFileName('a.nii.gz').getPosition()


        

    def getWavelet(self,wtype='Haar'):
        WT=uwlt(self.getImageAsNumpy(),wtype)
        NS=[g*2 for g in self.getImageSpacing()]
        O=[]
        #this seems to be an offset at least for haar
        Z=[0]*self.getImageDimension()
        U=[0]*self.getImageDimension()
        T=[(o-z)/2 for z,o in zip(self.getCoordinatesFromIndex(Z),self.getCoordinatesFromIndex(U))]
        for t in WT.keys():
            K=numpyToImaginable(WT[t],self)
            K.setImageSpacing(NS)
            K.translateImage(T)
            O.append({"type":type(self),
                    "name":t,
                    "map":K.getDuplicate()
            })
        return O
    def getImage(self):
        return self.imageStack.peek()

    def setImage(self,p,w=None):
        self.imageStack.push(p)
        if w:
            self.__tellme__(w)
    
    def reset(self):
        while self.imageStack.size()>1:
            self.undo()
    def undo(self):
        if self.imageStack.size()>1:
            self.imageStack.pop()
            self.__tellme__('image popped')
        return self

    def isImageSet(self):
        try:
            if self.getImage() is None:
                return False
            else:
                return True
        except:
            return False

    def setVerbose(self,v):
        self.verbose=v
    def getVerbose(self):
        return self.verbose

    def getInputFileName(self):
        try:
            return self.InputFileName
        except:
            return None
    def setInputFileName(self,fn):
        self.InputFileName = fn
        
        if pn.Pathable(fn).exists():
            self.setImage(self.__readImage__(fn),'image read from filename')
            

    
    def __readImage__(self,f=None):
        if not f:
            f=self.getInputFileName()
        return sitk.ReadImage(f)
    
    def writeImageAs(self,filename,force=True):
        if ((not pn.Pathable(filename).exists()) or (force)):
            pn.Pathable(filename).ensureDirectoryExistence()
            try:
                sitk.WriteImage(self.getImage(), filename)
                return filename
            except:
                raise Exception(f" file {filename} can't be written!!")
    
    def printImageInfo(self):
        image= self.getImage()
        o={}
        for key in image.GetMetaDataKeys():
            print("\"{0}\":\"{1}\"".format(key, image.GetMetaData(key)))
            o[key]=image.GetMetaData(key)
        return o
    def getImageAsNumpyZYX(self):
        image=self.getImage() 
        return sitk.GetArrayFromImage(image)
    
    def getImageAsNumpy(self):
        #numpy change the order of the components
        L=list(range(self.getImageDimension()))
        L.reverse()
        o=np.transpose(self.getImageAsNumpyZYX(), L)
        return o

    def resampleOnCanonicalSpace(self,interpolator=None,useNearestNeighborExtrapolator=None,bgvalue=0.0):
        if interpolator == None:
            interpolator = self.dfltInterpolator
        if useNearestNeighborExtrapolator ==None:
            useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator

        
        t=sitk.Transform()
        t.SetIdentity()
        mess='to canonical'
        self.setImage(sitk.Resample(self.getImage(), self.getImageSize(), t,  interpolator, self.getImageOrigin(), self.getImageSpacing(), np.eye(3).flatten(), bgvalue,self.getImagePixelTypeAsID(),useNearestNeighborExtrapolator),mess)

    def setImageFromNumpy(self,nparray,refimage=None, vector=False,spacing=None,origin=None,direction=None):
        L=list(range(len(nparray.shape)))
        L.reverse()
        o=np.transpose(nparray, L)
        self.setImageFromNumpyZYX(o,refimage, vector,spacing,origin,direction)
        return self

    def setImageFromNumpyZYX(self,nparray,refimage=None, vector=False,spacing=None,origin=None,direction=None):
        nda=sitk.GetImageFromArray(nparray, isVector=vector)
        if refimage:
            REF=getmeTheSimpleITKImage(refimage)
            if np.array_equiv(REF.GetSize(),nparray.shape):
                nda.CopyInformation(REF)
            else:
                nda=setSITKImageInforFromImage(nda,REF)
        elif ((spacing) and (origin) and (direction) ):
            nda=setSITKImageInfo(nda,spacing=spacing,origin=origin,direction=direction)
        elif self.isImageSet():
            if(self.getImage()):
                r,o,d=getSITKImageInfo(getmeTheSimpleITKImage(self))
                nda=setSITKImageInfo(nda,spacing=r,origin=o,direction=d)            
        self.setImage(nda,'image set as numpy array ZYX!!')
    
    def getImageDirection(self):
        image=self.getImage()
        return image.GetDirection()
    
    def setImageDirection(self,direction):
        image=self.getImage()
        image.SetDirection(direction)
        self.setImage(image)
        return self

    def getImageSpacing(self):
        image=self.getImage()
        return image.GetSpacing()

    def changeImageSpacing(self,spacing,interpolator=None,useNearestNeighborExtrapolator=None,bgvalue=0.0):
        if interpolator == None:
            interpolator = self.dfltInterpolator
        if useNearestNeighborExtrapolator ==None:
            useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator

        image=self.getImage()
        d=self.getImageSpacing()
        s=self.getImageSize()
        newSize = [round((sz-1)*spc/s) for sz,spc,s in zip(image.GetSize(), image.GetSpacing(), spacing)]
        t=sitk.Transform()
        t.SetIdentity()
        mess=f'spacing changed from {d} to {spacing}'
        
        self.setImage(sitk.Resample(image, newSize, t,  interpolator, self.getImageOrigin(), spacing, self.getImageDirection(), bgvalue,image.GetPixelIDValue(),useNearestNeighborExtrapolator),mess)
        return self
    
    def changeImageDirection(self,direction,interpolator=None,useNearestNeighborExtrapolator=None,bgvalue=0.0):
        raise Exception("not yet implemented we are working on it")
        # if interpolator == None:
        #     interpolator = self.dfltInterpolator
        # if useNearestNeighborExtrapolator ==None:
        #     useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator

        # image=self.getImage()
        # d=self.getImageDirection()
        # t=sitk.Transform()
        # t.SetIdentity()
        # mess=f'direcion changed from {d} to {direction}'
        # self.setImage(sitk.Resample(image, self.getImageSize(), t,  interpolator, self.getImageOrigin(), self.getImageSpacing(),direction, bgvalue,image.GetPixelIDValue(),useNearestNeighborExtrapolator),mess)
        # return self


    def setImageSpacing(self,spacing):
        image=self.getImage()
        d=self.getImageSpacing()
        image.SetSpacing(spacing)
        self.setImage(image,f'spacing changed from {d} to {spacing}')
    
    def getImageOrigin(self):
        image=self.getImage()
        return image.GetOrigin()
    
    def setImageOrigin(self,o):
        image=self.getImage()
        d=self.getImageOrigin()
        image.SetOrigin(o)
        self.setImage(image,f'origin changed from {d} to {o}')
        
    def getImageDimension(self):
        image=self.getImage()
        return image.GetDimension()
    
    def getImageNumberOfComponentsPerPixel(self):
        image=self.getImage()
        return image.GetNumberOfComponentsPerPixel()

    def getImagePixelTypeAsString(self):
        image=self.getImage()
        return image.GetPixelIDValue(), image.GetPixelIDTypeAsString()

    def getImagePixelTypeAsID(self):
        image=self.getImage()
        return image.GetPixelIDValue()

    def getImageSize(self,index=None):
        image=self.getImage()
        S=list(image.GetSize())
        if not index==None:
            S=S[index]
        return S

         
    
    def getVoxelVolume(self):
        """get the volume of a voxel in the imaginable

        Returns:/discover
            float: voxel volume
        """        
        # image=self.getImage()
        return np.prod(self.getImageSpacing())

    def getNumberofVoxels(self):
        """get the number of a voxel in the imaginable

        Returns:
            float: N voxels
        """        
        # image=self.getImage()
        return np.prod(self.getImageSize())

    def getVolume(self):
        """get the volume of the imaginable

        Returns:
            float: volume
        """        
        # image=self.getImage()
        return np.prod(self.getVoxelVolume()*self.getNumberofVoxels())

    def __tellme__(self,m,t=None):
        if t:
            if t=='destroy xxx999':
                return
            
        else:
            self.log.append(m,t)

        if(self.getVerbose()):
            print(m)
    def whathappened(self):
        self.log.getWhatHappened()
    def __del__(self):
        self.__tellme__("I'm being automatically destroyed. Goodbye!",'destroy xxx999')

    def forkDuplicate(self):  
        return copy.deepcopy(self)

#    def getDuplicate(self):
#        PP=self.__class__()
#        PP.setImage(self.getImage())
#        return PP

    def getDuplicate(self):
        PP=self.__class__(image=self.getImage())
        # PP.setImage(self.getImage())
        return PP
            
    def resampleOnTargetImage(self,target,interpolator = None,default_value = 0,useNearestNeighborExtrapolator=None):
        target=getmeTheSimpleITKImage(target)
        if interpolator == None:
            interpolator = self.dfltInterpolator
        if useNearestNeighborExtrapolator ==None:
            useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator       
        if not default_value:
            default_value=0.0
        theT =sitk.Transform()
        theT.SetIdentity()
        self.setImage(sitk.Resample(self.getImage(),target,theT,interpolator,default_value,sitk.sitkUnknown,useNearestNeighborExtrapolator),'resampled on target image')
    

    def getCoordinatesFromIndex(self,P):
        image=self.getImage()
        return image.TransformContinuousIndexToPhysicalPoint(P)
    
    def getIndexFromCoordinates(self,I):
        image=self.getImage()
        return image.TransformPhysicalPointToIndex(I)

        # return image.TransformPhysicalPointToContinuousIndex(I)
    def changeImageSize(self,newSize,interpolator= None,bgvalue=0.0,useNearestNeighborExtrapolator=None):
        if interpolator == None:
            interpolator = self.dfltInterpolator
        if useNearestNeighborExtrapolator ==None:
            useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator
        
        image=self.getImage()
        dimension = image.GetDimension()
 
        reference_origin = image.GetOrigin()
        reference_direction = image.GetDirection()        

        reference_physical_size = np.zeros(image.GetDimension())
        reference_physical_size[:] = [round((sz-1)*spc) if sz*spc>mx  else mx for sz,spc,mx in zip(image.GetSize(), image.GetSpacing(), reference_physical_size)]
        reference_spacing = [ round(phys_sz/(sz-1), self.settings["spacingMinSize"]) for sz,phys_sz in zip(newSize, reference_physical_size) ]
        transform =sitk.Transform()
        transform.SetIdentity()
        mess=f"Image resized from {image.GetSize()} - {image.GetSpacing()} to {newSize} - {reference_spacing}"
        self.setImage(sitk.Resample(image, newSize, transform,  interpolator, reference_origin, reference_spacing, reference_direction, bgvalue,image.GetPixelIDValue(),useNearestNeighborExtrapolator),mess)
        return self
    
    def cropImage(self,lowerB,upperB,coordinates=None):
        PP="voxels"
        image=self.getImage()
        U=self.getImageSize()
        if coordinates:
            PP="coordinates"
            lowerB=[self.getIndexFromCoordinates(h) for h in lowerB]
            upperBtmp=[self.getIndexFromCoordinates(h) for h in upperB]
        

        for t in range(len(upperB)):
            if (((upperB[t]==0) and (isinstance(upperB[t],int))) |(upperB[t]==np.NaN)):
                upperB[t]=U[t]
            else:
                if coordinates:
                    upperB[t]=upperBtmp[t]

       
        S=[u-l for l,u in zip(lowerB,upperB)]
        crop = sitk.ExtractImageFilter()
        crop.SetSize(S)
        crop.SetIndex(lowerB)
        cropped_image = crop.Execute(image)
        m=f'image cropped to {PP} {lowerB} {upperB}'
        return self.setImage(cropped_image,m)
 
    def __transformImage__(self,transform,interpolator = None,reference_image=None ,default_value = 0,useNearestNeighborExtrapolator=None,fromregistration=False):
    # Output image Origin, Spacing, Size, Direction are taken from the reference
    # image in this call to Resample
        if interpolator == None:
            interpolator = self.dfltInterpolator
        if useNearestNeighborExtrapolator ==None:
            useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator       
        if not default_value:
            default_value=0.0
        theT =sitk.Transform()
        if (isinstance(transform, tuple) or isinstance(transform,list)):
            for t in transform:
                theT = sitk.CompositeTransform([theT,t])
            transform = theT

        if not reference_image:
            reference_image=self.getImage()

        if fromregistration:
            return sitk.Resample(self.getImage(), reference_image, transform, interpolator, default_value,sitk.sitkUnknown,useNearestNeighborExtrapolator)
        else:
            return sitk.Resample(self.getImage(), reference_image, transform.GetInverse(), interpolator, default_value,sitk.sitkUnknown,useNearestNeighborExtrapolator)



    def translateImage(self,T,interpolator = sitk.sitkLinear,reference_image=None ,default_value = 0,useNearestNeighborExtrapolator=False):
        dimension=self.getImageDimension()
        translation = sitk.TranslationTransform(dimension, T)
        return self.setImage(self.__transformImage__(translation,interpolator,reference_image,default_value,useNearestNeighborExtrapolator),f"tranlated of {T}")

    def scaleImage(self,S,center=None,centerindex=False,interpolator = None,reference_image=None ,default_value = 0,useNearestNeighborExtrapolator=None):
        dimension=self.getImageDimension()
        if interpolator == None:
            interpolator = self.dfltInterpolator
        if useNearestNeighborExtrapolator ==None:
            useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator

        if not center:
            center=self.getImageCenterCoordinate()
        else:
            if centerindex:
                center=self.getCoordinatesFromIndex(center)
        theS=[1]*dimension
        for i,s in enumerate(S):
            if (isinstance(s,int) and (s==0)):
                theS[i]=1
            else:
                theS[i]=s
        transform = sitk.ScaleTransform(dimension)
        transform.SetScale(theS)
        transform.SetCenter(center)
        return self.setImage(self.__transformImage__(transform,interpolator,reference_image,default_value,useNearestNeighborExtrapolator),f"scaled of {theS}")

    def transform(self,T,interpolator = None,reference_image=None ,default_value = 0,useNearestNeighborExtrapolator=None):
        if interpolator == None:
            interpolator = self.dfltInterpolator
        if useNearestNeighborExtrapolator ==None:
            useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator
        return self.setImage(self.__transformImage__(T,interpolator,reference_image,default_value,useNearestNeighborExtrapolator),f"tranlated of {T}")

    def transformImageAffine(self,A,center,centerindex=False,interpolator = None,reference_image=None ,default_value = 0.0,useNearestNeighborExtrapolator=None):
        if interpolator == None:
            interpolator = self.dfltInterpolator
        if useNearestNeighborExtrapolator ==None:
            useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator
        dimension=self.getImageDimension()
        
        if not center:
            center=self.getImageCenterCoordinate()
        else:
            if centerindex:
                center=self.getCoordinatesFromIndex(center)

        transform = sitk.AffineTransform(dimension)
        transform.SetMatrix(A)
        transform.SetCenter(center)
        return self.setImage(self.__transformImage__(transform,interpolator,reference_image,default_value),f"scaled of {A}")

   
   
    def getImageCenterIndex(self):
        return [round(t/2) for t in self.getImageSize()]

    def getImageCenterCoordinate(self):
        return self.getCoordinatesFromIndex(self.getImageCenterIndex())

    def rotateImage(self,rotation,center=None, centerindex=False,translation=None,interpolator = None,reference_image=None ,default_value = 0.0,useNearestNeighborExtrapolator=None):

        """
        This function rotates an image across each of the x, y, z axes by theta_x, theta_y, and theta_z degrees
        respectively and resamples it to be isotropic.
        :param image: An sitk 3D image
        :param angles: [theta_x in degrees, theta_y in degrees, param theta_z in degrees]
        :center: center of rotation (position of the center in mm)
        :centerindex: False if center is in cm True if it's in voxels 
        :translation: mm of translation 

        :return: The rotated image
        
        """

        if interpolator == None:
            interpolator = self.dfltInterpolator
        if useNearestNeighborExtrapolator ==None:
            useNearestNeighborExtrapolator=self.dfltuseNearestNeighborExtrapolator
        if not center:
            center=[int(x) for x in self.getImageCenterCoordinate()]
        else:
            if centerindex:
                center=self.getCoordinatesFromIndex(center)

        R=[np.deg2rad(r) for r in rotation]
        if not translation:
            T=[0.0]*self.getImageDimension()
        else:
            T=translation
        if self.getImageDimension()==3:
            
            transform = sitk.Euler3DTransform (center,R[0], 
                                                R[1], 
                                                R[2],T)

        elif self.getImageDimension()==2:
            transform = sitk.Euler2DTransform ()
            transform.SetAngle(R[0])
            transform.SetCenter(center)
            transform.SetTranslation(T)
        
        

        return self.setImage(self.__transformImage__(transform,interpolator,reference_image,default_value,useNearestNeighborExtrapolator),f"rotated of {R} and {T}")

    def changePixelType(self,dtype):
        return self.setImage(sitk.Cast(self.getImage(),dtype),f'casted to {dtype}')
    def cast(self,dtype):
        if dtype==float:
            dtype=sitk.sitkFloat32
        return self.changePixelType(dtype)
    
    def getNumberOfNonZeroVoxels(self):
        return np.count_nonzero(self.getImageAsNumpyZYX())

    def applyAbs(self):
        m=self.getImage()
        ABS=sitk.AbsImageFilter()
        self.setImage(ABS.Execute(m))
        return self


    def applyModulus(self):
        m=self.getImage()
        try:
            ABS=sitk.ComplexToModulusImageFilter()
            self.setImage(ABS.Execute(m))
        except:
            try:
                ABS2=sitk.ModulusImageFilter()
                self.setImage(ABS2.Execute(m))
            except:
                raise Exception("can't apply abs")
        return self
    import numbers

    def add(self, toadd):
        w="Image"
        if not isinstance(toadd,numbers.Number):
            w=str(toadd)
        return self.__filterSelfAndImage__(sitk.AddImageFilter(),toadd,f'add {w}')

    def multiply(self, toadd):
        w="Image"
        if not isinstance(toadd,numbers.Number):
            w=str(toadd)
        return self.__filterSelfAndImageMat__(sitk.MultiplyImageFilter(),toadd,f'multiply {w}')



    def subtract(self, toadd):
        w="Image"
        if not isinstance(toadd,numbers.Number):
            w=str(toadd)
        return self.__filterSelfAndImage__(sitk.SubtractImageFilter(),toadd,f'subtract {w}')

    def divide(self, toadd):
        w="Image"

        if not isinstance(toadd,numbers.Number):
            w=str(toadd)
        return self.__filterSelfAndImageMat__(sitk.DivideImageFilter(),toadd,f'divide {w}')


    def __filterSelfAndImage__(self,filter,toadd,message):
        if not isinstance(toadd,numbers.Number):
            sitkimage=getmeTheSimpleITKImage(toadd)
            L=SITKImaginable(image=sitkimage)
            L.resampleOnTargetImage(self.getImage())
            toadd=L.getImage()
            
        else:
            toadd=float(toadd)
        try:
            self.setImage(filter.Execute(self.getImage(),toadd),message)
        except:
            raise Exception("Can't {message}")
        return self

    def __filterSelfAndImageMat__(self,filter,toadd,message):
        #get original pixel id
        S=self.getDuplicate()
        O=self.getImagePixelTypeAsID()
        # cast to float
        S.changePixelType(sitk.sitkFloat32)

        if not isinstance(toadd,numbers.Number):
            sitkimage=getmeTheSimpleITKImage(toadd)
            L=SITKImaginable(image=sitkimage)
            L.resampleOnTargetImage(self.getImage())
            L.changePixelType(sitk.sitkFloat32)
            toadd=L.getImage()
            
        else:
            toadd=float(toadd)
        try:
            OUT=filter.Execute(S.getImage(),toadd)
            S.setImage(OUT)
            S.changePixelType(O)
            self.setImage(S.getImage(),message)
        except:
            raise Exception("Can't {message}")
        return self
    
    
    def isInsidePoint(self,P):
        size=self.getImageSize()
        V=self.getIndexFromCoordinates(P)
        #pretend it's inside
        O=True 

        for a in range(len(P)):
            if (V[a]<0 ) | (V[a]>size[a]):
                O=False
                break

        return O

    def isInsideIndex(self,V):
        size=self.getImageSize()
        #pretend it's inside
        O=True 

        for a in range(len(V)):
            if (V[a]<0 ) | (V[a]>size[a]):
                O=False
                break

        return O
    
    def getImageUniqueValues(self,exclude=[]):
        O=set(np.unique(self.getImageAsNumpy().flatten()))
        for e in exclude:
            O.discard(e)
        return O

    def getMaximumValue(self):
        image=self.getImage()
        filter = sitk.MinimumMaximumImageFilter()
        filter.Execute(image)
        return filter.GetMaximum()
    
    def getMeanValue(self):
        image=self.getImage()
        filter = sitk.StatisticsImageFilter()
        filter.Execute(image)
        return filter.GetMean()

    def getVariance(self):
        image=self.getImage()
        filter = sitk.StatisticsImageFilter()
        filter.Execute(image)
        return filter.GetVariance()
    
    def getSum(self):
        image=self.getImage()
        filter = sitk.StatisticsImageFilter()
        filter.Execute(image)
        return filter.GetSum()
        
    
    def getRoiableValuesUpper(self,th):
        return Roiable(image=self.getImage()>th)





    def getStdValue(self):
        image=self.getImage()
        filter = sitk.StatisticsImageFilter()
        filter.Execute(image)
        return filter.GetSigma()

    def getMinimumValue(self):
        image=self.getImage()
        filter = sitk.MinimumMaximumImageFilter()
        filter.Execute(image)
        return filter.GetMinimum()


    def __RegionExtractor__(self,size,index):
        Extractor = sitk.ExtractImageFilter()
        Extractor.SetSize(size)
        Extractor.SetIndex(index)
        return Extractor.Execute(self.getImage())

    def instantiateAnotherAble(self):
        able = self.__class__
        return able()

    def getSliceNormalKAsNumpy(self,slice):
        O=self.instantiateAnotherAble()
        out=self.getSliceNormalK(slice)
        O.setImage(out)
        return O.getImageAsNumpy()

    def getSliceNormalJAsNumpy(self,slice):
        O=self.instantiateAnotherAble()
        out=self.getSliceNormalJ(slice)
        O.setImage(out)
        return O.getImageAsNumpy()

    def getSliceNormalIAsNumpy(self,slice):
        O=self.instantiateAnotherAble()
        out=self.getSliceNormalI(slice)
        O.setImage(out)
        return O.getImageAsNumpy()

    def getSliceNormalK(self,slice):
        slice = int(slice)
        size = list(self.getImageSize())
        size[2] = 0
        index = [0, 0, slice]
        out = self.__RegionExtractor__(size,index)
        return out
    def getSliceNormalJ(self,slice):
        slice = int(slice)
        size = list(self.getImageSize())
        size[1] = 0
        index = [0, slice,0]
        out = self.__RegionExtractor__(size,index)
        return out

    def getSliceNormalI(self,slice):
        slice = int(slice)
        size = list(self.getImageSize())
        size[0] = 0
        index = [slice,0,0]
        out = self.__RegionExtractor__(size,index)
        return out

    def isImaginable(self):
        if isinstance(self,SITKImaginable):
            return True
        for b in self.__class__.__bases__:
            if isinstance(b,SITKImaginable):
                return True
        try:            
            return isinstance(self.getImage(),sitk.Image)
        except:
            return False
    def isSITKImaginable(self):
        return self.isImaginable()

    def viewK(self,km=[True,True]):
        fig, ax = plt.subplots(1, 1)
        tracker = IndexViewer(ax,self,km)
        fig.canvas.mpl_connect('scroll_event', tracker.onscroll)
        fig.canvas.mpl_connect('button_press_event', tracker.onclick)
        plt.show()
    def viewJ(self,km=[True,True]):
        fig, ax = plt.subplots(1, 1)
        tracker = IndexViewer(ax,self,km,normal=1)
        fig.canvas.mpl_connect('scroll_event', tracker.onscroll)
        fig.canvas.mpl_connect('button_press_event', tracker.onclick)
        plt.show()
    def viewI(self,km=[True,True]):
        fig, ax = plt.subplots(1, 1)
        tracker = IndexViewer(ax,self,km,normal=0)
        fig.canvas.mpl_connect('scroll_event', tracker.onscroll)
        fig.canvas.mpl_connect('button_press_event', tracker.onclick)
        plt.show()
    def viewAxial(self):
        if self.getImageDimension()==3:
            k,km=self.__getOrientation__()
            if k==[0,1,2]:
                self.viewK([km[0],km[1]])
        elif self.getImageDimension()==2:
            self.view2D()
    def view2D(self):
            o=self.getImageAsNumpyZYX()
            # if self.UD:
            #     o=np.flipud(o)
            # if self.LR:
            #     o=np.fliplr(o)
            fig, ax = plt.subplots(1, 1)
            im = ax.imshow(o)
            ratio=self.getImageSpacing()
            ratio=ratio[0]/ratio[1]
            ax.set_aspect(ratio)
    def __getOrientation__(self):
        L=self.getImageDirection()

        k=[np.argmax(np.abs(L[0:3])),np.argmax(np.abs(L[3:6])),np.argmax(np.abs(L[6:]))]
        km=list(map(lambda x: x>0, [L[k[0]],L[k[1]+3],L[k[2]+6]]))
        return k, km

    def viewSagittal(self):
        k,km=self.__getOrientation__()
        if k==[0,1,2]:
            self.viewI([km[1],km[2]])

    def viewCoronal(self):
        k,km=self.__getOrientation__()
        if k==[0,1,2]:
            self.viewJ([km[0],km[1]])
    # registration parameters file are written already to be used with the resampling filter so not need to inverse the transform
    # this is good since there's no inverse at the moment for bsplinetransform

    def transformFromRegitration(self,T,interpolator = sitk.sitkLinear,reference_image=None ,default_value = 0,useNearestNeighborExtrapolator=False):
        return self.setImage(self.__transformImage__(T,interpolator,reference_image,default_value,useNearestNeighborExtrapolator,fromregistration=True),f"transformed of {T}")
    
    # def mask(self,mask):
    #     mask=getmeTheSimpleITKImage(mask)
        
    #     self.setImage(,'masked with image')


def maskSITKImage(r,maskingvalue=1,foreground=1,outsidevalue=0):
    return sitk.Mask(r, sitk.Cast(foreground,sitk.sitkInt16), maskingValue=maskingvalue, outsideValue=outsidevalue)




def getDirectiontransform(image):
    dimension=image.getImageDimension()
    cosines = sitk.AffineTransform(dimension)
    cosines.SetCenter(image.getImageOrigin())
    return cosines

class SITKImaginable(Imaginable):
    pass

class Roiable(Imaginable):
    """
    A class For Region of Interest
    if you have more than a label in your ROI, use Labelmapable
    ROI can have a value but when getimage is called the output has 1 for region in ROI and 0 for outside
    
    """

    def __init__(self, filename=None, image=None, verbose=False,roivalue=None):
        """
        filename : str
            the filename of the ROI
        image : sitk.image
            the simple itk image that sotres the roi
        roivalue : int
            roi value
        """
        super().__init__(filename, image, verbose)
        self.dfltInterpolator=sitk.sitkNearestNeighbor
        self.dfltuseNearestNeighborExtrapolator=True
        if roivalue:
            self.setImage(self.getImage()==roivalue,'now the mask is rqual to one')

    def getCenterIndex(self):
        label_statistic = sitk.LabelIntensityStatisticsImageFilter()
        label_statistic.Execute(self.getImage())
        center_gravity = label_statistic.GetCenterGravity(1)
        return center_gravity
    
    def  getCenterCoordinates(self):
        center_gravity_coordinate = self.getCoordinatesFromIndex(self.getCenterIndex())
        return center_gravity_coordinate

    def dilateRadius(self,radius=2):
        return self.__derodeRadius__(radius,False)
    def erodeRadius(self,radius=2):
        return self.__derodeRadius__(radius)
    def __derodeRadius__(self,radius=2,erode=True):
        image=self.getImage()

        if erode:
            filter = sitk.BinaryErodeImageFilter()
        else:
            filter = sitk.BinaryDilateImageFilter()
        filter.SetKernelRadius ( radius )
        o=filter.Execute(image>0)
        self.setImage(o,'erode')
        return self
    
    def removeSmallObj(self,voxel_threshold=50,connectivity=26):
        mask =measure.label(self.getImageAsNumpy()==1)
        mask = morphology.remove_small_objects(mask, voxel_threshold,connectivity=connectivity)
        mask[np.where(mask>0)]=1
        self.setImageFromNumpy(mask,refimage=self.getImage())
        return self

    def removeHoles(self,voxel_threshold=50,connectivity=26):
        mask =measure.label(self.getImageAsNumpy()==1)
        mask = morphology.remove_small_holes(mask, voxel_threshold,connectivity=connectivity)
        mask[np.where(mask>0)]=1
        self.setImageFromNumpy(mask,refimage=self.getImage())
        return self
    def keepBiggestObj(self,connectivity=26):
        labelled = measure.label(self.getImageAsNumpy()==1)
        rp = measure.regionprops(labelled)
        # get size of largest cluster
        size = max([i.area for i in rp])
        # remove everything smaller than largest
        mask = morphology.remove_small_objects(labelled, min_size=size-1,connectivity=connectivity)
        mask[np.where(mask>0)]=1
        self.setImageFromNumpy(mask)
        return self















#     def toVtk(self):
#         return sitk2vtk(self.getImage(), debugOn=False)
if __name__=="__main__":

    # PT=pn.Pathable('/data/MYDATA/3T vs 7T/registration_test')
    # j=pn.forkPathable(PT)
    # t=SITKImaginable(j.addBaseName('Duke3T.nii.gz').getPosition())
    
    # s=SITKImaginable(j.addBaseName('Male7T.nii.gz').getPosition())
    # g=SITKImaginable(j.addBaseName('MaleGeometry.nii.gz').getPosition())
    # o=j.addBaseName('__tMale7T.nii.gz').getPosition()
    # o2=j.addBaseName('__t2Male7T.nii.gz').getPosition()
    # d=SITKImaginable(j.addBaseName('T.mhd').getPosition())
    # d2=SITKImaginable(j.addBaseName('A.mhd').getPosition())
    # d3=SITKImaginable(j.addBaseName('B.mhd').getPosition())
    
    # t0=j.appendPath('7T').addBaseName('t.txt').getPosition()
    # t1=j.changeBaseName('a.txt').getPosition()
    # t2=j.changeBaseName('b.txt').getPosition()

    # d.add(d2).add(d3)
    

    # W=sitk.WarpImageFilter()
    # I=sitk.sitkLinear
    # W.SetInterpolator(I)
    # W.SetOutputParameteresFromImage(t.getImage())
    # L=W.Execute(s.getImage(),d.getImage())
    # oi=SITKImaginable(image=L)
    # oi.writeImageAs(o)

    # W=sitk.WarpImageFilter()
    # I=sitk.sitkNearestNeighbor()
    # W.SetInterpolator(I)
    # W.SetOutputParameteresFromImage(t.getImage())
    # L=W.Execute(s.getImage(),d.getImage())
    # oi=SITKImaginable(image=L)
    # oi.writeImageAs(o)



    
    # T=getTransformFromFile([t0,t1,t2])
    # s.transformFromRegitration(T)
    # s.writeImageAs(o)


    # A=Roiable(filename='tests/data/b.nii.gz')
    # H=pn.Pathable('/data/MYDATA/TDCS/EROS_TDCS/Healthy/NC_sub23_20190523/Manual_mask_NC_sub23_20190523LCA.nii')
    # A=Roiable(filename=H.getPosition())
    # A.viewK()
    # A.viewJ()
    
    # h=A.getImageAsNumpyZYX()
    # h=h[:,0:-1:3,0:-1:2]
    # A.setImageFromNumpyZYX(h)
    # A.changeImageSpacing([2,3,1])
    # A.viewAxial()
    # A.rotateImage([0,0,20])
    # A.viewAxial()
    # A.viewSagittal()
    # A.viewCoronal()
    # A.writeImageAs(H.changeBaseName('A.mha').changePath('/data/').getPosition())
    # A.dilateRadius(9)
    
#    A.viewAxial()
    # A.writeImageAs('/data/B.mha')
    # A.whathappened()

    # A.viewAxial()
    # t=np.zeros((50,40,30))
    # saveNumpy(t,'/data/garbage/a.nii.gz')
    # t[:,10:20,10:30]=1
    # P=Imaginable()
    
    # P.setImageFromNumpyZYX(t,origin=[0,0,0],spacing=[1,1,1],direction=[1,0,0,0,1,0,0,0,1])

    # P.viewAxial()
    # ll=P.getImageAsNumpyXYZ()

    # P.changeImageSize([z*4 for z in P.getImageSize()],bgvalue=0)
    # P.viewAxial()
    # P.writeImageAs('/data/tmp/a.nii.gz')


    # t=np.array([[20,10,20],[20,10,20]])
    # P=Roiable()
    # P.setImageFromNumpy(t)
    # P.setImageSpacing([4,4,8])
    
    # t=np.array([[20,10,20],[20,10,4]])/2
    # V=Imaginable()
    # V.setImageFromNumpy(t,P)
    # V.changeImageSpacing([0.5,0.5,0.5])

    # V=Imaginable(filename='/data/PROJECTS/HIPSEGENTATION/data_link/input/p02.nii.gz')

    # J=V.getWavelet()
    # J[1]["map"].writeImageAs('/g/a.nii.gz')



    # I=Imaginable(filename='/data/PROJECTS/HIPSEGENTATION/data_link/input/p02.nii.gz')
    # print(I.getImageDirection())
    
    # I.resampleOnCanonicalSpace()

    # print(I.getImageDirection())
    # I.writeImageAs('/g/2.nii.gz')
    # I=Imaginable(filename='/data/PROJECTS/HIPSEGENTATION/data_link/input/p03.nii.gz')
    # P=I.getDuplicate()
    
    # P=np.array([[[0,0,0,0],[2,2,2,0],[2,2,0,0],[2,0,0,0],[0,0,0,0]],[[0,0,0,0],[2,2,2,0],[2,2,0,0],[2,0,0,2],[0,0,0,2]]])
    # R=Roiable(roivalue=2)
    # R.setImageFromNumpy(P)
    
    #R=LabelMapable(filename='/g/DAUG_p09-1/s3/Leftmriroi.nii.gz',labelsvalues=[1,2])
    #R.keepBiggestObj(connectivity=3)
    #R.writeImageAs('/g/a2.nii.gz')

    # from dev import LabelMapable

    A=Imaginable(filename='/g/home4/p22RightmriFemur.nii.gz')
    # R=LabelMapable('/data/MYDATA/Dixon_Hip_Data/p20/seg/roi.nii.gz',labelsvalues=[1,2])

    # A.cropImage([160, 0, 0],[0, 0 ,0])
    # R.cropImage([160,0, 0],[0, 0 ,0])
    # R.removeSmallObj(voxel_threshold=10)
    # A.writeImageAs('/g/20b/im.nii.gz')
    # R.writeImageAs('/g/20b/r.nii.gz')

    K=A.getRoiableValuesUpper(0.9)

    K.writeImageAs('/g/a.nii.gz')
