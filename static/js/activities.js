// Mock data for recent activities
const mockActivities = {
    activities: []
};

// Generate mock activities
function generateMockActivities() {
    const activityTypes = [
        { type: 'application', icon: 'fa-file-alt', color: 'primary' },
        { type: 'interview', icon: 'fa-video', color: 'info' },
        { type: 'status', icon: 'fa-exchange-alt', color: 'warning' },
        { type: 'note', icon: 'fa-sticky-note', color: 'success' },
        { type: 'email', icon: 'fa-envelope', color: 'danger' },
        { type: 'evaluation', icon: 'fa-star', color: 'warning' }
    ];
    
    const actions = {
        application: ['submitted', 'reviewed', 'shortlisted', 'rejected'],
        interview: ['scheduled', 'completed', 'rescheduled', 'cancelled'],
        status: ['status updated to', 'moved to', 'advanced to'],
        note: ['added a note', 'updated a note', 'commented'],
        email: ['sent', 'received', 'replied to'],
        evaluation: ['evaluated', 'scored', 'rated']
    };
    
    const candidates = [
        { name: 'Alex Johnson', position: 'Software Engineer' },
        { name: 'Taylor Swift', position: 'Data Scientist' },
        { name: 'Jordan Smith', position: 'Product Manager' },
        { name: 'Casey Wilson', position: 'UX Designer' },
        { name: 'Riley Cooper', position: 'DevOps Engineer' },
        { name: 'Jamie Lee', position: 'ML Engineer' },
        { name: 'Morgan Taylor', position: 'Frontend Developer' },
        { name: 'Quinn Evans', position: 'Backend Developer' }
    ];
    
    const statuses = [
        'Sourced', 'Applied', 'Phone Screen', 
        'Technical Interview', 'Final Interview', 
        'Offer Extended', 'Hired', 'Rejected'
    ];
    
    // Generate 20 mock activities
    for (let i = 0; i < 20; i++) {
        const activityType = activityTypes[Math.floor(Math.random() * activityTypes.length)];
        const candidate = candidates[Math.floor(Math.random() * candidates.length)];
        const action = actions[activityType.type][Math.floor(Math.random() * actions[activityType.type].length)];
        const timestamp = new Date(Date.now() - Math.floor(Math.random() * 7) * 24 * 60 * 60 * 1000 - Math.floor(Math.random() * 86400000));
        
        let description = '';
        
        switch(activityType.type) {
            case 'application':
                description = `Application ${action} for ${candidate.position}`;
                break;
            case 'interview':
                description = `Interview ${action} with ${candidate.name}`;
                break;
            case 'status':
                const newStatus = statuses[Math.floor(Math.random() * statuses.length)];
                description = `${action} ${newStatus}`;
                break;
            case 'note':
                description = `${action} on ${candidate.name}'s application`;
                break;
            case 'email':
                description = `Email ${action} to ${candidate.name}`;
                break;
            case 'evaluation':
                const score = Math.floor(50 + Math.random() * 50);
                description = `${action} ${candidate.name} (${score}/100)`;
                break;
        }
        
        mockActivities.activities.push({
            id: `ACT-${1000 + i}`,
            type: activityType,
            candidate: candidate.name,
            position: candidate.position,
            description: description,
            timestamp: timestamp,
            isRead: Math.random() > 0.5
        });
    }
    
    // Sort activities by timestamp (newest first)
    mockActivities.activities.sort((a, b) => b.timestamp - a.timestamp);
    
    return mockActivities;
}

