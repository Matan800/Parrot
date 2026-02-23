#!/bin/bash
# this script sets up pi-gen with the necessary changes to build a headless 
# parrot + Raspberry Pi OS Lite image
FILES="stage3/01-install-app/files"
if [ -d "pi-gen" ]; then
  echo "Directory pi-gen already exists. Exiting..."
  exit 1
fi
echo "Cloning pi-gen..."
git clone --branch arm64 https://github.com/RPI-Distro/pi-gen.git --depth=1
cd pi-gen
echo "Configuring pi-gen..."
rm -rf stage3
touch stage4/SKIP && touch stage4/SKIP_IMAGE
touch stage5/SKIP && touch stage5/SKIP_IMAGE
rm stage4/EXPORT_IMAGE stage5/EXPORT_IMAGE
echo "Copying files..."
cp -r ../stage3 .
cp ../../requirements.txt "${FILES}"
cp -r ../../parrot/* "${FILES}"
cp ../config .
find . -type f -iname "*.sh" -exec chmod +x {} \;
echo "Done!"
echo "Run build.sh or build-docker.sh from the pi-gen folder to build an image"
