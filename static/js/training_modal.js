document.addEventListener('DOMContentLoaded', function() {
    // Get the modal element
    const trainingModal = new bootstrap.Modal(document.getElementById('trainingDataModal'));
    
    // Show modal when view examples button is clicked
    const viewExamplesBtn = document.getElementById('viewExamplesBtn');
    if (viewExamplesBtn) {
        viewExamplesBtn.addEventListener('click', function(e) {
            e.preventDefault();
            trainingModal.show();
        });
    }

    // Handle view sample data buttons
    const viewButtons = document.querySelectorAll('.view-sample-data');
    viewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const row = this.closest('tr');
            const type = row.cells[1].textContent;
            const date = row.cells[0].textContent;
            
            // Update modal content based on the selected row
            document.getElementById('trainingTypeLabel').textContent = type;
            document.getElementById('trainingDate').textContent = date;
        });
    });

    // Handle use as template button
    const useTemplateBtn = document.getElementById('useAsTemplate');
    if (useTemplateBtn) {
        useTemplateBtn.addEventListener('click', function() {
            // Auto-fill the training form with sample data
            document.getElementById('trainingType').value = 'recruitment';
            document.getElementById('instructions').value = 'Focus on technical skills assessment and cultural fit evaluation. Pay special attention to problem-solving approaches and communication skills.';
            document.getElementById('sampleQnA').value = 'Q: Can you explain your experience with [specific technology]?\nA: [Expected answer format]\n\nQ: How do you handle tight deadlines?\nA: [Expected answer format]';
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('trainingDataModal'));
            modal.hide();
            
            // Scroll to form
            document.getElementById('trainingForm').scrollIntoView({ behavior: 'smooth' });
            
            // Show success message
            alert('Training form has been pre-filled with sample data. Please review and adjust as needed.');
        });
    }
});
