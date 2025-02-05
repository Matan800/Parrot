import cProfile
import parrot
import parrot_test
import pstats
from pstats import SortKey
import pyaudio
import torch
import vlc

# pyaudio setup
_CHANNELS = 1
_SAMPLE_RATE = 16000
_CHUNK = 512

if __name__ == '__main__':
    #init
    torch.set_num_threads(1)
    player = vlc.MediaPlayer()
    audio = pyaudio.PyAudio()
    test_audio = parrot_test.MockAudio()
    in_stream = test_audio.open(format=pyaudio.paInt16,
                                channels=_CHANNELS,
                                rate=_SAMPLE_RATE,
                                input=True,
                                frames_per_buffer=_CHUNK,
                                )
    out_stream = audio.open(format=pyaudio.paFloat32,
                                channels=_CHANNELS,
                                rate=_SAMPLE_RATE,
                                output=True,
                                frames_per_buffer=_CHUNK,
                                )
    parrot_obj = parrot.Parrot(player,in_stream,out_stream)
    # run
    print("Starting Parrot...")
    cProfile.run('parrot_obj.infinite_loop(count_limit=100)','profile.txt')
    # cleanup
    in_stream.stop_stream()
    in_stream.close()
    out_stream.stop_stream()
    out_stream.close()
    audio.terminate()

    p = pstats.Stats('profile.txt')
    print('Cummulative:')
    p.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(10)
    print('Time:')
    p.strip_dirs().sort_stats(SortKey.TIME).print_stats(10)