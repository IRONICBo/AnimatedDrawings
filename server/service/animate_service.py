from datetime import timedelta
from http.client import HTTPException
import io
import logging
import os
import shutil
import time
import uuid
from PIL import Image
from examples.image_to_animation import default_image_to_animation
from minio import Minio, S3Error
import numpy as np
from qiniu import Auth, put_file, etag
import qiniu.config

import os
import sys
import requests

from rpc import animate_service_pb2_grpc, animate_service_pb2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

# import parent directory
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
sys.path.append(project_root)


COMFYUI_SYNC_API_TIMOUT = 60
WORKFLOW_PROMPT = '''{"prompt":{"3":{"inputs":{"seed":712663807850154,"steps":20,"cfg":8,"sampler_name":"euler","scheduler":"normal","denoise":1,"model":["4",0],"positive":["6",0],"negative":["7",0],"latent_image":["5",0]},"class_type":"KSampler"},"4":{"inputs":{"ckpt_name":"v1-5-pruned-emaonly.ckpt"},"class_type":"CheckpointLoaderSimple"},"5":{"inputs":{"width":512,"height":512,"batch_size":1},"class_type":"EmptyLatentImage"},"6":{"inputs":{"text":"USER_INPUT_PROMPT","clip":["4",1]},"class_type":"CLIPTextEncode"},"7":{"inputs":{"text":"text, watermark","clip":["4",1]},"class_type":"CLIPTextEncode"},"8":{"inputs":{"samples":["3",0],"vae":["4",2]},"class_type":"VAEDecode"},"9":{"inputs":{"filename_prefix":"ComfyUI","images":["8",0]},"class_type":"SaveImage"}},"extra_data":{"extra_pnginfo":{"workflow":{"last_node_id":9,"last_link_id":9,"nodes":[{"id":7,"type":"CLIPTextEncode","pos":[413,389],"size":{"0":425.27801513671875,"1":180.6060791015625},"flags":{},"order":3,"mode":0,"inputs":[{"name":"clip","type":"CLIP","link":5}],"outputs":[{"name":"CONDITIONING","type":"CONDITIONING","links":[6],"slot_index":0}],"properties":{"Node name for S&R":"CLIPTextEncode"},"widgets_values":["text, watermark"]},{"id":6,"type":"CLIPTextEncode","pos":[415,186],"size":{"0":422.84503173828125,"1":164.31304931640625},"flags":{},"order":2,"mode":0,"inputs":[{"name":"clip","type":"CLIP","link":3}],"outputs":[{"name":"CONDITIONING","type":"CONDITIONING","links":[4],"slot_index":0}],"properties":{"Node name for S&R":"CLIPTextEncode"},"widgets_values":["beautiful scenery nature glass bottle landscape, , purple galaxy bottle,"]},{"id":5,"type":"EmptyLatentImage","pos":[473,609],"size":{"0":315,"1":106},"flags":{},"order":0,"mode":0,"outputs":[{"name":"LATENT","type":"LATENT","links":[2],"slot_index":0}],"properties":{"Node name for S&R":"EmptyLatentImage"},"widgets_values":[512,512,1]},{"id":3,"type":"KSampler","pos":[863,186],"size":{"0":315,"1":262},"flags":{},"order":4,"mode":0,"inputs":[{"name":"model","type":"MODEL","link":1},{"name":"positive","type":"CONDITIONING","link":4},{"name":"negative","type":"CONDITIONING","link":6},{"name":"latent_image","type":"LATENT","link":2}],"outputs":[{"name":"LATENT","type":"LATENT","links":[7],"slot_index":0}],"properties":{"Node name for S&R":"KSampler"},"widgets_values":[712663807850154,"randomize",20,8,"euler","normal",1]},{"id":8,"type":"VAEDecode","pos":[1209,188],"size":{"0":210,"1":46},"flags":{},"order":5,"mode":0,"inputs":[{"name":"samples","type":"LATENT","link":7},{"name":"vae","type":"VAE","link":8}],"outputs":[{"name":"IMAGE","type":"IMAGE","links":[9],"slot_index":0}],"properties":{"Node name for S&R":"VAEDecode"}},{"id":9,"type":"SaveImage","pos":[1451,189],"size":[210,270],"flags":{},"order":6,"mode":0,"inputs":[{"name":"images","type":"IMAGE","link":9}],"properties":{},"widgets_values":["ComfyUI"]},{"id":4,"type":"CheckpointLoaderSimple","pos":[26,474],"size":{"0":315,"1":98},"flags":{},"order":1,"mode":0,"outputs":[{"name":"MODEL","type":"MODEL","links":[1],"slot_index":0},{"name":"CLIP","type":"CLIP","links":[3,5],"slot_index":1},{"name":"VAE","type":"VAE","links":[8],"slot_index":2}],"properties":{"Node name for S&R":"CheckpointLoaderSimple"},"widgets_values":["v1-5-pruned-emaonly.ckpt"]}],"links":[[1,4,0,3,0,"MODEL"],[2,5,0,3,3,"LATENT"],[3,4,1,6,0,"CLIP"],[4,6,0,3,1,"CONDITIONING"],[5,4,1,7,0,"CLIP"],[6,7,0,3,2,"CONDITIONING"],[7,3,0,8,0,"LATENT"],[8,4,2,8,1,"VAE"],[9,8,0,9,0,"IMAGE"]],"groups":[],"config":{},"extra":{"ds":{"scale":1,"offset":[-214.72216796875,-16.35418701171875]}},"version":0.4}}}}'''

