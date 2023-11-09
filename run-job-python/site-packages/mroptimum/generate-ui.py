
import tkinter as tk
try:
    import generate
except:
    from mroptimum import generate
import argparse




parser = argparse.ArgumentParser(
                    prog='Mroptimum ui generate',
                    description='Generates a json file for MR Optimum!\n eros.montin@gmail.com',
                    epilog='cloudmrhub.com')

parser.add_argument('-j','--joptions', type=str, help='optionfile with the backbone of the calculation',default=None)
parser.add_argument('-r','--run', type=bool, help='optionfile with the backbone of the calculation',default=False)

args = parser.parse_args()


O={'grappa':None,
   'nr':None,
   'box':None,
   'mimic':None,
   'acl':None,
   'accelerations':None,
   'out':args.joptions
   }
try:
    from mro import *
except:
    from mroptimum.mro import *

import tkinter as tk
from tkinter.filedialog import askopenfilename

J={}

def get_the_files():
    filename1 = askopenfilename(title="Signal File", initialdir=".")
    filename2 = askopenfilename(title="Noise File", initialdir=pn.Pathable(filename1).getPath()) if not LL.get() else None
    global O
    if filename2 is None:
        O["signal"]=generate.theNoiseSiemensMultiraid(fn=None,f=filename1)
        O["noise"]=generate.theNoiseSiemensMultiraid(fn=None,f=filename1)
    else:
        O["signal"]=generate.theSignalSiemens(fn=None,f=filename1)
        O["noise"]=generate.theSignalSiemens(fn=None,f=filename2)
    
    finalize_panel = tk.LabelFrame(root, text="SNR Method")
    finalize_panel.grid()
    buttonf = tk.Button(finalize_panel, text="finalize", command=finalize_choice)
    buttonf.grid()

    # if O['out']==None:
    #     O["out"] = tk.filedialog.askdirectory(title="Where do you want to save the json file?", initialdir=".")
    # finalize_choice()
    

def finalize_choice():
    # print(file1.get(), file2.get())
    if O['out']==None:
        O["out"] = tk.filedialog.askdirectory(title="Where do you want to save the json file?", initialdir=".")

    root.quit()

def set_snr():
    
    SID=SNR.index(snrtype.get())
    O["snrtype"]=SF=generate.SNR_g[SID]
    
    if SID>1:
        nr_panel.grid()

    if SID>2:
        box_panel.grid()
    recon_panel.grid()


def set_recon():
    
    RID=RECON.index(recontype.get())
    # reconstruction function
    RF=generate.RECON_g[RID]
    k=RECON_classes[RID]
    O["reconClass"]=k()
    O["recon"]=RF
    panel_mimic.grid()
    print(RID)
    if RID==4:
        grappa_panel.grid()
   
def set_accelerations():
    
    x_acceleration = int(entry_x.get())
    y_acceleration = int(entry_y.get())
    O["accelerations"]=[x_acceleration, y_acceleration]
    print("Accelerations set to: x = {}, y = {}".format(x_acceleration, y_acceleration))

def set_acl():
    x_acl = int(entry_x_acl.get())
    y_acl = int(entry_y_acl.get())
    O["acl"]=[x_acl, y_acl]
    print("ACL set to: x = {}, y = {}".format(x_acl, y_acl))
def set_box():
    O["box"]=entry_box.get()
    print("Box Size = {}".format(O['box']))

def set_grappa():
    O["grappa"]=[entry_grappa0.get(),entry_grappa1.get() ]
    print("Box Size = {}".format(O['grappa']))
def set_nr():
    O["nr"]=entry_nr.get()
    print("Number of REplicas = {}".format(O['nr']))
def mimic():
    K=O["reconClass"]
    O["mimic"]=True

    if LL2.get():
        if K.HasAcceleration:
            accelerations_panel.grid()
        if K.HasAutocalibration:
            acl_panel.grid()
    file_panel.grid()

root = tk.Tk()
root.title("Generate Mr Optimum Json customization file")

#SNR
snr_panel = tk.LabelFrame(root, text="SNR Method")
snr_panel.grid()
snrtype = tk.StringVar(root)
snrtype.set("Select an Option")
  
snr_menu = tk.OptionMenu(snr_panel, snrtype, *SNR)
snr_menu.grid(row=0,column=0)

snr_submt_button = tk.Button(snr_panel, text='Submit', command=set_snr)
snr_submt_button.grid(row=0,column=1)


nr_panel=tk.LabelFrame(root, text="Number of Pseudo Replicas")
nr_panel.grid_remove()

label_nr = tk.Label(nr_panel, text="N Repllicas")
label_nr.grid(row=0, column=0)

entry_nr = tk.Entry(nr_panel)
entry_nr.grid(row=0, column=1)

nr_submit = tk.Button(nr_panel, text='Submit', command=set_nr)
nr_submit.grid(row=0,column=2)


box_panel=tk.LabelFrame(root, text="Box Size")
box_panel.grid_remove()

label_box = tk.Label(box_panel, text="Box Size")
label_box.grid(row=0, column=0)

