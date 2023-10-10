# this needs the me environment
import os

import SimpleITK as sitk
import numpy as np
import pylab
import nibabel as nib
import sys
import itertools
import math

class IndexTracker(object):
        def __init__(self, ax, X):
            self.ax = ax

            self.X = X
            ax.set_title('use scroll wheel to navigate the image size(' + str(X.shape) +')')
            self.slices, cols,rows   = X.shape
            self.ind = self.slices//2

            self.im = ax.imshow(self.X[self.ind])
            self.update()

        def onscroll(self, event):
            # print("%s %s" % (event.button, event.step))
            if event.button == 'up':
                self.ind = (self.ind + 1) % self.slices
            else:
                self.ind = (self.ind - 1) % self.slices
            self.update()

        def update(self):
            self.im.set_data(self.X[self.ind])
            self.ax.set_ylabel('slice ' + str(self.ind) )
            self.im.axes.figure.canvas.draw()
            # print(int(self.ind))
        
        def onclick(self,event):
            # print('you pressed', event.button, event.xdata, event.ydata)
            # print(type(event.button))
           
            if event.button == 2:
               print('you pressed', event.button, event.xdata, event.ydata)
               print('value %s' % self.X[int(np.floor(event.ydata)),int(np.floor(event.xdata)),self.ind])


""" @brief creates a simpleitk random image

    @param imageSize=[20,20,20],imageResolution=[1.0,1.0,1.0],imageOrigin=[0.0,0.0,0.0],imageDirection=[[1.0,0.0,0.0],[0,1.0.0,0.0],[0.0,0.0,1.0]]
"""

def old_createSITKImagefromNumpyArray(nda, imageResolution=[1.0,1.0,1.0],imageOrigin=[0.0,0.0,0.0],imageDirection=[1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1]):
    print("I was using this function but then i realized it didn't work as i wanted, in fact when you use getimagefromarray it already take into account the different indexing between numpy and sitk")
    img = sitk.GetImageFromArray(adjustNumpyArrayForITK(nda))
    img.SetDirection(imageDirection)
    img.SetOrigin(imageOrigin)
    img.SetSpacing(imageResolution)
    return img

def createSITKImagefromArray(nda, imageResolution=[1.0,1.0,1.0],imageOrigin=[0.0,0.0,0.0],imageDirection=[1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1],vector=False):
    img = sitk.GetImageFromArray(nda,isVector=vector)
    img.SetDirection(imageDirection)
    img.SetOrigin(imageOrigin)
    img.SetSpacing(imageResolution)
    return img

def getSITKImageGeometryInfo(sitkim):
    return  sitkim.GetSize(), sitkim.GetSpacing(), sitkim.GetOrigin(), sitkim.GetDirection()
def createRandomSITKImageFromSITKImage(sitkim,mean=1):
    size, res, origin,directions =getSITKImageGeometryInfo(sitkim)
    filter=sitk.MultiplyImageFilter()
    return filter(createRandomSITKImage(size,res,origin,directions,True),mean)

def createUniformRandomSITKImageFromSITKImage(sitkim,min,max):
    size, res, origin,directions =getSITKImageGeometryInfo(sitkim)
    return createRandomSITKImage(size,res,origin,directions,False,min,max)

def createRandomSITKImage(imageSize=[20,20,20],imageResolution=[1.0,1.0,1.0],imageOrigin=[0.0,0.0,0.0],imageDirection=[1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1],random=True,low=0.0,high=1.0):
    #this is for numpy-sitk indexing format
    try:
        imageSize.reverse()
    except:
        imageSize=list(imageSize)
        imageSize.reverse()
        print(imageSize)

    if random:
        nda=np.random.random(imageSize)
    else:
        nda=np.random.uniform(low=low, high=high, size=imageSize)
    #to get back the original value to right position
    imageSize.reverse()
    return createSITKImagefromArray(nda,imageResolution,imageOrigin,imageDirection)

def createZerosSITKImage(imageSize=[20,20,20],imageResolution=[1.0,1.0,1.0],imageOrigin=[0.0,0.0,0.0],imageDirection=[1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1]):
    #this is for numpy-sitk indexing format
    imageSize.reverse()
    nda=np.zeros(imageSize)
    return createSITKImagefromArray(nda,imageResolution,imageOrigin,imageDirection)

def createLabelMapSITKImage(imageSize=[20,20,20],imageResolution=[1.0,1.0,1.0],imageOrigin=[0.0,0.0,0.0],imageDirection=[1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1],values=[0,1]):
    #this is for numpy-sitk indexing format
    imageSize.reverse()
    nda = np.random.choice(values, size=imageSize)
    nda=np.uint8(nda)
    return createSITKImagefromArray(nda,imageResolution,imageOrigin,imageDirection)

""" @brief creates an imaginable random image
    @param imageSize=[20,20,20],imageResolution=[1.0,1.0,1],imageOrigin=[0.0,0.0,0.0],imageDirection=[[1.0.0,0.0,0.0],[0.0,1.0.0,0.0],[0.0,0.0,1.0]]
"""
def createImaginableFormSITKImage(sitk,imageName='randomImaginable.nii.gz'):
    A=Imaginable()
    A.setImage(sitk)
    A.setOutputFileName(imageName)
    return A

def createRandomImaginable(imageName='randomImaginable.nii.gz',imageSize=[20,20,20],imageResolution=[1.0,1.0,1.0],imageOrigin=[0.0,0.0,0.0],imageDirection=[1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1]):
    sitk=createRandomSITKImage(imageSize,imageResolution,imageOrigin,imageDirection)
    return createImaginableFormSITKImage(sitk,imageName)

def createRandomLabelmapImaginable(imageName='randomImaginable.nii.gz',imageSize=[20,20,20],imageResolution=[1.0,1.0,1.0],imageOrigin=[0.0,0.0,0.0],imageDirection=[1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1],values=[0,1]):
    sitk=createLabelMapSITKImage(imageSize,imageResolution,imageOrigin,imageDirection,values)
    return createImaginableFormSITKImage(sitk,imageName)

def createZerosImaginable(imageName='randomImaginable.nii.gz',imageSize=[20,20,20],imageResolution=[1.0,1.0,1.0],imageOrigin=[0.0,0.0,0.0],imageDirection=[1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1],values=[0,1]):
    sitk=createZerosSITKImage(imageSize,imageResolution,imageOrigin,imageDirection,values)
    return createImaginableFormSITKImage(sitk,imageName)

def createZerosImaginableSameSizeOfImaginable(imag,imageName='random.nii.gz'):
    imageSize,imageResolution,imageOrigin,imageDirection=getImaginableInformation(imag)
    print(imageDirection)
    sitk=createZerosSITKImage(imageSize,imageResolution,imageOrigin,imageDirection)
    return createImaginableFormSITKImage(sitk,imageName)

