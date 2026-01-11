// Microgrid SCADA UI script
// This script provides a simple client-side interface for interacting with
// the microgrid cloud API.  It allows you to list registered edges,
// view and edit site configurations and generate enrollment tokens.

async function apiRequest(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    if (!res.ok) {
        const err = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${err}`);
    }
    return await res.json();
}

function clearMain() {
    const main = document.getElementById('main');
    main.innerHTML = '';
    return main;
}

// Load the list of registered edges
async function loadEdges() {
    const main = clearMain();
    const h2 = document.createElement('h2');
    h2.textContent = 'Registered Edges';
    main.appendChild(h2);
    const list = document.createElement('ul');
    main.appendChild(list);
    try {
        const data = await apiRequest('GET', '/api/edges');
        if (data.edges && data.edges.length > 0) {
            data.edges.forEach(edge => {
                const li = document.createElement('li');
                li.textContent = `${edge.edge_id} (site: ${edge.site_id})`;
                list.appendChild(li);
            });
        } else {
            list.textContent = 'No edges registered.';
        }
    } catch (err) {
        const p = document.createElement('p');
        p.textContent = `Error loading edges: ${err.message}`;
        main.appendChild(p);
    }
}

// Form to edit a site's desired configuration
function loadConfig() {
    const main = clearMain();
    const h2 = document.createElement('h2');
    h2.textContent = 'Site Configuration';
    main.appendChild(h2);
    // Site ID input
    const siteLabel = document.createElement('label');
    siteLabel.textContent = 'Site ID: ';
    const siteInput = document.createElement('input');
    siteInput.type = 'text';
    siteInput.id = 'cfg-site-id';
    siteLabel.appendChild(siteInput);
    main.appendChild(siteLabel);
    main.appendChild(document.createElement('br'));
    // Text area for JSON config
    const textarea = document.createElement('textarea');
    textarea.id = 'cfg-json';
    textarea.rows = 15;
    textarea.cols = 80;
    textarea.placeholder = '{\n  "pcc_max_export_kw": 0\n}';
    main.appendChild(textarea);
    main.appendChild(document.createElement('br'));
    // Buttons: load, save, generate token
    const loadBtn = document.createElement('button');
    loadBtn.textContent = 'Load Config';
    loadBtn.onclick = async () => {
        const siteId = siteInput.value.trim();
        if (!siteId) return alert('Enter site ID');
        try {
            const config = await apiRequest('GET', `/api/sites/${siteId}/desired-config`);
            textarea.value = JSON.stringify(config, null, 2);
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };
    const saveBtn = document.createElement('button');
    saveBtn.textContent = 'Save Config';
    saveBtn.onclick = async () => {
        const siteId = siteInput.value.trim();
        if (!siteId) return alert('Enter site ID');
        let json;
        try {
            json = JSON.parse(textarea.value);
        } catch (e) {
            return alert('Invalid JSON');
        }
        try {
            await apiRequest('POST', `/api/sites/${siteId}/desired-config`, json);
            alert('Saved successfully');
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };
    const tokenBtn = document.createElement('button');
    tokenBtn.textContent = 'Generate Enrollment Token';
    tokenBtn.onclick = async () => {
        const siteId = siteInput.value.trim();
        if (!siteId) return alert('Enter site ID');
        try {
            const data = await apiRequest('POST', `/api/sites/${siteId}/enrollment-token`);
            prompt('Enrollment Token:', data.token);
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };
    // Button container
    const btnContainer = document.createElement('div');
    btnContainer.appendChild(loadBtn);
    btnContainer.appendChild(saveBtn);
    btnContainer.appendChild(tokenBtn);
    main.appendChild(btnContainer);
}

// Placeholder for sites view (if you want to display site list)
function loadSites() {
    const main = clearMain();
    const h2 = document.createElement('h2');
    h2.textContent = 'Sites';
    main.appendChild(h2);
    const p = document.createElement('p');
    p.textContent = 'To edit a site, go to Configuration and enter its Site ID.';
    main.appendChild(p);
}

// Navigation
function setupNav() {
    document.getElementById('nav-edges').addEventListener('click', (e) => {
        e.preventDefault();
        loadEdges();
    });
    document.getElementById('nav-config').addEventListener('click', (e) => {
        e.preventDefault();
        loadConfig();
    });
    document.getElementById('nav-sites').addEventListener('click', (e) => {
        e.preventDefault();
        loadSites();
    });
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    setupNav();
    loadSites();
});
