import glob
import librosa 
import noisereduce
import numpy as np
import os
import parrot_utils
import pydub
import pydub.effects
import random
import scipy.signal as sig
import silero_vad
import time
import torch

class Parrot:
    """class implementing the Parrot
    """    
    # constants
    _AUDIO_BUFFER_SEC = 20
    _AUDIO_BIT_SEC = 0.5
    _SPPECH_THRESHOLD = 0.5
    _NOISE_THRESHOLD = 0.2
    _SPEECH_FRAMES_THRESHOLD = 2
    _FILTER_CUTOFF_LOW = 300
    _FILTER_CUTOFF_HIGH = 6000
    _FILTER_ORDER = 5
    _PITCH_SHIFT = 2.1
    _RATE_SHIFT = 1.0
    _MIN_BORED = 60
    _MAX_BORED = 3*60
    _PLAY_PROB = 0.25

    def __init__(self,VLCplayer,in_stream,out_stream):
        self.model = silero_vad.load_silero_vad()
        self.player = VLCplayer
        self.in_stream = in_stream
        self.out_stream = out_stream
        self._SAMPLE_RATE = self.in_stream._rate # hack
        self._CHUNK = self.in_stream._frames_per_buffer #hack
        self._CHANNELS = self.in_stream._channels #hack
        frame_len = self._CHUNK / self._SAMPLE_RATE
        self.frames_to_record = round(self._AUDIO_BIT_SEC/frame_len) 
        self.audio_bits_num = round(self._AUDIO_BUFFER_SEC / self._AUDIO_BIT_SEC)
        # self.filter_coeffs = parrot_utils.butter_bandpass(self._FILTER_CUTOFF_LOW, self._FILTER_CUTOFF_HIGH, 
        #                                     self._SAMPLE_RATE, order=self._FILTER_ORDER)
        self.filter_coeffs = parrot_utils.butter_highpass(self._FILTER_CUTOFF_LOW, self._SAMPLE_RATE, 
                                                          order=self._FILTER_ORDER)
        self.init_file_lists()
        self.noise_bit = []

    def init_file_lists(self):
        self.whistels = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),'Media','Whistles','*.mp3'))
        self.sentences = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),'Media','Sentences','*.mp3'))

    def get_parrot_timeout(self):
        return random.randint(self._MIN_BORED,self._MAX_BORED)

    def get_audio_bit(self):
        bit_data = []
        for _ in range(0, self.frames_to_record):
            audio_chunk = self.in_stream.read(self._CHUNK)
            audio_int16 = np.frombuffer(audio_chunk, np.int16)
            audio_float32 = parrot_utils.int2float(audio_int16)
            bit_data.append(audio_float32)
        return bit_data
            
    def analyze_speech(self,np_data):
        voiced_confidences = []
        np_data = np_data.reshape((-1,self._CHUNK))
        for row in np_data:
            voiced_confidences.append(self.model(torch.from_numpy(row), self._SAMPLE_RATE).item())
        # not all silence is noise
        speech_parts = [True for x in voiced_confidences if x > self._SPPECH_THRESHOLD]
        if len(speech_parts) > 0:
            flag = parrot_utils.AudioType.SPEECH
        else:
            flag = parrot_utils.AudioType.SILENT
        noise_parts = [1 for x in voiced_confidences if x < self._NOISE_THRESHOLD]
        if sum(noise_parts) == len(noise_parts):
            flag = flag | parrot_utils.AudioType.NOISE
        return flag

    def play_random_whistle(self,force_play=False):
        time.sleep(0.1)
        if len(self.whistels) == 0:
            return
        if random.uniform(0,1) < self._PLAY_PROB or force_play:
            self.player.set_media(self.player.get_instance().media_new(random.choice(self.whistels)))
            self.player.play()
            time.sleep(0.05)
            while self.player.is_playing():
                time.sleep(0.05)

    def play_random_sentence(self):
        time.sleep(0.1)
        if random.uniform(0,1) < self._PLAY_PROB:
            if random.uniform(0,1) > 0.5:
                if len(self.sentences) == 0:
                    return  
                self.player.set_media(self.player.get_instance().media_new(random.choice(self.sentences)))
                self.player.play()
                time.sleep(0.05)
                while self.player.is_playing():
                    time.sleep(0.05)
            else:
                self.play_random_whistle(True)
                self.play_random_whistle(True)

    def precondition_signal(self,signal):
        signal = sig.filtfilt(self.filter_coeffs[0], self.filter_coeffs[1], signal)
        signal = librosa.util.normalize(signal)
        return signal
    
    def filter_noise(self,signal):
        if len(self.noise_bit) > 0:
            signal = noisereduce.reduce_noise(y=signal,sr=self._SAMPLE_RATE,
                                                n_fft=self._CHUNK,stationary=True,
                                                y_noise=self.noise_bit)
        else:
            signal = noisereduce.reduce_noise(y=signal,sr=self._SAMPLE_RATE,
                                                n_fft=self._CHUNK,stationary=True)
        signal = librosa.util.normalize(signal)
        return signal

    def condition_signal(self,signal):
        # compression (boost weak signals)
        signal = pydub.AudioSegment((10000*signal).astype(np.int32).tobytes(), 
                                    sample_width=np.dtype(np.int32).itemsize,
                                    frame_rate=self._SAMPLE_RATE, channels=self._CHANNELS)
        signal = pydub.effects.normalize(signal)
        signal = pydub.effects.compress_dynamic_range(signal,threshold=-30,ratio=6,release=20)
        tmp = signal.raw_data
        signal = np.frombuffer(tmp,dtype=np.int32).astype(np.float32)
        signal = librosa.util.normalize(signal)
        # effects
        signal = librosa.effects.pitch_shift(signal,sr=self._SAMPLE_RATE,
                                             n_steps=self._PITCH_SHIFT)
        signal = librosa.effects.time_stretch(signal, rate=self._RATE_SHIFT)
        signal = librosa.util.normalize(signal)
        signal = signal.astype(np.float32).tobytes()
        return signal
    
    def infinite_loop(self,count_limit = -1):
        bored_parrot_timeout_sec = self.get_parrot_timeout()
        last_conversation = time.time()
        count = 0
        while 1:
            data = []
            for _ in range(self.audio_bits_num):
                bit_data = self.get_audio_bit()
                np_data = np.array(bit_data).reshape(-1)
                flag = self.analyze_speech(np_data)
                if parrot_utils.AudioType.NOISE in flag:
                    self.noise_bit = np_data
                if parrot_utils.AudioType.SILENT in flag: 
                    if time.time() - last_conversation > bored_parrot_timeout_sec:
                        last_conversation = time.time()
                        bored_parrot_timeout_sec = self.get_parrot_timeout()
                        self.play_random_sentence()
                    break
                data.append(np_data)
                last_conversation = time.time()

            if len(data) > 0: 
                # stopping and restarting mic, half duplex operation
                self.in_stream.stop_stream()
                signal = np.array(data).reshape(-1)
                signal = self.precondition_signal(signal)
                signal = self.filter_noise(signal)
                signal = self.condition_signal(signal)
                self.out_stream.write(signal)
                self.play_random_whistle()
                self.in_stream.start_stream()
            
            # for self test
            if (count_limit > 0): 
                count += 1
                if (count > count_limit):
                    break
