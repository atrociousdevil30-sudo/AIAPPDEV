document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const exitForm = document.getElementById('exitForm');
    const feedbackTableBody = document.getElementById('feedbackTableBody');
    const feedbackModal = document.getElementById('feedbackModal');
    const feedbackModalBody = document.getElementById('feedbackModalBody');
    const exportDataBtn = document.getElementById('exportDataBtn');
    
    // Sample data for demonstration
    const sampleFeedbackData = [
        {
            id: 1,
            employeeName: 'John Smith',
            position: 'Senior Developer',
            department: 'Engineering',
            employmentLength: '3 years, 4 months',
            exitDate: '2025-10-15',
            reason: 'Career Advancement',
            feedback: 'I enjoyed working at the company, but I found a role with more growth opportunities and better compensation. The team was great to work with, and I learned a lot during my time here.',
            sentiment: 'positive',
            contactForDetails: true,
            submissionDate: '2025-10-10T14:30:00Z'
        },
        {
            id: 2,
            employeeName: 'Sarah Johnson',
            position: 'UX Designer',
            department: 'Design',
            employmentLength: '1 year, 8 months',
            exitDate: '2025-10-20',
            reason: 'Relocation',
            feedback: 'I had to move to another city due to personal reasons. I really enjoyed my time here and would consider returning if I move back. The work-life balance and team culture were excellent.',
            sentiment: 'positive',
            contactForDetails: false,
            submissionDate: '2025-10-15T09:15:00Z'
        },
        {
            id: 3,
            employeeName: 'Michael Chen',
            position: 'Product Manager',
            department: 'Product',
            employmentLength: '2 years',
            exitDate: '2025-10-25',
            reason: 'Better Opportunity',
            feedback: 'I received an offer for a more senior role with a higher salary. While I appreciate the experience I gained here, I felt there were limited opportunities for career growth in my current position.',
            sentiment: 'neutral',
            contactForDetails: true,
            submissionDate: '2025-10-18T16:45:00Z'
        },
        {
            id: 4,
            employeeName: 'Emily Rodriguez',
            position: 'Marketing Specialist',
            department: 'Marketing',
            employmentLength: '11 months',
            exitDate: '2025-11-01',
            reason: 'Work Environment',
            feedback: 'I found the work environment to be quite stressful with unrealistic deadlines. There was a lack of clear communication from management, which made it difficult to meet expectations. I hope the company can work on improving these aspects.',
            sentiment: 'negative',
            contactForDetails: false,
            submissionDate: '2025-10-20T11:20:00Z'
        },
        {
            id: 5,
            employeeName: 'David Kim',
            position: 'DevOps Engineer',
            department: 'Engineering',
            employmentLength: '4 years, 2 months',
            exitDate: '2025-11-05',
            reason: 'Career Change',
            feedback: 'I\'ve decided to pursue a different career path outside of technology. My time at the company has been valuable, and I\'ve grown both professionally and personally. Thank you for the opportunity.',
            sentiment: 'positive',
            contactForDetails: true,
            submissionDate: '2025-10-22T13:10:00Z'
        }
    ];
    
    // Initialize the page
    function initPage() {
        // Load feedback data
        loadFeedbackData();
        
        // Set up form submission
        if (exitForm) {
            setupFormSubmission();
        }
        
        // Set up export button
        if (exportDataBtn) {
            exportDataBtn.addEventListener('click', exportFeedbackData);
        }
    }
    
    // Load feedback data into the table
    function loadFeedbackData() {
        // In a real app, this would be an API call to your backend
        const feedbackData = getFeedbackData();
        
        if (feedbackData.length === 0) {
            feedbackTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4">
                        <i class="bi bi-inbox" style="font-size: 2rem; opacity: 0.5;"></i>
                        <p class="mt-2 mb-0">No exit feedback available yet.</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        // Sort by submission date (newest first)
        feedbackData.sort((a, b) => new Date(b.submissionDate) - new Date(a.submissionDate));
        
        // Clear existing rows
        feedbackTableBody.innerHTML = '';
        
        // Add rows to the table
        feedbackData.forEach(feedback => {
            const row = document.createElement('tr');
            
            // Format date
            const submissionDate = new Date(feedback.submissionDate);
            const formattedDate = submissionDate.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
            
            // Determine sentiment badge
            let sentimentBadge = '';
            if (feedback.sentiment === 'positive') {
                sentimentBadge = '<span class="badge bg-success">Positive</span>';
            } else if (feedback.sentiment === 'negative') {
                sentimentBadge = '<span class="badge bg-danger">Negative</span>';
            } else {
                sentimentBadge = '<span class="badge bg-secondary">Neutral</span>';
            }
            
            // Create row HTML
            row.innerHTML = `
                <td>${formattedDate}</td>
                <td>${feedback.employeeName}</td>
                <td>${feedback.position}</td>
                <td>${feedback.reason}</td>
                <td>${sentimentBadge}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-feedback" data-id="${feedback.id}">
                        <i class="bi bi-eye"></i> View
                    </button>
                </td>
            `;
            
            // Add click event to view feedback
            const viewBtn = row.querySelector('.view-feedback');
            if (viewBtn) {
                viewBtn.addEventListener('click', () => showFeedbackDetails(feedback.id));
            }
            
            feedbackTableBody.appendChild(row);
        });
    }
    
    // Set up form submission
    function setupFormSubmission() {
        exitForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const formData = {
                employeeName: document.getElementById('employeeName').value.trim(),
                position: document.getElementById('position').value.trim(),
                department: document.getElementById('department').value,
                employmentLength: document.getElementById('employmentLength').value,
                exitDate: document.getElementById('exitDate').value,
                reason: document.getElementById('reason').value,
                otherReason: document.getElementById('otherReason').value.trim(),
                feedback: document.getElementById('feedback').value.trim(),
                contactForDetails: document.getElementById('contactForDetails').checked,
                submissionDate: new Date().toISOString()
            };
            
            // Validate required fields
            if (!formData.employeeName || !formData.position || !formData.reason || !formData.feedback) {
                showToast('warning', 'Missing Information', 'Please fill in all required fields.');
                return;
            }
            
            // If "Other" reason is selected but no details provided
            if (formData.reason === 'Other' && !formData.otherReason) {
                showToast('warning', 'Missing Information', 'Please specify the reason for leaving.');
                return;
            }
            
            // Analyze sentiment of feedback
            formData.sentiment = analyzeSentiment(formData.feedback);
            
            // Show loading state
            const submitBtn = exitForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Submitting...';
            
            // In a real app, this would be an API call to your backend
            setTimeout(() => {
                // Save the feedback
                saveFeedback(formData);
                
                // Reset form
                exitForm.reset();
                
                // Reset button
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
                
                // Show success message
                showToast('success', 'Thank You!', 'Your feedback has been submitted successfully.');
                
                // Reload feedback data
                loadFeedbackData();
                
                // Scroll to top
                window.scrollTo({ top: 0, behavior: 'smooth' });
                
            }, 1500);
        });
        
        // Show/hide other reason field based on selection
        const reasonSelect = document.getElementById('reason');
        const otherReasonGroup = document.getElementById('otherReasonGroup');
        
        if (reasonSelect && otherReasonGroup) {
            reasonSelect.addEventListener('change', function() {
                otherReasonGroup.style.display = this.value === 'Other' ? 'block' : 'none';
            });
            
            // Initialize visibility
            otherReasonGroup.style.display = reasonSelect.value === 'Other' ? 'block' : 'none';
        }
    }
    
    // Analyze sentiment of feedback text (simple implementation)
    function analyzeSentiment(text) {
        const positiveWords = ['good', 'great', 'excellent', 'enjoy', 'happy', 'satisfied', 'appreciate', 'thank', 'thanks', 'wonderful', 'amazing', 'fantastic', 'pleasure'];
        const negativeWords = ['bad', 'poor', 'terrible', 'awful', 'stress', 'stressful', 'difficult', 'hard', 'challenging', 'issue', 'problem', 'concern', 'disappoint'];
        
        const textLower = text.toLowerCase();
        let positiveCount = 0;
        let negativeCount = 0;
        
        // Count positive and negative words
        positiveWords.forEach(word => {
            const regex = new RegExp(`\\b${word}\\b`, 'g');
            const matches = textLower.match(regex);
            if (matches) positiveCount += matches.length;
        });
        
        negativeWords.forEach(word => {
            const regex = new RegExp(`\\b${word}\\b`, 'g');
            const matches = textLower.match(regex);
            if (matches) negativeCount += matches.length;
        });
        
        // Determine overall sentiment
        if (positiveCount > negativeCount) {
            return 'positive';
        } else if (negativeCount > positiveCount) {
            return 'negative';
        } else {
            return 'neutral';
        }
    }
    
    // Show feedback details in modal
    function showFeedbackDetails(feedbackId) {
        // In a real app, this would be an API call to fetch the specific feedback
        const feedbackData = getFeedbackData();
        const feedback = feedbackData.find(item => item.id === feedbackId);
        
        if (!feedback) {
            showToast('danger', 'Error', 'Feedback not found.');
            return;
        }
        
        // Format dates
        const submissionDate = new Date(feedback.submissionDate);
        const exitDate = new Date(feedback.exitDate);
        
        const formattedSubmissionDate = submissionDate.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const formattedExitDate = exitDate.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        // Update employee information
        document.getElementById('feedbackEmployeeName').textContent = feedback.employeeName;
        document.getElementById('feedbackDate').textContent = `Submitted on ${formattedSubmissionDate}`;
        document.getElementById('feedbackDepartment').textContent = feedback.department;
        document.getElementById('feedbackDuration').textContent = feedback.employmentLength;
        
        // Update exit details
        const reasonElement = document.querySelector('#feedbackReason span');
        if (reasonElement) {
            reasonElement.textContent = feedback.reason;
        }
        
        // Update contact preference
        const contactCheckbox = document.getElementById('feedbackContactAllowed');
        if (contactCheckbox) {
            contactCheckbox.checked = feedback.contactForDetails;
        }
        
        // Update feedback content
        const feedbackContent = document.getElementById('feedbackContent');
        if (feedbackContent) {
            if (feedback.feedback && feedback.feedback.trim() !== '') {
                feedbackContent.innerHTML = feedback.feedback.replace(/\n/g, '<br>');
            } else {
                feedbackContent.innerHTML = '<p class="mb-0 text-muted fst-italic">No additional feedback provided.</p>';
            }
        }
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('feedbackModal'));
        modal.show();
    }
    
    // Export feedback data
    function exportFeedbackData() {
        const feedbackData = getFeedbackData();
        
        if (feedbackData.length === 0) {
            showToast('info', 'No Data', 'There is no feedback data to export.');
            return;
        }
        
        // Create CSV content
        let csvContent = 'data:text/csv;charset=utf-8,';
        
        // Add headers
        const headers = [
            'Employee Name',
            'Position',
            'Department',
            'Employment Length',
            'Exit Date',
            'Reason for Leaving',
            'Other Reason',
            'Sentiment',
            'Feedback',
            'Contact for Details',
            'Submission Date'
        ];
        
        csvContent += headers.join(',') + '\r\n';
        
        // Add data rows
        feedbackData.forEach(item => {
            const row = [
                `"${item.employeeName}"`,
                `"${item.position}"`,
                `"${item.department}"`,
                `"${item.employmentLength}"`,
                `"${item.exitDate}"`,
                `"${item.reason}"`,
                `"${item.otherReason || ''}"`,
                `"${item.sentiment}"`,
                `"${item.feedback.replace(/"/g, '""')}"`,
                `"${item.contactForDetails ? 'Yes' : 'No'}"`,
                `"${item.submissionDate}"`
            ];
            
            csvContent += row.join(',') + '\r\n';
        });
        
        // Create download link
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `exit-feedback-${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        
        // Trigger download
        link.click();
        
        // Clean up
        document.body.removeChild(link);
        
        showToast('success', 'Export Complete', 'Feedback data has been exported successfully.');
    }
    
    // Helper function to get feedback data (mocked for this example)
    function getFeedbackData() {
        // In a real app, this would be an API call to your backend
        // For this example, we'll use the sample data and any saved feedback
        const savedFeedback = JSON.parse(localStorage.getItem('exitFeedback') || '[]');
        return [...sampleFeedbackData, ...savedFeedback];
    }
    
    // Helper function to save feedback (mocked for this example)
    function saveFeedback(feedback) {
        // In a real app, this would be an API call to your backend
        // For this example, we'll save to localStorage
        const savedFeedback = JSON.parse(localStorage.getItem('exitFeedback') || '[]');
        
        // Generate a unique ID for the new feedback
        const newId = savedFeedback.length > 0 ? Math.max(...savedFeedback.map(f => f.id)) + 1 : 1;
        
        // Add the new feedback with an ID
        savedFeedback.push({
            id: newId,
            ...feedback
        });
        
        // Save back to localStorage
        localStorage.setItem('exitFeedback', JSON.stringify(savedFeedback));
    }
    
    // Helper function to show toast notifications
    function showToast(type, title, message) {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) return;
        
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = 'toast align-items-center text-white bg-' + type + ' border-0';
        toast.role = 'alert';
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
    
    // Initialize the page
    initPage();
});
