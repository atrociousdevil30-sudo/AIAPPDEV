// Mock data for recruitment pipeline
const mockPipelineData = {
    pipeline: {
        "Sourced": 0,
        "Applied": 0,
        "Phone Screen": 0,
        "Technical Interview": 0,
        "Final Interview": 0,
        "Offer Extended": 0,
        "Hired": 0
    },
    candidates: []
};

// Generate mock candidates
function generateMockCandidates() {
    const positions = [
        "Software Engineer",
        "Data Scientist",
        "Product Manager",
        "UX Designer",
        "DevOps Engineer",
        "ML Engineer",
        "Frontend Developer",
        "Backend Developer"
    ];
    
    const statuses = Object.keys(mockPipelineData.pipeline);
    const names = [
        "Alex Johnson", "Jordan Smith", "Taylor Swift", "Casey Wilson", 
        "Riley Cooper", "Jamie Lee", "Morgan Taylor", "Quinn Evans"
    ];
    
    // Generate 20 mock candidates
    for (let i = 1; i <= 20; i++) {
        const status = statuses[Math.floor(Math.random() * statuses.length)];
        const firstName = names[Math.floor(Math.random() * names.length)].split(' ')[0];
        const lastName = names[Math.floor(Math.random() * names.length)].split(' ')[1] || 'Smith';
        
        mockPipelineData.candidates.push({
            id: `CAN-${1000 + i}`,
            name: `${firstName} ${lastName}`,
            position: positions[Math.floor(Math.random() * positions.length)],
            email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}@example.com`,
            phone: `+1-555-${Math.floor(100 + Math.random() * 900)}-${Math.floor(1000 + Math.random() * 9000)}`,
            score: Math.floor(50 + Math.random() * 50),
            status: status,
            applied_date: new Date(Date.now() - Math.floor(Math.random() * 30) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            last_updated: new Date().toISOString()
        });
        
        // Update pipeline counts
        mockPipelineData.pipeline[status]++;
    }
    
    return mockPipelineData;
}

// Update the UI with pipeline data
function updatePipelineUI() {
    // Update pipeline cards
    Object.entries(mockPipelineData.pipeline).forEach(([status, count]) => {
        const statusId = status.toLowerCase().replace(/\s+/g, '-');
        const countElement = document.getElementById(`${statusId}-count`);
        const cardElement = document.getElementById(`pipeline-${statusId}`);
        
        if (countElement) countElement.textContent = count;
        if (cardElement) {
            const progressBar = cardElement.querySelector('.progress-bar');
            if (progressBar) {
                const percentage = Math.min(100, (count / 20) * 100);
                progressBar.style.width = `${percentage}%`;
                progressBar.setAttribute('aria-valuenow', percentage);
            }
        }
    });
    
    // Update candidate table in modal
    updateCandidateTable();
}

// Update the candidate table in the modal
function updateCandidateTable() {
    const tableBody = document.querySelector('#pipelineModal table tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    mockPipelineData.candidates.forEach(candidate => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${candidate.id}</td>
            <td>${candidate.name}</td>
            <td>${candidate.position}</td>
            <td>${candidate.email}</td>
            <td>${candidate.phone}</td>
            <td><span class="badge ${getScoreBadgeClass(candidate.score)}">${candidate.score}</span></td>
            <td><span class="badge ${getStatusBadgeClass(candidate.status)}">${candidate.status}</span></td>
            <td>${candidate.applied_date}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Helper function to get badge class based on score
function getScoreBadgeClass(score) {
    if (score >= 80) return 'bg-success';
    if (score >= 60) return 'bg-info';
    if (score >= 40) return 'bg-warning';
    return 'bg-danger';
}

// Helper function to get badge class based on status
function getStatusBadgeClass(status) {
    const statusClasses = {
        'Sourced': 'bg-secondary',
        'Applied': 'bg-primary',
        'Phone Screen': 'bg-info',
        'Technical Interview': 'bg-warning',
        'Final Interview': 'bg-primary',
        'Offer Extended': 'bg-success',
        'Hired': 'bg-success'
    };
    return statusClasses[status] || 'bg-secondary';
}

// Initialize the pipeline when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Generate mock data
    generateMockCandidates();
    
    // Update UI with mock data
    updatePipelineUI();
    
    // Add event listener for the modal show event to refresh data
    const pipelineModal = document.getElementById('pipelineModal');
    if (pipelineModal) {
        pipelineModal.addEventListener('show.bs.modal', function() {
            updatePipelineUI();
        });
    }
});