INPUT_DIR = "./input"
OUTPUT_DIR = "./output"

minio_client = Minio(
    "real-dream-ai:9000",
    access_key="minioadmin",
    secret_key="real-dream-ai",
    secure=False
)

if not os.path.exists(INPUT_DIR):
    os.makedirs(INPUT_DIR)
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

class AnimateServiceServicer(animate_service_pb2_grpc.AnimateServiceServicer):
    def __init__(self, minio_client, bucket_name):
        self.minio_client = minio_client
        self.bucket_name = bucket_name
        print(f"client: {minio_client}, bucket: {bucket_name}")
        logging.info("Initialized SDGenerateServiceServicer")

    def ProcessImage(self, request, context):
        image_url = request.image_url
        image_data = self.download_image(image_url)
        image = Image.open(io.BytesIO(image_data))

        # image = Image.open(io.BytesIO(request.image_url))
        # save to input directory with generated uuid
        uid = uuid.uuid4()
        img_path = f"{INPUT_DIR}/{uid}.png"
        save_dir = f"{OUTPUT_DIR}/{uid}/"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        image.save(img_path)

        default_image_to_animation(img_path, save_dir)

        # copy /tmp/out_anim.json & /tmp/out_mesh.json & /tmp/out_mesh.obj to save_dir
        shutil.copy("/tmp/out_anim.json", f"{save_dir}/out_anim.json")
        shutil.copy("/tmp/out_mesh.json", f"{save_dir}/out_mesh.json")
        shutil.copy("/tmp/out_mesh.obj", f"{save_dir}/out_mesh.obj")

        # pack the output files to a zip file
        shutil.make_archive(save_dir, 'zip', save_dir)

        logging.info(f"Generated animation for image: {image_url} to {save_dir}.zip")

        url = self.upload_file_qiniu(f"{uid}.zip", f"{OUTPUT_DIR}/{uid}.zip")
        print(f"Uploaded material to {url}")

        return animate_service_pb2.AnimateResponse(material_url=url)

    def get_image_data(self, image_path):
        """Retrieve the actual image from the ComfyUI server and return it as bytes."""
        view_url = f'http://127.0.0.1:8188/view?filename={image_path}'
        response = requests.get(view_url)
        if response.status_code == 200:
            return response.content
        return None

    def download_image(self, image_url):
        """donwload image to local with open url"""
        request = requests.get(image_url)
        image_data = request.content
        return image_data

    def upload_file_qiniu(self, object_name, file_path):
        print(f"Uploading '{file_path}' as object '{object_name}' to bucket '{self.bucket_name}'...")
        client = self.minio_client
        bucket_name = self.bucket_name
        token = client.upload_token(bucket_name, object_name, 3600)
        print(f"upload token: {token}")
        ret, info = put_file(token, object_name, file_path, version='v2')
        print(f"'{file_path}' is successfully uploaded as object '{object_name}' to bucket '{bucket_name}'.")
        print(f"ret:{ret} info:{info}")
        url = f"http://aigc-static-test.goplus.org/{object_name}"

        return url

    def upload_file(self, object_name, file_path):
        minio_client = self.minio_client
        bucket_name = self.bucket_name
        found = minio_client.bucket_exists(bucket_name)
        if not found:
            minio_client.make_bucket(bucket_name)
        else:
            print(f"Bucket '{bucket_name}' already exists")

        try:
            minio_client.fput_object(bucket_name, object_name, file_path)
            print(f"'{file_path}' is successfully uploaded as object '{object_name}' to bucket '{bucket_name}'.")

            # generate a presigned URL for the uploaded file
            # url = minio_client.presigned_get_object(bucket_name, object_name, expires=timedelta(days=1))
            # generate a public URL for the uploaded file
            url = f"http://minio:9000/{bucket_name}/{object_name}"
            print(f"Publicly accessible URL: {url}")
            return url
        except S3Error as exc:
            print("Error occurred.", exc)