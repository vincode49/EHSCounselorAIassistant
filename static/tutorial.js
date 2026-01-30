// Tutorial functionality
let currentStep = 1;
const totalSteps = 4;
let step2Completed = false;
let step3Completed = false;

// Initialize tutorial
document.addEventListener('DOMContentLoaded', () => {
    // Get tutorial completion status from data attribute
    let tutorialCompleted = 0;
    const tutorialDataEl = document.getElementById('tutorial-data');
    if (tutorialDataEl) {
        try {
            const data = JSON.parse(tutorialDataEl.textContent);
            tutorialCompleted = data.completed || 0;
        } catch (e) {
            console.error('Error parsing tutorial data:', e);
        }
    }
    
    // Check if tutorial should be shown
    if (tutorialCompleted === 0) {
        setTimeout(() => {
            tutorialStart();
        }, 500); // Small delay to let page load
    } else {
        // Show replay button if tutorial is completed
        document.getElementById('replayTutorialBtn').style.display = 'block';
    }
    
    initializeTutorialProgress();
});

function initializeTutorialProgress() {
    const progressContainer = document.getElementById('tutorialProgress');
    progressContainer.innerHTML = '';
    for (let i = 1; i <= totalSteps; i++) {
        const dot = document.createElement('div');
        dot.className = 'tutorial-progress-dot';
        if (i === 1) dot.classList.add('active');
        progressContainer.appendChild(dot);
    }
}

function tutorialStart() {
    currentStep = 1;
    step2Completed = false;
    step3Completed = false;
    document.getElementById('tutorialOverlay').classList.add('active');
    showStep(1);
    updateProgressDots(1);
}

function showStep(step) {
    // Hide all steps
    for (let i = 1; i <= totalSteps; i++) {
        document.getElementById(`step${i}`).classList.remove('active');
    }
    // Show current step
    document.getElementById(`step${step}`).classList.add('active');
    currentStep = step;
}

function updateProgressDots(step) {
    const dots = document.querySelectorAll('.tutorial-progress-dot');
    dots.forEach((dot, index) => {
        if (index < step) {
            dot.classList.add('active');
        } else {
            dot.classList.remove('active');
        }
    });
}

function tutorialNext() {
    if (currentStep < totalSteps) {
        // Check if step requirements are met
        if (currentStep === 2 && !step2Completed) {
            alert('Please ask a question first by clicking on one of the example questions!');
            return;
        }
        if (currentStep === 3 && !step3Completed) {
            alert('Please complete your profile and click "Save Changes" to continue.');
            return;
        }
        
        showStep(currentStep + 1);
        updateProgressDots(currentStep);
    }
}

function tutorialPrevious() {
    if (currentStep > 1) {
        showStep(currentStep - 1);
        updateProgressDots(currentStep);
    }
}

function tutorialSkip() {
    if (confirm('Are you sure you want to skip the tutorial? You can replay it anytime using the button in the bottom right.')) {
        tutorialComplete(true);
    }
}

async function tutorialComplete(skipped = false) {
    // Mark tutorial as completed on server
    try {
        const response = await fetch('/complete_tutorial', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            document.getElementById('tutorialOverlay').classList.remove('active');
            document.getElementById('replayTutorialBtn').style.display = 'block';
            
            if (!skipped) {
                // Show a brief welcome message
                setTimeout(() => {
                    alert('Tutorial completed! Welcome to Emerald High School Counselor Assistant. You\'re all set to start asking questions!');
                }, 300);
            }
        }
    } catch (error) {
        console.error('Error completing tutorial:', error);
        // Still close the tutorial even if API call fails
        document.getElementById('tutorialOverlay').classList.remove('active');
        document.getElementById('replayTutorialBtn').style.display = 'block';
    }
}

function isTutorialActive() {
    const overlay = document.getElementById('tutorialOverlay');
    return overlay && overlay.classList.contains('active');
}

function tutorialProfileStepRequired() {
    return isTutorialActive() && currentStep === 3;
}

function tutorialProfileStepCompleted(formData) {
    if (!tutorialProfileStepRequired()) {
        return false;
    }

    const displayName = (formData.display_name || '').trim();
    const bio = (formData.bio || '').trim();
    const grade = formData.current_grade;

    if (!displayName || !bio || !grade) {
        return false;
    }

    step3Completed = true;
    const taskComplete = document.getElementById('taskComplete3');
    const step3Next = document.getElementById('step3Next');
    if (taskComplete) taskComplete.classList.add('show');
    if (step3Next) step3Next.disabled = false;
    return true;
}

function tutorialTryQuestion(question) {
    // Fill the input field with the question
    const userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.value = question;
        userInput.focus();
        
        // Mark step 2 as completed immediately when question is filled
        step2Completed = true;
        document.getElementById('taskComplete2').classList.add('show');
        document.getElementById('step2Next').disabled = false;
        
        // Note: User can click send button themselves or we auto-send
        // Auto-send after a brief delay if user doesn't send
        setTimeout(() => {
            if (userInput.value === question) {
                const sendButton = document.getElementById('sendButton');
                if (sendButton && !step2Completed) {
                    sendButton.click();
                }
            }
        }, 1000);
    }
}

// Export functions for use in HTML onclick handlers
window.tutorialStart = tutorialStart;
window.tutorialNext = tutorialNext;
window.tutorialPrevious = tutorialPrevious;
window.tutorialSkip = tutorialSkip;
window.tutorialComplete = tutorialComplete;
window.tutorialTryQuestion = tutorialTryQuestion;
window.tutorialProfileStepRequired = tutorialProfileStepRequired;
window.tutorialProfileStepCompleted = tutorialProfileStepCompleted;

