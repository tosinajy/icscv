document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const resultsTable = document.getElementById('results-table');
    const resultsBody = document.getElementById('results-body');
    const statusMessage = document.getElementById('status-message');
    const adNative = document.getElementById('ad-results-native');

    // --- Core Functions ---

    // Utility function to copy text to clipboard
    function copyToClipboard(text) {
        // Use document.execCommand for better compatibility within iframes
        const tempInput = document.createElement('input');
        tempInput.value = text;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);

        // Simple notification (since alert is forbidden, we use a basic DOM element)
        showNotification('Copied: ' + text);
    }

    // Function to show transient notification (in lieu of alert)
    function showNotification(message) {
        let notif = document.getElementById('copy-notification');
        if (!notif) {
            notif = document.createElement('div');
            notif.id = 'copy-notification';
            notif.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #28a745; color: white; padding: 10px 20px; border-radius: 5px; z-index: 10000; opacity: 0; transition: opacity 0.5s;';
            document.body.appendChild(notif);
        }
        notif.textContent = message;
        notif.style.opacity = 1;
        setTimeout(() => {
            notif.style.opacity = 0;
        }, 2000);
    }
    
    // Make copyToClipboard globally accessible for dynamically added buttons
    window.copyToClipboard = copyToClipboard;

    // Function to perform search
    function performSearch() {
        const query = searchInput.value.trim();

        if (!query) {
            statusMessage.textContent = "Please enter a valid search term to begin verification.";
            statusMessage.style.display = 'block';
            resultsTable.style.display = 'none';
            adNative.style.display = 'none';
            return;
        }

        statusMessage.textContent = "Searching...";
        
        fetch(`/api/search?q=${encodeURIComponent(query)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                resultsBody.innerHTML = ''; // Clear previous results

                if (data.length === 0) {
                    statusMessage.textContent = "No carriers found matching that criteria.";
                    statusMessage.style.display = 'block';
                    resultsTable.style.display = 'none';
                    adNative.style.display = 'block';
                } else {
                    statusMessage.style.display = 'none';
                    adNative.style.display = 'block';
                    resultsTable.style.display = 'table';

                    // Populate Table with new data and copy buttons
                    data.forEach(carrier => {
                        const row = document.createElement('tr');
                        
                        const name = carrier.legal_name || 'N/A';
                        const state = carrier.state_domicile ? ` (${carrier.state_domicile})` : '';
                        const naic = carrier.naic_code || 'N/A';
                        const payer = carrier.payer_id || 'N/A';
                        const lob = carrier.line_of_business || '-';
                        const claimsPhone = carrier.phone_claims || 'N/A';
                        
                        // Function to create an element with copy button
                        const createCopyCell = (value) => {
                            if (value === 'N/A' || value === null) return value;
                            return `
                                <span>${value}</span>
                                <button class="copy-btn" onclick="window.copyToClipboard('${value}')" title="Copy ${value}">
                                    <i class="fa-regular fa-clipboard"></i>
                                </button>
                            `;
                        };

                        const detailsLink = naic !== 'N/A' ? 
                            `<a href="/carrier/${naic}" class="btn btn-sm btn-outline-primary" title="View all addresses and phones">View Details</a>` : 
                            '-';

                        row.innerHTML = `
                            <td><strong>${name}</strong>${state}</td>
                            <td>${createCopyCell(naic)}</td>
                            <td>${createCopyCell(payer)}</td>
                            <td>${lob}</td>
                            <td>${claimsPhone}</td>
                            <td>${detailsLink}</td>
                        `;
                        resultsBody.appendChild(row);
                    });
                }
            })
            .catch(error => {
                console.error('Fetch Error:', error);
                statusMessage.textContent = "Search failed. Please check the server connection and try again.";
                statusMessage.style.display = 'block';
                resultsTable.style.display = 'none';
            });
    }

    // --- Event Listeners ---
    searchButton.addEventListener('click', performSearch);

    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
});