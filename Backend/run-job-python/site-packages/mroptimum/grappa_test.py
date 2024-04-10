# # import multiprocessing

# # def job(num):
# #     return num * 2
# # p = multiprocessing.Pool(processes=5)
# # data = p.map(job, [i for i in range(20)])
# # p.close()
# # print(data)
# import os
# import boto3

# import shutil

# mroptimum_result="mroptimum-result"

# def s3FileTolocal(J,s3=None,pt="/tmp"):
#     key=J["key"]
#     bucket=J["bucket"]
#     filename=J["filename"]
#     if s3==None:
#         ID=os.getenv("AWS_ACCESS_KEY_ID")
#         SA_ID=os.getenv("AWS_SECRET_ACCESS_KEY")
#         TK=os.getenv("AWS_SESSION_TOKEN")
#         s3 = boto3.resource('s3',aws_access_key_id=ID,
#     aws_secret_access_key=SA_ID,aws_session_token=TK
#     )
#     O=pn.Pathable(pt)
#     O.addBaseName(filename)
#     O.changeFileNameRandom()
#     f=O.getPosition()
#     s3.Bucket(bucket).download_file(key,f)
#     J["filename"]=f
#     J["type"]="local"
#     return J

# from pynico_eros_montin import pynico as pn
# jf="/g/mroptimumCU/pmrgrappa.json"
# J=pn.Pathable(jf).readJson()

# T=J["task"]

# print(T["options"]["reconstructor"]["options"]["noise"]["options"])

# if (T["options"]["reconstructor"]["options"]["noise"]["options"]["type"])=="s3":
#     T["options"]["reconstructor"]["options"]["noise"]["options"]=s3FileTolocal(T["options"]["reconstructor"]["options"]["noise"]["options"])
# if (T["options"]["reconstructor"]["options"]["signal"]["options"]["type"])=="s3":
#     T["options"]["reconstructor"]["options"]["signal"]["options"]=s3FileTolocal(T["options"]["reconstructor"]["options"]["signal"]["options"])

# JO=pn.createRandomTemporaryPathableFromFileName("a.json")
# JO.writeJson(T)
# #create a directory for the calculation to be zippedin the end
# O=pn.createRandomTemporaryPathableFromFileName("a.json")
# O.appendPath('OUT')
# O.ensureDirectoryExistence()
# OUT=O.getPosition()
# #run mr optimum
# K=pn.BashIt()
# K.setCommand(f"MRO/bin/python -m mroptimum.snr -j {JO.getPosition()} -o {OUT}")
# K.run()
# Z=pn.createRandomTemporaryPathableFromFileName('a.zip')
# print("Zipping the file")
# shutil.make_archive(Z.getPosition()[:-4], 'zip', O.getPath())
# print("start uploading")
# ID=os.getenv("AWS_ACCESS_KEY_ID")
# SA_ID=os.getenv("AWS_SECRET_ACCESS_KEY")
# TK=os.getenv("AWS_SESSION_TOKEN")
# s3 = boto3.resource('s3',aws_access_key_id=ID,aws_secret_access_key=SA_ID,aws_session_token=TK)
# s3.Bucket("mroptimum-result").upload_file(Z.getPosition(),Z.getBaseName())
import twixtools as tx
import pygrappa
import numpy as np
from mro import fixAccelratedKSpace2D

# n='/data/MYDATA/siemensrawdataexamples/Sebastian/raw/meas_MID02696_FID183824_gre_GRAPPA_2.dat'
n='/data/MYDATA/siemensrawdataexamples/Sebastian/raw/meas_MID02697_FID183825_gre_GRAPPA_3.dat'
twix=tx.map_twix(n)
H=twix[1]["hdr"]
iPat=H['MeasYaps']['sPat']


print(iPat)
sl=0
print('---signal----')
im_array = twix[1]['image']
im_array.flags['remove_os'] = True  # activate automatic os removal
im_array.flags['average']['Rep'] = True  # average all repetitions
im_array.flags['average']['Ave'] = True # average all repetitions

signal=fixAccelratedKSpace2D(np.transpose(im_array[0,0,0,0,0,0,0,0,0,0,sl,0,0,:,:,:],[2,0,1]))
print('---noise----')
n_array = twix[0]['noise']

n_array.flags['average']['Rep'] = True  # average all repetitions
im_array.flags['average']['Ave'] = True # average all repetitions


noise=np.transpose(n_array[0,0,0,0,0,0,0,0,0,0,sl,0,0,:,:,:],[2,0,1])  


print('---refscan----')
r_array = twix[1]['refscan']
r_array.flags['remove_os'] = True  # activate automatic os removal
r_array.flags['average']['Rep'] = True  # average all repetitions
im_array.flags['average']['Ave'] = True # average all repetitions

ref_=np.transpose(r_array[0,0,0,0,0,0,0,0,0,0,sl,0,0,:,:,:],[2,0,1])  
n_ref=ref_.shape[1]

ref=np.zeros_like(signal)
ref[:,0:n_ref]=ref_
print("signal",signal.shape,"noise",noise.shape,"ref",ref.shape)
# 76 lines instead of 24

from cloudmrhub.cm2D import cm2DReconRSS
# pygrappa.grappa(,)


import matplotlib.pyplot as plt
def recon(signal,noise,tt):
    R=cm2DReconRSS()
    R.setNoiseKSpace(noise)
    R.setSignalKSpace(signal)
    plt.imshow(R.getOutput())
    plt.title(tt)
    plt.show()

recon(signal,noise,"signal")

recon(ref,noise,"ref")
import pygrappa

K=pygrappa.grappa(signal,ref,kernel_size=(5,5))
print(K.shape)
recon(K,noise,"signal,ref")

#only difference 76 lines