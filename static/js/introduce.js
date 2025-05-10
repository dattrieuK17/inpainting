// Add drag and drop functionality
const uploadBox = document.querySelector('.upload-box');
const fileInput = document.getElementById('file-input');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  uploadBox.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
  uploadBox.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
  uploadBox.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
  uploadBox.classList.add('highlight');
}

function unhighlight(e) {
  uploadBox.classList.remove('highlight');
}

uploadBox.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;
  fileInput.files = files;
  fileInput.form.submit();
}