document.addEventListener('DOMContentLoaded', () => {
    // Form
    const form = document.getElementById('expenseForm');
    const dateInput = document.getElementById('date');
    const fileInput = document.getElementById('invoice');
    const fileUpload = document.getElementById('fileUpload');
    const fileName = document.getElementById('fileName');
    const ocrStatus = document.getElementById('ocrStatus');
    const formMessage = document.getElementById('formMessage');
    
    // Category modal
    const addCategoryBtn = document.getElementById('addCategoryBtn');
    const categoryModal = document.getElementById('categoryModal');
    const closeModalBtn = document.getElementById('cancelCategory');
    const saveCategoryBtn = document.getElementById('saveCategory');
    const newCategoryName = document.getElementById('newCategoryName');
    const categoryError = document.getElementById('categoryError');
    
    // Initialize
    dateInput.value = new Date().toISOString().split('T')[0];
    
    // File upload
    fileUpload.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFile);
    
    function handleFile(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        fileName.textContent = file.name;
        
        // OCR processing
        ocrStatus.style.display = 'flex';
        
        const formData = new FormData();
        formData.append('invoice', file);
        
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(r => r.json())
        .then(data => {
            ocrStatus.style.display = 'none';
            
            if (data.success && data.extracted_data) {
                const d = data.extracted_data;
                if (d.amount) document.getElementById('amount').value = d.amount.toFixed(2);
                if (d.date) document.getElementById('date').value = d.date;
                if (d.vendor) document.getElementById('vendor').value = d.vendor;
                showMessage('Invoice data extracted!', 'success');
            }
        })
        .catch(() => {
            ocrStatus.style.display = 'none';
        });
    }
    
    // Form submit
    if (form) {
        form.addEventListener('submit', e => {
            e.preventDefault();
            
            const btn = form.querySelector('.btn-primary');
            btn.disabled = true;
            btn.textContent = 'Adding...';
            
            fetch('/api/expenses', {
                method: 'POST',
                body: new FormData(form)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showMessage('Expense added!', 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    showMessage(data.error || 'Error', 'error');
                    btn.disabled = false;
                    btn.textContent = 'Add';
                }
            })
            .catch(err => {
                showMessage('Error: ' + err.message, 'error');
                btn.disabled = false;
                btn.textContent = 'Add';
            });
        });
    }
    
    // Delete
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!confirm('Delete this expense?')) return;
            
            fetch(`/api/expenses/${btn.dataset.id}`, { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    btn.closest('tr').remove();
                }
            });
        });
    });
    
    // Category modal
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', () => {
            categoryModal.classList.add('active');
            newCategoryName.value = '';
            categoryError.textContent = '';
            newCategoryName.focus();
        });
    }
    
    closeModalBtn.addEventListener('click', () => categoryModal.classList.remove('active'));
    
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
                // Add to dropdowns
                const select = document.getElementById('category');
                const filter = document.getElementById('categoryFilter');
                
                const opt1 = new Option(data.category, data.category);
                select.add(opt1);
                select.value = data.category;
                
                if (filter) {
                    const opt2 = new Option(data.category, data.category);
                    filter.add(opt2);
                }
                
                categoryModal.classList.remove('active');
            } else {
                categoryError.textContent = data.error || 'Failed to add';
            }
        });
    });
    
    newCategoryName.addEventListener('keypress', e => {
        if (e.key === 'Enter') saveCategoryBtn.click();
    });
    
    // Analytics filters
    const monthFilter = document.getElementById('monthFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    const clearFiltersBtn = document.getElementById('clearFilters');
    
    // Load months
    if (monthFilter) {
        fetch('/api/months')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                data.months.forEach(m => {
                    const [y, month] = m.split('-');
                    const date = new Date(y, month - 1);
                    const opt = new Option(date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }), m);
                    monthFilter.add(opt);
                });
            }
        });
    }
    
    // Apply filters on analytics page
    function updateAnalytics() {
        const params = new URLSearchParams();
        if (monthFilter?.value) params.append('month', monthFilter.value);
        if (categoryFilter?.value) params.append('category', categoryFilter.value);
        
        fetch(`/api/summary?${params}`)
        .then(r => r.json())
        .then(data => {
            document.getElementById('totalAmount').textContent = `€${data.total.toFixed(2)}`;
            document.getElementById('expenseCount').textContent = `${data.count} expenses`;
        });
    }
    
    if (monthFilter) monthFilter.addEventListener('change', updateAnalytics);
    if (categoryFilter) categoryFilter.addEventListener('change', updateAnalytics);
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            if (monthFilter) monthFilter.value = '';
            if (categoryFilter) categoryFilter.value = '';
            updateAnalytics();
        });
    }
    
    function showMessage(msg, type) {
        formMessage.textContent = msg;
        formMessage.className = `message ${type}`;
        formMessage.style.display = 'block';
        setTimeout(() => formMessage.style.display = 'none', 4000);
    }
});