def getImaginableInformation(immag):
    immag=Imaginable()
    return immag.getImageSize(), immag.getImageSpacing(),immag.getImageOrigin(),immag.getImageDirections()

def command_iteration(method):
    if (method.GetOptimizerIteration() == 0):
        print("Estimated Scales: ", method.GetOptimizerScales())
    print(f"{method.GetOptimizerIteration():3} = {method.GetMetricValue():7.5f} : {method.GetOptimizerPosition()}")


class Registrationable():        
        
        def __init__(self,fixed=None,moving=None):
            
            self.MovingRegisteredImaginable=Imaginable()
            self.FixedImaginable=Imaginable()
            self.MovingImaginable=Imaginable()
            self.Transform=None
            self.TransformDf=None

            if fixed is not None:
                if isinstance(fixed, str):
                    self.FixedImaginable.setImage(sitk.ReadImage(fixed,sitk.sitkFloat32))
                    self.Log.append("set Fixed image from file " + fixed)
                elif isinstance(fixed,sitk.Image):
                    self.FixedImaginable.setImage(fixed)
                    self.Log.append("set Fixed image from image")
                elif isinstance(fixed,Imaginable):
                    self.FixedImaginable=fixed
                else:
                    self.Log.appendError("some problem with the fixed ")
                    return False
                self.reset()

            if moving is not None:
                if isinstance(moving, str):
                    self.MovingImaginable.setImage(sitk.ReadImage(moving,sitk.sitkFloat32))
                elif isinstance(moving,sitk.Image):
                    self.MovingImaginable.setImage(moving)
                elif isinstance(moving,Imaginable):
                    self.MovingImaginable=moving
                else:
                    self.Log.appendError("some problem with the moving ")
                    return False
                
                self.reset()

  

        def transformInitializer(self,moving):
            fixed = self.FixedImaginable.getImage()
            moving = self.MovingImaginable.getImage()
            
            tx2 = sitk.CenteredTransformInitializer(fixed, moving,
                                sitk.Euler3DTransform(),
                                sitk.CenteredTransformInitializerFilter.MOMENTS)
            return tx2
    
        def getTransform(self):
            if self.Transform is None:
                o=self.register()
                if o:
                    return self.Transform
                else:
                    return None
            else:
                return self.Transform

        def setTransform(self,t):

            self.Transform=t
        def writeTransform(self,fn):
            t=self.getTransform()
            if t is not None:
                try:
                    sitk.WriteTransform(t, fn)
                    return True
                    
                except:
                    return False
            else:
                return False
        
        def writeRegisterMovingImaginableAs(self,fn):
            t=self.getMovingRegisteredImaginable()
            if t is not None:
                try:
                    t.writeImageAs(fn)                    
                    return True
                except:
                    return False
            else:
                return False



        def register(self):
            f=self.FixedImaginable.getImage()
            m=self.MovingImaginable.getImage()
    
            initial_transform=self.transformInitializer()

            registration_method = sitk.ImageRegistrationMethod()

            # Similarity metric settings.
            registration_method.SetMetricAsMeanSquares()
            registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
            registration_method.SetMetricSamplingPercentage(1)
            

            registration_method.SetInterpolator(sitk.sitkNearestNeighbor)

            # Optimizer settings.
            registration_method.SetOptimizerAsGradientDescent(learningRate=1, numberOfIterations=10000, convergenceMinimumValue=1e-6, convergenceWindowSize=10)
            registration_method.SetOptimizerScalesFromPhysicalShift()

            # Setup for the multi-resolution framework.            
            registration_method.SetShrinkFactorsPerLevel(shrinkFactors = [2,1,1])
            registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[0,0,0])
            registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

            # Don't optimize in-place, we would possibly like to run this cell multiple times.
            registration_method.SetInitialTransform(initial_transform, inPlace=False)

        
            # registration_method.SetInitialTransform(initial_transform, inPlace=False)

            registration_method.AddCommand(sitk.sitkIterationEvent, lambda: command_iteration(registration_method))

            # Connect all of the observers so that we can perform plotting during registration.
            # registration_method.AddCommand(sitk.sitkStartEvent, rgui.start_plot)
            # registration_method.AddCommand(sitk.sitkEndEvent, rgui.end_plot)
            # registration_method.AddCommand(sitk.sitkMultiResolutionIterationEvent, rgui.update_multires_iterations) 
            # registration_method.AddCommand(sitk.sitkIterationEvent, lambda: rgui.plot_values(registration_method))

            final_transform = registration_method.Execute(f, m)
            

            # Always check the reason optimization terminated.
            print('Final metric value: {0}'.format(registration_method.GetMetricValue()))
            print('Optimizer\'s stopping condition, {0}'.format(registration_method.GetOptimizerStopConditionDescription()))


            # self.MovingRegisteredImaginable.transformAndreshapeOverImage(self.FixedImaginable,final_transform,interpolator=sitk.sitkNearestNeighbor)
            self.setTransform(final_transform)
            print(final_transform)
            return True
        
        def setMovingRegisteredImaginable(self,f):
            self.MovingRegisteredImaginable=f

        def getMovingRegisteredImaginable(self,interpolator=sitk.sitkNearestNeighbor):
            if self.MovingRegisteredImaginable.isImageSet():
                return self.MovingRegisteredImaginable
            else:
                self.MovingRegisteredImaginable=self.MovingImaginable.getDuplicate()
                self.MovingRegisteredImaginable.transformAndreshapeOverImage(self.FixedImaginable,self.getTransform(),interpolator=interpolator)
                return self.MovingRegisteredImaginable



        def setTransform(self,T):
            self.Transform=T
        
        def getTransform(self):
            return self.Transform

        
        def reset(self):
            self.Transform=None
            self.TransformDf=None
            self.Log.append("reset","reset")
        
        def setFixedImaginable(self,F):
            self.FixedImaginable=F
            self.reset()
        
        def getFixedImaginable(self):
            return self.FixedImaginable

        def setMovingImaginable(self,F):
            self.MovingImaginable=F
            self.reset()
        
        def getMovingImaginable(self):
            return self.MovingImaginable

        def warpMovingImaginable(self,t,reference=None):
            if reference is None:
                reference=self.getFixedImaginable()
            m=self.getMovingRegisteredImaginable()
            m.transformAndreshapeOverImage(reference,t,interpolator=sitk.sitkLinear)