// Update the activities list in the UI
function updateActivitiesList(limit = 5) {
    const activitiesList = document.getElementById('activities-list');
    const activitiesModalList = document.getElementById('activities-modal-list');
    
    if (!activitiesList && !activitiesModalList) return;
    
    // Get the most recent activities
    const recentActivities = mockActivities.activities.slice(0, limit);
    const allActivities = mockActivities.activities;
    
    // Update the main activities list (dashboard)
    if (activitiesList) {
        activitiesList.innerHTML = recentActivities.map(activity => `
            <div class="d-flex align-items-start mb-3">
                <div class="flex-shrink-0 me-3">
                    <div class="avatar-sm">
                        <div class="avatar-title rounded-circle bg-${activity.type.color}-subtle text-${activity.type.color} fs-16">
                            <i class="fas ${activity.type.icon}"></i>
                        </div>
                    </div>
                </div>
                <div class="flex-grow-1">
                    <h6 class="mb-1">${activity.description}</h6>
                    <p class="text-muted mb-0 small">
                        ${activity.candidate} • ${activity.position}
                        <span class="ms-2">${formatTimeAgo(activity.timestamp)}</span>
                    </p>
                </div>
                ${!activity.isRead ? '<span class="badge bg-danger badge-dot"></span>' : ''}
            </div>
        `).join('');
    }
    
    // Update the activities modal list
    if (activitiesModalList) {
        activitiesModalList.innerHTML = allActivities.map(activity => `
            <div class="d-flex align-items-start mb-3 ${!activity.isRead ? 'bg-dark bg-opacity-25 p-2 rounded' : 'p-2'}">
                <div class="flex-shrink-0 me-3">
                    <div class="avatar-sm">
                        <div class="avatar-title rounded-circle bg-${activity.type.color}-subtle text-${activity.type.color} fs-16">
                            <i class="fas ${activity.type.icon}"></i>
                        </div>
                    </div>
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-start">
                        <h6 class="mb-1">${activity.description}</h6>
                        <small class="text-muted">${formatTimeAgo(activity.timestamp)}</small>
                    </div>
                    <p class="text-muted small mb-0">
                        ${activity.candidate} • ${activity.position}
                    </p>
                </div>
            </div>
        `).join('');
    }
    
    // Update the unread count badge
    const unreadCount = mockActivities.activities.filter(a => !a.isRead).length;
    const unreadBadge = document.getElementById('unread-count');
    const unreadBadgeModal = document.getElementById('unread-count-modal');
    
    if (unreadBadge) {
        unreadBadge.textContent = unreadCount;
        unreadBadge.style.display = unreadCount > 0 ? 'inline-block' : 'none';
    }
    
    if (unreadBadgeModal) {
        unreadBadgeModal.textContent = unreadCount;
        unreadBadgeModal.style.display = unreadCount > 0 ? 'inline-block' : 'none';
    }
}

// Format timestamp as "time ago"
function formatTimeAgo(timestamp) {
    const seconds = Math.floor((new Date() - timestamp) / 1000);
    
    let interval = Math.floor(seconds / 31536000);
    if (interval > 1) return `${interval} years ago`;
    if (interval === 1) return '1 year ago';
    
    interval = Math.floor(seconds / 2592000);
    if (interval > 1) return `${interval} months ago`;
    if (interval === 1) return '1 month ago';
    
    interval = Math.floor(seconds / 86400);
    if (interval > 1) return `${interval} days ago`;
    if (interval === 1) return 'yesterday';
    
    interval = Math.floor(seconds / 3600);
    if (interval > 1) return `${interval} hours ago`;
    if (interval === 1) return '1 hour ago';
    
    interval = Math.floor(seconds / 60);
    if (interval > 1) return `${interval} minutes ago`;
    if (interval === 1) return '1 minute ago';
    
    return 'just now';
}

// Mark all activities as read
function markAllAsRead() {
    mockActivities.activities.forEach(activity => {
        activity.isRead = true;
    });
    updateActivitiesList();
}

// Initialize the activities when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Generate mock data
    generateMockActivities();
    
    // Update the UI with mock data
    updateActivitiesList();
    
    // Add event listener for the refresh button
    const refreshButton = document.getElementById('refresh-activities');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            generateMockActivities();
            updateActivitiesList();
            // Show a toast or notification
            const toast = new bootstrap.Toast(document.getElementById('refreshToast'));
            toast.show();
        });
    }
    
    // Add event listener for the mark all as read button
    const markAllReadButton = document.getElementById('mark-all-read');
    if (markAllReadButton) {
        markAllReadButton.addEventListener('click', markAllAsRead);
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
