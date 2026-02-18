import parrot
import pyaudio

# pyaudio setup
_CHANNELS = 1
_SAMPLE_RATE = 16000
_CHUNK = 8192

def main():
    #init
    audio = pyaudio.PyAudio()
    in_stream = audio.open(format=pyaudio.paInt16,
                                channels=_CHANNELS,
                                rate=_SAMPLE_RATE,
                                input=True,
                                frames_per_buffer=_CHUNK,
                                start=False,
                                )
    out_stream = audio.open(format=pyaudio.paInt16,
                                channels=_CHANNELS,
                                rate=_SAMPLE_RATE,
                                output=True,
                                frames_per_buffer=_CHUNK,
                                )
    parrot_obj = parrot.Parrot(in_stream,out_stream)
    # run
    parrot_obj.infinite_loop()
    # cleanup
    in_stream.stop_stream()
    in_stream.close()
    out_stream.stop_stream()
    out_stream.close()
    audio.terminate()
    
if __name__ == '__main__':
    main()