def getIndexPositions(list_of_elems, element):
    ''' Returns the indexes of all occurrences of give element in
    the list- listOfElements '''
    index_pos_list = []
    index_pos = 0
    while True:
        try:
            # Search for item in list from indexPos to the end of list
            index_pos = list_of_elems.index(element, index_pos)
            # Add the index position in list
            index_pos_list.append(index_pos)
            index_pos += 1
            
        except ValueError as e:
            break
    return index_pos_list

from operator import itemgetter
def getiListIndexes(l,indexes):
    return [l[index] for index in indexes]

def checkRegistrationAccuracyWithRegionOfInterest(referenceRoiable,testRoiable,transformArray,referenceThreshold=1,testThreshold=1):
    
    c=0
    check=ROIable()
    check.setReference(referenceRoiable)
    check.setReferenceThreshold(referenceThreshold)
    similarity=[]
    for t in transformArray:
        im=testRoiable.getDuplicate()
        im.transformAndreshapeOverImage(referenceRoiable,t,interpolator=sitk.sitkNearestNeighbor)
        check.setTest(im)
        check.setTestThreshold(testThreshold)
        similarity.append(check.getSimilarity())
    return similarity

def getBestRegistrationAccuracyWithRegionOfInterest(referenceRoiable,testRoiable,transformArray,referenceThreshold=1,testThreshold=1):
    O=checkRegistrationAccuracyWithRegionOfInterest(referenceRoiable,testRoiable,transformArray,referenceThreshold,testThreshold)
    return getIndexPositions(O,max(O))







    

    
