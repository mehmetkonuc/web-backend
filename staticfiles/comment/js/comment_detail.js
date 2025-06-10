document.addEventListener('DOMContentLoaded', function() {
    // Image preview functionality
    const imageInput = document.getElementById('id_images');
    const previewContainer = document.getElementById('imagePreviewContainer');
    const maxImages = 4;
    let selectedImages = [];
    
    // Karakter sayacı ve autosize işlevselliği
    const contentTextarea = document.getElementById('commentBody');
    const characterCounter = document.getElementById('characterCounter');
    const maxLength = 280;
    const submitButton = document.getElementById('postSubmitBtn');
    
    // Textarea'yı otomatik boyutlandırma fonksiyonu
    function autosize(textarea) {
        // Önce yüksekliği resetleyelim
        textarea.style.height = 'auto';
        
        // Sonra içeriğe göre yüksekliği ayarlayalım (ekstra 2px border için)
        textarea.style.height = (textarea.scrollHeight) + 'px';
        
        // Maksimum yükseklik kontrolü
        const maxHeight = 200; // Piksel cinsinden maksimum yükseklik
        if (textarea.scrollHeight > maxHeight) {
            textarea.style.height = maxHeight + 'px';
            textarea.style.overflowY = 'auto';
        } else {
            textarea.style.overflowY = 'hidden';
        }
    }
    
    // Sayacı başlangıçta güncelleyelim
    if(contentTextarea && characterCounter) {
        // Başlangıç değerini ayarla
        updateCharacterCount();
        
        // Başlangıçta textarea boyutunu ayarla
        autosize(contentTextarea);
        
        // Her tuş vuruşunda sayacı ve textarea boyutunu güncelle
        contentTextarea.addEventListener('input', function() {
            updateCharacterCount();
            autosize(this);
        });
        
        function updateCharacterCount() {
            const currentLength = contentTextarea.value.length;
            const remainingChars = maxLength - currentLength;
            
            // Sayacı güncelle
            characterCounter.textContent = remainingChars;
            
            // Sayacın rengini kalan karakter sayısına göre değiştir
            if(remainingChars <= 10) {
                characterCounter.className = 'position-absolute end-0 bottom-0 me-2 mb-2 badge bg-danger rounded-pill';
            } else if(remainingChars <= 20) {
                characterCounter.className = 'position-absolute end-0 bottom-0 me-2 mb-2 badge bg-warning rounded-pill';
            } else {
                characterCounter.className = 'position-absolute end-0 bottom-0 me-2 mb-2 badge bg-primary rounded-pill';
            }
            
            // Karakter sayısı sınırı aşıldığında butonu devre dışı bırak
            if(currentLength > maxLength || currentLength === 0) {
                submitButton.disabled = true;
            } else {
                submitButton.disabled = false;
            }
        }
    }
    
    imageInput.style.display = 'none'; // Hide the default file input
    
    imageInput.addEventListener('change', function() {
        const files = Array.from(this.files);
        
        // Validate number of images
        if (files.length > maxImages) {
            alert(`En fazla ${maxImages} resim yükleyebilirsiniz.`);
            this.value = '';
            return;
        }
        
        // Clear previous previews
        previewContainer.innerHTML = '';
        selectedImages = [];
        
        // Create preview for each file
        files.forEach(file => {
            const reader = new FileReader();
            reader.onload = function(e) {
                const previewWrapper = document.createElement('div');
                previewWrapper.className = 'post-image-preview';
                
                const img = document.createElement('img');
                img.src = e.target.result;
                img.className = 'img-thumbnail';
                
                const removeBtn = document.createElement('span');
                removeBtn.className = 'remove-image';
                removeBtn.innerHTML = '&times;';
                removeBtn.addEventListener('click', function() {
                    previewWrapper.remove();
                    
                    // Remove from selected images
                    const index = selectedImages.indexOf(file);
                    if (index > -1) {
                        selectedImages.splice(index, 1);
                    }
                    
                    // Update file input
                    const dataTransfer = new DataTransfer();
                    selectedImages.forEach(img => dataTransfer.items.add(img));
                    imageInput.files = dataTransfer.files;
                });
                
                previewWrapper.appendChild(img);
                previewWrapper.appendChild(removeBtn);
                previewContainer.appendChild(previewWrapper);
                
                // Add to selected images
                selectedImages.push(file);
            };
            reader.readAsDataURL(file);
        });
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});