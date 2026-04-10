// ============================================
// GLOBAL JAVASCRIPT
// Consolidated from base.html
// ============================================

// ============================================
// THEME TOGGLE FUNCTIONALITY
// ============================================

// Theme toggle function for onclick handler
function toggleTheme() {
    const isDark = document.documentElement.classList.toggle("dark");
    if (isDark) {
        document.body.classList.add("dark");
    } else {
        document.body.classList.remove("dark");
    }
    const themeIcon = document.getElementById("theme-icon");
    if (themeIcon) themeIcon.textContent = isDark ? "🌞" : "🌙";
    localStorage.setItem("theme", isDark ? "dark" : "light");
}

// Persistent Dark Mode - with safety check
document.addEventListener('DOMContentLoaded', function () {
    const storedTheme = localStorage.getItem("theme");
    const themeToggle = document.getElementById("theme-toggle");
    const themeIcon = document.getElementById("theme-icon");

    if (
        storedTheme === "dark" ||
        (!storedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
        document.documentElement.classList.add("dark");
        document.body.classList.add("dark");
        if (themeIcon) themeIcon.textContent = "🌞";
    } else {
        document.documentElement.classList.remove("dark");
        document.body.classList.remove("dark");
        if (themeIcon) themeIcon.textContent = "🌙";
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            const isDark = document.documentElement.classList.toggle("dark");
            if (isDark) {
                document.body.classList.add("dark");
            } else {
                document.body.classList.remove("dark");
            }
            if (themeIcon) themeIcon.textContent = isDark ? "🌞" : "🌙";
            localStorage.setItem("theme", isDark ? "dark" : "light");
        });
    }
});

// ============================================
// TAILWIND CONFIG
// (Note: darkMode is already configured in header.html)
// ============================================

// Removed duplicate tailwind.config as it's already in header.html

// ============================================
// AUTO-HIDE MESSAGES
// ============================================

// Auto-hide messages after 20 seconds
document.addEventListener('DOMContentLoaded', function () {
    const messages = document.querySelectorAll('.message-toast');
    messages.forEach(function (msg) {
        setTimeout(function () {
            msg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-20px)';
            setTimeout(function () {
                if (msg.parentElement) {
                    msg.remove();
                }
            }, 500);
        }, 20000);
    });
});

// ============================================
// GLOBAL DARK MODE AUTO-APPLY
// Note: This is for pages that don't use native Tailwind dark mode classes
// Most pages now use native dark mode (dark:bg-gray-800, etc.)
// ============================================

// Disabled - using native Tailwind dark mode instead
/*
(function () {
    // Function to apply dark mode classes
    function applyGlobalDarkModeFix() {
        // Wait for DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function () {
                setTimeout(applyGlobalDarkModeFix, 50);
            });
            return;
        }

        var isDark = document.documentElement.classList.contains('dark');

        // Fix all bg-white elements (cards, containers)
        document.querySelectorAll('.bg-white').forEach(function (el) {
            if (isDark) {
                el.classList.add('dark-bg-card');
            } else {
                el.classList.remove('dark-bg-card');
            }
        });

        // Fix all gray text elements
        document.querySelectorAll('[class*="text-gray-"]').forEach(function (el) {
            if (isDark) {
                el.classList.add('dark-text-fix');
            } else {
                el.classList.remove('dark-text-fix');
            }
        });

        // Fix form inputs
        document.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(function (el) {
            if (isDark) {
                el.classList.add('dark-input-fix');
            } else {
                el.classList.remove('dark-input-fix');
            }
        });
    }

    // Run on page load with small delay
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            setTimeout(applyGlobalDarkModeFix, 50);
        });
    } else {
        setTimeout(applyGlobalDarkModeFix, 50);
    }

    // Run when theme toggles (instant - no delay)
    var themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            // Apply immediately when clicking toggle
            applyGlobalDarkModeFix();
        });
    }

    // Expose function globally for external calls
    window.applyDarkModeFix = applyGlobalDarkModeFix;
})();
*/

// ============================================
// LOGOUT MODAL FUNCTIONS
// ============================================

let logoutFormId = '';

function confirmLogout(formId) {
    logoutFormId = formId;
    document.getElementById('logout-modal').classList.remove('hidden');
}

function closeLogoutModal() {
    document.getElementById('logout-modal').classList.add('hidden');
    logoutFormId = '';
}

function submitLogout() {
    if (logoutFormId) {
        document.getElementById(logoutFormId).submit();
    }
}

// Close modal on outside click
document.addEventListener('DOMContentLoaded', function () {
    const logoutModal = document.getElementById('logout-modal');
    if (logoutModal) {
        logoutModal.addEventListener('click', function (e) {
            if (e.target === this) {
                closeLogoutModal();
            }
        });
    }
});

// Close modal on Escape key
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        closeLogoutModal();
    }
});
