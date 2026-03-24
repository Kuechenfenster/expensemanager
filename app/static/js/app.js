document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const form = document.getElementById('expenseForm');
    const uploadArea = document.getElementById('uploadArea');
    const uploadInput = document.getElementById('invoice');
    const uploadPreview = document.getElementById('uploadPreview');
    const previewImage = document.getElementById('previewImage');
    const previewName = document.getElementById('previewName');
    const removeUploadBtn = document.getElementById('removeUpload');
    const uploadProgress = document.getElementById('uploadProgress');
    const formMessage = document.getElementById('formMessage');
    
    // Filter elements
    const monthFilter = document.getElementById('monthFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    const applyFiltersBtn = document.getElementById('applyFilters');
    const clearFiltersBtn = document.getElementById('clearFilters');
    
    // Category modal elements
    const addCategoryBtn = document.getElementById('addCategoryBtn');
    const categoryModal = document.getElementById('categoryModal');
    const closeModalBtn = document.getElementById('closeModal');
    const cancelCategoryBtn = document.getElementById('cancelCategory');
    const saveCategoryBtn = document.getElementById('saveCategory');
    const newCategoryName = document.getElementById('newCategoryName');
    const categoryError = document.getElementById('categoryError');
    
    // Initialize
    initializeDateField();
    loadAvailableMonths();
    bindEvents();
    
    function initializeDateField() {
        const dateField = document.getElementById('date');
        if (!dateField.value) {
            const today = new Date().toISOString().split('T')[0];
            dateField.value = today;
        }
    }
    
    function bindEvents() {
        // Form submission
        form.addEventListener('submit', handleFormSubmit);
        
        // Upload handling
        uploadArea.addEventListener('click', () => uploadInput.click());
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleDrop);
        uploadInput.addEventListener('change', handleFileSelect);
        removeUploadBtn.addEventListener('click', removeUpload);
        
        // Delete buttons
        document.querySelectorAll('.delete-expense').forEach(btn => {
            btn.addEventListener('click', handleDelete);
        });
        
        // Filters
        applyFiltersBtn.addEventListener('click', applyFilters);
        clearFiltersBtn.addEventListener('click', clearFilters);
        
        // Category modal
        addCategoryBtn.addEventListener('click', openCategoryModal);
        closeModalBtn.addEventListener('click', closeCategoryModal);
        cancelCategoryBtn.addEventListener('click', closeCategoryModal);
        saveCategoryBtn.addEventListener('click', saveCategory);
        newCategoryName.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') saveCategory();
        });
        
        // Close modal on outside click
        categoryModal.addEventListener('click', (e) => {
            if (e.target === categoryModal) closeCategoryModal();
        });
    }
    
    // Filter functions
    function loadAvailableMonths() {
        fetch('/api/months')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.months) {
                    monthFilter.innerHTML = '<option value="">All Months</option>';
                    data.months.forEach(month => {
                        const [year, mon] = month.split('-');
                        const monthName = new Date(year, mon - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                        const option = document.createElement('option');
                        option.value = month;
                        option.textContent = monthName;
                        monthFilter.appendChild(option);
                    });
                }
            })
            .catch(err => console.error('Error loading months:', err));
    }
    
    function applyFilters() {
        const month = monthFilter.value;
        const category = categoryFilter.value;
        
        // Build query string
        const params = new URLSearchParams();
        if (month) params.append('month', month);
        if (category) params.append('category', category);
        
        // Reload page with filters
        window.location.href = `/?${params.toString()}`;
    }
    
    function clearFilters() {
        monthFilter.value = '';
        categoryFilter.value = '';
        window.location.href = '/';
    }
    
    // Category modal functions
    function openCategoryModal() {
        categoryModal.classList.add('active');
        newCategoryName.value = '';
        categoryError.style.display = 'none';
        newCategoryName.focus();
    }
    
    function closeCategoryModal() {
        categoryModal.classList.remove('active');
    }
    
    function saveCategory() {
        const name = newCategoryName.value.trim();
        
        if (!name) {
            showCategoryError('Category name is required');
            return;
        }
        
        fetch('/api/categories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: name })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Add new category to dropdown
                const categorySelect = document.getElementById('category');
                const categoryFilter = document.getElementById('categoryFilter');
                
                const option1 = document.createElement('option');
                option1.value = data.category;
                option1.textContent = data.category;
                categorySelect.appendChild(option1);
                
                const option2 = document.createElement('option');
                option2.value = data.category;
                option2.textContent = data.category;
                categoryFilter.appendChild(option2);
                
                // Select the new category
                categorySelect.value = data.category;
                
                closeCategoryModal();
                showMessage('Category added successfully', 'success');
            } else {
                showCategoryError(data.error || 'Failed to add category');
            }
        })
        .catch(err => {
            showCategoryError('Error adding category: ' + err.message);
        });
    }
    
    function showCategoryError(message) {
        categoryError.textContent = message;
        categoryError.style.display = 'block';
    }
    
    // Upload handling
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add('dragover');
    }
    
    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
    }
    
    function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length) {
            handleFile(files[0]);
        }
    }
    
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            handleFile(file);
        }
    }
    
    function handleFile(file) {
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'application/pdf'];
        const maxSize = 16 * 1024 * 1024; // 16MB
        
        if (!allowedTypes.includes(file.type)) {
            showMessage('Invalid file type. Please upload an image (JPEG, PNG, GIF) or PDF.', 'error');
            return;
        }
        
        if (file.size > maxSize) {
            showMessage('File too large. Maximum size is 16MB.', 'error');
            return;
        }
        
        // Show preview for images
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImage.src = e.target.result;
                previewImage.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            // For PDF, show icon
            previewImage.src = '';
            previewImage.style.display = 'none';
        }
        
        previewName.textContent = file.name;
        uploadPreview.classList.add('active');
        
        // Process OCR
        processOCR(file);
    }
    
    function processOCR(file) {
        uploadProgress.classList.add('active');
        
        const formData = new FormData();
        formData.append('invoice', file);
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            uploadProgress.classList.remove('active');
            
            if (data.success && data.extracted_data) {
                const extracted = data.extracted_data;
                
                // Auto-fill form fields
                if (extracted.amount) {
                    document.getElementById('amount').value = extracted.amount.toFixed(2);
                }
                if (extracted.date) {
                    document.getElementById('date').value = extracted.date;
                }
                if (extracted.vendor) {
                    document.getElementById('vendor').value = extracted.vendor;
                }
                
                showMessage('Auto-filled data from invoice. Please verify.', 'success');
            }
        })
        .catch(err => {
            uploadProgress.classList.remove('active');
            console.error('OCR error:', err);
        });
    }
    
    function removeUpload(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadInput.value = '';
        uploadPreview.classList.remove('active');
        previewImage.src = '';
        previewName.textContent = '';
    }
    
    // Form submission
    function handleFormSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Saving...';
        
        fetch('/api/expenses', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
            
            if (data.success) {
                showMessage('Expense added successfully!', 'success');
                form.reset();
                removeUpload({ preventDefault: () => {}, stopPropagation: () => {} });
                initializeDateField();
                setTimeout(() => location.reload(), 500);
            } else {
                showMessage(data.error || 'Failed to add expense', 'error');
            }
        })
        .catch(err => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
            showMessage('Error: ' + err.message, 'error');
        });
    }
    
    // Delete handling
    function handleDelete(e) {
        const id = e.currentTarget.dataset.id;
        
        if (!confirm('Are you sure you want to delete this expense?')) {
            return;
        }
        
        fetch(`/api/expenses/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const row = document.querySelector(`tr[data-id="${id}"]`);
                if (row) {
                    row.remove();
                }
                showMessage('Expense deleted', 'success');
            } else {
                showMessage(data.error || 'Failed to delete', 'error');
            }
        })
        .catch(err => {
            showMessage('Error: ' + err.message, 'error');
        });
    }
    
    // Utility functions
    function showMessage(message, type) {
        formMessage.textContent = message;
        formMessage.className = `form-message ${type}`;
        formMessage.style.display = 'block';
        
        setTimeout(() => {
            formMessage.style.display = 'none';
        }, 5000);
    }
});
