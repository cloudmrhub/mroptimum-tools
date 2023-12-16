from raider_eros_montin import raider as rd
K=rd.readMultiRaidNoise('meas_MID02317_FID373207_AXIAL_2D_GRE_1SL.dat',False,False)
rd.KSpace2DtoISMRMRD(K,"aaa.h5",[1,1,1])
