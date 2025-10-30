// Document ready
$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Handle document uploads
    $('.document-upload').on('change', function() {
        const fileName = $(this).val().split('\\').pop();
        if (fileName) {
            $(this).next('.custom-file-label').addClass('selected').html(fileName);
        }
    });

    // Handle application status updates
    $('.application-status').each(function() {
        const status = $(this).data('status');
        let statusClass = 'bg-secondary';
        
        switch(status.toLowerCase()) {
            case 'submitted':
                statusClass = 'bg-info';
                break;
            case 'under review':
                statusClass = 'bg-primary';
                break;
            case 'interview scheduled':
                statusClass = 'bg-warning text-dark';
                break;
            case 'offer extended':
                statusClass = 'bg-success';
                break;
            case 'rejected':
                statusClass = 'bg-danger';
                break;
        }
        
        $(this).addClass(statusClass);
    });

    // Handle interview countdown timers
    $('.interview-countdown').each(function() {
        const countdownDate = new Date($(this).data('datetime')).getTime();
        
        const updateCountdown = setInterval(() => {
            const now = new Date().getTime();
            const distance = countdownDate - now;
            
            if (distance < 0) {
                clearInterval(updateCountdown);
                $(this).html('Interview time!');
                $(this).addClass('text-danger');
                return;
            }
            
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            
            let countdownText = '';
            if (days > 0) countdownText += `${days}d `;
            if (hours > 0 || days > 0) countdownText += `${hours}h `;
            countdownText += `${minutes}m`;
            
            $(this).html(countdownText);
        }, 60000);
        
        // Initial call
        updateCountdown();
        this.dispatchEvent(new Event('update'));
    });

    // Handle document preview modals
    $('.document-preview').on('click', function(e) {
        e.preventDefault();
        const documentUrl = $(this).attr('href');
        const documentTitle = $(this).data('title') || 'Document Preview';
        
        $('#documentPreviewModal .modal-title').text(documentTitle);
        $('#documentPreviewFrame').attr('src', documentUrl);
        const documentModal = new bootstrap.Modal(document.getElementById('documentPreviewModal'));
        documentModal.show();
    });

    // Handle skill level indicators
    $('.skill-level').each(function() {
        const level = $(this).data('level');
        const $progressBar = $(this).find('.progress-bar');
        
        $progressBar.css('width', level + '%');
        $progressBar.attr('aria-valuenow', level);
        
        if (level < 30) {
            $progressBar.addClass('bg-danger');
        } else if (level < 70) {
            $progressBar.addClass('bg-warning');
        } else {
            $progressBar.addClass('bg-success');
        }
    });

    // Handle form validation
    $('.needs-validation').on('submit', function(e) {
        if (!this.checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
        }
        $(this).addClass('was-validated');
    });

    // Handle tab persistence
    if (location.hash) {
        $('a[href="' + location.hash + '"]').tab('show');
    }
    
    $('a[data-bs-toggle="tab"]').on('click', function(e) {
        e.preventDefault();
        const tabId = $(this).attr('href');
        history.pushState(null, null, tabId);
        $(this).tab('show');
    });

    // Handle AJAX form submissions
    $('.ajax-form').on('submit', function(e) {
        e.preventDefault();
        const $form = $(this);
        const $submitBtn = $form.find('button[type="submit"]');
        const originalBtnText = $submitBtn.html();
        
        $submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...');
        
        $.ajax({
            type: $form.attr('method'),
            url: $form.attr('action'),
            data: $form.serialize(),
            success: function(response) {
                if (response.redirect) {
                    window.location.href = response.redirect;
                } else {
                    // Show success message
                    const alert = `
                        <div class="alert alert-success alert-dismissible fade show" role="alert">
                            ${response.message || 'Action completed successfully'}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;
                    $form.before(alert);
                    
                    // Reset form if needed
                    if (response.resetForm) {
                        $form.trigger('reset');
                    }
                    
                    // Reload data if needed
                    if (response.reload) {
                        setTimeout(() => location.reload(), 1500);
                    }
                }
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON?.message || 'An error occurred. Please try again.';
                const alert = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        ${errorMsg}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
                $form.before(alert);
            },
            complete: function() {
                $submitBtn.prop('disabled', false).html(originalBtnText);
            }
        });
    });
});

// Utility function to format dates
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

// Utility function to handle file previews
function previewFile(input, previewElement) {
    const file = input.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        if (file.type.startsWith('image/')) {
            previewElement.html(`<img src="${e.target.result}" class="img-fluid" alt="Preview">`);
        } else if (file.type === 'application/pdf') {
            previewElement.html(`
                <div class="text-center py-3">
                    <i class="fas fa-file-pdf fa-4x text-danger mb-2"></i>
                    <p class="mb-0">${file.name}</p>
                </div>
            `);
        } else {
            previewElement.html(`
                <div class="text-center py-3">
                    <i class="fas fa-file fa-4x text-secondary mb-2"></i>
                    <p class="mb-0">${file.name}</p>
                </div>
            `);
        }
    };
    reader.readAsDataURL(file);
}
