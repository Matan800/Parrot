from enum import Flag, auto
import numpy as np
import scipy.signal as sig

class AudioType(Flag):
    SILENT = auto()
    NOISE = auto()
    SPEECH = auto()

def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1/32768
    sound = sound.squeeze()  # depends on the use case
    return sound

def butter_highpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = sig.butter(order, normal_cutoff, btype='high', analog=False)
    return b, a

def butter_bandpass(freq_low, freq_high, fs, order=5):
    nyq = 0.5 * fs
    normal_low = freq_low / nyq
    normal_high = freq_high / nyq
    b, a = sig.butter(order, [normal_low,normal_high], btype='bandpass', analog=False)
    return b, a

