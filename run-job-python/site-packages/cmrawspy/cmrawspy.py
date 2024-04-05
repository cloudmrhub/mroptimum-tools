import uuid
import boto3
from pynico_eros_montin import pynico as pn
import shutil

import scipy

def getAwsCredentials(credentialsfn='~/.aws/credentials'):
    with open(credentialsfn) as f:
        lines = f.readlines()
    AWS_ACCESS_KEY = lines[1].strip()[len('aws_access_key_id')+1:]
    AWS_SECRET_KEY = lines[2].strip()[len('aws_secret_access_key')+1:]
    AWS_SESSION_TOKEN = lines[3].strip()[len('aws_session_token')+1:]   
    # aws_session_token = lines[3].strip()
    return AWS_ACCESS_KEY, AWS_SECRET_KEY,AWS_SESSION_TOKEN

def getS3Resource(aws_access_key_id, aws_secret_access_key,aws_session_token):
    return boto3.resource('s3',
                             aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key,
                             aws_session_token=aws_session_token)

def getS3ResourceFromCredentials(credentialsfn='~/.aws/credentials'):
    AWS_ACCESS_KEY, AWS_SECRET_KEY,AWS_SESSION_TOKEN = getAwsCredentials(credentialsfn)
    return getS3Resource(AWS_ACCESS_KEY, AWS_SECRET_KEY,AWS_SESSION_TOKEN)

def saveMatlab(fn,vars):
    J=dict()
    for k in vars:
        J[k["name"].replace(" ","")]=k["data"]
    scipy.io.savemat(fn,J)

def s3FileTolocal(J, s3=None, pt="/tmp"):
    key = J["key"]
    bucket = J["bucket"]
    filename = J["filename"]
    O = pn.Pathable(pt)
    O.addBaseName(filename)
    O.changeFileNameRandom()
    f = O.getPosition()
    downloadFileFromS3(bucket,key,f, s3)
    J["filename"] = f
    J["type"] = "local"
    return J

def getBucketAndKeyIdFromUplaodEvent(event):
    """
    Args:
        event (_type_): _description_
    Returns:
        bucket_name (str): bucket name
        file_key (str): file key identifier
    """
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    file_key = event["Records"][0]["s3"]["object"]["key"]
    return bucket_name, file_key

def downloadFileFromS3(bucket_name,file_key,outfile=None, s3=None):
    """
    Args:
        bucket_name (str): bucket name
        file_key (str): file key identifier
        outfile (str): output file name
        s3 (_type_): the s3 resource
    Returns:
        filename (str): output file name
    """
    if s3 == None:
        s3 = boto3.resource("s3")
    if outfile == None:
        outfile = pn.createRandomTemporaryPathableFromFileName(file_key).getPosition()
    s3.Bucket(bucket_name).download_file(file_key, outfile)
    return outfile

def uploadFiletoS3(filename,bucket_name,file_key=None, s3=None):
    if s3 == None:
        s3 = boto3.resource("s3")
    if file_key == None:
        file_key = pn.Pathable(filename).addSuffix(f'-{str(uuid.uuid1())}').getBaseName()
    
    s3.Bucket(bucket_name).upload_file(filename, file_key)
    return {"bucket": bucket_name, "key": file_key}



def getCMRFile(filedict,s3=None):
    """    
    Args:
        s (dict): {
                "type": "file",
                "id": -1,
                "options": {
                    "type": "local",
                    "filename": "/data/MYDATA/TESStestData/Density.nii.gz",
                    "options": {}
                }
            }
    Returns:
      fn (str): position of the file in the local filesystem
    """
    s=filedict["options"]
    if (s["type"].lower()=='local'):
        return s["filename"]
    elif (s["type"].lower()=='s3'):
        T=pn.createRandomTemporaryPathableFromFileName(s["filename"]).getPosition()
        T=downloadFileFromS3(s["bucket"],s["key"],T,s3=s3)
        return T
    else:
        raise Exception("I can't get this file modality")

