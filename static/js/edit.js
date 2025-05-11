const imageCanvas = document.getElementById("imageCanvas");
const maskCanvas = document.getElementById("maskCanvas");
const imageCtx = imageCanvas.getContext("2d");
const maskCtx = maskCanvas.getContext("2d");

let painting = false;
let brushSize = 15;
let isEraser = false;
let lastX, lastY;

let originalImage = null;
const originalFilename = window.initialFilename;
let inpaintHistory = [];   // chứa các file inpainted
let historyIndex = -1;     // con trỏ hiện tại trong stack

if (!originalFilename) {
    console.error("No filename provided!");
    window.location.href = "/";
}

function getCurrentImageFilename() {
    if (historyIndex >= 0 && inpaintHistory[historyIndex]) {
        return inpaintHistory[historyIndex];
    }
    return originalFilename;
}

function loadImageToCanvas(imgSrc) {
    const img = new Image();
    img.onload = function () {
        imageCanvas.width = img.width;
        imageCanvas.height = img.height;
        maskCanvas.width = img.width;
        maskCanvas.height = img.height;

        // Tính tỷ lệ hiển thị nhỏ hơn
        const maxDisplayHeight = 450;
        const scale = maxDisplayHeight / img.height;
        imageCanvas.style.width = img.width * scale + 'px';
        imageCanvas.style.height = img.height * scale + 'px';
        maskCanvas.style.width = img.width * scale + 'px';
        maskCanvas.style.height = img.height * scale + 'px';

        imageCtx.clearRect(0, 0, img.width, img.height);
        imageCtx.drawImage(img, 0, 0);
        maskCtx.clearRect(0, 0, img.width, img.height);
        originalImage = img;
    };
    img.src = imgSrc + "?t=" + Date.now();
}

function resetImage() {
    fetch(`/reset/${originalFilename}`, {
        method: "POST"
    })
    .then(res => res.json())
    .then(data => {
        console.log("Reset completed, deleted files:", data.deleted);
        loadImageToCanvas(`/static/uploads/${originalFilename}`);
        inpaintHistory = [];
        historyIndex = -1;
    })
    .catch(err => {
        console.error("Reset failed:", err);
    });
}

function updateBrushSize(size) {
    brushSize = size;
}

function toggleEraser() {
    isEraser = !isEraser;
    const eraserButton = document.getElementById("eraserButton");
    eraserButton.classList.toggle("active", isEraser);
}

maskCanvas.addEventListener("mousedown", startDraw);
maskCanvas.addEventListener("mousemove", draw);
maskCanvas.addEventListener("mouseup", stopDraw);
maskCanvas.addEventListener("mouseleave", stopDraw);

function getCanvasCoordinates(event, canvas) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: (event.clientX - rect.left) * scaleX,
        y: (event.clientY - rect.top) * scaleY
    };
}

function startDraw(event) {
    painting = true;
    const coords = getCanvasCoordinates(event, maskCanvas);
    lastX = coords.x;
    lastY = coords.y;
    draw(event);
}

function draw(event) {
    if (!painting) return;
    const coords = getCanvasCoordinates(event, maskCanvas);
    const x = coords.x;
    const y = coords.y;

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

function applyInpainting() {
    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = maskCanvas.width;
    tempCanvas.height = maskCanvas.height;
    const tempCtx = tempCanvas.getContext("2d");

    tempCtx.fillStyle = "black";
    tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
    tempCtx.drawImage(maskCanvas, 0, 0);

    tempCanvas.toBlob((blob) => {
        const formData = new FormData();
        formData.append("mask", blob, "mask.png");

        fetch(`/inpaint/${getCurrentImageFilename()}`, {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                console.error("Error:", data.error);
                return;
            }

            // Cập nhật stack
            inpaintHistory = inpaintHistory.slice(0, historyIndex + 1); // xoá redo future
            inpaintHistory.push(data.result);
            historyIndex = inpaintHistory.length - 1;

            loadImageToCanvas(`/static/inpainted/${data.result}`);
        })
        .catch(err => {
            console.error("Inpainting error:", err);
        });
    }, "image/png");
}

function undo() {
    if (historyIndex > 0) {
        historyIndex--;
        const prev = inpaintHistory[historyIndex];
        loadImageToCanvas(`/static/inpainted/${prev}`);
    } else if (historyIndex === 0) {
        // Quay về ảnh gốc
        historyIndex = -1;
        loadImageToCanvas(`/static/uploads/${originalFilename}`);
    }
}

function redo() {
    if (historyIndex < inpaintHistory.length - 1) {
        historyIndex++;
        const next = inpaintHistory[historyIndex];
        loadImageToCanvas(`/static/inpainted/${next}`);
    }
}

// Load ảnh gốc khi mở trang
loadImageToCanvas(`/static/uploads/${originalFilename}`);
