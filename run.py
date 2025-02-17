from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
from PIL import Image
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

    img = img.resize((new_width, new_height), Image.LANCZOS)
    return img

@app.route('/')
def index():
    return render_template('introduce.html')

@app.route('/introduce', methods=['POST'])
def upload():
    if 'uploadedFile' not in request.files:
        return redirect(url_for('index'))

    file = request.files['uploadedFile']
    if file.filename == '':
        return redirect(url_for('index'))

    # Resize ảnh trước khi lưu
    img = resize_image(file)

    # Lưu ảnh đã resize
    filename = file.filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img.save(filepath)  # Lưu dưới dạng ảnh gốc

    return redirect(url_for('edit', filename=filename))

@app.route('/edit')
def edit():
    filename = request.args.get('filename')
    if not filename:
        return "No file provided", 400

    # Trang chỉnh sửa sử dụng file đã upload
    return render_template('edit.html', filename=filename)

if __name__ == '__main__':
    app.run(debug=True)
