document.addEventListener('DOMContentLoaded', () => {
    // Render detailed slots map if present (User Dashboard)
    const slotsContainer = document.getElementById('slots-container');
    if (slotsContainer) {
        fetchSlotsGrid();
        setInterval(fetchSlotsGrid, 5000);
    }

    // Render available count if present (Index Landing Page)
    const availableCount = document.getElementById('available-count');
    if (availableCount) {
        fetchAvailableCount();
        setInterval(fetchAvailableCount, 5000);
    }
});

async function fetchSlotsGrid() {
    try {
        const response = await fetch('/api/slots');
        const slots = await response.json();
        const container = document.getElementById('slots-container');
        container.innerHTML = '';

        slots.forEach(slot => {
            const card = document.createElement('div');
            card.className = 'slot-card';

            const statusClass = slot.is_occupied ? 'occupied' : 'available';
            const statusText = slot.is_occupied ? 'Occupied' : 'Open';

            card.innerHTML = `
                <h3>${slot.name}</h3>
                <span class="badge ${statusClass}">${statusText}</span>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error fetching slots:', error);
    }
}

async function fetchAvailableCount() {
    try {
        const response = await fetch('/api/slots');
        const slots = await response.json();
        const count = slots.filter(s => !s.is_occupied).length;
        document.getElementById('available-count').innerText = count;
    } catch (error) {
        console.error('Error fetching count:', error);
    }
}