class Imaginable():
    
    def __init__(self,fileName=None,**kwargs ):

        self.InputFileName = None
        self.OutputFileName = None
        self.Image = None
        self.verbose=False
        
        if fileName is not None:
            self.setInputFileName(fileName)
            
        if kwargs is None:
            print("start")
        elif len(kwargs)==1: #immaginable('filename.nii')
            v=kwargs.values()
            vi=iter(v)
            self.setInputFileName(next(vi))
            
        else:
            if 'inputFileName' in kwargs:
                self.setInputFileName(kwargs['inputFileName'])
            if 'outputFileName' in kwargs:
                self.setOutputFileName(kwargs['outputFileName'])

    def takeThisImage(self,ima):
        
        if isinstance(ima, str):
            self.setInputFileName(ima)
        elif isinstance(ima,sitk.Image):
            self.setImage(ima)
        elif isinstance(ima,Imaginable):
                    self=ima
        elif isinstance(ima,np.ndarray):
            image = sitk.GetImageFromArray(ima)
            self.setImage(image)

        
        else:
            return False
        return True
 
    def isImageSet(self):
        if self.getImage() is None:
            return False
        else:
            return True

    def isImaginable(self):
        O=False
        if isinstance(self,Imaginable):
            return True
        for b in self.__class__.__bases__:
            if isinstance(b,Imaginable):
                O=True
                break
        return O

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
    def getOutputFileName(self):
        try: 
            return self.OutputFileName
        except:
            return None
    def setOutputFileName(self,fn):
        self.OutputFileName = fn
    def getImage(self):
        if self.Image is None:
            if self.getInputFileName() is None:
                return None
            self.readImage()
        return self.Image
        
    def getImageSize(self):
        image=self.getImage()
        return image.GetSize()
    
    def getVoxelVolume(self):
        """get the volume of a voxel in the imaginable

        Returns:
            float: voxel volume
        """        
        # image=self.getImage()
        return math.prod(self.getImageSpacing())

    def getNumberofVoxels(self):
        """get the number of a voxel in the imaginable

        Returns:
            float: N voxels
        """        
        # image=self.getImage()
        return math.prod(self.getImageSize())

    def getVolume(self):
        """get the volume of the imaginable

        Returns:
            float: volume
        """        
        # image=self.getImage()
        return math.prod(self.getVoxelVolume()*self.getNumberofVoxels())

    def getNumberOfNonZeroVoxels(self,image=None):
        if image is  None:
            image=self
        return np.count_nonzero(image.getImageArray())
    def getImageDirections(self):
        image=self.getImage()
        return image.GetDirection()
    
    def getImageSpacing(self):
        image=self.getImage()
        return image.GetSpacing()
    
    def setImageSpacing(self,spacing):
        image=self.getImage()
        image.SetSpacing(spacing)
    
    def getImageOrigin(self):
        image=self.getImage()
        return image.GetOrigin()
        
    def getImageDimension(self):
        image=self.getImage()
        return image.GetDimension()
    
    def getImageNumberOfComponentsPerPixel(self):
        image=self.getImage()
        return image.GetNumberOfComponentsPerPixel()

    def getImagenumberOfComponents(self):
        return self.getImageNumberOfComponentsPerPixel()

    def getImagePixelType(self):
        image=self.getImage()
        return image.GetPixelIDValue(), image.GetPixelIDTypeAsString()

    def setImage(self,im):
        #simpleitk image
        self.Image = im
    
    def getImageArray(self):
        image=self.getImage()
        return sitk.GetArrayFromImage(image)
        
    def setImageFromNibabel(self,filename):
        img = nib.load(filename)
        data = img.get_fdata()
        self.setImageArray(data)

    def getDuplicate(self):
        S=Imaginable()
        S.setImage(self.getImage())
        return S

    def __tellme(self,m):
        if(self.getVerbose()):
            print(m)
    def __del__(self):
        self.__tellme("I'm being automatically destroyed. Goodbye!")
    
    def setImageArray(self,array,changepositions=False, vector=False):
        #input is a nd array #         nda = sitk.GetArrayFromImage(image) or image.getImageArray()
        image=self.getImage()
        if image is None:
            if changepositions:
                array=adjustNumpyArrayForITK(array)
            
            self.setImage(sitk.GetImageFromArray(array, isVector=False))
            
        else:
            nda = sitk.GetImageFromArray(array)
            nda.CopyInformation(image)
            nda.SetSpacing(self.getImageSpacing())
            nda.SetOrigin(self.getImageOrigin())
            nda.SetDirection(self.getImageDirections())
            self.setImage(nda)
    def setImageInformationFromExternalImage(self,externalImage):
        image=self.getImage()
        image.SetSpacing(externalImage.getImageSpacing())
        image.SetOrigin(externalImage.getImageOrigin())
        image.SetDirection(externalImage.getImageDirections())
        self.setImage(image)

    def readImage(self):
        self.setImage(sitk.ReadImage(self.getInputFileName()))
    def writeImageAs(self,filename):
        try:
            self.writeImage(outputFileName=filename)
            print(f'file {filename} saved')
            return True
        except:
            return False

    def createZerosNumpyImageSameDimensionOfImaginable(self,dtype=float):
        size = list(self.getImageSize())
        size.reverse()
        return np.zeros(size,dtype=dtype)


    def resampleOnTargetImage(self,target):
        if target.isImaginable():
            target=target.getImage()
        O=sitk.Resample(self.getImage(),target)

        self.setImage(O)
        
    def writeImage(self,**kwargs):
        if kwargs is not None:
            if 'outputFileName' in kwargs:
                self.setOutputFileName(kwargs['outputFileName'])
        sitk.WriteImage(self.getImage(), self.getOutputFileName())

    def printImageInfo(self):
        image= self.getImage()
        print(image)
        for key in image.GetMetaDataKeys():
            print("\"{0}\":\"{1}\"".format(key, image.GetMetaData(key)))
    def getImageAsNumpyArray(self):
        #it's the same!!!
        return self.getImageArray()

    def viewAxial(self):
        fig, ax = pylab.subplots(1, 1)
        tracker = IndexTracker(ax, self.getImageAsNumpyArray())
        fig.canvas.mpl_connect('scroll_event', tracker.onscroll)
        fig.canvas.mpl_connect('button_press_event', tracker.onclick)
        pylab.show()
   
    def resetImage(self):
        filen=self.getInputFileName()
        if filen is not None:
            self.readImage()
            return True
        return False

    def resizeImage(self,newSize,interpolator=sitk.sitkLinear):
        image=self.getImage()
        dimension = image.GetDimension()
        reference_physical_size = np.zeros(image.GetDimension())
        reference_physical_size[:] = [round((sz-1)*spc) if sz*spc>mx  else mx for sz,spc,mx in zip(image.GetSize(), image.GetSpacing(), reference_physical_size)]

        reference_origin = image.GetOrigin()
        reference_direction = image.GetDirection()

        
        reference_spacing = [ phys_sz/(sz-1) for sz,phys_sz in zip(newSize, reference_physical_size) ]
        centered_transform =sitk.Transform()
        
        self.setImage(regridSitkImage(image, newSize, centered_transform,  interpolator, reference_origin, reference_spacing, reference_direction, 0.0,image.GetPixelIDValue()))
        return True

    def cropImagev0(self,lowerB,upperB):
        image=self.getImage()
        return self.setImage(sitk.Crop(image,lowerB,upperB))

    def cropImage(self,lowerB,upperB):
        image=self.getImage()
        U=self.getImageSize()
        for t in range(len(upperB)):
            if ((upperB[t]==0) |(upperB[t]==np.NaN)):
                upperB[t]=U[t]

        S=[u-l for l,u in zip(lowerB,upperB)]
        crop = sitk.ExtractImageFilter()
        crop.SetSize(S)
        crop.SetIndex(lowerB)
        cropped_image = crop.Execute(image)
        return self.setImage(cropped_image)

    def getImageCornersVoxel(self,image=None):
        # image is an IMmaginable image
        if image is None:
            image=self.getImage()
        max_indexes = [sz-1 for sz in image.GetSize()]
        extreme_indexes = list(itertools.product(*(list(zip([0]*image.GetDimension(),max_indexes)))))
        return extreme_indexes
    # extreme_points_transformed = [euler_transform.TransformPoint(image.TransformContinuousIndexToPhysicalPoint(p)) for p in extreme_indexes]
    
    # output_min_coordinates = np.min(extreme_points_transformed, axis=0)
    # output_max_coordinates = np.max(extreme_points_transformed, axis=0)
    
    # # isotropic ouput spacing
    # if output_spacing is None:
    #   output_spacing = min(image.GetSpacing())
    # output_spacing = [output_spacing]*image.GetDimension()  
                    
    # output_origin = output_min_coordinates
    # output_size = [int(((omx-omn)/ospc)+0.5)  for ospc, omn, omx in zip(output_spacing, output_min_coordinates, output_max_coordinates)]
    
    # output_direction = [1,0,0,0,1,0,0,0,1]
    # output_pixeltype = image.GetPixelIDValue()

    # return sitk.Resample(image, 
    #                      output_size, 
    #                      euler_transform.GetInverse(), 
    #                      sitk.sitkLinear, 
    #                      output_origin,
    #                      output_spacing,
    #                      output_direction,
    #                      background_value,
    #                      output_pixeltype) 

    
    def reshapeOverImage(self,targetImage,**kwargs):
        if kwargs is None:
            print("start")
        else:
            if 'interpolator' in kwargs:
                interpolator= kwargs['interpolator']
            else:
                interpolator =  sitk.sitkLinear
        self.reshapeImageToNewGrid(pixelValue=0,
        intrepolator= interpolator,
        newSize= targetImage.getImageSize(),
        newOrigin=targetImage.getImageOrigin(),
        newDirections=targetImage.getImageDirections(),
        newSpacing=targetImage.getImageSpacing()
        )


    def saveVoxelsCloudAs(self,filename,mask=None):
        return self.getVoxelsCloud(filename=filename,mask=mask)

    def writeVoxelsCloudAs(self,filename,mask=None):
        return self.saveVoxelsCloudAs(filename,mask)

    def writePointsCloudAs(self,filename,mask=None):
        return self.savePointsCloudAs(filename,mask)

    def savePointsCloudAs(self,filename,mask=None):
        return self.getPointsCloud(filename=filename)
    def getPointsCloud(self,image=None,filename=None,mask=None):
        """ Generate a points cloud of the image
        Args:
            image (_type_): if you pass an image we'll give you back the point cvloud of that image
        """

        if image is None:
            image=self
        
        if(isinstance(image,sitk.Image)):
            im=image
            image=Imaginable()
            image.setImage(im)
        if mask is None:
            PC=image.__scanPointsCloud__(realworldcoordinates=True,filename=filename)
        else:
            PC=image.__scanPointsCloudMasked__(realworldcoordinates=True,filename=filename,mask=mask)
        return PC

    def getVoxelsCloud(self,image=None,filename=None,mask=None):
        """ Generate a voxels cloud of the image
        Args:
            image (_type_): if you pass an image we'll give you back the point cvloud of that image
        """
        if image is None:
            image=self

        if(isinstance(image,sitk.Image)):
            im=image
            image=Imaginable()
            image.setImage(im)
        if mask is None:
            PC=image.__scanPointsCloud__(realworldcoordinates=False,filename=filename)
        else:
            if mask.isImageSet():
                PC=image.__scanPointsCloudMasked__(realworldcoordinates=False,filename=filename,mask=mask)
            else:
                PC=image.__scanPointsCloudMasked__(realworldcoordinates=False,filename=filename)
        return PC


    def transformAndreshapeOverImage(self,tImage,transform,**kwargs):
        if kwargs is None:
            print("start")
        else:
            if 'interpolator' in kwargs:
                interpolator= kwargs['interpolator']
            else:
                interpolator =  sitk.sitkLinear
        if isinstance(tImage,sitk.Image):
            targetImage=Imaginable()
            targetImage.setImage(tImage)
        else:
            targetImage=tImage
        return self.reshapeImageToNewGrid(pixelValue=0,
        intrepolator= interpolator,
        newSize= targetImage.getImageSize(),
        newOrigin=targetImage.getImageOrigin(),
        newDirections=targetImage.getImageDirections(),
        newSpacing=targetImage.getImageSpacing(),
        transform=transform
        )

    
    def resizeImageInVoxelSpace(self,sizemin,sizemax,**kwargs):
        spacing='original'
        newSpacing=self.getImageSpacing()
        newSize=[]
        [newSize.append(ma-mi) for mi,ma in zip(sizemin,sizemax)]            
        oldSize=self.getImageSize()
        if kwargs is None:
            print("start")
        else:
            if 'interpolator' in kwargs:
                interpolator= kwargs['interpolator']
            else:
                interpolator =  sitk.sitkLinear
            if 'spacing' in kwargs:
                spacing= kwargs['spacing']
                if(spacing.lower()=='calculate'):
                    oldSpacing=newSpacing
                    newSpacing=[]
                    [newSpacing.append(float(float(n)/float(o)*s)) for n,o,s in zip(newSize,oldSize,oldSpacing)]
                    print(newSpacing)
            else:
                interpolator =  sitk.sitkLinear
        
        newOrigin=self.getCoordinatesFromIndex(sizemin)
        self.reshapeImageToNewGrid(pixelValue=0,
        intrepolator= interpolator,
        newSize= newSize,
        newOrigin=newOrigin,
        newDirections=self.getImageDirections(),
        newSpacing=newSpacing
        )

    def addImage(self, imaginableToBeAdd):
        image=self.getImage()
        imaginableToBeAdd.reshapeOverImage(self)
        add=imaginableToBeAdd.getImage()
        return self.setImage(image+add)

    def applyABS(self):
        m=self.getImage()
        try:
            ABS=sitk.ComplexToModulusImageFilter()
            self.setImage(ABS.Execute(m))
        except:
            try:
                ABS2=sitk.ModulusImageFilter()
                self.setImage(ABS2.Execute(m))
            except:
                return False
        return True



        
    def reshapeImageToNewGrid(self,**kwargs):
        image=self.getImage()
        

        if kwargs is None:
            print("start")
        else:
            if 'pixelValue' in kwargs:
                default_value= kwargs['pixelValue']
            else:
                default_value=0
            if ('interpolator' in kwargs):
                interpolator= kwargs['interpolator']
            else:
                interpolator =  sitk.sitkLinear
            if 'transform' in kwargs:
                transform=kwargs['transform']
            else:
                transform=sitk.Transform()
            if 'newSize' in kwargs:
                newSize=kwargs['newSize']
            else:
                newSize=self.getImageSize()
            if 'newOrigin' in kwargs:
                newOrigin=kwargs['newOrigin']
            else:
                newOrigin=self.getImageOrigin()
            
            if 'newSpacing' in kwargs:
                newSpacing=kwargs['newSpacing']
            else:
                newSpacing=self.getImageSpacing()

            if 'newDirections' in kwargs:
                newDirections=kwargs['newDirections']
            else:
                newDirections=self.getImageDirections()
            

        self.setImage(regridSitkImage(image, newSize, transform , interpolator, newOrigin, newSpacing, newDirections, default_value,image.GetPixelIDValue()))
        return self.getImage()


    def isPointInside(self,P):
        #works with points
        image=self.getImage()
        size=self.getImageSize()
        V=self.getIndexFromCoordinates(P)
        #pretend it's inside
        O=True 

        for a in range(len(P)):
            if (V[a]<0 ) | (V[a]>size[a]):
                O=False
                break

        return O
    
        

    def translateImage(self,T):
        image=self.getImage()
        dimension=self.getImageDimension()
        translation = sitk.TranslationTransform(dimension, T)
        self.setImage(transformImage(image,translation))
    def getCoordinatesFromIndex(self,P):
        image=self.getImage()
        return image.TransformContinuousIndexToPhysicalPoint(P)
    def getIndexFromCoordinates(self,I):
        image=self.getImage()
        return image.TransformPhysicalPointToIndex(I)
        # return image.TransformPhysicalPointToContinuousIndex(I)



    def getImageCenterCoordinates(self):
        return self.getCoordinatesFromIndex(np.array(self.getImageSize())/2.0)

    def composeImageCosinesTransform(self,transform):
        image=self.getImage()
        dimension=self.getImageDimension()
        cosines = sitk.AffineTransform(dimension)
        cosines.SetCenter(self.getImageOrigin())
        
        return sitk.CompositeTransform([cosines,transform])

    def transformImageAffine(self,transform):
        #transform will be parsed with the cosines
        image=self.getImage()
        # thetransform=self.composeImageCosinesTransform(transform)
        thetransform=transform.GetInverse()
        return transformImage(image,thetransform,interpolator=sitk.sitkLinear),thetransform

    def translateImageAffine(self,T):
        dimension=self.getImageDimension()
        
        transform = sitk.AffineTransform(dimension)
        transform.SetTranslation(T)

        transform.SetCenter(self.getImageOrigin())
        im,thetransform =self.transformImageAffine(transform)
        self.setImage(im)
        return thetransform

    def scaleImageAffine(self,S,**kwargs):
        dimension=self.getImageDimension()
        
        if kwargs is not None:
            if 'transformCenter' in kwargs:
                if kwargs["transformCenter"] is None:
                    center=self.getImageCenterCoordinates()
                else:
                    center=kwargs['transformCenter']
            else :
                center = self.getImageCenterCoordinates()
   
        transform = sitk.AffineTransform(dimension)
        #transform.SetMatrix(self.getImageDirections())
        
        matrix = np.array(transform.GetMatrix()).reshape((dimension,dimension))
        for s in range(dimension):
            matrix[s,s] = S[s]
        transform.SetMatrix(matrix.ravel())
        transform.SetCenter(center)
        im,thetransform =self.transformImageAffine(transform)
        self.setImage(im)
        return thetransform
        


    def rotateImage3D(self, theta_x, theta_y, theta_z,transformation_center=None):
        """
        This function rotates an image across each of the x, y, z axes by theta_x, theta_y, and theta_z degrees
        respectively and resamples it to be isotropic.
        :param image: An sitk 3D image
        :param theta_x: The amount of degrees the user wants the image rotated around the x axis
        :param theta_y: The amount of degrees the user wants the image rotated around the y axis
        :param theta_z: The amount of degrees the user wants the image rotated around the z axis
        :param output_spacing: Scalar denoting the isotropic output image spacing. If None, then use the smallest
                            spacing from original image.
        :return: The rotated image
        """
        image =self.getImage()
        if transformation_center is None:
            transformation_center=self.getImageCenterCoordinates()

        euler_transform = sitk.Euler3DTransform (transformation_center, 
                                                np.deg2rad(theta_x), 
                                                np.deg2rad(theta_y), 
                                                np.deg2rad(theta_z))
        
        im,thetransform =self.transformImageAffine(euler_transform)
        self.setImage(im)
        return thetransform




    def multiply(self,v,image=None):
        
        if image is None:
            image=self.getImage()
        
        filter = sitk.MultiplyImageFilter()
        
        return sitk.Cast(filter.Execute(image,float(v)),image.GetPixelIDValue())

    def divide(self,v,image=None):
        return self.multiply(1.0/v,image)
        
    def multiplyAndSet(self,v,image=None):
        if image is None:
            image=self.getImage()

        m= self.multiply(v,image)
        self.setImage(m)
        return m

    def divideAndSet(self,v,image=None):
        return self.multiplyAndSet(1.0/v,image)
    
    def addAndSet(self,image2,image=None):
        if image is None:
            image=self.getImage()
            
        m= self.add(image2,image)
        self.setImage(m)
        return m
    
    def add(self,image2,image=None):
        
        if image is None:
            image=self.getImage()
        
        filter = sitk.AddImageFilter()
        if isinstance(image2,type(image)):
            return self.cast(image.GetPixelIDValue(),filter.Execute(self.cast(sitk.sitkFloat64,image),self.cast(sitk.sitkFloat64,image2)))
        else:
            return self.cast(image.GetPixelIDValue(),filter.Execute(self.cast(sitk.sitkFloat64,image),image2))

    
    def cast(self,type,image=None):
        if image is None:
            image=self.getImage()
        
        return sitk.Cast(image,type)

    def castAndSet(self,type,image=None):
        if image is None:
            image=self.getImage()
        if type==float:
            thetype= sitk.sitkFloat32
            

        self.setImage(sitk.Cast(image,thetype))
        return True


    def getValuesInImageUnique(self,image=None):
        if image is None:
            image=self.getImage()
    
        return np.unique(self.getImageArray().flatten())

    def getMaximumValue(self,image=None):
        if image is None:
            image=self.getImage()
        filter = sitk.MinimumMaximumImageFilter()
        filter.Execute(image)
        return filter.GetMaximum()
    
    def getMeanValue(self,image=None):
        if image is None:
            image=self.getImage()
        filter = sitk.StatisticsImageFilter()
        filter.Execute(image)
        return filter.GetMean()

    def getStdValue(self,image=None):
        if image is None:
            image=self.getImage()
        filter = sitk.StatisticsImageFilter()
        filter.Execute(image)
        return filter.GetSigma()

    def getMinimumValue(self,image=None):
        if image is None:
            image=self.getImage()

        filter = sitk.MinimumMaximumImageFilter()
        filter.Execute(image)
        return filter.GetMinimum()
    
    def getAxialSlice(self,slice,image=None):
        if image is None:
            image = self.getImage()
        slice = int(slice)
        size = list(image.GetSize())
        size[2] = 0
        index = [0, 0, slice]
        out = self.__SliceExtractor(image,size,index)
        return out
    def getCoronalSlice(self,slice,image=None):
        if image is None:
            image = self.getImage()
        slice = int(slice)
        size = list(image.GetSize())
        size[1] = 0
        index = [0, slice,0]
        out = self.__SliceExtractor(image,size,index)
        return out
    def getSagittalSlice(self,slice,image=None):
        if image is None:
            image = self.getImage()
        slice = int(slice)
        size = list(image.GetSize())
        size[0] = 0
        index = [slice,0,0]
        out = self.__SliceExtractor(image,size,index)
        return out
    
    def writeSliceAs(self,plan,index,filename,image):
        if image is None:
            image = self.getImage()
        
        if((plan==0)|(plan=='axial')):
            slice=self.getAxialSlice(index,image)
        elif((plan==1)|(plan=='sagittal')):
            slice=self.getSagittalSlice(index,image)
        elif((plan==2)|(plan=='coronal')):
            slice=self.getCoronalSlice(index,image)
        

    

    def __SliceExtractor(self,image,size,index):
        Extractor = sitk.ExtractImageFilter()
        Extractor.SetSize(size)
        Extractor.SetIndex(index)
        return Extractor.Execute(image)
    
    def __scanPointsCloudMasked__(self,realworldcoordinates=True,filename=None,mask=None):
        NC=self.getImageNumberOfComponentsPerPixel()
        dimensions=self.getImageDimension()
        size=self.getImageSize()
        L=[]
        if mask is None:
            return None
        else:
            if dimensions==3:
                X,Y,Z=size
                for x in range(X):
                    for y in range(Y):
                        for z in range(Z):
                            P=[x,y,z]
                            V=self.getImage().GetPixel(P)
                            M=mask.getImage().GetPixel(P)
                            if M>0:
                                if realworldcoordinates:
                                        P=self.getIndexFromCoordinates(P)
                                l={'coordinates':P,'values':V}
                                L.append(l)

            if filename is not None:
                O=True
                C=[k['coordinates'] for k in L]
                V=[k['values'] for k in L]
                return self.__writeToFile__(C,V,filename)
            else:
                return L 

    def __scanPointsCloud__(self,realworldcoordinates=True,filename=None):
        NC=self.getImageNumberOfComponentsPerPixel()
        dimensions=self.getImageDimension()
        size=self.getImageSize()
        L=[]
        if dimensions==3:
            X,Y,Z=size
            for x in range(X):
                for y in range(Y):
                    for z in range(Z):
                        P=[x,y,z]
                        V=self.getImage().GetPixel(P)
                        if realworldcoordinates:
                                P=self.getIndexFromCoordinates(P)
                        l={'coordinates':P,'values':V}
                        L.append(l)

        if filename is not None:
            O=True
            C=[k['coordinates'] for k in L]
            V=[k['values'] for k in L]
            return self.__writeToFile__(C,V,filename)
        else:
            return L    
       
    def __writeToFile__(self,C,V,filename):
        with open(filename, 'w') as f:
            c=0
            for k in C:
                f.write(f'{k[0]}, {k[1]}, {k[2]} {V[c]}\n')
                c=c+1




