const imageCanvas = document.getElementById("imageCanvas");
const maskCanvas = document.getElementById("maskCanvas");
const imageCtx = imageCanvas.getContext("2d");
const maskCtx = maskCanvas.getContext("2d");

let painting = false;
let brushSize = 15;
let isEraser = false;
let lastX, lastY;
let originalImage = null;
let currentFilename = window.initialFilename; // Get filename from global variable

if (!currentFilename) {
    console.error("No filename provided!");
    window.location.href = "/";
}

// Load and display the image
function loadImage(imgSrc) {
    const img = new Image();
    img.onload = function () {
        const size = {width: img.width, height: img.height};

        imageCanvas.width = size.width;
        imageCanvas.height = size.height;
        maskCanvas.width = size.width;
        maskCanvas.height = size.height;

        imageCtx.drawImage(img, 0, 0, size.width, size.height);
        originalImage = img; // Store original image for reset
    };
    img.src = imgSrc;
}

// Reset to original image
function resetImage() {
    currentFilename = window.initialFilename; // Reset to original filename
    loadImage(`/static/uploads/${currentFilename}`);
    maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
}

function updateBrushSize(size) {
    brushSize = size;
}

function toggleEraser() {
    isEraser = !isEraser;
    const eraserButton = document.getElementById("eraserButton");

    if (isEraser) {
        eraserButton.classList.add("active");
    } else {
        eraserButton.classList.remove("active");
    }
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
    return new Promise((resolve, reject) => {
        const tempCanvas = document.createElement("canvas");
        tempCanvas.width = maskCanvas.width;
        tempCanvas.height = maskCanvas.height;
        const tempCtx = tempCanvas.getContext("2d");

        tempCtx.fillStyle = "black";
        tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
        tempCtx.drawImage(maskCanvas, 0, 0);

        tempCanvas.toBlob((blob) => {
            const formData = new FormData();
            // Always use the original filename for the mask
            formData.append("mask", blob, `mask-${window.initialFilename}`);

            fetch(`/save-mask/${window.initialFilename}`, {
                method: "POST",
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log(data.message);
                resolve();
            })
            .catch(error => {
                console.error("Error:", error);
                reject(error);
            });
        }, "image/png");
    });
}

function applyInpainting() {
    // Get the base filename without any "inpainted-" prefix
    const baseFilename = currentFilename; 
    
    // Save mask first and wait for it to complete
    saveMask()
        .then(() => {
            // Only proceed with inpainting after mask is saved
            return fetch(`/inpaint/${baseFilename}`, {
                method: "POST"
            });
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error:', data.error);
                return;
            }
            
            // Update the original image with the inpainted result
            const img = new Image();
            img.onload = function() {
                // Update canvas dimensions if needed
                if (img.width !== imageCanvas.width || img.height !== imageCanvas.height) {
                    imageCanvas.width = img.width;
                    imageCanvas.height = img.height;
                    maskCanvas.width = img.width;
                    maskCanvas.height = img.height;
                }

                // Draw the inpainted result on the image canvas
                imageCtx.clearRect(0, 0, imageCanvas.width, imageCanvas.height);
                imageCtx.drawImage(img, 0, 0);
                
                // Clear the mask canvas for new drawing
                maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
                
                // Update the original image reference
                originalImage = img;
                
                // Update the current filename to the inpainted result
                currentFilename = data.result;
            };
            img.src = `/static/uploads/${data.result}`;
        })
        .catch(error => console.error("Error:", error));
}

// Load initial image
loadImage(`/static/uploads/${currentFilename}`);


