// DOM Boot-up progress bar sequence
window.addEventListener('DOMContentLoaded', () => {
    const loader = document.getElementById('loading-screen');
    
    // Check sessionStorage to see if the system has already run the boot decryption sequence
    if (sessionStorage.getItem('vault_loaded')) {
        // Immediately hide loading overlay on sub-loads to prevent flashes of background styles
        loader.classList.add('d-none');
        return;
    }

    // Run the decryption loading animation on initial page boot
    loader.classList.remove('d-none');
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
            // Save state to sessionStorage for the active browser tab session
            sessionStorage.setItem('vault_loaded', 'true');
            loader.classList.add('fade-out');
            setTimeout(() => {
                loader.classList.add('d-none');
            }, 800);
        }
    }
    setTimeout(runLoader, 400); 
});

// Controls modal displaying completely using Bootstrap class transitions
function triggerDecrypt(filename) {
    const deniedOverlay = document.getElementById('deniedOverlay');
    const successOverlay = document.getElementById('successOverlay');

    if (activeRole !== "Admin") {
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