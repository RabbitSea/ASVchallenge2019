import numpy as np
import sklearn.preprocessing
from collections import defaultdict
from operator import itemgetter
import os, sys, glob, json
import h5py
import librosa
import librosa.display
from scipy import signal
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

################################################################
# To run:
# python 03_dataset_create.py [train|dev|eval] [feat]
#
# Example:
# python 03_dataset_create.py train mfccDD 
# python 03_dataset_create.py dev mfccDD
# feats_types = ["mfccDD", "imfccDD", "rfccDD", "scmcDD"] etc
###############################################################

# command line args
dataset = sys.argv[1]
feat = sys.argv[2]
task = "PA"

########################################################################



def get_bin(l, edges):
    for i in range(len(edges)):
        e = edges[i]
        if l < e:
            return int(e)
    return int(edges[-1])
        

def resample(y, n):
    x = np.arange(len(y))
    y_new = signal.resample(y, n)
    return y_new


def load_csv(infile):
    input = open(infile, "r")
    data = input.read().split("\n")[:-1]
    input.close()
    truth = defaultdict(list)
    for item in data:
        fname, envID, attackID, t = item.split(",")
        fname = fname.split(".wav")[0]
        truth[fname] = item
    return truth


def get_bin_info(task, framez):
    efile = task+"_edges_4bins.npy"
    ffile = task+"_freqd_4bins.npy"
    if os.path.isfile(efile):
        edges = np.load(efile)
    if os.path.isfile(ffile):
        freqs = np.load(ffile)
    else:
        freqs, edges = np.histogram(np.array(framez), bins=4)
        np.save(ffile, np.array(freqs))
        np.save(efile, np.array(edges))
    return freqs, edges


########################################################################

count = 0
filelist = glob.glob(task+"_feats_"+dataset+"/"+feat+"/*.h5")
total = len(filelist)
coefs_ref = {"mfcc":70, "imfcc":60, "rfcc":30, "scmc":40}
num_coefs = coefs_ref[feat]

truth = load_csv(task+"_reference_"+dataset+".csv")
framez = []

TRUTH = []
SINGLE = []
DELTA = []
DELTADELTA = []
for f in filelist:
    h5f = h5py.File(f,'r')
    dat = h5f[feat+"DD"][:]
    h5f.close()
    count += 1
    print("file "+str(count)+" of "+str(total))
    num_frames = np.array(dat[:,:num_coefs]).shape[0]
    framez.append(num_frames)
    fkey = f.split(".h5")[0].split("/")[-1]
    TRUTH.append(truth[fkey])
    SINGLE.append(dat[:,:num_coefs])
    DELTA.append(dat[:,num_coefs:(num_coefs*2)])
    DELTADELTA.append(dat[:,(num_coefs*2):])


freqs, edges = get_bin_info(task, framez)    

NEW = defaultdict(list)
NEW_TRUTH = defaultdict(list)
# the variable "edges" contains the resample sizes
for j in range(len(SINGLE)):
    s = SINGLE[j]
    d = DELTA[j]
    dd = DELTADELTA[j]
    t = TRUTH[j]
    n = get_bin(len(s), edges)
    s_new = resample(s, n) # frames(rows) x coefs(columns)
    s_new = s_new.flatten() # 1 x (coefs*frames): [coefs_f1][coefs_f2][coefs_f3]..
    d_new = resample(d, n).flatten()
    dd_new = resample(dd, n).flatten()
    interm = np.concatenate((s_new, d_new), axis=None)
    final = np.concatenate((interm, dd_new), axis=None) # mfcc, mfccD, mfccDD
    NEW[n].append(final)
    # need ground truth to go with this stacked representation
    NEW_TRUTH[n].append(t)
for k in NEW.keys():
    # num_wavs x [mfcc mfccD mfccDD] where mfcc = 70_f1 70_f2 .. n_frames
    D = np.array(NEW[k]) 
    T = NEW_TRUTH[k]
    outfile = task+"_"+dataset+"_resample/"+task+"_"+dataset+"_"+feat+"_bin"+str(k)+".h5"
    f = h5py.File(outfile,'w')
    dset = f.create_dataset("Features", data=D, dtype=np.float)
    dset = f.create_dataset("Targets", data=json.dumps(T))
    f.close()
