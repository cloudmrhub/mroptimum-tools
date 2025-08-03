import argparse
from pynico_eros_montin import pynico as pn
from pyable_eros_montin import imaginable as ima

try:
    from mro import *
    V='local'
except:
    from mrotools.mro import *
    V="pip"
import cmtools.cm2D as cm2D


import cmtools.cm as cm
import os


#read debug from environment and put it to false if not present
debug=os.getenv('DEBUG',False)
   
def getAccellerationInfo2D(s,raid=1):
    N=pn.Pathable(getFile(s))
    n=N.getPosition()
    twix=twixtools.map_twix(n)
    H=twix[raid]["hdr"]
    iPat=H['MeasYaps']['sPat']
    return [1,int(iPat['lAccelFactPE'])],[np.nan,int(iPat['lRefLinesPE'])]



if __name__=="__main__":
    parser = argparse.ArgumentParser(
                        prog='Mr Optimum',
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
        LOG=pn.Log("SNR calculation",{"packages":getPackagesVersion()})
        if args.loutput ==None:
            args.loutput=pn.createRandomTemporaryPathableFromFileName('a.log').getPosition()
        logfn=args.loutput
        M=[]
        IMAOUT=[]
        #check version of the option json file
        if J["version"]!="v0":
            LOG.appendError(f"wrong json options ({J['version']})")
            LOG.writeLogAs(logfn)
            raise Exception("options file is not v0")
        LOG.append("options json file validated it's v0")

        #this version only works with 2D K-Space
        if J["acquisition"]!=2:
            LOG.appendError('acquisition is not 2D')
            LOG.writeLogAs(logfn)
            LOG.append('acquisition is 2D')
            LOG.appendError('acquisition is not 2D')
            raise Exception("sorry only 2D K-Space")
        LOG.append('acquisition is 2D')
        try:
            #which reconstructor has been requested
            reconstructor_dictionary=J["options"]["reconstructor"]
            
            #recon id
            RID=RECON.index(reconstructor_dictionary["name"].lower())
            LOG.append(f'reconstructor is {reconstructor_dictionary["name"]} - RID={RID}')
            #snr id
            SID=SNR.index(J["name"].lower())
            #reconstruction classes
            reconstructor=RECON_classes[RID]
            #if the snr is analytical
            # SID= SNR ID, RID = RECONSTRUCTOR ID
            if SID==0:
                reconstructor=KELLMAN_classes[RID]
            LOG.append(f'Reconstructor class is {reconstructor.__name__}')
            NR=None
            if SID>1:
                NR=J["options"]["NR"]

            
            
            boxSize=None
            if SID>2:
                boxSize=J["options"]["boxSize"]      
            
            LOG.append(f'SNR is {J["name"]} - SID={SID}')
            LOG.append('reconstructor and SNR are set')

            LOG.append('Signal K-Space reading')
            #how many slices // CHANGE here for others vendors
            if reconstructor_dictionary["options"]["signal"]["options"]["vendor"].lower()=='siemens':
                MR=(SID==1)
                SL=getSiemensKSpace2DInformation(reconstructor_dictionary["options"]["signal"],signal=True,MR=MR)
                if isinstance(SL,str):
                    LOG.appendError(SL)
                    LOG.writeLogAs(logfn)
                    raise Exception(SL)
            else:
                LOG.appendError('filetype unknown')
                LOG.appendError('this version of SNR tool only works with siemens file at the moment')
                LOG.writeLogAs(logfn)
                raise Exception(' this version of SNR tool only works with siemens file at the moment')
            #intialize the output array (id,dimension,UI name,imaginable,fn,outputtype)
            
            LOG.append('Signal K-Space read')
            IMAOUT=[]
            LOG.append('Noise K-Space reading')
            # calculates the noise statistics
            NOISE=None
            #noise file
            if "noise" in reconstructor_dictionary["options"].keys():
                NOISE=getNoiseKSpace(reconstructor_dictionary["options"]["noise"],'all')
            # multiraid in signal
            if(reconstructor_dictionary["options"]["signal"]["options"]["vendor"].lower()=='siemens') and (reconstructor_dictionary["options"]["signal"]["options"]["multiraid"])    :
                NOISE=getNoiseKSpace(reconstructor_dictionary["options"]["signal"],'all')
            
            LOG.append('Noise K-Space read')
            # if no noise file is provided
            if NOISE==None:
                NC=None
                NCC=None
            else:
                NC,NCC=calculteNoiseCovariance(NOISE,args.verbose)
                IMAOUT.append({"id":1,"dim":2,"name":"Noise Covariance","data":NC,"filename":'data/NC.nii.gz',"type":'output'})
                IMAOUT.append({"id":2,"dim":2,"name":"Noise Coefficients","data":NCC,"filename":"data/NCC.nii.gz","type":'output'})

            # get the specialized function for the snr calculation
            _SNR_calculator=SNR_calculator[SID]
            
            TASK=[]
                    
            #decimate area
            mimic =False
            if "decimate" in reconstructor_dictionary["options"].keys():
                if reconstructor_dictionary["options"]["decimate"]!=None:
                    mimic=reconstructor_dictionary["options"]["decimate"]
            LOG.append(f'decimate is {mimic}')

            #acceleration
            accelleration=None
            autocalibration=None
            grappakernel=[4,4]
            if RID==3: #if grappa
                if "kernelSize" in reconstructor_dictionary["options"].keys():
                    if reconstructor_dictionary["options"]["kernelSize"]!=None:
                        grappakernel=reconstructor_dictionary["options"]["kernelSize"]
                LOG.append(f'grappakernel is {grappakernel}')

            if reconstructor().HasAcceleration:
                if "accelerations" in reconstructor_dictionary["options"].keys():
                    if reconstructor_dictionary["options"]["accelerations"]!=None:
                        acceleration=reconstructor_dictionary["options"]["accelerations"]
                else:
                    acceleration,_acl=getAccellerationInfo2D(s=reconstructor_dictionary["options"]["signal"])
                    
                LOG.append(f'acceleration is {acceleration}')
                if "acl" in reconstructor_dictionary["options"].keys():
                    if reconstructor_dictionary["options"]["acl"]!=None:
                        autocalibration=[np.nan if v is None else v for v in reconstructor_dictionary["options"]["acl"]]
                else:
                    autocalibration=_acl
                    if RID==3:
                        autocalibration=[_acl[1], _acl[1]]
                LOG.append(f'autocalibration is {autocalibration}')
            #sensitivities
            
            #grappa
            if RID==3 and not mimic:
                reference=getSiemensReferenceKSpace2D(reconstructor_dictionary["options"]["signal"],signal_acceleration_realsize=SL[0]["size"][1],slice='all')

            if reconstructor().HasSensitivity:
                sensitivitymethod=reconstructor_dictionary["options"]["sensitivityMap"]["options"]["sensitivityMapMethod"]
                #if b1
                if RID==1:
                    reference=[s["KSpace"] for s in  SL]
                elif RID==2:
                    if mimic:
                        if sensitivitymethod=="inner":
                            reference=[s["KSpace"] for s in  SL]
                        else:
                            reference=[None]*len(SL)
                    else:                    
                        reference=getSiemensReferenceKSpace2D(reconstructor_dictionary["options"]["signal"],signal_acceleration_realsize=SL[0]["size"][1],slice='all')
                else:
                    LOG.appendError('sensitivity method not implemented')
                    LOG.appendError('this version of SNR tool only works with inner and outer sensitivity method at the moment')
                    LOG.writeLogAs(logfn)

                LOG.append(f'sensitivity method is {sensitivitymethod}')

            #decimate area
            mask =[False]*len(SL)
            if reconstructor().HasSensitivity:
                SENSOPTIONS=reconstructor_dictionary["options"]["sensitivityMap"]["options"]
                
                if "mask" in SENSOPTIONS.keys():
                    mask=[SENSOPTIONS["mask"]]*len(SL)
                    if not isinstance(mask[0],str):
                        if 'method' in mask[0].keys():
                            if mask[0]["method"]=='upload':
                                F=getFile(mask[0]["file"])
                                if (pn.Pathable(F).getExtension()=="nii") or (pn.Pathable(F).getExtension()=="nii.gz") or (pn.Pathable(F).getExtension()=="mha") or (pn.Pathable(F).getExtension()=="mhd")  or (pn.Pathable(F).getExtension()=="mat")  or (pn.Pathable(F).getExtension()=="json"): 
                                    # in this case i am going to read the mask and creating a multi slice 2d mask
                                    m=ima.Imaginable(F)
                                    mask=m.getImageAsNumpy()
                                    mask=mask>0
                                    mask=mask.astype(np.uint8)
                                    if len(mask.shape)==2:
                                        mask=[mask for i in range(len(SL))]
                                    if len(mask.shape)==3:
                                        if mask.shape[2]==len(SL):
                                            mask=[mask[...,i] for i in range(mask.shape[2])]
                                        elif mask.shape[2]==1:
                                            mask=[mask for i in range(len(SL))]
                                
            LOG.append(f'mask is {mask}')

            LOG.append('start the calculation')
        
            for counter,slice in enumerate(SL):
                O=dict()
                O["signal"]=slice['KSpace']
                O["noise"]=None
                # we are using th NC calculated before instead of passing the noise KSpace
                O["noisecovariance"]=NC
                if (reconstructor().HasSensitivity or (RID==3 and not mimic)):
                    O["reference"]=reference[counter]
                else:
                    O["reference"]=None
                O["mask"]=mask[counter]
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
            T=pn.Timer()
            if args.parallel:
                #get the number of cpus

                num_cpus = mlp.cpu_count()
                if num_cpus>len(TASK):
                    num_cpus=len(TASK)
                LOG.append(f'number of cpus {num_cpus}')                        
                p=mlp.Pool(num_cpus)
                pooled_results=p.map(_SNR_calculator,TASK)
                p.close()

            else:
                pooled_results=[]
                for _t in TASK:
                    sn = _SNR_calculator(_t)
                    pooled_results.append(sn)
            LOG.append(f'calculation time {T.stop()}')
            LOG.append('start gathering the output')
            for slice_results in pooled_results:
                for k in slice_results["images"].keys():
                    IDS=[x["id"] for x in IMAOUT]
                    r=slice_results["images"]
                    if r[k]["id"] not in IDS:
                        DATA=np.zeros((*r[k]["data"].shape,len(TASK)),dtype=r[k]["data"].dtype)
                        DATA[...,slice_results["slice"]]=r[k]["data"]
                        r[k]["data"]=DATA
                        # check if the dtype is complex if it is complex write it i a variable
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
                
                IMAOUT = sorted(IMAOUT, key=lambda x: x["id"])

                for im in IMAOUT:
                    O.addBaseName(im["filename"])
                    O.ensureDirectoryExistence()
                    pixeltype='real'
                    if debug:
                        im["data"]=np.abs(im["data"])
                    if np.iscomplexobj(im["data"]):
                        pixeltype='complex'
                        im["data"]=im["data"].astype(np.complex64)
                    im["data"][np.isnan(im["data"])]=0
                    im["data"][np.isinf(im["data"])]=0
                  
                    if im["dim"]==3:
                        # saveImage(ima.numpyToImaginable(im["data"]),origin,spacing,direction,O.getPosition())
                        # set nan values to 0
                        
                        saveImage(ima.numpyToImaginable(im["data"]),origin,spacing,direction,O.getPosition())
                    if im["dim"]==2:
                        saveImage(ima.numpyToImaginable(np.expand_dims(im["data"],axis=-1)),fn=O.getPosition())

                    O.undo()


                    o={'filename':im["filename"],
                    'id':im["id"],
                    'dim':im["dim"],
                    'name':im["name"],
                    'type':im["type"],
                    'numpyPixelType':im["data"].dtype.name,
                    'pixelType':pixeltype}
                    JO["data"].append(o)
                    
                O.addBaseName('info.json')
                
                JO["info"]={"calculation_time":T.stop(),"slices":len(SL)}

            if args.matlab:
                O2=pn.Pathable(args.output)
                cm.saveMatlab(O2.addBaseName('matlab.mat').getPosition(),IMAOUT)
                LOG.append('matlab file saved')
            
            
            if args.verbose:
                plt.show()  
            LOG.append('end of the calculation',"END")
            JO["headers"]["log"]=LOG.getLog()
            O.writeJson(JO)
            LOG.writeLogAs(logfn)          

        except Exception as e:
            import traceback
            LOG.appendError(f'Error: {e}')
            LOG.appendError(traceback.format_exc())
            LOG.appendError()
            LOG.writeLogAs(logfn)
            raise e


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
    


