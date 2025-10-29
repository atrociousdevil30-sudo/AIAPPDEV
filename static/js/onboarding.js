document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const resumeForm = document.getElementById('resumeForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const analyzeSpinner = document.getElementById('analyzeSpinner');
    const analyzeText = document.getElementById('analyzeText');
    const resultCard = document.getElementById('resultCard');
    const startInterviewBtn = document.getElementById('startInterviewBtn');
    const saveCandidateBtn = document.getElementById('saveCandidateBtn');
    const notifyItBtn = document.getElementById('notifyItBtn');
    const resumeTextArea = document.getElementById('resumeText');
    const jobDescriptionArea = document.getElementById('jobDescription');
    const candidateNameInput = document.getElementById('candidateName');
    const jobTitleInput = document.getElementById('jobDescriptionTitle');
    const clearFormBtn = document.getElementById('clearForm');
    
    // Sample candidate click handler
    document.querySelectorAll('.sample-candidate').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            try {
                // Fill form with sample data
                candidateNameInput.value = this.dataset.name;
                jobTitleInput.value = this.dataset.job;
                
                // Set job description based on role
                let jobDesc = '';
                const role = this.dataset.job.toLowerCase();
                
                if (role.includes('python') || role.includes('developer')) {
                    jobDesc = 'We are looking for a skilled Software Engineer with experience in Python, JavaScript, and cloud technologies. The ideal candidate should have 3+ years of experience in full-stack development and a strong understanding of software architecture.';
                } else if (role.includes('data')) {
                    jobDesc = 'Seeking a Data Scientist with expertise in machine learning, statistical analysis, and data visualization. The role involves working with large datasets and developing predictive models to drive business decisions.';
                } else if (role.includes('design') || role.includes('ux') || role.includes('ui')) {
                    jobDesc = 'Looking for a creative UX/UI Designer to create amazing user experiences. The ideal candidate should have a strong portfolio, proficiency in design tools, and experience with user research and testing.';
                } else {
                    jobDesc = 'We are seeking a qualified professional for this role. The ideal candidate will have relevant experience and a strong track record of success in their field.';
                }
                
                jobDescriptionArea.value = jobDesc;
                
                // Handle the escaped resume text
                const resumeText = this.dataset.resume
                    .replace(/\\n/g, '\n')         // Convert \n to newlines
                    .replace(/\\"/g, '"')         // Unescape double quotes
                    .replace(/\\'/g, "'");          // Unescape single quotes
                
                resumeTextArea.value = resumeText;
                
                // Auto-expand textareas
                autoExpandTextarea(jobDescriptionArea);
                autoExpandTextarea(resumeTextArea);
                
                // Scroll to form
                document.querySelector('#resumeForm').scrollIntoView({ behavior: 'smooth' });
                
            } catch (error) {
                console.error('Error loading sample candidate:', error);
                showToast('danger', 'Error', 'Failed to load sample candidate data.');
            }
        });
    });
    
    // Clear form button
    if (clearFormBtn) {
        clearFormBtn.addEventListener('click', function() {
            resumeForm.reset();
            if (resultCard) resultCard.classList.add('d-none');
            // Reset textarea heights
            jobDescriptionArea.style.height = 'auto';
            resumeTextArea.style.height = 'auto';
        });
    }
    
    // Sample job descriptions for auto-suggestion
    const sampleJobDescriptions = {
        'software_engineer': 'We are looking for a skilled Software Engineer with experience in Python, JavaScript, and cloud technologies. The ideal candidate should have 3+ years of experience in full-stack development and a strong understanding of software architecture.',
        'data_scientist': 'Seeking a Data Scientist with expertise in machine learning, statistical analysis, and data visualization. The role involves working with large datasets and developing predictive models to drive business decisions.',
        'ux_designer': 'Looking for a creative UX Designer to create amazing user experiences. The ideal candidate should have a strong portfolio, proficiency in design tools, and experience with user research and testing.'
    };

    // Auto-expand textareas as user types
    function autoExpandTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight) + 'px';
    }

    // Add event listeners for auto-expanding textareas
    [resumeTextArea, jobDescriptionArea].forEach(area => {
        if (area) {
            area.addEventListener('input', function() {
                autoExpandTextarea(this);
            });
            // Initialize height
            autoExpandTextarea(area);
        }
    });

    // Handle form submission
    if (resumeForm) {
        resumeForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Validate form
            const name = candidateNameInput.value.trim();
            const jobTitle = jobTitleInput.value.trim();
            const jobDesc = jobDescriptionArea.value.trim();
            const resumeText = resumeTextArea.value.trim();
            
            if (!name || !jobTitle || !jobDesc || !resumeText) {
                showToast('warning', 'Missing Information', 'Please fill in all required fields.');
                // Highlight empty fields
                if (!name) candidateNameInput.classList.add('is-invalid');
                if (!jobTitle) jobTitleInput.classList.add('is-invalid');
                if (!jobDesc) jobDescriptionArea.classList.add('is-invalid');
                if (!resumeText) resumeTextArea.classList.add('is-invalid');
                
                // Remove validation after 3 seconds
                setTimeout(() => {
                    [candidateNameInput, jobTitleInput, jobDescriptionArea, resumeTextArea].forEach(
                        el => el && el.classList.remove('is-invalid')
                    );
                }, 3000);
                return;
            }
            
            // Show loading state
            analyzeBtn.disabled = true;
            analyzeSpinner.classList.remove('d-none');
            analyzeText.textContent = 'Analyzing...';
            
            try {
                // Submit the form directly - let the server handle the redirect
                resumeForm.submit();
                
            } catch (error) {
                console.error('Error submitting form:', error);
                showToast('danger', 'Error', 'Failed to submit the form. Please try again.');
                analyzeBtn.disabled = false;
                analyzeText.textContent = 'Analyze Resume';
                analyzeSpinner.classList.add('d-none');
            }
        });
    }
    
    // Mock resume analysis function
    async function mockResumeAnalysis(name, jobDesc, resumeText) {
        return new Promise((resolve) => {
            // Simulate API delay
            setTimeout(() => {
                // Simple keyword matching for demo purposes
                const keywords = {
                    'python': { weight: 1.5, found: false },
                    'javascript': { weight: 1.5, found: false },
                    'machine learning': { weight: 2, found: false },
                    'react': { weight: 1.2, found: false },
                    'sql': { weight: 1.3, found: false },
                    'cloud': { weight: 1.4, found: false },
                    'agile': { weight: 1.1, found: false },
                    'docker': { weight: 1.3, found: false },
                    'api': { weight: 1.2, found: false },
                    'git': { weight: 1.1, found: false }
                };
                
                // Check which keywords are in the resume
                const resumeLower = resumeText.toLowerCase();
                let score = 30; // Base score
                let matchedKeywords = [];
                
                for (const [keyword, data] of Object.entries(keywords)) {
                    if (resumeLower.includes(keyword)) {
                        keywords[keyword].found = true;
                        score += data.weight * 5; // Add weighted score for each match
                        matchedKeywords.push(keyword);
                    }
                }
                
                // Cap score at 100
                score = Math.min(Math.round(score), 95);
                
                // Generate summary based on matches
                let summary = `Based on our analysis, ${name} has relevant experience for this position. `;
                
                if (matchedKeywords.length > 0) {
                    summary += `The resume shows strong skills in ${matchedKeywords.slice(0, 3).join(', ')}. `;
                }
                
                if (score > 80) {
                    summary += "This candidate is highly recommended for the next interview round.";
                } else if (score > 60) {
                    summary += "This candidate meets the basic requirements and could be considered.";
                } else {
                    summary += "This candidate may not be the best fit based on the resume alone.";
                }
                
                // In a real implementation, the server would return the candidate ID
                // For now, we'll use a mock candidate ID and construct the URL
                const candidateId = Math.floor(Math.random() * 1000);
                resolve({
                    success: true,
                    candidate: {
                        id: candidateId,
                        name: name,
                        score: score,
                        summary: summary,
                        matchedKeywords: matchedKeywords
                    },
                    redirect: true,
                    url: `/hr/resume-review/${candidateId}`
                });
            });
        });
    }
    
    // Display analysis results
    function displayAnalysisResults(data) {
        if (!data.success || !data.candidate) return;
        
        const { name, score, summary } = data.candidate;
        
        // Update result card
        if (document.getElementById('resultName')) {
            document.getElementById('resultName').textContent = name;
        }
        if (document.getElementById('aiSummary')) {
            document.getElementById('aiSummary').textContent = summary;
        }
        
        // Animate score bar
        const scoreBar = document.getElementById('scoreBar');
        const scoreValue = document.getElementById('scoreValue');
        
        // Reset and animate
        scoreBar.style.width = '0%';
        scoreBar.className = 'progress-bar';
        
        // Determine color based on score
        if (score >= 80) {
            scoreBar.classList.add('bg-success');
        } else if (score >= 60) {
            scoreBar.classList.add('bg-warning');
        } else {
            scoreBar.classList.add('bg-danger');
        }
        
        // Animate progress bar
        let width = 0;
        const interval = setInterval(() => {
            if (width >= score) {
                clearInterval(interval);
                scoreValue.textContent = `${score}%`;
            } else {
                width++;
                scoreBar.style.width = `${width}%`;
                scoreValue.textContent = `${width}%`;
            }
        }, 20);
        
        // Show result card with animation
        resultCard.classList.remove('d-none');
        resultCard.style.opacity = '0';
        resultCard.style.transition = 'opacity 0.5s ease-in';
        
        // Trigger reflow
        void resultCard.offsetWidth;
        
        // Fade in
        resultCard.style.opacity = '1';
        
        // Scroll to results
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    // Event listeners for action buttons
    if (startInterviewBtn) {
        startInterviewBtn.addEventListener('click', function() {
            // In a real app, this would navigate to the interview page with the candidate's data
            showToast('info', 'Interview', 'Redirecting to interview page...');
            setTimeout(() => {
                window.location.href = '/interview';
            }, 1000);
        });
    }
    
    if (saveCandidateBtn) {
        saveCandidateBtn.addEventListener('click', function() {
            // In a real app, this would save the candidate's data to the database
            const saveSpinner = document.createElement('span');
            saveSpinner.className = 'spinner-border spinner-border-sm me-2';
            saveSpinner.role = 'status';
            saveSpinner.setAttribute('aria-hidden', 'true');
            
            const originalContent = saveCandidateBtn.innerHTML;
            saveCandidateBtn.disabled = true;
            saveCandidateBtn.innerHTML = '';
            saveCandidateBtn.appendChild(saveSpinner);
            saveCandidateBtn.appendChild(document.createTextNode('Saving...'));
            
            setTimeout(() => {
                saveCandidateBtn.innerHTML = originalContent;
                saveCandidateBtn.disabled = false;
                
                const checkIcon = document.createElement('i');
                checkIcon.className = 'bi bi-check2 me-2';
                
                saveCandidateBtn.innerHTML = '';
                saveCandidateBtn.appendChild(checkIcon);
                saveCandidateBtn.appendChild(document.createTextNode('Saved!'));
                
                setTimeout(() => {
                    saveCandidateBtn.innerHTML = originalContent;
                }, 2000);
                
                showToast('success', 'Success', 'Candidate information saved successfully!');
            }, 1000);
        });
    }
    
    if (notifyItBtn) {
        notifyItBtn.addEventListener('click', function() {
            // In a real app, this would send a notification to the IT department
            const originalContent = notifyItBtn.innerHTML;
            notifyItBtn.disabled = true;
            notifyItBtn.innerHTML = '<i class="bi bi-bell-fill me-2"></i> Notified!';
            
            setTimeout(() => {
                notifyItBtn.innerHTML = originalContent;
                notifyItBtn.disabled = false;
            }, 2000);
            
            showToast('info', 'Notification Sent', 'IT Department has been notified about the new hire.');
        });
    }
    
    // Add sample job description button
    const sampleJobContainer = document.createElement('div');
    sampleJobContainer.className = 'mb-3';
    sampleJobContainer.innerHTML = `
        <div class="btn-group btn-group-sm" role="group">
            <button type="button" class="btn btn-outline-secondary" id="sampleSoftwareEngineer">Software Engineer</button>
            <button type="button" class="btn btn-outline-secondary" id="sampleDataScientist">Data Scientist</button>
            <button type="button" class="btn btn-outline-secondary" id="sampleUxDesigner">UX Designer</button>
        </div>
        <small class="text-muted d-block mt-1">Try sample job descriptions</small>
    `;
    
    // Insert the sample job buttons before the job description textarea
    if (jobDescriptionArea && jobDescriptionArea.parentNode) {
        jobDescriptionArea.parentNode.insertBefore(sampleJobContainer, jobDescriptionArea);
        
        // Add event listeners for sample job buttons
        document.getElementById('sampleSoftwareEngineer')?.addEventListener('click', () => {
            jobDescriptionArea.value = sampleJobDescriptions.software_engineer;
            autoExpandTextarea(jobDescriptionArea);
        });
        
        document.getElementById('sampleDataScientist')?.addEventListener('click', () => {
            jobDescriptionArea.value = sampleJobDescriptions.data_scientist;
            autoExpandTextarea(jobDescriptionArea);
        });
        
        document.getElementById('sampleUxDesigner')?.addEventListener('click', () => {
            jobDescriptionArea.value = sampleJobDescriptions.ux_designer;
            autoExpandTextarea(jobDescriptionArea);
        });
    }
    
    // Add resume template button
    const resumeTemplateBtn = document.createElement('button');
    resumeTemplateBtn.type = 'button';
    resumeTemplateBtn.className = 'btn btn-sm btn-outline-secondary mb-2';
    resumeTemplateBtn.innerHTML = '<i class="bi bi-file-earmark-text me-1"></i> Use Sample Resume';
    resumeTemplateBtn.addEventListener('click', function() {
        resumeTextArea.value = `John Doe
123 Main Street, City, ST 12345
(123) 456-7890 | john.doe@email.com | linkedin.com/in/johndoe

SUMMARY
Results-driven Software Engineer with 5+ years of experience in full-stack development. Proficient in JavaScript, Python, and cloud technologies. Passionate about building scalable web applications and solving complex problems.

EXPERIENCE
Senior Software Engineer
Tech Solutions Inc. | Jan 2020 - Present
• Led a team of 5 developers to build a scalable microservices architecture using Node.js and React
• Implemented CI/CD pipelines reducing deployment time by 40%
• Developed RESTful APIs handling 10,000+ requests per minute

Software Developer
WebApps Co. | Jun 2017 - Dec 2019
• Built responsive web applications using React and Redux
• Optimized database queries, improving performance by 30%
• Collaborated with cross-functional teams to deliver features on time

EDUCATION
Bachelor of Science in Computer Science
University of Technology, 2017

SKILLS
• Programming: JavaScript, Python, Java, SQL
• Frameworks: React, Node.js, Express, Django
• Tools: Git, Docker, AWS, Jenkins
• Methodologies: Agile, Scrum, TDD`;
        
        autoExpandTextarea(resumeTextArea);
        showToast('info', 'Sample Resume', 'A sample resume has been loaded. Feel free to modify it.');
    });
    
    // Insert the resume template button before the resume textarea
    if (resumeTextArea && resumeTextArea.parentNode) {
        resumeTextArea.parentNode.insertBefore(resumeTemplateBtn, resumeTextArea);
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
});
