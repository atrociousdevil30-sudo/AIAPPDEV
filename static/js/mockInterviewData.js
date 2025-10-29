// Mock interview data for demonstration
const mockCandidates = [
    {
        id: 1,
        name: "Sarah Johnson",
        position: "Senior Frontend Developer",
        status: "Completed",
        email: "sarah.johnson@example.com",
        phone: "(555) 123-4567",
        location: "San Francisco, CA",
        skills: ["React", "TypeScript", "Redux", "Node.js", "GraphQL"],
        score: 92,
        interviewDate: "Oct 24, 2023",
        avatar: "default-avatar.png",
        resume: "Sarah_Johnson_Resume.pdf",
        interview: [
            {
                id: 1,
                sender: "AI Interviewer",
                time: "10:00 AM",
                content: "Can you tell me about your experience with React and how you've used it in your previous projects?",
                type: "question",
                analysis: {
                    score: 95,
                    feedback: "Excellent response. The candidate demonstrated deep knowledge of React's core concepts and provided specific examples of performance optimization techniques they've implemented.",
                    keywords: ["React Hooks", "Performance Optimization", "State Management"]
                }
            },
            {
                id: 2,
                sender: "Sarah Johnson",
                time: "10:02 AM",
                content: "I've been working with React for over 5 years. In my current role at TechCorp, I've built several high-traffic applications using React with TypeScript. I'm particularly proud of implementing a custom hook system that reduced our component re-renders by 40%. I also have extensive experience with Redux for state management and have contributed to open-source React libraries.",
                type: "answer"
            },
            {
                id: 3,
                sender: "AI Interviewer",
                time: "10:05 AM",
                content: "How do you handle state management in large applications?",
                type: "question",
                analysis: {
                    score: 90,
                    feedback: "Strong understanding of state management patterns. The candidate provided a clear explanation of when to use different state management solutions.",
                    keywords: ["Redux", "Context API", "State Management", "Performance"]
                }
            },
            {
                id: 4,
                sender: "Sarah Johnson",
                time: "10:08 AM",
                content: "For large applications, I prefer a hybrid approach. I use Redux for global state that needs to be accessed across multiple components, React Context for theme and user preferences, and local component state for UI-specific state. I also leverage Redux Toolkit to reduce boilerplate and improve maintainability. In my last project, I implemented Redux Persist to maintain state across page refreshes, which significantly improved the user experience.",
                type: "answer"
            },
            {
                id: 5,
                sender: "AI Interviewer",
                time: "10:12 AM",
                content: "Can you explain how you would optimize the performance of a React application?",
                type: "question",
                analysis: {
                    score: 98,
                    feedback: "Exceptional response. The candidate demonstrated advanced knowledge of React performance optimization techniques with specific metrics from previous projects.",
                    keywords: ["Performance", "Optimization", "React.memo", "useMemo", "useCallback"]
                }
            },
            {
                id: 6,
                sender: "Sarah Johnson",
                time: "10:15 AM",
                content: "Performance optimization is crucial. I typically start with code splitting using React.lazy and Suspense to reduce the initial bundle size. I use React.memo for preventing unnecessary re-renders, and I'm careful with context to avoid unnecessary re-renders. For heavy computations, I use useMemo, and for callbacks, I use useCallback. I also leverage the React DevTools profiler to identify performance bottlenecks. In my last project, these techniques helped reduce the Time to Interactive by 35%.",
                type: "answer"
            }
        ],
        skillsAssessment: {
            technicalKnowledge: 95,
            problemSolving: 90,
            communication: 88,
            teamwork: 85
        },
        keyInsights: [
            "Extensive experience with React and modern JavaScript/TypeScript",
            "Strong understanding of performance optimization techniques",
            "Experience with testing frameworks like Jest and React Testing Library",
            "Good communication skills and ability to explain complex concepts"
        ]
    },
    {
        id: 2,
        name: "Michael Chen",
        position: "Full Stack Developer",
        status: "Completed",
        email: "michael.chen@example.com",
        phone: "(555) 234-5678",
        location: "New York, NY",
        skills: ["Node.js", "Express", "MongoDB", "React", "AWS"],
        score: 85,
        interviewDate: "Oct 23, 2023",
        avatar: "default-avatar.png",
        resume: "Michael_Chen_Resume.pdf",
        interview: [
            {
                id: 1,
                sender: "AI Interviewer",
                time: "2:00 PM",
                content: "Can you describe your experience with building RESTful APIs using Node.js?",
                type: "question",
                analysis: {
                    score: 88,
                    feedback: "Good understanding of RESTful principles and Node.js. The candidate provided specific examples of API design patterns they've implemented.",
                    keywords: ["REST API", "Node.js", "Express", "MongoDB"]
                }
            },
            {
                id: 2,
                sender: "Michael Chen",
                time: "2:03 PM",
                content: "I've built several RESTful APIs using Node.js and Express. In my current role, I designed and implemented an API that handles over 10,000 requests per minute. I used JWT for authentication, implemented rate limiting, and used MongoDB with Mongoose for the database layer. I also wrote comprehensive unit tests using Jest and Supertest to ensure reliability.",
                type: "answer"
            },
            {
                id: 3,
                sender: "AI Interviewer",
                time: "2:07 PM",
                content: "How do you handle database migrations and schema changes in MongoDB?",
                type: "question",
                analysis: {
                    score: 82,
                    feedback: "Adequate response. The candidate understands the basics but could benefit from more experience with complex migration scenarios.",
                    keywords: ["MongoDB", "Migrations", "Schema Design", "Database"]
                }
            },
            {
                id: 4,
                sender: "Michael Chen",
                time: "2:10 PM",
                content: "For schema changes, I typically use Mongoose schema versioning. I write migration scripts that can be run before the application starts to update documents to match the new schema. For larger changes, I create a new collection and gradually migrate data to avoid downtime. I also make sure to back up the database before running any migrations.",
                type: "answer"
            }
        ],
        skillsAssessment: {
            technicalKnowledge: 85,
            problemSolving: 82,
            communication: 80,
            teamwork: 78
        },
        keyInsights: [
            "Strong backend development skills with Node.js and Express",
            "Experience with MongoDB and database design",
            "Understanding of RESTful API design principles",
            "Could improve on frontend development skills"
        ]
    },
    {
        id: 3,
        name: "Emily Rodriguez",
        position: "Senior UI/UX Designer",
        status: "In Progress",
        email: "emily.rodriguez@example.com",
        phone: "(555) 345-6789",
        location: "Austin, TX",
        skills: ["Figma", "Sketch", "React", "CSS-in-JS", "User Research"],
        score: 88,
        interviewDate: "Oct 22, 2023",
        avatar: "default-avatar.png",
        resume: "Emily_Rodriguez_Resume.pdf",
        interview: [
            {
                id: 1,
                sender: "AI Interviewer",
                time: "2:00 PM",
                content: "Can you walk us through your design process when starting a new project?",
                type: "question",
                analysis: {
                    score: 90,
                    feedback: "Strong understanding of user-centered design principles. Provided a clear, structured approach to the design process.",
                    keywords: ["Design Thinking", "User Research", "Wireframing", "Prototyping"]
                }
            },
            {
                id: 2,
                sender: "Emily Rodriguez",
                time: "2:03 PM",
                content: "I start with user research to understand pain points, then create user personas and user flows. I move to low-fidelity wireframes, gather feedback, and iterate before creating high-fidelity designs. I work closely with developers throughout the process to ensure feasibility.",
                type: "answer"
            }
        ]
    },
    {
        id: 4,
        name: "David Kim",
        position: "DevOps Engineer",
        status: "Scheduled",
        email: "david.kim@example.com",
        phone: "(555) 456-7890",
        location: "Seattle, WA",
        skills: ["Docker", "Kubernetes", "AWS", "Terraform", "CI/CD"],
        score: 0,
        interviewDate: "Oct 27, 2023",
        avatar: "default-avatar.png",
        resume: "David_Kim_Resume.pdf"
    },
    {
        id: 5,
        name: "Priya Patel",
        position: "Machine Learning Engineer",
        status: "Completed",
        email: "priya.patel@example.com",
        phone: "(555) 567-8901",
        location: "Boston, MA",
        skills: ["Python", "TensorFlow", "PyTorch", "NLP", "Computer Vision"],
        score: 94,
        interviewDate: "Oct 21, 2023",
        avatar: "default-avatar.png",
        resume: "Priya_Patel_Resume.pdf"
    },
    {
        id: 6,
        name: "James Wilson",
        position: "Senior Backend Developer",
        status: "In Progress",
        email: "james.wilson@example.com",
        phone: "(555) 678-9012",
        location: "Chicago, IL",
        skills: ["Java", "Spring Boot", "Microservices", "Kafka", "PostgreSQL"],
        score: 0,
        interviewDate: "Oct 25, 2023",
        avatar: "default-avatar.png",
        resume: "James_Wilson_Resume.pdf"
    },
    {
        id: 7,
        name: "Aisha Mohammed",
        position: "Product Manager",
        status: "Scheduled",
        email: "aisha.mohammed@example.com",
        phone: "(555) 789-0123",
        location: "Denver, CO",
        skills: ["Agile", "Scrum", "Product Strategy", "Market Research", "JIRA"],
        score: 0,
        interviewDate: "Oct 28, 2023",
        avatar: "default-avatar.png",
        resume: "Aisha_Mohammed_Resume.pdf"
    },
    {
        id: 8,
        name: "Carlos Mendez",
        position: "Mobile Developer",
        status: "Completed",
        email: "carlos.mendez@example.com",
        phone: "(555) 890-1234",
        location: "Miami, FL",
        skills: ["React Native", "Swift", "Kotlin", "Firebase", "Redux"],
        score: 89,
        interviewDate: "Oct 20, 2023",
        avatar: "default-avatar.png",
        resume: "Carlos_Mendez_Resume.pdf"
    },
    {
        id: 9,
        name: "Olivia Chen",
        position: "Data Scientist",
        status: "In Progress",
        email: "olivia.chen@example.com",
        phone: "(555) 901-2345",
        location: "Portland, OR",
        skills: ["Python", "Pandas", "SQL", "Machine Learning", "Data Visualization"],
        score: 0,
        interviewDate: "Oct 26, 2023",
        avatar: "default-avatar.png",
        resume: "Olivia_Chen_Resume.pdf"
    },
    {
        id: 10,
        name: "Marcus Johnson",
        position: "Cloud Solutions Architect",
        status: "Scheduled",
        email: "marcus.johnson@example.com",
        phone: "(555) 012-3456",
        location: "Atlanta, GA",
        skills: ["AWS", "Azure", "Terraform", "Kubernetes", "DevOps"],
        score: 0,
        interviewDate: "Oct 29, 2023",
        avatar: "default-avatar.png",
        resume: "Marcus_Johnson_Resume.pdf"
    }
];

