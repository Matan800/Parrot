import glob
import numpy as np
import os
import parrot_utils
import pyaudio
import scipy.signal as sig
import wave

class MockStream():
    def __init__(self,audio_stream,rate,channels,frames_per_buffer):
        self.audio_stream = audio_stream
        self._buffer_pointer = 0
        self._rate = rate
        self._frames_per_buffer = frames_per_buffer
        self._channels = channels

    def read(self, chunk):
        if chunk > len(self.audio_stream):
            raise EOFError()
        buffer = self.audio_stream[self._buffer_pointer:]
        if len(buffer) > chunk:
            output_buffer = buffer[:chunk]
            self._buffer_pointer += chunk
        else:
            residual = chunk - len(buffer)
            output_buffer = buffer + self.audio_stream[:residual]
            self._buffer_pointer = residual
        return output_buffer
    
    def stop_stream(self):
        pass

    def start_stream(self):
        pass

    def close(self):
        pass

class MockAudio():
    def __init__(self):
        self.files = glob.glob(os.path.join('..','Media','Tests','*.wav'))
        if len(self.files) == 0:
            raise FileNotFoundError

    def open(self,format,channels,rate,frames_per_buffer,
             input=True,output=False):
        if output:
            raise NotImplementedError()
        if format is not pyaudio.paInt16:
            raise NotImplementedError()
        if channels != 1:
            raise NotImplementedError()
        self._buffer_pointer = 0

        audio_stream = []
        for file in self.files:
            with wave.open(file,'rb') as wf:
                frame_rate = wf.getframerate()
                channel_num = wf.getnchannels()
                width = wf.getsampwidth()
                audio = wf.readframes(wf.getnframes())
                if width == 2:
                    audio_int16 = np.frombuffer(audio, np.int16)
                    audio_float32 = parrot_utils.int2float(audio_int16)
                else:
                    raise NotImplementedError()
                if channel_num > channels:
                    # convert stereo to mono
                    audio_float32 = (audio_float32[::2] + audio_float32[1::2]) / 2
                ratio = frame_rate / rate
                if round(ratio) != ratio:
                    raise ValueError()
                if ratio > 1:
                    audio_float32 = sig.decimate(audio_float32,ratio)
                if ratio < 1:
                    audio_float32 = np.interp(range(ratio*len(audio_float32)),range(len(audio_float32)),
                                              audio_float32)
                audio_stream.append(audio_float32.reshape(-1)*32768)
        audio_stream = np.array(audio_stream).astype(np.int16).tobytes()
        return MockStream(audio_stream,rate,channels,frames_per_buffer)
