// DOM Boot-up progress bar sequence
window.addEventListener('DOMContentLoaded', () => {
    const loader = document.getElementById('loading-screen');
    if (!loader) return;

    // Run the G-DES boot animation sequence on every page load
    const progressBar = document.getElementById('loader-bar-fill');
    const progressPct = document.getElementById('loader-pct');
    const statusTxt = document.getElementById('loader-status');
    
    const steps = [
        { pct: 25, text: "INITIATING_GDES_DECRYPT_PIPELINE..." },
        { pct: 55, text: "DECOMPOSING_CIPHER_SBOX_BLOCKS..." },
        { pct: 80, text: "ENFORCING_RBAC_POLICY_CONSTRAINTS..." },
        { pct: 100, text: "SECURE_VAULT_NODE_RECONCILIATION_COMPLETE" }
    ];
    
    let currentStep = 0;
    function runLoader() {
        if (currentStep < steps.length) {
            const step = steps[currentStep];
            progressBar.style.width = step.pct + "%";
            progressPct.innerText = step.pct + "%";
            statusTxt.innerText = step.text;
            currentStep++;
            setTimeout(runLoader, 550);
        } else {
            // Fade out the overlay cleanly
            loader.classList.add('fade-out');
            setTimeout(() => {
                loader.classList.add('d-none');
            }, 800);
        }
    }
    setTimeout(runLoader, 400); 
});

// Controls decryption modal displaying completely using Bootstrap class transitions
function triggerDecrypt(filename, isAllowed) {
    const deniedOverlay = document.getElementById('deniedOverlay');
    const successOverlay = document.getElementById('successOverlay');

    if (!isAllowed) {
        deniedOverlay.classList.remove('d-none');
        deniedOverlay.classList.add('d-flex');
    } else {
        successOverlay.classList.remove('d-none');
        successOverlay.classList.add('d-flex');
        document.getElementById('successConfirmBtn').onclick = () => {
            closeSuccessOverlay();
            window.location.href = `/decrypt/${encodeURIComponent(filename)}`;
        };
    }
}

// Fetches the raw ciphertext hex and plaintext from the backend to display on the dashboard
function triggerInspect(filename) {
    fetch(`/inspect/${encodeURIComponent(filename)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            
            document.getElementById('inspect-title').innerText = `G-DES // INSPECT: ${data.original_name}`;
            document.getElementById('inspect-ciphertext').innerText = data.ciphertext_hex;
            
            const plainPanel = document.getElementById('inspect-plaintext');
            plainPanel.innerText = data.plaintext;
            
            // Adjust panel style based on dynamic authorization clearances
            if (data.authorized) {
                plainPanel.className = "code-panel plaintext-view font-monospace";
            } else {
                plainPanel.className = "code-panel plaintext-denied font-monospace";
            }
            
            const inspectOverlay = document.getElementById('inspectOverlay');
            inspectOverlay.classList.remove('d-none');
            inspectOverlay.classList.add('d-flex');
        })
        .catch(err => {
            console.error("Cryptographic inspector failure:", err);
        });
}

function closeDeniedOverlay() { 
    const deniedOverlay = document.getElementById('deniedOverlay');
    deniedOverlay.classList.add('d-none');
    deniedOverlay.classList.remove('d-flex');
}

function closeSuccessOverlay() { 
    const successOverlay = document.getElementById('successOverlay');
    successOverlay.classList.add('d-none');
    successOverlay.classList.remove('d-flex');
}

function closeInspectOverlay() {
    const inspectOverlay = document.getElementById('inspectOverlay');
    inspectOverlay.classList.add('d-none');
    inspectOverlay.classList.remove('d-flex');
}

// Event Delegation: Clean method to capture click events from templates without syntax parsing warnings
document.addEventListener('click', (event) => {
    // Check Decrypt trigger
    const decryptTrigger = event.target.closest('.decrypt-trigger');
    if (decryptTrigger) {
        const filename = decryptTrigger.getAttribute('data-filename');
        const isAllowed = decryptTrigger.getAttribute('data-allowed') === 'true';
        triggerDecrypt(filename, isAllowed);
        return;
    }
    
    // Check Inspect trigger
    const inspectTrigger = event.target.closest('.inspect-trigger');
    if (inspectTrigger) {
        const filename = inspectTrigger.getAttribute('data-filename');
        triggerInspect(filename);
    }
});