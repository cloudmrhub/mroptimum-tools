import argparse
from pynico_eros_montin import pynico as pn
from pyable_eros_montin import imaginable as ima
try:
    from mro import *
except:
    from mroptimum.mro import *
import cloudmrhub.cm2D as cm2D


import cloudmrhub.cm as cm


def saveMatlab(fn,vars):
    J=dict()
    for k in vars:
        J[k["name"].replace(" ","")]=k["data"]
    
    scipy.io.savemat(fn,J)
   
def getAccellerationInfo2D(s,raid=1):
    N=pn.Pathable(getFile(s["options"]))
    n=N.getPosition()
    twix=twixtools.map_twix(n)
    H=twix[raid]["hdr"]
    iPat=H['MeasYaps']['sPat']
    return [1,int(iPat['lAccelFactPE'])],[np.nan,int(iPat['lRefLinesPE'])]






if __name__=="__main__":
    parser = argparse.ArgumentParser(
                        prog='Mroptimum',
                        description='Calculates SNR as it should be done!\n eros.montin@gmail.com',
                        epilog='cloudmrhub.com')

    T=pn.Timer()
    parser.add_argument('-j','--joptions', type=str, help='optionfile with the backbone of the calculation')
    parser.add_argument('-o','--output', type=str, help='output path')
    parser.add_argument('-l','--loutput', type=str, help='output log file')
    parser.add_argument('-c','--coilsens', type=bool, help='output coil sensitivities',default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('-g','--gfactor', type=bool, help='otput g-factor',default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('-f','--outputformat', choices=['mat','cmr','nifti','mha'],type=str, help='output g-factor')
    parser.add_argument('-v','--verbose', choices=[True,False],type=bool, help='would you like to see the plots while calculating',default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('-m','--matlab', choices=[True,False],type=bool, help='would you like to have a mat file',default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('-p','--parallel', choices=[True,False],type=bool, help='Parallel?',default=True, action=argparse.BooleanOptionalAction)

       
    args = parser.parse_args()

    if args.joptions==None:
        raise Exception("please input a json file forthe customization of the SNR calculation")
    else:
        #read the json options file
        O=pn.Pathable(args.joptions)
        J=O.readJson()
        #start the log
        LOG=pn.Log()
        if args.loutput ==None:
            args.loutput=pn.createRandomTemporaryPathableFromFileName('a.log').getPosition()
        logfn=args.loutput
        M=[]
        IMAOUT=[]
        if J["version"]!="v0":
            LOG.appendError(f"wrong json options ({J['version']})")
            LOG.writeLogAs(logfn)
            raise Exception("options file is not v0")
        LOG.append('options file valiadated')

        #this version only works with 2D k-space
        if J["acquisition"]!=2:
            LOG.appendError('acquisition is not 2D')
            LOG.writeLogAs(logfn)
            raise Exception("sorry only 2D k-space")

        #which reconstructor has been requested
        reconstructor_dictionary=J["options"]["reconstructor"]
        #recon id
        RID=RECON.index(reconstructor_dictionary["name"].lower())
        #snr id
        SID=SNR.index(J["name"].lower())
        #reconstruction classes
        reconstructor=RECON_classes[RID]
        #if the snr is analytical
        if SID==0:
            reconstructor=KELLMAN_classes[RID]
        NR=None
        if SID>1:
            NR=J["options"]["NR"]
        
        boxSize=None
        if SID>2:
            boxSize=J["options"]["boxSize"]      
        #how many slices // CHANGE here for others vendors
        if reconstructor_dictionary["options"]["signal"]["options"]["vendor"].lower()=='siemens':
            MR=(SID==1)
            SL=getSiemensKSpace2DInformation(reconstructor_dictionary["options"]["signal"],signal=True,MR=MR)
        else:
            LOG.appendError('filetype unknown')
            LOG.writeLogAs(logfn)
            raise Exception(' this version of SNR tool only works with siemens file at the moment')
        #intialize the output array (id,dimension,UI name,imaginable,fn,outputtype)

        IMAOUT=[]
        # calculates the noise statistics
        NOISE=None
        #noise file
        if "noise" in reconstructor_dictionary["options"].keys():
            NOISE=getNoiseKSpace(reconstructor_dictionary["options"]["noise"],'all')
        # multiraid in signal
        if(reconstructor_dictionary["options"]["signal"]["options"]["vendor"].lower()=='siemens') and (reconstructor_dictionary["options"]["signal"]["options"]["multiraid"])    :
            NOISE=getNoiseKSpace(reconstructor_dictionary["options"]["signal"],'all')
        # if no noise file is provided
        if NOISE==None:
            NC=None
            NCC=None
        else:
            NC,NCC=calculteNoiseCovariance(NOISE,args.verbose)
            IMAOUT.append({"id":1,"dim":2,"name":"Noise Covariance","data":NC,"filename":'data/NC.nii.gz',"type":'output'})
            IMAOUT.append({"id":2,"dim":2,"name":"Noise Coefficient","data":NCC,"filename":"data/NCC.nii.gz","type":'output'})

        
        

        # get the specialized fnction for the snr calculation
        _SNR_calculator=SNR_calculator[SID]
           
        TASK=[]
        
        #if multiple replicas
        
        # REFERECENCE
        # read the accelerations and autocalibrations
        # read the grappa kernel
        
        #decimate area
        mimic =False
        if "decimate" in reconstructor_dictionary["options"].keys():
            if reconstructor_dictionary["options"]["decimate"]!=None:
                mimic=reconstructor_dictionary["options"]["decimate"]
        #acceleration
        accelleration=None
        autocalibration=None
        grappakernel=[4,4]
        if RID==3:
            if "kernelSize" in reconstructor_dictionary["options"].keys():
                if reconstructor_dictionary["options"]["kernelSize"]!=None:
                    grappakernel=reconstructor_dictionary["options"]["kernelSize"]

        if reconstructor().HasAcceleration:
            if "accelerations" in reconstructor_dictionary["options"].keys():
                if reconstructor_dictionary["options"]["accelerations"]!=None:
                    acceleration=reconstructor_dictionary["options"]["accelerations"]
            else:
                acceleration,_acl=getAccellerationInfo2D(s=reconstructor_dictionary["options"]["signal"])
            
            if "acl" in reconstructor_dictionary["options"].keys():
                if reconstructor_dictionary["options"]["acl"]!=None:
                    autocalibration=reconstructor_dictionary["options"]["acl"]
            else:
                autocalibration=_acl
        
        #sensitivities
        if reconstructor().HasSensitivity:
            sensitivitymethod=reconstructor_dictionary["options"]["sensitivityMap"]["options"]["sensitivityMapMethod"]
            #if b1
            if RID==1:
                reference=[s["KSpace"] for s in  SL]
            elif RID==2:
                if mimic:
                    reference=[None]*len(SL)
                else:
                    
                    reference=getSiemensReferenceKSpace2D(reconstructor_dictionary["options"]["signal"],signal_acceleration_realsize=SL[0]["size"][1],slice='all')
      


        for counter,slice in enumerate(SL):
            O=dict()
            O["signal"]=slice['KSpace']
            O["noise"]=None
            # we are using th NC calculated before instead of passing the noise KSpace
            O["noisecovariance"]=NC
            if reconstructor().HasSensitivity:
                O["reference"]=reference[counter]
            else:
                O["reference"]=None
            
            O["mimic"]=mimic
            if reconstructor().HasAcceleration:
                O["acceleration"]=acceleration
                O["autocalibration"]=autocalibration
            else:
                O["acceleration"]=None
                O["autocalibration"]=None
            if reconstructor().HasAcceleration and not reconstructor().HasSensitivity:
                O["grappakernel"]=grappakernel
            else:
                O["grappakernel"]=None
            O["slice"]=counter
            O["NR"]=NR
            O["boxSize"]=boxSize
            O["reconstructor"]=reconstructor()
            O["savecoilsens"]=args.coilsens
            O["savegfactor"]=args.gfactor
            TASK.append(O)

        if args.parallel:        
            p=mlp.Pool()
            pooled_results=p.map(_SNR_calculator,TASK)
            p.close()

        else:
            pooled_results=[]
            for _t in TASK:
                sn = _SNR_calculator(_t)
                pooled_results.append(sn)

        for slice_results in pooled_results:
            for k in slice_results["images"].keys():
                IDS=[x["id"] for x in IMAOUT]
                r=slice_results["images"]
                if r[k]["id"] not in IDS:
                    DATA=np.zeros((*r[k]["data"].shape,len(TASK)),dtype=r[k]["data"].dtype)
                    DATA[...,slice_results["slice"]]=r[k]["data"]
                    r[k]["data"]=DATA
                    # check if the dtype is complex if it is complex write it i a variablee
                    IMAOUT.append(r[k])

                else:
                    working_id=IDS.index(r[k]["id"])
                    IMAOUT[working_id]["data"][...,slice_results["slice"]]=r[k]["data"]


        IDS=[x["id"] for x in IMAOUT]
        snrid=IDS.index(0)
        if args.verbose:
            plt.figure()
            SNR=IMAOUT[snrid]["data"]
            plt.imshow(np.abs(SNR[:,:,0]))
            plt.title('SNR of the First Slice')
            #remove the xticks and xticklabels from the imshow
            plt.gca().set_xticklabels([])
            plt.gca().set_yticklabels([])
            plt.colorbar()

        
        if len(IMAOUT)>0:
            direction=SL[0]["direction"].flatten()
            spacing=SL[0]["spacing"]
            origin=SL[0]["origin"]
            JO={"headers":{
                "calculation_time":T.stop(),
                "options":J
            },
                "data":[]
            };
            O=pn.Pathable(args.output)
            for im in IMAOUT:
                O.addBaseName(im["filename"])
                O.ensureDirectoryExistence()
                if im["dim"]==3:
                    # saveImage(ima.numpyToImaginable(im["data"]),origin,spacing,direction,O.getPosition())
                    # set nan values to 0
                    im["data"][np.isnan(im["data"])]=0
                    saveImage(ima.numpyToImaginable(im["data"]),origin,spacing,direction,O.getPosition())
                if im["dim"]==2:
                    saveImage(ima.numpyToImaginable(np.expand_dims(np.abs(im["data"]),axis=-1)),fn=O.getPosition())

                O.undo()
              
                pixeltype='real'
                if np.iscomplexobj(im["data"]):
                    pixeltype='complex'
                o={'filename':im["filename"],
                'id':im["id"],
                'dim':im["dim"],
                'name':im["name"],
                'type':im["type"],
                'numpyPixelType':im["data"].dtype.name,
                'pixelType':pixeltype}
                JO["data"].append(o)
                JO["headers"]["log"]=LOG.getLog()
            O.addBaseName('info.json')
            O.writeJson(JO)
        if args.matlab:
            O=pn.Pathable(args.output)
            saveMatlab(O.addBaseName('matlab.mat').getPosition(),IMAOUT)
        LOG.writeLogAs(logfn)
        if args.verbose:
            plt.show()    



# FA=1
# PA=2
# ACLF=20
# ACLP=20
# GK=[3,2]

# L=cm2D.cm2DReconGRAPPA()
# L.AccelerationF=FA
# L.AccelerationP=PA
# L.AutocalibrationF=ACLF
# L.AutocalibrationP=ACLP
# US=cm.undersample2DDatamGRAPPA(S,frequencyacceleration=FA,phaseacceleration=PA,frequencyACL=ACLF,phaseACL=ACLP)
# L.setSignalKSpace(US)
# L.setNoiseKSpace(N)
# L.setGRAPPAKernel(GK)


# L2=cm2D.cm2DSignalToNoiseRatioPseudoMultipleReplicas()

# L2.numberOfReplicas=100
# L2.reconstructor=L

# plt.subplot(121)
# plt.imshow(L2.getOutput(),vmax=250)
# plt.title('PMR')
# plt.colorbar()

# R2=cm2D.cm2DSignalToNoiseRatioPseudoMultipleReplicasWen()
# R=cm2D.cm2DReconRSS()
# R2.numberOfReplicas=5
# R2.boxSize=10
# R.setNoiseKSpace(N)
# R.setSignalKSpace(S)
# R2.reconstructor=R






# plt.subplot(122)
# plt.imshow(R2.getOutput(),vmax=250)
# plt.title('CR')
# plt.colorbar()



# plt.show()








# L2=cm2D.cm2DSignalToNoiseRatioPseudoMultipleReplicas()
# L=cm2D.cm2DReconRSS()
# L2.numberOfReplicas=100
# L.setNoiseKSpace(N)
# L.setSignalKSpace(S)
# L2.reconstructor=L

# plt.subplot(221)
# plt.imshow(L2.getOutput(),vmax=250)
# plt.title('PMR')
# plt.colorbar()

# R2=cm2D.cm2DSignalToNoiseRatioPseudoMultipleReplicasWen()
# R=cm2D.cm2DReconRSS()
# R2.numberOfReplicas=5
# R2.boxSize=10
# R.setNoiseKSpace(N)
# R.setSignalKSpace(S)
# R2.reconstructor=R






# plt.subplot(222)
# plt.imshow(R2.getOutput(),vmax=250)
# plt.title('CR')
# plt.colorbar()

# R=cm2D.cm2DKellmanRSS()
# R.setNoiseKSpace(N)
# R.setSignalKSpace(S)
# plt.subplot(223)
# plt.imshow(R.getOutput(),vmax=250)
# plt.title('Kellman')
# plt.colorbar()


# plt.show()



# FA=1
# PA=2
# ACL=20
# L=cm2D.cm2DReconSense()
# L.AccelerationF=FA
# L.AccelerationP=PA

# US=cm.undersample2DDataSENSE(S,frequencyacceleration=FA,phaseacceleration=PA)

# L.setSignalKSpace(US)
# L.setNoiseKSpace(N)
# L.setCoilSensitivityMatrixSource(S)
# L.setCoilSensitivityMatrixCalculationMethod('inner')

# plt.figure()
# plt.imshow(np.abs(L.getOutput()))
# plt.colorbar()
# plt.title('recon')


# # transform in Kellman!!!
# L.__class__=cm2D.cm2DKellmanSense

# plt.figure()
# plt.imshow(np.abs(L.getOutput()))
# plt.colorbar()
# plt.title('SNR')

# # transform in Kellman!!!
# L.__class__=cm2D.cm2DGfactorSense

# plt.figure()
# plt.imshow(np.abs(L.getOutput()))
# plt.colorbar()
# plt.title('GFactor')
# plt.show()
    