class Lablemappable(Imaginable):
    def getValuesInImageUnique(self, image=None):
        L= super().getValuesInImageUnique(image)
        return L[L>0]


    def dilate(self,radius=2,foregraundvalue=1,image=None):
        return self.__derode(radius,foregraundvalue,image,False)
    def erode(self,radius=2,foregraundvalue=1,image=None):
        return self.__derode(radius,foregraundvalue,image,True)
    def __derode(self,radius=2,foregraundvalue=None,image=None,erode=True):
        
        if image is None:
            image=self.getImage()
        
        if erode:
            filter = sitk.BinaryErodeImageFilter()
        else:
            filter = sitk.BinaryDilateImageFilter()

        filter.SetKernelRadius ( radius )

        L=self.getValuesInImageUnique(image)
        imagetype=image.GetPixelIDValue()
        size = self.getImageSize()
        out = sitk.Image(size, imagetype)
        out.CopyInformation(image)
        for l in range(len(L)):
            f=L[l]
            filter.SetForegroundValue ( float(f))
            out+=filter.Execute(self.multiply(f,self.mask(f,image)))


        return sitk.Cast(out, image.GetPixelIDValue())
        
    def getMapFromLabelMap(self,value,image=None):
        if image is None:
            image=self.getImage()
        return value*(image==value)

    def mask(self,value,image=None):
        if image is None:
            image=self.getImage()
        
        return sitk.Cast(image==value,image.GetPixelIDValue())
        
    
    def treshold(self,low=None,high=None,image=None):
        
        if image is None:
            image=self.getImage()
        
       
        filter = sitk.ThresholdImageFilter()
        if low is not None:
            filter.SetLower(float(low))
        
        if high is not None:
            filter.SetUpper(float(high))
        
        
        return sitk.Cast(filter.Execute ( image ), image.GetPixelIDValue())

    def getDuplicate(self):
        S=Lablemappable()
        S.setImage(self.getImage())
        return S
        #override because we want to force a nearest neighbour interp
    
    def transformImageAffine(self,transform=None):
        
        thetransform=self.composeImageCosinesTransform(transform)
        theim=transformImage(self.getImage(),thetransform,interpolator=sitk.sitkNearestNeighbor)
        return theim,thetransform

    # def transformImageAffine(self,transform=None):
    #     #transform will be parsed with the cosines
    #     output_image=self.getDuplicate()
    #     L=self.getValuesInImageUnique()
    #     imagetype=self.GetPixelIDValue()
    #     size = self.getImageSize()
    #     SS=self.getImageSpacing()
    #     SSs=[s/4 for s in SS]
    #     Sizes=[s*4 for s in size]
    #     OL=self.getImageOrigin()
    #     output_image.reshapeImageToNewGrid(newSize=Sizes,
    #         newOrigin=OL,
    #         newSpacing=SSs,
    #         interpolator=sitk.sitkNearestNeighbor)
        


    #     output_image = sitk.Image(size, imagetype)
    #     output_image.CopyInformation(image)
    #     for l in range(len(L)):
    #         f=L[l]
    #         #obtain the mask
    #         im=self.mask(f)
    #         B=Lablemappable()
    #         B.setImage(im)
        

    #         thetransform=self.composeImageCosinesTransform(transform)
    #         theim=transformImage(B.getImage(),thetransform,interpolator=sitk.sitkNearestNeighbor)
    #         output_image+=self.multiply(f,theim)
        
    #     return output_image,thetransform
