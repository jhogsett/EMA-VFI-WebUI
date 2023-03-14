"""Core Code for all frame interpolations"""
import os
import cv2
import sys
import torch
import numpy as np
import argparse
from tqdm import tqdm
from imageio import imsave
import argparse
from typing import Callable
from webui_utils.simple_log import SimpleLog
from webui_utils.simple_utils import sortable_float_index
from webui_utils.file_utils import split_filepath
from interpolate_engine import InterpolateEngine

'''==========import from our code=========='''
sys.path.append('.')
from benchmark.utils.padder import InputPadder # pylint: disable=import-error

def main():
    """Use Frame Interpolation from the command line"""
    parser = argparse.ArgumentParser(description='Video Frame Interpolation (shallow)')
    parser.add_argument('--model',
        default='ours', type=str)
    parser.add_argument('--gpu_ids', type=str, default='0',
        help='gpu ids: e.g. 0  0,1,2, 0,2. use -1 for CPU (FUTURE USE)')
    parser.add_argument('--img_before', default="images/image0.png", type=str,
        help="Path to before frame image")
    parser.add_argument('--img_after', default="images/image2.png", type=str,
        help="Path to after frame image")
    parser.add_argument('--img_new', default="images/image1.png", type=str,
        help="Path to new middle frame image")
    parser.add_argument("--time_step", dest="time_step", default=Interpolate.STD_MIDFRAME,
        type=float, help="Middle frame time step if one frame (Default: 0.5)")
    parser.add_argument("--multiple", dest="multiple", default=1,
        type=int, help="Create multiple evenly-spaced frames if > 1 (Default: 1)")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
        help="Show extra details")
    args = parser.parse_args()

    log = SimpleLog(args.verbose)
    use_time_step = args.multiple > 1 or args.time_step != Interpolate.STD_MIDFRAME
    engine = InterpolateEngine(args.model, args.gpu_ids, use_time_step)
    interpolater = Interpolate(engine.model, log.log)

    if args.multiple > 1:
        interpolater.create_between_frames(args.img_before, args.img_after, args.img_new,
                                           args.multiple)
    else:
        interpolater.create_between_frame(args.img_before, args.img_after, args.img_new,
                                          args.time_step)

class Interpolate:
    """Encapsulate logic for the Frame Interpolation feature"""
    STD_MIDFRAME = 0.5

    def __init__(self,
                model,
                log_fn : Callable | None):
        self.model = model
        self.log_fn = log_fn
        self.output_paths = []

    def create_between_frame(self,
                            before_filepath : str,
                            after_filepath : str,
                            middle_filepath : str,
                            time_step : float = STD_MIDFRAME):
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

        mid = (padder.unpad(model.inference(I0_, I2_, TTA=TTA, fast_TTA=TTA, timestep = time_step))[0].detach().cpu().numpy().transpose(1, 2, 0) * 255.0).astype(np.uint8)
        images = [I0[:, :, ::-1], mid[:, :, ::-1], I2[:, :, ::-1]]
        imsave(middle_filepath, images[1])
        self.output_paths.append(middle_filepath)
        self.log("create_between_frame() saved " + middle_filepath)

    def create_between_frames(self,
                            before_filepath : str,
                            after_filepath : str,
                            middle_filepath : str,
                            frame_count : int):
        """Invoke the Frame Interpolation feature for multiple between frames
           frame_count is the number of new frames, ex: 8X interpolation, 7 new frames are needed
        """
        # code borrowed from EMA-VFI/demo_2x.py
        I0 = cv2.imread(before_filepath)
        I2 = cv2.imread(after_filepath)

        I0_ = (torch.tensor(I0.transpose(2, 0, 1)).cuda() / 255.).unsqueeze(0)
        I2_ = (torch.tensor(I2.transpose(2, 0, 1)).cuda() / 255.).unsqueeze(0)

        padder = InputPadder(I0_.shape, divisor=32)
        I0_, I2_ = padder.pad(I0_, I2_)

        model = self.model["model"]
        TTA = self.model["TTA"]
        set_count = 2 if frame_count < 1 else frame_count + 1

        output_path, filename, extension = split_filepath(middle_filepath)
        output_filepath = os.path.join(output_path, f"{filename}@0.0.png")
        images = [I0[:, :, ::-1]]
        imsave(output_filepath, images[0])
        self.output_paths.append(output_filepath)
        self.log("create_between_frames() saved " + output_filepath)

        preds = model.multi_inference(I0_, I2_, TTA=TTA, time_list=[(i+1)*(1./set_count) for i in range(set_count - 1)], fast_TTA=TTA)
        for pred in preds:
            images.append((padder.unpad(pred).detach().cpu().numpy().transpose(1, 2, 0) * 255.0).astype(np.uint8)[:, :, ::-1])
        images.append(I2[:, :, ::-1])

        pbar_desc = "Writing frames"
        for index, image in enumerate(tqdm(images, desc=pbar_desc)):
            if 0 < index < len(images) - 1:
                time = sortable_float_index(index / set_count)
                output_filepath = os.path.join(output_path, f"{filename}@{time}.png")
                imsave(output_filepath, image)
                self.output_paths.append(output_filepath)
                self.log("create_between_frames() saved " + output_filepath)

        output_filepath = os.path.join(output_path, f"{filename}@1.0.png")
        imsave(output_filepath, images[-1])
        self.output_paths.append(output_filepath)
        self.log("create_between_frames() saved " + output_filepath)

    def log(self, message):
        """Logging"""
        if self.log_fn:
            self.log_fn(message)

if __name__ == '__main__':
    main()
