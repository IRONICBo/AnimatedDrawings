# syntax = docker/dockerfile:1.2

FROM continuumio/miniconda3:24.1.2-0

# install os dependencies
RUN mkdir -p /usr/share/man/man1
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    ca-certificates \
    curl \
    vim \
    sudo \
    default-jre \
    git \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN conda install python=3.8.13 -y
# install python dependencies
RUN pip install openmim -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install torch==2.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN mim install mmcv-full==1.7.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install mmdet==2.27.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install torchserve -i https://pypi.tuna.tsinghua.edu.cn/simple

# bugfix for xtcocoapi, an mmpose dependency
RUN git clone https://github.com/jin-s13/xtcocoapi.git
WORKDIR xtcocoapi
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN python setup.py install
WORKDIR /
RUN pip install mmpose==0.29.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
# solve torch version problem
RUN pip install torchvision==0.15.1  -i https://pypi.tuna.tsinghua.edu.cn/simple


# prep torchserve
RUN mkdir -p /home/torchserve/model-store
RUN wget https://github.com/facebookresearch/AnimatedDrawings/releases/download/v0.0.1/drawn_humanoid_detector.mar -P /home/torchserve/model-store/
RUN wget https://github.com/facebookresearch/AnimatedDrawings/releases/download/v0.0.1/drawn_humanoid_pose_estimator.mar -P /home/torchserve/model-store/
COPY torchserve/config.properties /home/torchserve/config.properties

### Prepare the rpc server
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION python

WORKDIR /app
COPY requirements.txt /app/
RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . /app

EXPOSE 50051

WORKDIR /app

RUN chmod +x start.sh

# starting command
CMD ["./start.sh"]