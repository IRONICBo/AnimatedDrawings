# Copyright (c) Meta Platforms, Inc. and affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from image_to_annotations import image_to_annotations
from annotations_to_animation import annotations_to_animation
from pathlib import Path
import logging
import sys
from pkg_resources import resource_filename
import os
import argparse

EDrawService_Nothing = 0
EDrawService_BoundingBox = 1
EDrawService_Segment = 2
EDrawService_KeyPoint = 3
EDrawService_Retarget = 4
EDrawService_AllButRetarget = 5
EDrawService_All = 6
    
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t",'--type', type=int, default=0, help='delete the output dir')
    parser.add_argument("-o",'--output', type=str, default='data/json/body17', help='The destination directory')
    parser.add_argument("-i",'--input', type=str, default='data/motion3d/body17/', help='The destination directory')
    parser.add_argument('--motion_cfg_fn', type=str, default='config/motion/dab.yaml', help='The destination directory')
    parser.add_argument('--retarget_cfg_fn', type=str, default='config/retarget/fair1_ppf.yaml', help='The destination directory')

    opts = parser.parse_args()
    return opts



if __name__ == '__main__':
    log_dir = Path('./logs')
    log_dir.mkdir(exist_ok=True, parents=True)
    logging.basicConfig(filename=f'{log_dir}/log.txt', level=logging.DEBUG)
    opts = parse_args()
    
    img_fn = opts.input
    char_anno_dir = opts.output
    motion_cfg_fn = resource_filename(__name__, opts.motion_cfg_fn)
    retarget_cfg_fn = resource_filename(__name__, opts.retarget_cfg_fn)
    type = opts.type
    if EDrawService_Nothing == type :
        print("Do nothing skip")
    elif EDrawService_BoundingBox == type:
        image_to_annotations(img_fn, char_anno_dir) # TODO
    elif EDrawService_Segment == type:
        image_to_annotations(img_fn, char_anno_dir) # TODO
    elif EDrawService_KeyPoint == type:
        image_to_annotations(img_fn, char_anno_dir) # TODO
    elif EDrawService_Retarget == type:
        annotations_to_animation(char_anno_dir, motion_cfg_fn, retarget_cfg_fn)
    elif EDrawService_AllButRetarget == type:
        image_to_annotations(img_fn, char_anno_dir)
    elif EDrawService_All == type:
        image_to_annotations(img_fn, char_anno_dir)
        annotations_to_animation(char_anno_dir, motion_cfg_fn, retarget_cfg_fn)
