from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import os
import shutil
from PIL import Image
import sys
import torch
import numpy as np
sys.path.append(os.path.abspath("lama"))
import traceback
from utils import (
    resize_image,
    load_model,
    get_base_name,
    prepare_batch,
    get_next_inpaint_index
)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['INPAINTED_FOLDER'] = 'static/inpainted'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if os.path.exists(app.config['INPAINTED_FOLDER']):
    shutil.rmtree(app.config['INPAINTED_FOLDER'])
os.makedirs(app.config['INPAINTED_FOLDER'], exist_ok=True)

model = load_model()

@app.route('/')
def index():
    return render_template('introduce.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('uploadedFile')
        if not file or file.filename == '':
            return redirect(url_for('index'))

        if file.filename.rsplit('.', 1)[1].lower() not in {'png', 'jpg', 'jpeg', 'webp'}:
            return redirect(url_for('index'))

        img = resize_image(file)
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img.save(filepath, quality=95)
        return redirect(url_for('edit', filename=filename))
    except Exception as e:
        print(f"Upload error: {e}")
        return redirect(url_for('index'))

@app.route('/edit')
def edit():
    filename = request.args.get('filename')
    if not filename:
        return redirect(url_for('index'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return redirect(url_for('index'))

    return render_template('edit.html', filename=filename)

@app.route("/reset/<filename>", methods=["POST"])
def reset(filename):
    try:
        base_name = get_base_name(filename)
        folder = app.config['INPAINTED_FOLDER']
        deleted = []

        for f in os.listdir(folder):
            if re.fullmatch(rf"inpainted-{re.escape(base_name)}_\d+\.jpg", f):
                os.remove(os.path.join(folder, f))
                deleted.append(f)

        return jsonify({"message": "Reset completed", "deleted": deleted}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/inpaint/<filename>", methods=["POST"])
def inpaint(filename):
    try:
        if "mask" not in request.files:
            return jsonify({"error": "Mask not uploaded"}), 400

        folder = app.config["INPAINTED_FOLDER"] if filename.startswith("inpainted-") else app.config["UPLOAD_FOLDER"]
        image_path = os.path.join(folder, filename)
        if not os.path.exists(image_path):
            return jsonify({"error": "Image not found"}), 400

        image = Image.open(image_path)
        mask = Image.open(request.files["mask"])
        batch, original_size = prepare_batch(image, mask)
        print("Running model...")
        with torch.no_grad():
            result = model(batch)["inpainted"][0].permute(1, 2, 0).cpu().numpy()
        print("Model ran successfully")
        h, w = original_size
        result = result[:h, :w]
        result_img = Image.fromarray(np.clip(result * 255, 0, 255).astype(np.uint8))

        base_name = get_base_name(filename)
        i = get_next_inpaint_index(base_name, app.config["INPAINTED_FOLDER"])
        result_filename = f"inpainted-{base_name}_{i}.jpg"
        result_path = os.path.join(app.config["INPAINTED_FOLDER"], result_filename)
        result_img.save(result_path, quality=95)

        return jsonify({"message": "Inpainting completed", "result": result_filename, "i": i}), 200
    except Exception as e:
        print("Error during inpainting:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
