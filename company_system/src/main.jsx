import React from 'react';
import { createRoot } from 'react-dom/client';
import RemedialActionFlowchart from './remedial-flowchart.jsx';

// Store the root so we can unmount later
let flowchartRoot = null;

// Function to mount the React Flow component (called when modal opens)
function mountFlowchart() {
    const container = document.getElementById('remedial-flowchart-root');

    if (container && !flowchartRoot) {
        // Clear any existing content
        container.innerHTML = '';

        // Create React root and render
        flowchartRoot = createRoot(container);
        flowchartRoot.render(React.createElement(RemedialActionFlowchart));

        console.log('Remedial Action Flowchart mounted successfully');
    } else if (container && flowchartRoot) {
        // Re-render if already mounted
        flowchartRoot.render(React.createElement(RemedialActionFlowchart));
    }
}

// Function to unmount (called when modal closes)
function unmountFlowchart() {
    if (flowchartRoot) {
        const container = document.getElementById('remedial-flowchart-root');
        if (container) {
            flowchartRoot.render(null);
        }
    }
}

// Auto-mount when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(mountFlowchart, 100);
    });
} else {
    setTimeout(mountFlowchart, 100);
}

// Also try to mount when the modal opens
document.addEventListener('click', (e) => {
    if (e.target && e.target.textContent.includes('View Flowchart')) {
        setTimeout(mountFlowchart, 50);
    }
});

// Expose functions globally for manual control
window.RemedialFlowchart = {
    mount: mountFlowchart,
    unmount: unmountFlowchart
};