document.addEventListener('DOMContentLoaded', function() {
    // Handle webcal protocol links
    document.querySelectorAll('a[data-protocol="webcal"]').forEach(link => {
        // Always convert to webcal:// regardless of original protocol
        const url = new URL(link.href);
        link.href = 'webcal://' + url.host + url.pathname + url.search + url.hash;
    });
});
