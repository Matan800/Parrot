from parrot import Parrot
import pyaudio
import systemd_watchdog
import signal 
 
Sentry = True

# Create a Signal Handler for Signals.SIGINT / Signals.SIGTERM
def SignalHandler_Terminate(SignalNumber,Frame):
   global Sentry 
   Sentry = False
   
signal.signal(signal.SIGINT,SignalHandler_Terminate) #regsiter signal with handler
signal.signal(signal.SIGTERM,SignalHandler_Terminate) #regsiter signal with handler

# pyaudio setup
_CHANNELS = 1
_SAMPLE_RATE = 16000
_CHUNK = 8192

def main():
    global Sentry
    #init
    wd = systemd_watchdog.WatchDog()
    if not wd.is_enabled:
        # we expect a systemd with watchdog enabled
        raise Exception("Watchdog not enabled") 
    print("Starting Parrot...")
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
    parrot_obj = Parrot(in_stream,out_stream)
    wd.ready()
    print("Init complete.")
    wd.notify()
    # run
    while Sentry:
        parrot_obj.infinite_loop(1) # run once
        wd.notify()
    # cleanup
    print("Shutting down...")
    in_stream.stop_stream()
    in_stream.close()
    out_stream.stop_stream()
    out_stream.close()
    audio.terminate()
    
if __name__ == '__main__':
    main()