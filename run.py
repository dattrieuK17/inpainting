from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import os
from PIL import Image
import cv2
from omegaconf import OmegaConf
import yaml
import torch
import numpy as np
import sys 
sys.path.append(os.path.abspath("lama"))

from lama.saicinpainting.evaluation.utils import move_to_device
from lama.saicinpainting.training.trainers import load_checkpoint
app = Flask(__name__)

# Cấu hình thư mục lưu trữ file upload
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Hàm resize ảnh trước khi lưu
def resize_image(file):
    img = Image.open(file)
    width, height = img.size

    # Nếu một trong hai chiều nhỏ hơn 512px, giữ nguyên
    if width < 512 or height < 512:
        return img  

    # Lấy giá trị nhỏ nhất giữa width và height
    min_dim = min(width, height)

    # Resize về 512px nhưng giữ nguyên tỉ lệ
    scale_factor = 512 / min_dim
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    # Ensure dimensions are divisible by 8
    new_width = ((new_width + 7) // 8) * 8
    new_height = ((new_height + 7) // 8) * 8

    img = img.resize((new_width, new_height), Image.LANCZOS)
    return img

def load_model():
    model_path = "big-lama"  # Đường dẫn thư mục chứa model
    checkpoint = "models/best.ckpt"
    train_config_path = os.path.join(model_path, 'config.yaml')
    checkpoint_path = os.path.join(model_path, checkpoint)
    
    with open(train_config_path, 'r') as f:
        train_config = OmegaConf.create(yaml.safe_load(f))
    train_config.training_model.predict_only = True
    train_config.visualizer.kind = 'noop'
    
    model = load_checkpoint(train_config, checkpoint_path, strict=False, map_location='cpu')
    model.freeze()
    return model

model = load_model()


@app.route('/')
def index():
    return render_template('introduce.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'uploadedFile' not in request.files:
            print("No file part in request")
            return redirect(url_for('index'))

        file = request.files['uploadedFile']
        if file.filename == '':
            print("No selected file")
            return redirect(url_for('index'))

        # Check if file is allowed
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            print("File type not allowed")
            return redirect(url_for('index'))

        # Resize và preprocess ảnh trước khi lưu
        img = resize_image(file)

        # Lưu ảnh đã resize
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img.save(filepath, quality=95)  # Save with high quality
        print(f"File saved successfully at: {filepath}")
        print(f"Image dimensions: {img.size}")

        return redirect(url_for('edit', filename=filename))
    except Exception as e:
        print(f"Error during upload: {str(e)}")
        return redirect(url_for('index'))

@app.route('/edit')
def edit():
    try:
        filename = request.args.get('filename')
        if not filename:
            print("No filename provided")
            return redirect(url_for('index'))

        # Verify file exists
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return redirect(url_for('index'))

        # Verify it's an image file
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            print(f"Invalid file type: {filename}")
            return redirect(url_for('index'))

        return render_template('edit.html', filename=filename)
    except Exception as e:
        print(f"Error in edit route: {str(e)}")
        return redirect(url_for('index'))


@app.route("/save-mask/<filename>", methods=["POST"])
def save_mask(filename):
    if "mask" not in request.files:
        return jsonify({"error": "No mask uploaded"}), 400
    
    mask = request.files["mask"]
    mask_filename = f"mask-{filename}"
    mask_path = os.path.join(app.config["UPLOAD_FOLDER"], mask_filename)

    mask.save(mask_path)
    return jsonify({"message": f"Mask saved as {mask_filename}"}), 200

@app.route("/inpaint/<filename>", methods=["POST"])
def inpaint(filename):
    try:
        # Đọc ảnh gốc và mask từ thư mục lưu trữ
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        mask_path = os.path.join(app.config["UPLOAD_FOLDER"], f"mask-{filename}")

        if not os.path.exists(image_path) or not os.path.exists(mask_path):
            return jsonify({"error": "Image or mask not found"}), 400

        # Read image and mask using PIL
        image = Image.open(image_path).convert('RGB')
        mask = Image.open(mask_path).convert('L')  # Convert to grayscale

        # Convert PIL images to numpy arrays
        image_np = np.array(image)
        mask_np = np.array(mask)

        # Ensure mask is binary (0 or 255)
        mask_np = (mask_np > 128).astype(np.uint8) * 255

        # Pad image and mask to be divisible by 8
        h, w = image_np.shape[:2]
        pad_h = (8 - h % 8) % 8
        pad_w = (8 - w % 8) % 8
        if pad_h > 0 or pad_w > 0:
            image_np = np.pad(image_np, ((0, pad_h), (0, pad_w), (0, 0)), mode='constant')
            mask_np = np.pad(mask_np, ((0, pad_h), (0, pad_w)), mode='constant')

        # Convert to tensor
        image_tensor = torch.from_numpy(image_np.transpose(2, 0, 1)).float() / 255.0
        mask_tensor = torch.from_numpy(mask_np).float().unsqueeze(0) / 255.0
        mask_tensor = (mask_tensor > 0).float()  # Convert to binary

        # Move tensors to model
        batch = {"image": image_tensor.unsqueeze(0), "mask": mask_tensor.unsqueeze(0)}
        batch = move_to_device(batch, "cpu")

        # Generate result
        with torch.no_grad():
            batch = model(batch)
            result = batch["inpainted"][0].permute(1, 2, 0).cpu().numpy()

        # Remove padding from result
        if pad_h > 0 or pad_w > 0:
            result = result[:h, :w]

        # Convert result back to PIL Image
        result = np.clip(result * 255, 0, 255).astype('uint8')
        result_image = Image.fromarray(result)

        # Save result
        result_filename = f"inpainted-{filename}"
        result_path = os.path.join(app.config["UPLOAD_FOLDER"], result_filename)
        result_image.save(result_path, quality=95)

        print(f"Inpainting hoàn thành! Ảnh lưu tại: {result_path}")

        return jsonify({"message": "Inpainting completed", "result": result_filename}), 200
    except Exception as e:
        print(f"Error during inpainting: {str(e)}")  # Add error logging
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)