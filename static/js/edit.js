const imageCanvas = document.getElementById("imageCanvas");
const maskCanvas = document.getElementById("maskCanvas");
const imageCtx = imageCanvas.getContext("2d");
const maskCtx = maskCanvas.getContext("2d");

let painting = false;
let brushSize = 15;
let isEraser = false;
let lastX, lastY;

const img = new Image();
img.src = `/static/uploads/${filename}`;
img.onload = function () {
    const size = getResizedSize(img.width, img.height);

    imageCanvas.width = size.width;
    imageCanvas.height = size.height;
    maskCanvas.width = size.width;
    maskCanvas.height = size.height;

    imageCtx.drawImage(img, 0, 0, size.width, size.height);
};

function getResizedSize(width, height) {
    const maxSize = 512;
    if (width <= maxSize && height <= maxSize) return { width, height };
    const scale = maxSize / Math.max(width, height);
    return { width: Math.round(width * scale), height: Math.round(height * scale) };
}

function updateBrushSize(size) {
    brushSize = size;
}

function toggleEraser() {
    isEraser = !isEraser;
    document.getElementById("eraserButton").textContent = isEraser ? "Brush" : "Eraser";
}

maskCanvas.addEventListener("mousedown", startDraw);
maskCanvas.addEventListener("mousemove", draw);
maskCanvas.addEventListener("mouseup", stopDraw);
maskCanvas.addEventListener("mouseleave", stopDraw);

function startDraw(event) {
    painting = true;
    lastX = event.offsetX;
    lastY = event.offsetY;
    draw(event);
}

function draw(event) {
    if (!painting) return;
    const x = event.offsetX;
    const y = event.offsetY;

    maskCtx.globalCompositeOperation = isEraser ? "destination-out" : "source-over";
    maskCtx.strokeStyle = isEraser ? "rgba(0,0,0,1)" : "white";
    maskCtx.lineWidth = brushSize;
    maskCtx.lineCap = "round";
    maskCtx.lineJoin = "round";

    maskCtx.beginPath();
    maskCtx.moveTo(lastX, lastY);
    maskCtx.lineTo(x, y);
    maskCtx.stroke();
    maskCtx.closePath();

    lastX = x;
    lastY = y;
}

function stopDraw() {
    painting = false;
    maskCtx.globalCompositeOperation = "source-over";
}

function saveMask() {
    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = maskCanvas.width;
    tempCanvas.height = maskCanvas.height;
    const tempCtx = tempCanvas.getContext("2d");

    tempCtx.fillStyle = "black";
    tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
    tempCtx.drawImage(maskCanvas, 0, 0);

    tempCanvas.toBlob((blob) => {
        const formData = new FormData();
        formData.append("mask", blob, `mask-${filename}`);

        fetch(`/save-mask/${filename}`, {  // Dùng filename từ biến toàn cục
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => alert(data.message))
        .catch(error => console.error("Error:", error));
    }, "image/png");
}
