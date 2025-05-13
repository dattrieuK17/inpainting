import os
import re
from PIL import Image
import numpy as np
import torch
import yaml
from omegaconf import OmegaConf
from lama.saicinpainting.training.trainers import load_checkpoint
from lama.saicinpainting.evaluation.utils import move_to_device

MIN_SIZE = 1024
device = "cuda" if torch.cuda.is_available() else "cpu"

def resize_image(file):
    img = Image.open(file)
    width, height = img.size

    if width < MIN_SIZE or height < MIN_SIZE:
        return img

    min_dim = min(width, height)
    scale_factor = MIN_SIZE / min_dim
    new_width = ((int(width * scale_factor) + 7) // 8) * 8
    new_height = ((int(height * scale_factor) + 7) // 8) * 8

    return img.resize((new_width, new_height), Image.LANCZOS)

def load_model():
    model_path = "LaMa_models/big-lama"
    checkpoint = "models/best.ckpt"
    config_path = os.path.join(model_path, 'config.yaml')
    checkpoint_path = os.path.join(model_path, checkpoint)

    with open(config_path, 'r') as f:
        train_config = OmegaConf.create(yaml.safe_load(f))
    train_config.training_model.predict_only = True
    train_config.visualizer.kind = 'noop'

    model = load_checkpoint(train_config, checkpoint_path, strict=False, map_location=device)
    model.to(device)
    model.freeze()
    return model

def get_base_name(filename):
    filename_wo_ext = os.path.splitext(filename)[0]
    match = re.search(r"(?:inpainted-)*(.+?)(?:_\d+)?$", filename_wo_ext)
    return match.group(1) if match else filename_wo_ext

def prepare_batch(image, mask):
    image_np = np.array(image.convert("RGB"))
    mask_np = np.array(mask.convert("L"))
    mask_np = (mask_np > 128).astype(np.uint8) * 255

    h, w = image_np.shape[:2]
    pad_h = (8 - h % 8) % 8
    pad_w = (8 - w % 8) % 8

    if pad_h or pad_w:
        image_np = np.pad(image_np, ((0, pad_h), (0, pad_w), (0, 0)), mode="constant")
        mask_np = np.pad(mask_np, ((0, pad_h), (0, pad_w)), mode="constant")

    image_tensor = torch.from_numpy(image_np.transpose(2, 0, 1)).float() / 255.0
    mask_tensor = torch.from_numpy(mask_np).float().unsqueeze(0) / 255.0
    mask_tensor = (mask_tensor > 0).float()

    batch = {"image": image_tensor.unsqueeze(0), "mask": mask_tensor.unsqueeze(0)}
    return move_to_device(batch, device), (h, w)

def get_next_inpaint_index(base_name, folder):
    pattern = re.compile(rf"inpainted-{re.escape(base_name)}_(\d+)\.jpg")
    existing = [f for f in os.listdir(folder) if pattern.match(f)]
    indices = [int(pattern.match(f).group(1)) for f in existing]
    return max(indices, default=0) + 1
