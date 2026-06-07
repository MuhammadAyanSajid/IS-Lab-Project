// DOM Boot-up progress bar sequence
window.addEventListener('DOMContentLoaded', () => {
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
            document.getElementById('loading-screen').classList.add('fade-out');
        }
    }
    setTimeout(runLoader, 400); 
});

// Dynamic Preview Role Toggle (Class-based transitions)
function setRole(role) {
    const badge = document.getElementById('role-badge');
    const uploaderSection = document.getElementById('uploader-section');
    const repositorySection = document.getElementById('repository-section');

    if (role === "Admin") {
        badge.className = "badge bg-transparent border px-3 py-2 badge-admin";
        badge.innerHTML = '<i class="bi bi-shield-fill"></i> ADMIN_PRIVILEGES';
        uploaderSection.classList.remove('d-none');
        repositorySection.className = "col-lg-8";
    } else {
        badge.className = "badge bg-transparent border px-3 py-2 badge-employee";
        badge.innerHTML = '<i class="bi bi-person-badge-fill"></i> EMPLOYEE_PROFILE';
        uploaderSection.classList.add('d-none');
        repositorySection.className = "col-lg-12";
    }
}

// Controls modal displaying completely using Bootstrap class transitions
function triggerDecrypt(filename) {
    const deniedOverlay = document.getElementById('deniedOverlay');
    const successOverlay = document.getElementById('successOverlay');

    // activeRole is defined in the HTML file using Jinja2 injection
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