import pyable_eros_montin.imaginable as ima      
import numpy as np

class cmrOutput:
    def __init__(self,app=None,filename=None,path=None,s3=None):
            self.out={"headers":{"options":{}},"data":[]}
            if filename!=None:
                self.outputfilename=pn.Pathable(filename)
            else:
                self.outputfilename=pn.createRandomTemporaryPathableFromFileName("a.zip")
            
            self.outputfilename.ensureDirectoryExistence()
            if path==None:
                self.outputpath=pn.createRandomTemporaryPathableFromFileName(self.outputfilename.getPosition()).appendPathRandom()
            else:
                self.outputpath=pn.Pathable(path)
            self.outputpath.ensureDirectoryExistence()
            self.outputfilename.ensureDirectoryExistence()
            self.setApp(app)
            self.forkable=self.outputpath.fork()
            self.forkable.addBaseName("data")
            self.savematlab=True          

    
    def addAbleFromFilename(self,filename,id,name,type="output"):
        L=ima.Imaginable(filename=filename)
        N=pn.Pathable(filename)
        o=self.addAble(L,id,name,type,N.getBaseName())
        o["filename"]=filename
        return o
        
    def addAble(self,L,id,name,type="output",basename=None):
        pixeltype='real'
        im=L.getImageAsNumpy()

        if np.iscomplexobj(im):
            pixeltype='complex'
            L.setImageFromNumpy(im.astype(np.singlecomplex))
        if basename==None:
            basename=pn.createRandomTemporaryPathableFromFileName("a.nii.gz").getBaseName()
        o={'filename':None,
           'basename':basename,
           'able':L,
                'id':id,
                'dim':L.getImageDimension(),
                'name':name,
                'type':type,
                'numpyPixelType':im.dtype.name,
                'pixelType':pixeltype}
        
        self.out["data"].append(o)
        return o
    
    def setHeader(self,a={}):
        for k in a.keys():
            self.out["headers"][k]=a[k]
    def setPipeline(self,a):
        if "options" not in self.out["headers"].keys():
            self.out["headers"]["options"]={}
        self.out["headers"]["options"]["pipeline"]=a
        self.out["headers"]["options"]["pipelineid"]=a

    def setToken(self,a):
        if "options" not in self.out["headers"].keys():
            self.out["headers"]["options"]={}
        self.out["headers"]["options"]["token"]=a
    def setLog(self,a):
        l=self.forkable.fork()
        l.changeBaseName("log.json")
        a.writeLogAs(l.getPosition())
        self.out["log"]=a.getLog()

    def setApp(self,a):
        self.out["app"]=a
    def setTask(self,a):
        l=self.forkable.fork()
        l.changeBaseName("task.json")
        l.writeJson(a)

    
    def setOptions(self,a):
        for k in a.keys():
            self.out["headers"]["options"][k]=a[k]
        l=self.forkable.fork()
        l.changeBaseName("options.json")
        l.writeJson(a)

    def setEvent(self,a):
        l=self.forkable.fork()
        l.changeBaseName("event.json")
        l.writeJson(a)

    def exportResults(self):
        outputdirectory=self.outputpath.getPath()
        #check id the data are in the expected directory
        J=[]
        for d in self.out["data"]:
            theo= outputdirectory+"/data/"+d["basename"]
            pn.Pathable(theo).ensureDirectoryExistence()

            if d["filename"]==None:
                d["able"].writeImageAs(theo)
            
            elif d["filename"]!=theo:
                shutil.copy(d["filename"],theo)
            d["filename"]="data/"+d["basename"]
            
            if self.savematlab:
                J.append({"name":d["name"],"data":d["able"].getImageAsNumpy()})
            if "able" in d.keys():
                del d["able"]
            # if "basename" in d.keys():
            #     del d["basename"]

        #write the json file
        OUT=self.forkable.fork()
        OUT.changeBaseName("info.json")
        OUT.writeJson(self.out)
        OUT.changeBaseName("matlab.mat")
        saveMatlab(OUT.getPosition(),J)

    def changeOutputPath(self,path):
        #copy the data to the new path
        shutil.copytree(self.outputpath.getPosition(),path)
        shutil.rmtree(self.outputpath.getPosition())          
        self.outputpath=pn.Pathable(path)
        self.outputpath.ensureDirectoryExistence()
        self.forkable=self.outputpath.fork()
        self.forkable.addBaseName("data.nii.gz")
        
        return self.outputpath.getPosition()


    def exportAndZipResults(self,outzipfile=None,delete=False):
        p=self.exportResults()
        if outzipfile==None:
            outzipfile=self.outputfilename.getPosition()
        print(f"{ self.outputpath.getPosition()} - {p} -{outzipfile}")
        ext=pn.Pathable(outzipfile).getExtension()
        print(ext)
        fi=outzipfile.replace(f'.{ext}',"")
        print(fi,ext)
        shutil.make_archive(fi,ext , self.outputpath.getPosition())
        if delete:
            shutil.rmtree(self.outputpath.getPosition())
        return outzipfile
    
    def exportAndZipResultsToS3(self,bucket,key=None,outzipfile=None,delete=False,deletezip=False,s3=None):
        p=self.exportAndZipResults(outzipfile=outzipfile,delete=delete)
        print(f"file {p} will be upladed to {bucket}/{key}")
        O= uploadFiletoS3(p,bucket,key,s3=s3)
        if deletezip:
            shutil.rmtree(p)
        return O
    


