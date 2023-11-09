import argparse
from pynico_eros_montin import pynico as pn
try:
    from mro import RECON,SNR
except:
    from mroptimum.mro import RECON,SNR


def thefileS3(fn=None,signal=None,noise=None):
    J={
        "type":"s3",
        "filename":None,
        "key":None,
        "bucket":None
    }
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J



def thefile(fn=None,f='/youtpath/to/the/file.dat'):
    J={
        "type":"local",
        "filename":f,
        "options":{}
    }
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J


def theK(fn=None,f='/youtpath/to/the/file.dat'):
    J={
        "type":"file",
        "options":thefile(fn=fn,f=f)

        
    }
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J

def theSignalSiemens(fn=None,f='/youtpath/to/the/file.dat'):
    J=theK(fn=None,f=f)
    J["options"]["multiraid"]=False
    J["options"]["vendor"]="Siemens"
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J



def theNoiseSiemensMultiraid(fn=None,f='/youtpath/to/the/file.dat'):
    J=theK(fn=None,f=f)
    J["options"]["multiraid"]=True
    J["options"]["vendor"]="Siemens"
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J

def generatePMR(fn=None,reconstructor=None,J0=None):
    J={
        "type":"SNR",
        "id":2,
        "name":"PMR",
        "options":{
            "NR":100,
            "reconstructor":reconstructor
        }
    }
    if J0 is not None:
        J = {**J0, **J}
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J


def generateCR(fn=None,reconstructor=None,J0=None):
    J={
        "type":"SNR",
        "id":3,
        "name":"CR",
        "options":{
            "NR":5,
            "reconstructor":reconstructor,
            "boxSize":2
        }
    }
    if J0 is not None:
        J = {**J0, **J}
 
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J

def generateMR(fn=None,reconstructor=None,J0=None):
    J={
        "type":"SNR",
        "id":1,
        "name":"MR",
        "options":{
            "reconstructor":reconstructor,
        }
    }
    if J0 is not None:
        J = {**J0, **J}
 
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J



def reconRSS(fn=None,signal=None,noise=None):
    J={
        "type":"recon",
        "id":1,
        "name":'RSS',
        "options":{
            "noise":theNoiseSiemensMultiraid(fn=fn,f=noise),
            "signal":theSignalSiemens(fn=fn,f=signal),
        }
    }
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J



def sensitivityMapsInner(fn=None,f='/youtpath/to/the/file.dat'):
    J={
        "type":"sensitivityMap",
        "id":1,
        "name":"inner",
        "options":{
            "sensitivityMapSource":theK(fn=fn,f=f),
            "sensitivityMapMethod":"innner",
            }
        }

    if fn:
        pn.Pathable(fn).writeJson(J)
    return J

    
def sensitivityMapsInnerACL(fn=None,f='/youtpath/to/the/file.dat'):
    J=sensitivityMapsInner(fn=None,f=f)
    J["id"]=2
    J["name"]="innerACL"
    J["options"]["sensitivityMapMethod"]="innerACL"

    if fn:
        pn.Pathable(fn).writeJson(J)
    return J
    
def generateKellman(fn=None,reconstructor=None,J0=None):
    J={
        "type":"SNR",
        "id":0,
        "name":"AC",
        "options":{
            "reconstructor":reconstructor,
        }
    }
   
    if J0 is not None:
        J = {**J0, **J}
 
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J


def reconB1(fn=None,signal=None,noise=None):
    J={
        "type":"recon",
        "name":"B1",
        "id":2,
        "options":{
            "type":"B1",
            "noise":theNoiseSiemensMultiraid(fn=fn,f=noise),
            "signal":theSignalSiemens(fn=fn,f=signal),
            "sensitivityMap":sensitivityMapsInner(fn=fn,f=signal)
        }
    }
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J

def reconSense(fn=None,signal=None,noise=None):
    J={
        "type":"recon",
        "name":"Sense",
        "id":3,
        "options":{
            "noise":theNoiseSiemensMultiraid(fn=fn,f=noise),
            "signal":theSignalSiemens(fn=fn,f=signal),
            "sensitivityMap":sensitivityMapsInner(),
            "decimate":True,
            "accelerations":[1,1],
        }
    }
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J


def reconmSense(fn=None,signal=None,noise=None):
    J=reconSense(fn=None,signal=signal,noise=noise)
    J["name"]='mSense'
    J["id"]=4
    J["options"]["sensitivityMap"]=sensitivityMapsInnerACL()
    J["options"]["acl"]=[20,20]

    if fn:
        pn.Pathable(fn).writeJson(J)
    return J


def reconGrappa(fn=None,signal=None,noise=None):
    J=reconmSense(fn=None,signal=signal,noise=noise)
    J["name"]='Grappa'
    J["id"]=5
    del J["options"]['sensitivityMap']
    J["options"]["kernelSize"]=[4,4]
    if fn:
        pn.Pathable(fn).writeJson(J)
    return J

def start(acquisition=2):
    return {"version":"v0",
       "acquisition":acquisition
       }


RECON_g=[reconRSS,reconB1,reconSense,reconmSense,reconGrappa]

SNR_g=[generateKellman,generateMR,generatePMR,generatePMR]

if __name__=="__main__":
    parser = argparse.ArgumentParser(
                        prog='Mroptimum',
                        description='Calculates SNR as it should be done!',
                        epilog='cloudmrhub.com')


    parser.add_argument('-t','--typeofsnr', choices=SNR,type=str, help='type of snr')
    parser.add_argument('-a','--acquisition', choices=[2,3],type=int, help='kspace acquisition dimension',default=2)
    parser.add_argument('-r','--reconstructions', choices=RECON,type=str, help='type of trteconstructions')
    parser.add_argument('-s','--signal',type=str, help='signal file')
    parser.add_argument('-n','--noise', type=str, help='noise file')
    parser.add_argument('-j','--joptions', type=str, help='optionfile with the backbone of the calculation that will be written')
    parser.add_argument('-m','--multiraid', type=bool, help='Are Data multiraid',default=False)
    args = parser.parse_args()

    J=start(args.acquisition)
    # reconstructor index
    RID=RECON.index(args.reconstructions)
    # reconstruction function
    RF=RECON_g[RID]
    
    
    # reconstructor index
    SID=SNR.index(args.typeofsnr)
    # reconstruction function
    SF=SNR_g[SID]
    pn.Pathable(args.joptions).ensureDirectoryExistence()
    SF(fn=args.joptions,reconstructor=RF(fn=None,signal=args.signal,noise=args.noise),J0=J)
    print(f"option file correctly written in {args.joptions} for a ", SF.__name__.replace('generate',''), "SNR and ", RF.__name__, "reconstructor")




        
    
