"""Core Code for all frame interpolations"""
import cv2
import sys
import torch
import numpy as np
import argparse
from imageio import imsave
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from interpolate_engine import InterpolateEngine

'''==========import from our code=========='''
sys.path.append('.')
from benchmark.utils.padder import InputPadder

def main():
    """Use Frame Interpolation from the command line"""
    parser = argparse.ArgumentParser(description='Video Frame Interpolation (shallow)')
    parser.add_argument('--model',
        default='ours', type=str)
    parser.add_argument('--gpu_ids', type=str, default='0',
        help='gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU (FUTURE USE)')
    parser.add_argument('--img_before', default="./images/image0.png", type=str,
        help="Path to before frame image")
    parser.add_argument('--img_after', default="./images/image2.png", type=str,
        help="Path to after frame image")
    parser.add_argument('--img_new', default="./images/image1.png", type=str,
        help="Path to new middle frame image")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    engine = InterpolateEngine(args.model, args.gpu_ids)
    interpolater = Interpolate(engine.model, log.log)
    interpolater.create_between_frame(args.img_before, args.img_after, args.img_new)

class Interpolate:
    """Encapsulate logic for the Frame Interpolation feature"""
    def __init__(self,
                model,
                log_fn : Callable | None):
        self.model = model
        self.log_fn = log_fn

    def create_between_frame(self,
                            before_filepath : str,
                            after_filepath : str,
                            middle_filepath : str):
        """Invoke the Frame Interpolation feature"""
        # code borrowed from EMA-VFI/demo_2x.py
        I0 = cv2.imread(before_filepath)
        I2 = cv2.imread(after_filepath)

        I0_ = (torch.tensor(I0.transpose(2, 0, 1)).cuda() / 255.).unsqueeze(0)
        I2_ = (torch.tensor(I2.transpose(2, 0, 1)).cuda() / 255.).unsqueeze(0)

        padder = InputPadder(I0_.shape, divisor=32)
        I0_, I2_ = padder.pad(I0_, I2_)

        model = self.model["model"]
        TTA = self.model["TTA"]

        mid = (padder.unpad(model.inference(I0_, I2_, TTA=TTA, fast_TTA=TTA))[0].detach().cpu().numpy().transpose(1, 2, 0) * 255.0).astype(np.uint8)
        images = [I0[:, :, ::-1], mid[:, :, ::-1], I2[:, :, ::-1]]
        imsave(middle_filepath, images[1])
        self.log("create_mid_frame() saved " + middle_filepath)

    def log(self, message):
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
