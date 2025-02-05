import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

packages = [
    'numpy',
    'scipy',
    'librosa', 
    'noisereduce',
    'pydub',
    'silero_vad',
    'python-vlc',
    'configparser',
    'pyaudio',
    'torch',
]

for package in packages:
    install(package)