# def transformImageAffine(self,transform=None):
#         #transform will be parsed with the cosines
#         image=self.getImage()
#         thetransform=self.composeImageCosinesTransform(transform)
#         theim=transformImage(image,thetransform,interpolator=sitk.sitkNearestNeighbor)
        
#         return theim,thetransform


class ROIable():
    def __init__(self):
        self.Reference=None
        self.Test=None
        self.Overlap=None
        self.ReferenceThreshold=1
        self.TestThreshold=1
        
    def getReference(self):
        return self.Reference
    def getTest(self):
        return self.Test
    def setReference(self,reference):
        self.resetOverlap()
        self.Reference =reference
    def setTest(self,test):
        self.resetOverlap()
        self.Test=test
    def setOverlapFilter(self,overlap):
        self.Overlap =overlap
    def resetOverlap(self):
        self.Overlap =None

    def getOverlapFilter(self):
        ov=self.Overlap
        if ov is None:
            R=self.getReference()
            T=self.getTest()
            t=T.getImage()
            r=R.getImage()
            if (r is not None) & (t is not None):
                ov=sitk.LabelOverlapMeasuresImageFilter()
                thr=self.getReferenceThreshold()
                tht=self.getTestThreshold()
                ov.Execute(r==thr, t==tht)
                self.setOverlapFilter(ov)
                return ov
            else:
                return None

        else:
            return ov
    def getReferenceThreshold(self):
        return self.ReferenceThreshold
    def setReferenceThreshold(self,t):
        self.resetOverlap()
        self.ReferenceThreshold=t
    
    def getTestThreshold(self):
        return self.TestThreshold
    def setTestThreshold(self,t):
        self.resetOverlap()
        self.TestThreshold=t


    def getJaccard(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetJaccardCoefficient()
        else:
            return None
    
    def getDice(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetDiceCoefficient()
        else:
            return None

    def getSimilarity(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetVolumeSimilarity()
        else:
            return None
    
    def getFalseNegativeError(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetFalseNegativeError()
        else:
            return None
    
    def getFalsePostiveError(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetFalsePositiveError()
        else:
            return None
    
    def getHahusdorf(self):
        ov = sitk.HausdorffDistanceImageFilter()
        R=self.getReference()
        T=self.getTest()
        t=T.getImage()
        r=R.getImage()

        thr=self.getReferenceThreshold()
        tht=self.getTestThreshold()
        ov.Execute(r==thr, t==tht)
        if ov is not None:
            return ov.GetHausdorffDistance()
        else:
            return None
    def getVolmeSimilarity(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetVolumeSimilarity()
        else:
            return None

    def getMeanOverlap(self):
        ov=self.getOverlapFilter()
        if ov is not None:
            return ov.GetMeanOverlap()
        else:
            return None

    def getSimilarity(self):
        ov = sitk.SimilarityIndexImageFilter()
        R=self.getReference()
        T=self.getTest()
        t=T.getImage()
        r=R.getImage()

        thr=self.getReferenceThreshold()
        tht=self.getTestThreshold()
        ov.Execute(r==thr, t==tht)
        if ov is not None:
            return ov.GetSimilarityIndex()
        else:
            return None

    def getOverlappedVoxels(self):
        ov = sitk.AddImageFilter()
        R=self.getReference()
        T=self.getTest()
        t=T.getImage()
        r=R.getImage()
        thr=self.getReferenceThreshold()
        tht=self.getTestThreshold()
        L=ov.Execute(r==thr, t==tht)
        if ov is not None:
            s=sitk.StatisticsImageFilter()
            s.Execute(L==2)
            return s.GetSum()
        else:
            return None

    def getNonOverlappedVoxels(self):
        ov = sitk.AddImageFilter()
        R=self.getReference()
        T=self.getTest()
        t=T.getImage()
        r=R.getImage()
        thr=self.getReferenceThreshold()
        tht=self.getTestThreshold()
        L=ov.Execute(r==thr, t==tht)
        if ov is not None:
            s=sitk.StatisticsImageFilter()
            s.Execute(L!=2)
            return s.GetSum()
        else:
            return None

            




    def testImages(self,pt): 
        #check if th images are overlapped
        ro=os.path.join(pt,'r.nii.gz')
        to=os.path.join(pt,'t.nii.gz')
        
        R=self.getReference()
        T=self.getTest()
        t=T.getImage()
        r=R.getImage()
        RA=Imaginable()
        RA.setImage(r==self.getReferenceThreshold())
        RA.writeImage(outputFileName=ro)

        TA=Imaginable()
        TA.setImage(t==self.getTestThreshold())
        TA.writeImage(outputFileName=to)
    
    def getAllMetrics(self):
        O={
            "Hahusdorf":self.getHahusdorf(),
            "FNE":self.getFalseNegativeError(),
            "FPE":self.getFalsePostiveError(),
            "Dice":self.getDice(),
            "Jaccard":self.getJaccard(),
            "VS":self.getVolmeSimilarity(),
            "MO":self.getMeanOverlap(),
            "SM":self.getSimilarity(),
            "OV":self.getOverlappedVoxels(),
            "NOV":self.getNonOverlappedVoxels(),
        }
        return O
    

        

#used in the classes
def transformImage(image, transform, **kwargs):
    # Output image Origin, Spacing, Size, Direction are taken from the reference
    # image in this call to Resample
    default_value = 0
    interpolator = sitk.sitkLinear
    reference_image=image

    if kwargs is None:
        print("start")
    else:
        if 'pixelValue' in kwargs:
            default_value= kwargs['pixelValue']
        if 'interpolator' in kwargs:
            interpolator= kwargs['interpolator']
        if 'referenceImage' in kwargs:
            reference_image=kwargs['referenceImage']
        
    return sitk.Resample(image, reference_image, transform,
                         interpolator, default_value)
def regridSitkImage(image, newSize, transform , interpolator, newOrigin, newSpacing, newDirections, default_value,pixelidvalue):
    return sitk.Resample(image, newSize, transform , interpolator, newOrigin, newSpacing, newDirections, default_value,pixelidvalue)


        
        
def adjustNumpyArrayForITK(array):
    # ITK's Image class does not have a bracket operator. It has a GetPixel which takes an ITK Index object as an argument, which is an array ordered as (x,y,z). This is the convention that SimpleITK's Image class uses for the GetPixel method as well. While in numpy, an array is indexed in the opposite order (z,y,x).

    if(len(array.shape)==3):
        return np.swapaxes(array,0,2)
    elif(len(array.shape)==2):
        return np.swapaxes(array,0,1)
    elif(len(array.shape)==4):
        return np.transpose(array, (3, 2, 1, 0) )
    elif(len(array.shape)==5):
        return np.transpose(array, (4 ,3, 2, 1, 0) )
    else:
        print("numpy shape not yet seen!! in adjustNumpyArrayForITK")
        return None
        





def dicomread(fname,dirout=None):
    if len(sys.argv) < 1:
        print("Usage: DicomSeriesReader <input_directory> <outputdirectory>")
        sys.exit(1)

    print("Reading Dicom directory:", fname)
    reader = sitk.ImageSeriesReader()

    dicom_names = reader.GetGDCMSeriesFileNames(fname)
    reader.set
    reader.SetFileNames(dicom_names)
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()
    #image = reader.Execute()

    #size = image.GetSize()
    #print("Image size:", size[0], size[1], size[2])

    

        # Copy relevant tags from the original meta-data dictionary (private tags are also
        # accessible).
    tags_to_copy = ["0010|0010", # Patient Name
                    "0010|0020", # Patient ID
                    "0010|0030", # Patient Birth Date
                    "0020|000D", # Study Instance UID, for machine consumption
                    "0020|0010", # Study ID, for human consumption
                    "0008|0020", # Study Date
                    "0008|0030", # Study Time
                    "0008|0050", # Accession Number
                    "0008|0060"  # Modality
    ]

    series_tag_values = [(k, reader.GetMetaData(0,k)) for k in tags_to_copy if reader.HasMetaDataKey(0,k)]
                #  [("0008|0031",modification_time), # Series Time
                #   ("0008|0021",modification_date), # Series Date
                #   ("0008|0008","DERIVED\\SECONDARY"), # Image Type
                #   ("0020|000e", "1.2.826.0.1.3680043.2.1125."+modification_date+".1"+modification_time), # Series Instance UID
                #   ("0020|0037", '\\'.join(map(str, (direction[0], direction[3], direction[6],# Image Orientation (Patient)
                #                                     direction[1],direction[4],direction[7])))),
                #   ("0008|103e", series_reader.GetMetaData(0,"0008|103e") + " Processed-SimpleITK")] # Series Description

    print(tags_to_copy)
    # for i in range(filtered_image.GetDepth()):
    #     image_slice = filtered_image[:,:,i]
    #     # Tags shared by the series.
    #     for tag, value in series_tag_values:
    #         image_slice.SetMetaData(tag, value)
    #     # Slice specific tags.
    #     image_slice.SetMetaData("0008|0012", time.strftime("%Y%m%d")) # Instance Creation Date
    #     image_slice.SetMetaData("0008|0013", time.strftime("%H%M%S")) # Instance Creation Time
    #     image_slice.SetMetaData("0020|0032", '\\'.join(map(str,filtered_image.TransformIndexToPhysicalPoint((0,0,i))))) # Image Position (Patient)
    #     image_slice.SetMetaData("0020,0013", str(i)) # Instance Number


def dcm2nii(pt,out=None):
    print("Reading Dicom directory:", pt)
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(pt)
    reader.SetFileNames(dicom_names)
    image = reader.Execute()
    size = image.GetSize()
    print("Image size:", size[0], size[1], size[2])
    if out:
        print("Writing image:", out)
        sitk.WriteImage(image,out)
        return 
    else:
        o=Imaginable();
        o.setImage(image)
    return o

