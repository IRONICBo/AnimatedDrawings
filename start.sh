#!/bin/sh
cd rpcserver && PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 rpc_server.py --config config_prod.yaml &
# Go to the directory where the main.py is located
/opt/conda/bin/torchserve --start --disable-token-auth --ncs --ts-config /home/torchserve/config.properties &
wait
