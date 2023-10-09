from myPy import *
import SimpleITK as sitk
import json
def writeResultsAsCmJSONOutput(results,filename,info=None):
    """_summary_

    Args:
        images (_type_): array of [type,name,imaginable,outputName]
        filename (_type_): oyutput filename
        info (_type_, optional): type, subType. Defaults to None.
    """
    OUTPUT={
        'version':'20220314',
        'language':'python',
        'type':'CMOutput',
        'subType':"default",
        'author':'eros.montin@gmail.com',
    }

        
    if info is not None:
        if info["type"] is not  None:
            OUTPUT["type"]=info['type']
        if info['subType'] is not None:
            OUTPUT["subType"]=info['subType']
    IMAGES=[]
    for r in results:
        if r['type']=='imaginable2D':
            if ((isinstance(r['imaginable'], Imaginable))):
                theim=r['imaginable']
            elif isinstance(r['imaginable'],sitk.Image):
                theim= Imaginable()
                theim.setImage(r['imaginable'])
            else:
                try:
                    if r['imaginable'].isImaginable():
                        theim=r['imaginable']
                    else:
                        return False
                except:
                    return False


            
            getSlice=theim.getAxialSlice
            orientation=2
            try:
                if r['orientation']==1:
                    getSlice=theim.getSagittalSlice
                    print('sagittal slices:)')
                elif r['orientation']==0:
                    getSlice=theim.getCoronalSlice
                    print('corona; slices:)')
                orientation=r['orientation']
                
            except:
                print('axial slices:)')
            
            S=theim.getImageSize()

            SL=[]
            for s in range(S[orientation]):
                o={"type":"double complex"}
                sl=getSlice(s)
                o['w'],o['h']=sl.GetSize()
                o['s']=sl.GetSpacing()
                o['o']=sl.GetOrigin()
                o['d']=sl.GetDirection()
                nda = sitk.GetArrayFromImage(sl) #YX
                s=nda.flatten('F').astype(complex)
                o['Vi']=s.imag.tolist()
                o['Vr']=s.real.tolist()
                SL.append(o)
            R={
                "slice":SL, # this should be slices... i know
                "imageName":r["name"]
            }
            
            try:
                R["imageOutputName"]=r["outputName"]
            except:
                R["imageOutputName"]=r["name"]
            
            IMAGES.append(R)
    
    OUTPUT["images"]=IMAGES

    if filename is None:
        return OUTPUT
    else:

        # create json object from dictionary
        js = json.dumps(OUTPUT)

        # open file for writing, "w" 
        f = open(filename,"w")

        # write json object to file
        f.write(js)

        # close file
        f.close()
        return True
