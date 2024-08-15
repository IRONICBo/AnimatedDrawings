#!/bin/bash

#conda create -n drawing python=3.8.13 -y
#conda install pytorch==2.0.0 torchvision==0.15.0 torchaudio==2.0.0 pytorch-cuda=11.8 -c pytorch -c nvidia
#sudo apt-get install libosmesa6-dev freeglut3-dev
#sudo apt-get install libglfw3-dev libgles2-mesa-dev
#sudo apt-get install libosmesa6
#export PYOPENGL_PLATFORM=osmesa
##conda install -c conda-forge libstdcxx-ng=12

# install os dependencies
if ! command -v java &> /dev/null
then
	sudo apt-get update 
	sudo apt install ca-certificates
	echo "java could not be found, installing"
	sudo apt install default-jre
fi


# install python dependencies
pip install openmim
pip install torch==2.0.0
pip install torchserve

# Check if the directory exists
if [ ! -d "xtcocoapi" ]; then
	git clone https://github.com/jin-s13/xtcocoapi.git
fi
cd xtcocoapi
pip install -r requirements.txt
python setup.py install
cd ../


cd torchserve
if [ ! -d "model-store" ]; then
	mkdir -p ./model-store
	echo "download checkpoints to " ./model-store
	wget https://github.com/facebookresearch/AnimatedDrawings/releases/download/v0.0.1/drawn_humanoid_detector.mar -P ./model-store/
	wget https://github.com/facebookresearch/AnimatedDrawings/releases/download/v0.0.1/drawn_humanoid_pose_estimator.mar -P ./model-store/
fi
cd ..

pip install -U openmim
mim install mmcv-full==1.7.0
pip install mmdet==2.27.0


# bugfix for xtcocoapi, an mmpose dependency
pip install mmpose==0.29.0
pip install torchvision==0.15.1  # solve torch version problem

echo "*** Now run torchserve:"
echo "cd torchserve && torchserve --start --ts-config config.local.properties --foreground"