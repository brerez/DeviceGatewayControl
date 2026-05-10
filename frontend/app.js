document.addEventListener('DOMContentLoaded', () => {
    const devicesBody = document.getElementById('devices-body');
    const totalDevicesSpan = document.getElementById('total-devices');
    const routedDevicesSpan = document.getElementById('routed-devices');
    const refreshBtn = document.getElementById('refresh-btn');

    async function fetchDevices() {
        devicesBody.innerHTML = '<tr><td colspan="5" class="loading">Loading devices...</td></tr>';
        
        try {
            const response = await fetch('/api/devices');
            const devices = await response.json();
            renderDevices(devices);
        } catch (error) {
            console.error('Error fetching devices:', error);
            devicesBody.innerHTML = '<tr><td colspan="5" class="loading" style="color: #f87171;">Error loading devices. Is the backend running?</td></tr>';
        }
    }

    function renderDevices(devices) {
        devicesBody.innerHTML = '';
        
        let routedCount = 0;
        
        devices.forEach(device => {
            if (device.routed) routedCount++;
            
            const tr = document.createElement('tr');
            
            tr.innerHTML = `
                <td>
                    <div class="device-name">${device.name || 'Unknown Device'}</div>
                </td>
                <td>${device.ip}</td>
                <td><code>${device.mac}</code></td>
                <td>
                    <span class="badge ${device.routed ? 'routed' : 'direct'}">
                        ${device.routed ? 'Israel' : 'Direct'}
                    </span>
                </td>
                <td>
                    <div class="actions">
                        <label class="switch">
                            <input type="checkbox" ${device.routed ? 'checked' : ''} data-mac="${device.mac}" class="toggle-route">
                            <span class="slider"></span>
                        </label>
                        ${!device.static ? `
                            <button class="btn secondary make-static" data-mac="${device.mac}">Make Static</button>
                        ` : `
                            <button class="btn success" disabled style="opacity: 0.5; cursor: default;">Static</button>
                        `}
                    </div>
                </td>
            `;
            
            devicesBody.appendChild(tr);
        });

        // Update stats
        totalDevicesSpan.textContent = devices.length;
        routedDevicesSpan.textContent = routedCount;

        // Add event listeners to toggles
        document.querySelectorAll('.toggle-route').forEach(checkbox => {
            checkbox.addEventListener('change', async (e) => {
                const mac = e.target.getAttribute('data-mac');
                const enable = e.target.checked;
                
                try {
                    const response = await fetch(`/api/devices/${mac}/toggle`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ enable })
                    });
                    
                    if (response.ok) {
                        fetchDevices(); // Refresh list to update status and badges
                    } else {
                        alert('Failed to update routing');
                        e.target.checked = !enable; // Revert
                    }
                } catch (error) {
                    console.error('Error toggling route:', error);
                    alert('Error toggling route');
                    e.target.checked = !enable; // Revert
                }
            });
        });

        // Add event listeners to "Make Static" buttons
        document.querySelectorAll('.make-static').forEach(button => {
            button.addEventListener('click', async (e) => {
                const mac = e.target.getAttribute('data-mac');
                
                try {
                    const response = await fetch(`/api/devices/${mac}/static`, {
                        method: 'POST'
                    });
                    
                    if (response.ok) {
                        fetchDevices(); // Refresh list
                    } else {
                        alert('Failed to make static');
                    }
                } catch (error) {
                    console.error('Error making static:', error);
                    alert('Error making static');
                }
            });
        });
    }

    refreshBtn.addEventListener('click', fetchDevices);

    // Initial fetch
    fetchDevices();
});