if __name__ == "__main__":

#dowbload file
        # J=pn.Pathable("data/s3job.json").readJson()
        # T=J["task"]
        # OPT=T["options"]
        # MATLAB=J["output"]["matlab"]
        # s3=getS3ResourceFromCredentials('/home/eros/.aws/credentials')
        # md=getCMRFile(OPT["materialDensity"],s3=s3)
        # print(md)

## bucket and key
    # event=pn.readJson("data/event.json")
    # job_bucket, job_file_key = getBucketAndKeyIdFromUplaodEvent(event)
    # print(job_bucket, job_file_key)


# OUPUT
    a=ima.Imaginable()
    b=ima.Imaginable()
    a.setImageFromNumpy(np.random.random((10,10,10)))
    b.setImageFromNumpy(np.random.random((10,10,10)))



    R=cmrOutput("TESS","/g/zzz.zip",'/g/aaa/')
    # Create a session
    # read aws credentials from a file
    AWS_ACCESS_KEY, AWS_SECRET_KEY,AWS_SESSION_TOKEN = getAwsCredentials('/home/eros/.aws/credentials')

    s3=getS3Resource(AWS_ACCESS_KEY, AWS_SECRET_KEY,AWS_SESSION_TOKEN)
    

    R.addAble(a,1,"test",basename="test.nii.gz")
    R.addAble(a,1,"test2",basename="test2.nii.gz")
    R.addAbleFromFilename("/g/SAR2.nii.gz",3,"test3")
    R.setApp("TESS")
    R.setToken("dede")
    R.setPipeline("dedde")
    L=pn.Log()
    L.append("test")
    L.append("test2")
    R.setLog(L)
    R.changeOutputPath("/g/bbb/")
    R.setTask({"id":1,
    "name":"test"})
    R.setOptions({"id":1,'ded':'rrr'})

    R.changeOutputPath("/g/aa2ea/")
    R.setEvent({"id":1})
    # R.exportAndZipResults(outzipfile='/g/zzz.zip',delete=False)
    # R.exportAndZipResults(delete=True)
    o=R.exportAndZipResultsToS3(delete=True,s3=s3,bucket="mytestcmr")
    print(o)



    


    
    
                

    

            

