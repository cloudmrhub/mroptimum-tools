import argparse
from pynico_eros_montin import pynico as pn
from pyable_eros_montin import imaginable as ima
try:
    from mro import *
except:
    from mroptimum.mro import *
import cloudmrhub.cm2D as cm2D


import cloudmrhub.cm as cm


def savematlab(fn,vars):
    J=dict()
    for n,v in vars:
        J[n]=v
    scipy.io.savemat(fn,J)
   
    


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

        if J["acquisition"]!=2:
            LOG.appendError('acquisition is not 2D')
            LOG.writeLogAs(logfn)
            raise Exception("sorry only 2D k-space")
        
        #which reconstructor has been requested
        R=J["options"]["reconstructor"]
        RID=RECON.index(R["name"].lower())
        SID=SNR.index(J["name"].lower())
        
        #how many slices
        if R["options"]["signal"]["options"]["vendor"].lower()=='siemens':
            SL=getSiemensKSpace2DInformation(R["options"]["signal"])
        else:
            LOG.appendError('filetype unknown')
            LOG.writeLogAs(logfn)
            raise Exception(' this version of SNR tool only works with siemens file at the moment')
        # if it's analitical    
        if (SID==0) and (RID<5):
            THERECON=KELLMAN_classes[RID]
        else:
            #otherwise i go with the other methods of snr
            THERECON=RECON_classes[RID]
        NN=cm2D.cm2DRecon()
        LOG.append('reconstructor set')
        NOISE=getNoiseKSpace(R["options"]["noise"],'all')
        BN=NOISE[0]
        for tn in range(1,len(NOISE)):
            BN=np.concatenate((BN,NOISE[tn]),axis=1)
        LOG.append('Noise Covariance calculated')
        NN.setNoiseKSpace(BN)
        NC=NN.getNoiseCovariance()
        if args.verbose:
            plt.show()
            plt.imshow(np.abs(NC))
            plt.title('Noise Covariance Matrix')
            
        SNR=np.zeros((*SL[0]['size'][:2],len(SL)))
        TASK=[]
            #instantiate the recon
        ac=False
        
        for counter,slice in enumerate(SL):
            r=THERECON()
            S=slice['KSpace']
            r.setNoiseCovariance(NC)
            if r.HasAcceleration:
                r.AccelerationF,r.AccelerationP=[1,1]
                if R["options"]["accelerations"]!=None:
                    r.AccelerationF,r.AccelerationP=R["options"]["accelerations"]
                LOG.append(f'Acceleration set to {R["options"]["accelerations"]}' )
            if ((r.HasAcceleration) and (R["options"]["decimate"])):
                UK,ac=undersample(S,R)
                r.setSignalKSpace(UK)
                LOG.append(f'Mimicked an accelaration of {R["options"]["decimate"]}')
            else:
                r.setSignalKSpace(S)
            if ac:
                r.setAutocalibrationLines(R["options"]["acl"])
                LOG.append(f'Autocalibration Lines set to {R["options"]["acl"]}' )
            if r.HasSensitivity:
                r.setCoilSensitivityMatrixCalculationMethod(R["options"]["sensitivityMap"]["name"])
                LOG.append(f'Sensitivity Map calculation method set to {R["options"]["sensitivityMap"]["name"]}' )
            if ((r.HasAcceleration) and (not r.HasSensitivity)):
                # this is grappa:
                if R["options"]["kernelSize"]!=None:
                    r.setGrappaKernel(R["options"]["kernelSize"])
                else:
                    r.setGrappaKernel([5,4])
                LOG.append(f'Grappa Kernel set to {r.GrappaKernel}' )

            if SID==0:
                TASK.append(manalitical(r,counter))  

            else:
                SN=SNR_classes[SID]
                s=SN()

                try:
                    NR=J["options"]["NR"]
                except:
                    NR=None

                try:
                    boxSize=J["options"]["boxSize"]
                except:
                    boxSize=None
                
                TASK.append(mreplicas(r,s,NR,boxSize,counter))

        if args.parallel:        
            p=mlp.Pool()
            dd=p.map(rT,TASK)
            p.close()
            for sn,cc in dd:
                SNR[:,:,cc]=np.abs(sn)
        else:
            for _t in TASK:
                sn,cc = rT(_t)
                SNR[:,:,cc]=np.abs(sn)
                print(cc)

        NN=np.isnan(SNR)
        LOG.append(f'{np.count_nonzero(NN)} NaN are now 0 over the {np.prod(SNR.shape)} voxels' )
        SNR[NN]=0
        LOG.append(f'{len(TASK)} slices calculated' )


        if args.verbose:
            plt.figure()
            plt.imshow(np.abs(SNR[:,:,0]))
            plt.title('First Slice SNR')
            plt.colorbar()

        
        if args.output:
            M.append(["NoiseCovariance",NC])
            IMAOUT.append([0,2,"Noise Covariance",ima.numpyToImaginable(np.expand_dims(np.abs(NC),axis=-1)),'data/NC.nii.gz','output'])
            ISNR=ima.numpyToImaginable(SNR)
            IMAOUT.append([1,3,"SNR",ISNR,'data/snr.nii.gz','output'])
            M.append(["SNR",SNR])

        if args.coilsens:
            if r.HasSensitivity:
                SENS=np.zeros((*S.shape[0:2],len(TASK), S.shape[-1]),dtype=S.dtype)
                
                for ic,ia in enumerate(TASK):
                    SENS[:,:,ic,:]=ia.reconstructor.getCoilSensitivityMatrix()
                M.append(["Sensitivitymaps",SENS])
                for nn in range(SENS.shape[-1]):
                    IMAOUT.append([2,3,f"Coil Sensitivity Map {nn:02d}",ima.numpyToImaginable(np.abs(SENS[:,:,:,nn])),f'data/coilsens{nn:02d}.nii.gz','accessory'])
                LOG.append(f'Sensitivity maps are saved to file' )

        
        if args.gfactor:
            if ((r.HasAcceleration) and (r.HasSensitivity)):
                G=np.zeros_like(SNR)
                for ic,ia in enumerate(TASK):
                    ia.reconstructor.__class__=G_classes[RID]
                    G[:,:,ic]=np.abs(ia.reconstructor.getOutput())
                IMAOUT.append([3,3,"G-Factor",ima.numpyToImaginable(G),'data/gfactor.nii.gz','accessory'])
                M.append(["G-factor",G])
                LOG.append(f'G-factor saved to file' )

        
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
            for id,dim,n,imm,pos,access in IMAOUT:
                O.addBaseName(pos)
                O.ensureDirectoryExistence()
                if dim==3:
                    saveImage(imm,origin,spacing,direction,O.getPosition())
                if dim==2:
                    saveImage(imm,fn=O.getPosition())

                O.undo()
                o={'filename':pos,
                'id':id,
                'dim':dim,
                'name':n,
                'type':access}
                JO["data"].append(o)
                JO["headers"]["log"]=LOG.getLog()
            O.addBaseName('info.json')
            O.writeJson(JO)
        if args.matlab:
            O=pn.Pathable(args.output)
            savematlab(O.addBaseName('matlab.mat').getPosition(),M)
        LOG.writeLogAs(logfn)
        if args.verbose:
            plt.show()    



# FA=1
# PA=2
# ACLF=20
# ACLP=20
# GK=[3,2]

# L=cm2D.cm2DReconGrappa()
# L.AccelerationF=FA
# L.AccelerationP=PA
# L.AutocalibrationF=ACLF
# L.AutocalibrationP=ACLP
# US=cm.undersample2DDatamGRAPPA(S,frequencyacceleration=FA,phaseacceleration=PA,frequencyACL=ACLF,phaseACL=ACLP)
# L.setSignalKSpace(US)
# L.setNoiseKSpace(N)
# L.setGrappaKernel(GK)


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
    


