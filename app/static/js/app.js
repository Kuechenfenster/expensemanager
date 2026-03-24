// Expense Manager App

document.addEventListener('DOMContentLoaded', function() {
    // Set today's date as default
    const dateInput = document.getElementById('date');
    if (dateInput) {
        dateInput.valueAsDate = new Date();
    }
    
    // Handle file upload change
    const fileInput = document.getElementById('invoice');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
    }
    
    // Handle form submission
    const form = document.getElementById('expenseForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
});

// Handle file upload with OCR
async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Update file name display
    const fileNameSpan = document.querySelector('.file-name');
    fileNameSpan.textContent = file.name;
    
    // Show loading state
    const ocrStatus = document.getElementById('ocr-status');
    ocrStatus.classList.remove('hidden');
    ocrStatus.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing invoice...';
    
    const formData = new FormData();
    formData.append('invoice', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            ocrStatus.innerHTML = '<i class="fas fa-check-circle"></i> Invoice processed!';
            
            // Auto-fill form fields
            const data = result.extracted_data;
            
            if (data.amount && !document.getElementById('amount').value) {
                document.getElementById('amount').value = data.amount;
            }
            
            if (data.date && !document.getElementById('date').value) {
                document.getElementById('date').value = data.date;
            }
            
            if (data.vendor && !document.getElementById('vendor').value) {
                document.getElementById('vendor').value = data.vendor;
            }
            
            // Show extracted info
            setTimeout(() => {
                ocrStatus.innerHTML = '<i class="fas fa-info-circle"></i> Auto-filled data from invoice. Please verify.';
            }, 1500);
        } else {
            ocrStatus.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${result.error || 'Failed to process invoice'}`;
            ocrStatus.style.background = 'rgba(239, 68, 68, 0.1)';
        }
    } catch (error) {
        ocrStatus.innerHTML = `<i class="fas fa-exclamation-circle"></i> Error: ${error.message}`;
        ocrStatus.style.background = 'rgba(239, 68, 68, 0.1)';
    }
}

// Handle form submission
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading"></span> Saving...';
    
    const formData = new FormData(form);
    
    try {
        const response = await fetch('/api/expenses', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Expense saved successfully!', 'success');
            form.reset();
            
            // Reset date to today
            document.getElementById('date').valueAsDate = new Date();
            
            // Clear file name
            document.querySelector('.file-name').textContent = '';
            document.getElementById('ocr-status').classList.add('hidden');
            
            // Reload page to show new expense
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast(result.error || 'Failed to save expense', 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    }
}

// Delete expense
async function deleteExpense(id) {
    if (!confirm('Are you sure you want to delete this expense?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/expenses/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Expense deleted successfully!', 'success');
            
            // Remove row from table
            const row = document.querySelector(`tr[data-id="${id}"]`);
            if (row) {
                row.style.transition = 'opacity 0.3s';
                row.style.opacity = '0';
                setTimeout(() => row.remove(), 300);
            }
            
            // Reload after short delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast(result.error || 'Failed to delete expense', 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Show toast notification
function showToast(message, type = 'success') {
    // Remove existing toasts
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Mobile menu toggle
function toggleMenu() {
    // For future mobile menu expansion
    console.log('Menu toggled');
}
