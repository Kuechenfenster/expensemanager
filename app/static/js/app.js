document.addEventListener('DOMContentLoaded', () => {
    // Form elements
    const form = document.getElementById('expenseForm');
    const dateInput = document.getElementById('date');
    const amountInput = document.getElementById('amount');
    const vendorInput = document.getElementById('vendor');
    const categorySelect = document.getElementById('category');
    const invoiceFilenameInput = document.getElementById('invoiceFilename');
    const ocrDataInput = document.getElementById('ocrData');
    const formMessage = document.getElementById('formMessage');
    const uploadStatus = document.getElementById('uploadStatus');
    
    // Upload buttons
    const cameraBtn = document.getElementById('cameraBtn');
    const fileBtn = document.getElementById('fileBtn');
    const cameraInput = document.getElementById('cameraInput');
    const fileInput = document.getElementById('fileInput');
    
    // Category modal
    const addCategoryBtn = document.getElementById('addCategoryBtn');
    const categoryModal = document.getElementById('categoryModal');
    const closeModalBtn = document.getElementById('cancelCategory');
    const saveCategoryBtn = document.getElementById('saveCategory');
    const newCategoryName = document.getElementById('newCategoryName');
    const categoryError = document.getElementById('categoryError');
    
    // Review modal
    const reviewModal = document.getElementById('reviewModal');
    const reviewImage = document.getElementById('reviewImage');
    const reviewAmount = document.getElementById('reviewAmount');
    const reviewDate = document.getElementById('reviewDate');
    const reviewVendor = document.getElementById('reviewVendor');
    const reviewCategory = document.getElementById('reviewCategory');
    const ocrTextPreview = document.getElementById('ocrTextPreview');
    const skipReviewBtn = document.getElementById('skipReview');
    const confirmReviewBtn = document.getElementById('confirmReview');
    
    // Current OCR data for learning
    let currentOCRData = null;
    let uploadedFilePath = null;
    
    // Initialize
    dateInput.value = new Date().toISOString().split('T')[0];
    
    // Camera and file upload handlers
    cameraBtn.addEventListener('click', () => cameraInput.click());
    fileBtn.addEventListener('click', () => fileInput.click());
    cameraInput.addEventListener('change', (e) => handleFileUpload(e.target.files[0]));
    fileInput.addEventListener('change', (e) => handleFileUpload(e.target.files[0]));
    
    function handleFileUpload(file) {
        if (!file) return;
        
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'application/pdf'];
        const maxSize = 16 * 1024 * 1024;
        
        if (!allowedTypes.includes(file.type)) {
            showMessage('Please upload an image (JPG, PNG) or PDF', 'error');
            return;
        }
        
        if (file.size > maxSize) {
            showMessage('File too large. Max 16MB.', 'error');
            return;
        }
        
        uploadStatus.innerHTML = '<span class="spinner"></span> Processing invoice with OCR...';
        uploadStatus.className = 'upload-status processing';
        
        const formData = new FormData();
        formData.append('invoice', file);
        
        console.log('Uploading file:', file.name);
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(r => r.json())
        .then(data => {
            uploadStatus.innerHTML = '';
            uploadStatus.className = 'upload-status';
            
            console.log('Upload response:', data);
            
            if (data.success) {
                uploadedFilePath = data.filename;
                
                // Store OCR data for review
                currentOCRData = {
                    filename: data.filename,
                    filepath: data.filepath,
                    extracted: data.extracted_data,
                    full_text: data.extracted_data.raw_text,
                    original_amount: data.extracted_data.amount,
                    original_date: data.extracted_data.date,
                    original_vendor: data.extracted_data.vendor
                };
                
                console.log('Stored OCR data:', currentOCRData);
                
                // Show review modal
                openReviewModal(file, data.extracted_data);
            } else {
                showMessage(data.error || 'Failed to process invoice', 'error');
            }
        })
        .catch(err => {
            uploadStatus.innerHTML = '';
            console.error('Upload error:', err);
            showMessage('Error: ' + err.message, 'error');
        });
    }
    
    function openReviewModal(file, extractedData) {
        // Show image preview
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                reviewImage.src = e.target.result;
                reviewImage.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            reviewImage.src = '';
            reviewImage.style.display = 'none';
            reviewImage.parentElement.innerHTML = '<p style="color: var(--text-light)">📄 PDF uploaded</p>';
        }
        
        // Populate extracted data
        reviewAmount.value = extractedData.amount ? extractedData.amount.toFixed(2) : '';
        reviewDate.value = extractedData.date || '';
        reviewVendor.value = extractedData.vendor || '';
        
        // Set category if vendor matches
        if (extractedData.vendor) {
            const matchingCat = findCategoryForVendor(extractedData.vendor);
            if (matchingCat && reviewCategory.querySelector(`option[value="${matchingCat}"]`)) {
                reviewCategory.value = matchingCat;
            }
        }
        
        // Show OCR text preview
        ocrTextPreview.textContent = extractedData.raw_text || 'No text detected';
        
        reviewModal.classList.add('active');
    }
    
    function findCategoryForVendor(vendor) {
        const vendorLower = vendor.toLowerCase();
        const mappings = {
            'uber': 'Transport',
            'taxi': 'Transport',
            'train': 'Transport',
            'flight': 'Transport',
            'hotel': 'Hotel',
            'restaurant': 'Meals',
            'cafe': 'Meals',
            'coffee': 'Meals'
        };
        
        for (const [key, cat] of Object.entries(mappings)) {
            if (vendorLower.includes(key)) return cat;
        }
        return null;
    }
    
    function closeReviewModal() {
        reviewModal.classList.remove('active');
    }
    
    skipReviewBtn.addEventListener('click', () => {
        // Still save the invoice filename even if skipped
        if (currentOCRData && currentOCRData.filename) {
            invoiceFilenameInput.value = currentOCRData.filename;
            console.log('Invoice filename saved (skip):', invoiceFilenameInput.value);
        }
        closeReviewModal();
        showMessage('Invoice saved. Fill in details manually.', 'info');
    });
    
    confirmReviewBtn.addEventListener('click', () => {
        console.log('Confirm clicked, currentOCRData:', currentOCRData);
        
        // Copy review data to main form
        amountInput.value = reviewAmount.value;
        dateInput.value = reviewDate.value;
        vendorInput.value = reviewVendor.value;
        if (reviewCategory.value) {
            categorySelect.value = reviewCategory.value;
        }
        
        // CRITICAL: Save the filename to hidden field
        if (currentOCRData && currentOCRData.filename) {
            invoiceFilenameInput.value = currentOCRData.filename;
            console.log('Invoice filename set:', invoiceFilenameInput.value);
        }
        
        // Prepare OCR correction data for learning
        if (currentOCRData) {
            const wasCorrected = (
                reviewAmount.value != String(currentOCRData.original_amount) ||
                reviewDate.value != String(currentOCRData.original_date) ||
                reviewVendor.value != String(currentOCRData.original_vendor)
            );
            
            const ocrData = {
                filename: currentOCRData.filename,
                original_amount: currentOCRData.original_amount,
                original_date: currentOCRData.original_date,
                original_vendor: currentOCRData.original_vendor,
                full_text: currentOCRData.full_text,
                was_corrected: wasCorrected
            };
            
            ocrDataInput.value = JSON.stringify(ocrData);
            console.log('OCR data set:', ocrDataInput.value);
        }
        
        closeReviewModal();
        showMessage('Data confirmed. Click "Add Expense" to save.', 'success');
        
        // Auto-focus the Add button to guide user
        form.querySelector('.btn-primary').focus();
    });
    
    // Form submission
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        
        console.log('Form submitting...');
        console.log('Invoice filename:', invoiceFilenameInput.value);
        console.log('OCR data:', ocrDataInput.value);
        
        const btn = form.querySelector('.btn-primary');
        btn.disabled = true;
        btn.textContent = 'Adding...';
        
        // Ensure all fields are included in FormData
        const formData = new FormData();
        formData.append('date', dateInput.value);
        formData.append('amount', amountInput.value);
        formData.append('category', categorySelect.value);
        formData.append('vendor', vendorInput.value);
        formData.append('description', document.getElementById('description').value);
        formData.append('invoice_filename', invoiceFilenameInput.value);
        formData.append('ocr_data', ocrDataInput.value);
        
        console.log('FormData entries:');
        for (let [key, val] of formData.entries()) {
            console.log(key, ':', val);
        }
        
        fetch('/api/expenses', {
            method: 'POST',
            body: formData
        })
        .then(r => r.json())
        .then(data => {
            console.log('Server response:', data);
            if (data.success) {
                showMessage('Expense added!', 'success');
                setTimeout(() => location.reload(), 500);
            } else {
                showMessage(data.error || 'Error', 'error');
                btn.disabled = false;
                btn.textContent = 'Add Expense';
            }
        })
        .catch(err => {
            console.error('Submit error:', err);
            showMessage('Error: ' + err.message, 'error');
            btn.disabled = false;
            btn.textContent = 'Add Expense';
        });
    });
    
    // Delete
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!confirm('Delete this expense?')) return;
            
            fetch(`/api/expenses/${btn.dataset.id}`, { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (data.success) btn.closest('tr').remove();
            });
        });
    });
    
    // Category modal
    addCategoryBtn.addEventListener('click', () => {
        categoryModal.classList.add('active');
        newCategoryName.value = '';
        categoryError.textContent = '';
        newCategoryName.focus();
    });
    
    closeModalBtn.addEventListener('click', () => {
        categoryModal.classList.remove('active');
    });
    
    saveCategoryBtn.addEventListener('click', () => {
        const name = newCategoryName.value.trim();
        if (!name) {
            categoryError.textContent = 'Enter a name';
            return;
        }
        
        fetch('/api/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Add to all dropdowns
                [categorySelect, reviewCategory].forEach(sel => {
                    if (sel) {
                        const opt = new Option(data.category, data.category);
                        sel.add(opt);
                    }
                });
                categorySelect.value = data.category;
                categoryModal.classList.remove('active');
            } else {
                categoryError.textContent = data.error || 'Failed to add';
            }
        });
    });
    
    newCategoryName.addEventListener('keypress', e => {
        if (e.key === 'Enter') saveCategoryBtn.click();
    });
    
    // Close modals on outside click
    window.addEventListener('click', (e) => {
        if (e.target === reviewModal) closeReviewModal();
        if (e.target === categoryModal) categoryModal.classList.remove('active');
    });
    
    function showMessage(msg, type) {
        formMessage.textContent = msg;
        formMessage.className = `message ${type}`;
        formMessage.style.display = 'block';
        setTimeout(() => formMessage.style.display = 'none', 5000);
    }
});
