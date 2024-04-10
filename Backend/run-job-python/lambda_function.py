import json
import boto3
import os
import shutil
from pynico_eros_montin import pynico as pn
import os

mroptimum_result = os.getenv("ResultsBucketName", "mroptimum-result")
mroptimum_failed = os.getenv("FailedBucketName", "mroptimum-failed")


def s3FileTolocal(J, s3=None, pt="/tmp"):
    key = J["key"]
    bucket = J["bucket"]
    filename = J["filename"]
    if s3 == None:
        s3 = boto3.resource("s3")
    O = pn.Pathable(pt)
    O.addBaseName(filename)
    O.changeFileNameRandom()
    f = O.getPosition()
    s3.Bucket(bucket).download_file(key, f)
    J["filename"] = f
    J["type"] = "local"
    return J


def handler(event, context):
    # connect to the s3
    L = pn.Log("mroptimum lambda function",{ "event": event, "context": context})
    # create a directory for the calculation to be zippedin the end
    O = pn.createRandomTemporaryPathableFromFileName("a.json")
    O.appendPath("OUT")
    O.ensureDirectoryExistence()
    try:
        s3 = boto3.client("s3")
        # Get the bucket name and file key
        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        file_key = event["Records"][0]["s3"]["object"]["key"]
        L.append(f"bucket_name {bucket_name}")
        L.append(f"file_key {file_key}")
        L.append(f"mroptimum_result {mroptimum_result}")
        # save json file to local
        fj = pn.createRandomTemporaryPathableFromFileName("a.json")
        s3 = boto3.resource("s3")
        s3.Bucket(bucket_name).download_file(file_key, fj.getPosition())
        L.append(f"file downloaded {fj.getPosition()}")
        J = pn.Pathable(fj.getPosition()).readJson()
        L.append("json file read ")

        # copy the task part of mroptimum ui
        pipelineid = J["pipeline"]
        L.append(f"pipelineid {pipelineid}")
        token = J["token"]
        L.append(f"token {token}")

        OUTPUT = J["output"]
        savecoils = "--no-coilsens"
        savematlab = "--no-matlab"
        savegfactor = "--no-gfactor"
        if "coilsensitivity" in OUTPUT.keys():
            if OUTPUT["coilsensitivity"]:
                savecoils = "--coilsens"

        if "matlab" in OUTPUT.keys():
            if OUTPUT["matlab"]:
                savematlab = "--matlab"
        if "gfactor" in OUTPUT.keys():
            if OUTPUT["gfactor"]:
                savegfactor = "--gfactor"
        L.append(f"savecoils {savecoils}")
        L.append(f"savematlab {savematlab}")
        L.append(f"savegfactor {savegfactor}")

        # output can have matlab, coilsensitivity and, gfactor

        T = J["task"]
        print(T)
        print(
            f'noise - file {T["options"]["reconstructor"]["options"]["noise"]}')

        # donwload the file if needed
        if (T["options"]["reconstructor"]["options"]["noise"]["options"]["type"]) == "s3":
            T["options"]["reconstructor"]["options"]["noise"]["options"] = s3FileTolocal(
                T["options"]["reconstructor"]["options"]["noise"]["options"], s3)
        print("noise - file - downloaded")
        L.append(
            f'noise - file {T["options"]["reconstructor"]["options"]["noise"]}')
        print(
            f'signal - file {T["options"]["reconstructor"]["options"]["signal"]}')

        if (T["options"]["reconstructor"]["options"]["signal"]["options"]["type"]) == "s3":
            T["options"]["reconstructor"]["options"]["signal"]["options"] = s3FileTolocal(
                T["options"]["reconstructor"]["options"]["signal"]["options"], s3)
        # write the update json structure to compute with mroptimum
        L.append(
            f'signal - file {T["options"]["reconstructor"]["options"]["signal"]}')
        JO = pn.createRandomTemporaryPathableFromFileName("a.json")
        T["token"] = token
        T["pipelineid"] = pipelineid
        JO.writeJson(T)

        OUT = O.getPosition()
        L.append(f"output dir set to {OUT}")
        log=pn.createRandomTemporaryPathableFromFileName("a.json").getPosition()
        # run mr optimum
        K = pn.BashIt()
        # -p is for parallel and is set to false because of the lambda number of cores
        K.setCommand(
            f"python -m mroptimum.snr -j {JO.getPosition()} -o {OUT} --no-parallel {savematlab} {savecoils} {savegfactor} --no-verbose -l {log}")
        print(K.getCommand())
        K.run()
        
        L.appendFullLog(log)
        L.append("the command ran")
        Z = pn.createRandomTemporaryPathableFromFileName("a.zip")
        Z.ensureDirectoryExistence()
        print(f"Zipping the file {Z.getPosition()[:-4]}")
        shutil.make_archive(Z.getPosition()[:-4], "zip", O.getPath())
        print("start uploading")
        L.append("start uploading")
        s3.Bucket(mroptimum_result).upload_file(
            Z.getPosition(), Z.getBaseName())
        L.append("uploading ended")
        return {
            "statusCode": 200,
            "body": json.dumps({"results": {"key": Z.getBaseName(), "bucket": mroptimum_result}})
        }
    except Exception as e:
        print(e)
        L.append(str(e), 'error')
        L.append("error")
        O.changeBaseName("error.log")
        L.writeLogAs(O.getPosition())
        O.changeBaseName("task.json")
        # copy the file inthe variable jf in /tmp
        try:

            O.writeJson(T)
        except:
            print(f"coudn't copy {fj.getPosition()}")

        E = pn.createRandomTemporaryPathableFromFileName("a.json")
        E.changePath(O.getPath())
        E.changeFileName("event")
        E.writeJson(event)
        E.changeFileName("options")
        try:
            E.writeJson(J)
        except:
            print("couldn't write the options")
        E.changeFileName("log")
        E.writeJson(L.getWhatHappened())

        INFO = {"headers": {
                    "options": {
                        "token": token,
                        "pipelineid": pipelineid
                    }
        }
        }
        E.changeFileName("info")
        E.writeJson(INFO)
        Z = pn.createRandomTemporaryPathableFromFileName("a.zip")
        shutil.make_archive(Z.getPosition()[:-4], "zip", O.getPath())
        s3.Bucket(mroptimum_failed).upload_file(
            Z.getPosition(), Z.getBaseName())
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
