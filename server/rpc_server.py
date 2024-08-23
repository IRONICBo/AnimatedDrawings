import os
import sys
from concurrent import futures
import time
import uuid

import grpc
import etcd3
import threading
from minio import Minio
from minio.error import S3Error
import yaml
from qiniu import Auth, put_file, etag
import qiniu.config

from rpc import animate_service_pb2, animate_service_pb2_grpc
from server.service import animate_service
import argparse


LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(LOCAL_PATH, '..'))
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/rpc')

def init_minio():
    minio_client = Minio(
        "real-dream-ai:9000",
        access_key="minioadmin",
        secret_key="real-dream-ai",
        secure=False
    )

    bucket_name = "mybucket"
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            print(f"Bucket '{bucket_name}' created.")
        else:
            print(f"Bucket '{bucket_name}' already exists.")
    except S3Error as e:
        print(f"MinIO error: {e}")

    try:
        minio_client.fput_object(bucket_name, "hello.txt", "/path/to/hello.txt")
        print("File 'hello.txt' uploaded to bucket 'mybucket'.")
    except S3Error as e:
        print(f"MinIO error during upload: {e}")


def register_with_etcd(etcd_host, etcd_port, etcd_key, etcd_value, ttl=10):
    etcd = etcd3.client(host=etcd_host, port=etcd_port)
    key = etcd_key + '/' + str(uuid.uuid4().int)
    value = etcd_value
    lease = etcd.lease(ttl)
    etcd.put(key, value, lease)
    print(f"Registered {value} with key {key} in etcd.")

    try:
        while True:
            lease.refresh()
            print(f"Lease for key {key} refreshed with TTL {ttl} seconds.")
            time.sleep(ttl / 2)
    except KeyboardInterrupt:
        print("Stopping keepalive.")
    finally:
        lease.revoke()

def create_minio_client(endpoint, access_key, secret_key, use_ssl):
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=use_ssl
    )

def create_qiniu_client(endpoint,  access_key, secret_key):
    return Auth(access_key, secret_key)

def serve(minio_client, bucket_name, host, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    animate_service_pb2_grpc.add_AnimateServiceServicer_to_server(animate_service.AnimateServiceServicer(minio_client, bucket_name), server)
    # server.add_insecure_port('[::]:50051')
    server.add_insecure_port('{}:{}'.format(host, port))
    server.start()
    print("Server started on {}:{}".format(host, port))
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

def parse_args():
    parser = argparse.ArgumentParser(description='RPC Server')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    config_file = args.config

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    print(f"Loaded config: {config}")

    register_key = config['ContainerName']+":"+str(config['Port'])
    etcd_thread = threading.Thread(target=register_with_etcd, args=(config['ETCD']['Host'], config['ETCD']['Port'], config['Name'], register_key))
    etcd_thread.start()

    # minio_client = create_minio_client(config['Minio']['Endpoint'], config['Minio']['AccessKeyID'], config['Minio']['SecretAccessKey'], config['Minio']['UseSSL'])
    qiniu_client = create_qiniu_client(config['Minio']['Endpoint'], config['Minio']['AccessKeyID'], config['Minio']['SecretAccessKey'])
    serve(qiniu_client, config['Minio']['BucketName'], config['Host'], config['Port'])
