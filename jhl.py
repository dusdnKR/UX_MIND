import os
import sys
from typing import Literal, Dict, Optional
import fire
import cv2
import numpy as np
import torch
from diffusers import LCMScheduler, StableDiffusionControlNetPipeline, ControlNetModel
from diffusers.utils import load_image
from controlnet_aux import OpenposeDetector
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from utils.wrapper import StreamDiffusionWrapper
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
def main(
    model_id_or_path: str = "stabilityai/sd-turbo", #"stabilityai/sd-turbo", "stabilityai/sdxl-turbo"
    lora_dict: Optional[Dict[str, float]] = None,
    prompt: str = "happy woman, party, flower, ballon, face painting",
    # Joker: Portrait of The Joker halloween costume, face painting, glare pose, detailed, intricate, full of color, cinematic lighting, hyperrealistic, extreme details, masterpiece
    negative_prompt: str = "low quality, worst quality",
    width: int = 720,
    height: int = 480,
    acceleration: Literal["none", "xformers", "tensorrt"] = "xformers",
    use_denoising_batch: bool = True,
    guidance_scale: float = 1,
    cfg_type: Literal["none", "full", "self", "initialize"] = "self",\
    seed: int = 123,
    delta: float = 1,
):
    """
    Initializes the StreamDiffusionWrapper.
    Parameters
    ----------
    model_id_or_path : str
        The model id or path to load.
    lora_dict : Optional[Dict[str, float]], optional
        The lora_dict to load, by default None.
        Keys are the LoRA names and values are the LoRA scales.
        Example: {'LoRA_1' : 0.5 , 'LoRA_2' : 0.7 ,...}
    prompt : str
        The prompt to generate images from.
    negative_prompt : str, optional
        The negative prompt to use.
    width : int, optional
        The width of the image, by default 512.
    height : int, optional
        The height of the image, by default 512.
    acceleration : Literal["none", "xformers", "tensorrt"], optional
        The acceleration method, by default "tensorrt".
    use_denoising_batch : bool, optional
        Whether to use denoising batch or not, by default True.
    guidance_scale : float, optional
        The CFG scale, by default 1.2.
    cfg_type : Literal["none", "full", "self", "initialize"],
    optional
        The cfg_type for img2img mode, by default "self".
        You cannot use anything other than "none" for txt2img mode.
    seed : int, optional
        The seed, by default 2. if -1, use random seed.
    delta : float, optional
        The delta multiplier of virtual residual noise,
        by default 1.0.
    """
    stream = StreamDiffusionWrapper(
        model_id_or_path=model_id_or_path,
        lora_dict=lora_dict,
        t_index_list=[27], #28    24, 30, 35
        frame_buffer_size=1,
        width=width,
        height=height,
        warmup=10,
        acceleration=acceleration,
        mode="img2img",
        use_denoising_batch=use_denoising_batch,
        cfg_type=cfg_type,
        seed=seed,
    )
    stream.prepare(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=50,
        guidance_scale=guidance_scale,
        delta=delta,
    )
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame from webcam.")
                break
            # Save frame to temporary file
            temp_input_path = os.path.join(CURRENT_DIR, "temp_input.png")
            cv2.imwrite(temp_input_path, frame)
            output_image = stream(image=temp_input_path)
            # Convert PIL image to OpenCV format
            output_image_cv = cv2.cvtColor(np.array(output_image), cv2.COLOR_RGB2BGR)
            # Display the output image
            cv2.imshow('Output', output_image_cv)
            # Exit loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
if __name__ == "__main__":
    fire.Fire(main)