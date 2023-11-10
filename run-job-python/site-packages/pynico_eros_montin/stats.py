def accuracyFromConfusion(C):
    tn_, fp_, fn_, tp_ = C.ravel()
    return (tp_+tn_)/(tp_+tn_+fn_+fp_)
def specificityFromConfusion(C):
    tn_, fp_, fn_, tp_ = C.ravel()
    return ( tn_ /(tn_+fp_))
def sensitivityFromConfusion(C):
    tn_, fp_, fn_, tp_ = C.ravel()
    return ( tp_ /(tp_+fn_))