// Function to get candidate by ID
function getCandidateById(id) {
    return mockCandidates.find(candidate => candidate.id === id) || null;
}

// Function to load candidate data into the UI
function loadCandidateData(candidate) {
    if (!candidate) return;

    // Update candidate info
    document.getElementById('candidateName').textContent = candidate.name;
    document.getElementById('candidatePosition').textContent = candidate.position;
    document.getElementById('candidateEmail').textContent = candidate.email;
    document.getElementById('candidatePhone').textContent = candidate.phone;
    document.getElementById('candidateLocation').textContent = candidate.location;
    document.getElementById('candidateScore').textContent = `${candidate.score}% Match`;
    document.getElementById('interviewDate').textContent = candidate.interviewDate;

    // Update skills
    const skillsContainer = document.getElementById('candidateSkills');
    skillsContainer.innerHTML = candidate.skills.map(skill => 
        `<span class="badge bg-light text-dark me-1 mb-1">${skill}</span>`
    ).join('');

    // Update interview chat
    const chatContainer = document.getElementById('interviewChat');
    const messageTemplate = document.getElementById('messageTemplate');
    chatContainer.innerHTML = '';

    candidate.interview.forEach(message => {
        const messageElement = messageTemplate.content.cloneNode(true);
        const messageDiv = messageElement.querySelector('.message');
        
        messageDiv.classList.add(`message-${message.sender === 'AI Interviewer' ? 'ai' : 'candidate'}`);
        messageElement.querySelector('.message-sender').textContent = message.sender;
        messageElement.querySelector('.message-time').textContent = message.time;
        messageElement.querySelector('.message-content').innerHTML = message.content;
        
        if (message.analysis) {
            const analysisDiv = messageElement.querySelector('.message-analysis');
            analysisDiv.classList.add('show');
            messageElement.querySelector('.analysis-text').textContent = message.analysis.feedback;
            
            const keywords = message.analysis.keywords.map(kw => 
                `<span class="badge bg-info text-dark me-1 mb-1">${kw}</span>`
            ).join('');
            
            messageElement.querySelector('.analysis-details').innerHTML = `
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <div>
                        <strong>Score:</strong> ${message.analysis.score}/100
                    </div>
                    <div>
                        <strong>Keywords:</strong> ${keywords}
                    </div>
                </div>
            `;
        }
        
        chatContainer.appendChild(messageElement);
    });

    // Update skills assessment
    if (candidate.skillsAssessment) {
        Object.entries(candidate.skillsAssessment).forEach(([skill, score]) => {
            const skillElement = document.createElement('div');
            skillElement.className = 'skill-item mb-2';
            skillElement.innerHTML = `
                <div class="d-flex justify-content-between mb-1">
                    <span>${skill.split(/(?=[A-Z])/).join(' ')}</span>
                    <span>${score}%</span>
                </div>
                <div class="progress" style="height: 6px;">
                    <div class="progress-bar bg-info" style="width: ${score}%"></div>
                </div>
            `;
            document.querySelector('.skills-container')?.appendChild(skillElement);
        });
    }

    // Update key insights
    const insightsList = document.getElementById('keyInsightsList');
    if (insightsList && candidate.keyInsights) {
        insightsList.innerHTML = candidate.keyInsights.map(insight => 
            `<li class="mb-2">
                <i class="bi bi-check-circle-fill text-success me-2"></i>
                ${insight}
            </li>`
        ).join('');
    }
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    // Load the first candidate by default
    const firstCandidate = mockCandidates[0];
    if (firstCandidate) {
        loadCandidateData(firstCandidate);
    }

    // Handle candidate selection
    document.querySelectorAll('.candidate-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Update active state
            document.querySelectorAll('.candidate-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            
            // Load candidate data
            const candidateId = parseInt(item.getAttribute('data-candidate-id'));
            const candidate = getCandidateById(candidateId);
            loadCandidateData(candidate);
        });
    });

    // Toggle analysis visibility
    const showAnalysisCheckbox = document.getElementById('showAnalysis');
    if (showAnalysisCheckbox) {
        showAnalysisCheckbox.addEventListener('change', (e) => {
            const analysisSections = document.querySelectorAll('.message-analysis');
            analysisSections.forEach(section => {
                if (e.target.checked) {
                    section.classList.add('show');
                } else {
                    section.classList.remove('show');
                }
            });
        });
    }
});
