document.addEventListener('DOMContentLoaded', function() {
    // Handle webcal links
    document.querySelectorAll('a[data-protocol="webcal"]').forEach(link => {
        link.href = link.href.replace(/^https?:\/\//, 'webcal://');
    });
});
