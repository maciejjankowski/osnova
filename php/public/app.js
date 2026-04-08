// Initialize Lucide icons
lucide.createIcons();

// Show app
function showApp() {
    document.getElementById('landing').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    lucide.createIcons();
}

// Ring selector
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.ring-badge').forEach(badge => {
        badge.addEventListener('click', () => {
            document.querySelectorAll('.ring-badge').forEach(b => b.classList.remove('active'));
            badge.classList.add('active');
        });
    });
});
