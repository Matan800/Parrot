
# parrot

A Python app that listens to your microphone, detects when you speak, and plays back a  **distorted** copy. **Whistles** and **parrot sounds** are added randomly. Built for fun, 
as a proposed mechanism for the [BluBa Fairytale Garden](https://www.blueba.de/en/fairytale-garden-alt.html) Parrot.

---

## Features
- **Always-on mic** with **voice activity detection (VAD)** to trigger recording only when you speak
- **Noise reduction** and **basic EQ** for cleaner input, using parts identified as noise to improve the noise filter 
- **Real-time(ish) effects**: pitch/rate shifting to mimic a parrot
- **Parrot flair**: random **whistles** and **squawks** added at sentence ends
- **Headless mode** & optional **systemd watchdog** heartbeat (Linux) with Raspberry Pi image generation
- **GPIO 26** is on when listening, off when speaking, can be used to drive the parrot's eye light

> Note: This is a local/offline app. No cloud calls are required.

---

## Dependencies
Core Python packages used by **parrot**:

- `numpy`
- `scipy`
- `librosa`
- `noisereduce`
- `pydub`
- `configparser`
- `pyaudio`
- `playsound3`
- `onnxruntime`
- `systemd-watchdog` *(optional for raspberri-pi deployment; Linux-only)*

Models/Assets:
- **Silero VAD** ONNX model (`silero_vad.onnx`)
---

Please add parrot sounds as mp3 files under parrot/Media.
I forgot where I got my files, so I cannot publish them due to licensing issues...

## Quick Start

### 1) System prerequisites
- **Audio backend**: Ensure your OS has a working input/output device
- **PortAudio** (for `pyaudio`)
  - macOS: `brew install portaudio`
  - Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y portaudio19-dev`
  - Windows: install wheel from PyPI if needed (or use `pipwin install pyaudio`)

### 2) Clone & install
```bash
git clone https://github.com/Matan800/Parrot
cd parrot
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

### 3) Run
```bash
python ./parrot/main.py # Windows: parrot\main.py
```

---

## Raspberry Pi Headless Deployment (Linux, optional)
To enable wi-fi, add the following parameters to pi-gen-work\config:
```bash
WPA_COUNTRY= ...
WPA_PASSWORD= ...
WPA_ESSID= ...
```
Also, feel free to change the username and password.

To build on a Linux machine:
```bash
cd pi-gen-work
source pi-gen-pre-build.sh
cd pi-gen
source build.sh # Native Raspberri Pi
source build-docker.sh # Linux with docker and QEMU
```

### Docker Setup (Linux, optional)
```bash
sudo apt update
# remove old installations
 sudo apt remove $(dpkg --get-selections docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc | cut -f1)
 # set up Docker's apt repo:
 # Add Docker's official GPG key:
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update 
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo apt install binfmt-support qemu-user-static -y # Install the qemu packages
```
---

## Privacy & Security
Audio never leaves your machine. Grant mic permissions to the Python interpreter when prompted by your OS.

---

## Licensing
- Project license: MIT (see [LICENSE](./LICENSE)).  
- Third‑party software licenses: see [THIRD-PARTY-NOTICES](./THIRD-PARTY-NOTICES).  
- Models and media distributed with this project (e.g., Silero‑VAD ONNX) retain their
  original licenses and attribution (see `THIRD-PARTY-NOTICES`).
  
---

## Acknowledgements
- **Silero VAD** authors for their lightweight, accurate voice activity detection model.
- The maintainers of `librosa`, `noisereduce`, `pydub`, and `pyaudio` for excellent audio tooling.

