document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const resultsContainer = document.getElementById('results-container');
    const resultsTable = document.getElementById('results-table');
    const resultsBody = document.getElementById('results-body');
    const statusMessage = document.getElementById('status-message');
    
    // --- Core Functions ---

    function copyToClipboard(text) {
        if (!text || text === 'null' || text === 'undefined') return;
        
        const tempInput = document.createElement('input');
        tempInput.value = text.trim();
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);

        showToast('Copied to clipboard!');
    }
    
    // Expose to window for inline HTML onclicks
    window.copyToClipboard = copyToClipboard;

    function showToast(message) {
        // Simple toast implementation
        let toast = document.createElement('div');
        toast.className = 'position-fixed bottom-0 end-0 p-3';
        toast.style.zIndex = '11';
        toast.innerHTML = `
            <div class="toast show align-items-center text-white bg-success border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fa-solid fa-check-circle me-2"></i> ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        document.body.appendChild(toast);
        setTimeout(() => { toast.remove(); }, 3000);
    }

    function performSearch() {
        const query = searchInput.value.trim();

        if (!query) {
            alert("Please enter a search term.");
            return;
        }

        // 1. Feedback: Show the results container (previously hidden)
        resultsContainer.style.display = 'block';
        
        // 2. Feedback: Show loading state
        statusMessage.innerHTML = `
            <div class="spinner-border text-primary mb-3" role="status"></div>
            <p class="lead text-muted">Searching database for "<strong>${query}</strong>"...</p>
        `;
        statusMessage.style.display = 'block';
        resultsTable.style.display = 'none';

        // 3. Fetch Data
        fetch(`/api/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                resultsBody.innerHTML = ''; 

                if (data.length === 0) {
                    statusMessage.innerHTML = `<div class="text-danger"><i class="fa-regular fa-face-frown fa-2x mb-2"></i><p>No carriers found matching "${query}".</p></div>`;
                } else {
                    statusMessage.style.display = 'none';
                    resultsTable.style.display = 'table';

                    data.forEach(carrier => {
                        const row = document.createElement('tr');
                        
                        const name = carrier.legal_name || 'N/A';
                        const state = carrier.state_domicile ? `<span class="badge bg-light text-dark border ms-2">${carrier.state_domicile}</span>` : '';
                        const naic = carrier.naic_code || 'N/A';
                        const payer = carrier.payer_id || 'N/A';
                        const lob = carrier.line_of_business || '<span class="text-muted">-</span>';
                        const claimsPhone = carrier.phone_claims || 'N/A';

                        // Action Button (View Details)
                        const detailsBtn = naic !== 'N/A' ? 
                            `<a href="/carrier/${naic}" class="btn btn-sm btn-primary rounded-pill px-3">Details <i class="fa-solid fa-arrow-right ms-1"></i></a>` : 
                            '<span class="text-muted">-</span>';

                        // Helper for copyable cells
                        const createCopyCell = (val) => {
                            if(val === 'N/A') return `<span class="text-muted">N/A</span>`;
                            return `
                                <div class="d-flex align-items-center">
                                    <span class="me-2">${val}</span>
                                    <button class="copy-btn" onclick="window.copyToClipboard('${val}')"><i class="fa-regular fa-copy"></i></button>
                                </div>
                            `;
                        };

                        row.innerHTML = `
                            <td class="ps-4 fw-bold text-primary">${name} ${state}</td>
                            <td>${createCopyCell(naic)}</td>
                            <td>${createCopyCell(payer)}</td>
                            <td>${lob}</td>
                            <td>${claimsPhone}</td>
                            <td class="pe-4">${detailsBtn}</td>
                        `;
                        resultsBody.appendChild(row);
                    });
                    
                    // Scroll to results
                    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                statusMessage.innerHTML = `<div class="text-danger">Search failed. Please try again.</div>`;
            });
    }

    // --- Event Listeners ---
    if(searchButton) {
        searchButton.addEventListener('click', performSearch);
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') performSearch();
        });
    }
});