entry_box = tk.Entry(box_panel)
entry_box.grid(row=0, column=1)

box_submit = tk.Button(box_panel, text='Submit', command=set_box)
box_submit.grid(row=0,column=2)




# recon
recon_panel = tk.LabelFrame(root, text="Reconstruction Method")
recon_panel.grid_remove()

recontype = tk.StringVar(root)
recontype.set("Select an Option")

recon_menu = tk.OptionMenu(recon_panel, recontype, *RECON)
recon_menu.grid(row=0,column=0)

recon_submit = tk.Button(recon_panel, text='Submit', command=set_recon)
recon_submit.grid(row=0,column=1)

#mimic
panel_mimic = tk.LabelFrame(root, text="Mimic Accelration")
panel_mimic.grid_remove()



grappa_panel=tk.LabelFrame(root, text="grappa Size")
grappa_panel.grid_remove()

label_grappa0 = tk.Label(grappa_panel, text="grappa Size Frequency")
label_grappa0.grid(row=0, column=0)

entry_grappa0 = tk.Entry(grappa_panel)
entry_grappa0.grid(row=0, column=1)


label_grappa1 = tk.Label(grappa_panel, text="grappa Size Phase")
label_grappa1.grid(row=1, column=0)

entry_grappa1 = tk.Entry(grappa_panel)
entry_grappa1.grid(row=1, column=1)


grappa_submit = tk.Button(grappa_panel, text='Submit', command=set_grappa)
grappa_submit.grid(row=0,column=2)



LL2=tk.BooleanVar(root)
mimic_ckheckbutton = tk.Checkbutton(panel_mimic, text="Mimic Acceleration",variable=LL2)
mimic_ckheckbutton.grid(row=0,column=0)


submit_mimic = tk.Button(panel_mimic, text='contnue', command=mimic)
submit_mimic.grid(row=0,column=1)


accelerations_panel = tk.LabelFrame(root, text="Accelerations")
accelerations_panel.grid_remove()

label_x = tk.Label(accelerations_panel, text="Frequency acceleration")
label_x.grid(row=0, column=0)

entry_x = tk.Entry(accelerations_panel)
entry_x.grid(row=0, column=1)

label_y = tk.Label(accelerations_panel, text="Phase acceleration")
label_y.grid(row=1, column=0)

entry_y = tk.Entry(accelerations_panel)
entry_y.grid(row=1, column=1)

button_set_accelerations = tk.Button(accelerations_panel, text="Set accelerations", command=set_accelerations)
button_set_accelerations.grid(row=2, column=0)

acl_panel = tk.LabelFrame(root, text="ACL")
acl_panel.grid_remove()

label_x_acl = tk.Label(acl_panel, text="Frequency ACL")
label_x_acl.grid(row=0, column=0)

entry_x_acl = tk.Entry(acl_panel)
entry_x_acl.grid(row=0, column=1)

label_y_acl = tk.Label(acl_panel, text="Phase ACL")
label_y_acl.grid(row=1, column=0)

entry_y_acl = tk.Entry(acl_panel)
entry_y_acl.grid(row=1, column=1)

button_set_acl = tk.Button(acl_panel, text="Set ACL", command=set_acl)
button_set_acl.grid(row=2, column=0)




LL=tk.BooleanVar(root)
file_panel = tk.LabelFrame(root, text="Signal")
file_panel.grid_remove()

checkbutton = tk.Checkbutton(file_panel, text="Use MultiRaid Noise",variable=LL)
checkbutton.grid(row=0, column=0)


button = tk.Button(file_panel, text="Select files", command=get_the_files)
button.grid(row=0,column=1)

root.mainloop()


SF=O['snrtype']
RF=O["recon"]
J=generate.start()
J=SF(fn=None,reconstructor=RF(fn=None),J0=J)

J['options']['reconstructor']['options']['noise']=O['noise']
J['options']['reconstructor']['options']['signal']=O['signal']


if O['box']:
    J["options"]["boxSize"]=int(O['box'])

if O['nr']:
    J["options"]["NR"]=int(O['nr'])

if O['grappa']:
    J["options"]['reconstructor']["options"]["kernelSize"]=[int(gk)for gk in O['grappa']]

if O["mimic"]:
    J["options"]['reconstructor']["options"]["decimate"]=O['mimic']

if O['acl']:
    J["options"]['reconstructor']["options"]["acl"]=[int(gk)for gk in O['acl']]

if O['accelerations']:
    J["options"]['reconstructor']["options"]["accelerations"]=[int(gk)for gk in O['accelerations']]

from pynico_eros_montin import pynico as pn
A=pn.Pathable(O['out'])
A.addBaseName('settings.json')
A.ensureDirectoryExistence()
A.writeJson(J)

if args.run:
    import subprocess
    subprocess.run(["python","-m", "mroptimum.snr",
    # subprocess.run(["python", "snr.py",
                    "-j",
                A.getPosition(),
                "-o",
                A.getPath(),
                "-c",
                "True",
                "-g",
                "True",
                "-m",
                "True"
    ])


