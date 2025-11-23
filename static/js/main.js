// ===== Mobile Menu Toggle =====
const hamburger = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobileMenu');

if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = mobileMenu.style.display === 'block';
        mobileMenu.style.display = isOpen ? 'none' : 'block';
        hamburger.classList.toggle('active');
    });

    // Close mobile menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
            mobileMenu.style.display = 'none';
            hamburger.classList.remove('active');
        }
    });
    
    // Close mobile menu when clicking on a link
    mobileMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            mobileMenu.style.display = 'none';
            hamburger.classList.remove('active');
        });
    });
}
// ===== Custom Code Toggle =====
const customCodeToggle = document.getElementById('customCodeToggle');
const customCodeInput = document.getElementById('customCodeInput');

if (customCodeToggle && customCodeInput) {
    customCodeToggle.addEventListener('change', (e) => {
        customCodeInput.style.display = e.target.checked ? 'block' : 'none';
    });
}

// ===== URL Shortener =====
const shortenBtn = document.getElementById('shortenBtn');
const urlInput = document.getElementById('urlInput');
const customCode = document.getElementById('customCode');
const resultBox = document.getElementById('resultBox');
const resultUrl = document.getElementById('resultUrl');
const originalUrlLink = document.getElementById('originalUrlLink');
const copyBtn = document.getElementById('copyBtn');

if (shortenBtn) {
    shortenBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        
        if (!url) {
            showToast('Please enter a URL', 'error');
            return;
        }
        
        shortenBtn.disabled = true;
        shortenBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Shortening...</span>';
        
        try {
            const response = await fetch('/shorten', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    custom_code: customCodeToggle.checked ? customCode.value.trim() : '',
                    turnstile_token: turnstileToken
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                resultUrl.value = data.short_url;
                originalUrlLink.href = data.original_url;
                originalUrlLink.textContent = data.original_url;
                resultBox.style.display = 'block';
                showToast('URL shortened successfully!', 'success');
                
                resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                showToast(data.error || 'Failed to shorten URL', 'error');
            }
        } catch (error) {
            showToast('An error occurred. Please try again.', 'error');
            console.error('Error:', error);
        } finally {
            shortenBtn.disabled = false;
            shortenBtn.innerHTML = '<span>Shorten URL</span><i class="fas fa-arrow-right"></i>';
        }
    });
}

// ===== Copy to Clipboard =====
if (copyBtn) {
    copyBtn.addEventListener('click', () => {
        resultUrl.select();
        resultUrl.setSelectionRange(0, 99999); // For mobile devices
        
        try {
            document.execCommand('copy');
            copyBtn.innerHTML = '<i class="fas fa-check"></i><span>Copied!</span>';
            showToast('URL copied to clipboard!', 'success');
            
            setTimeout(() => {
                copyBtn.innerHTML = '<i class="fas fa-copy"></i><span>Copy</span>';
            }, 2000);
        } catch (err) {
            showToast('Failed to copy. Please copy manually.', 'error');
        }
    });
}

// ===== Toast Notification =====
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    if (toast && toastMessage) {
        toastMessage.textContent = message;
        toast.className = `toast ${type}`;
        
        const icon = toast.querySelector('i');
        if (type === 'error') {
            icon.className = 'fas fa-exclamation-circle';
        } else if (type === 'warning') {
            icon.className = 'fas fa-exclamation-triangle';
        } else {
            icon.className = 'fas fa-check-circle';
        }
        
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

// ===== Navbar Scroll Effect =====
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// ===== Animated Counter for Stats =====
const observerOptions = {
    threshold: 0.5,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const counters = entry.target.querySelectorAll('.stat-number');
            counters.forEach(counter => {
                animateCounter(counter);
            });
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

const statsSection = document.querySelector('.stats');
if (statsSection) {
    observer.observe(statsSection);
}

function animateCounter(counter) {
    const target = parseFloat(counter.getAttribute('data-target'));
    const duration = 2000;
    const step = target / (duration / 16);
    let current = 0;
    
    const updateCounter = () => {
        current += step;
        if (current < target) {
            counter.textContent = Math.floor(current).toLocaleString();
            requestAnimationFrame(updateCounter);
        } else {
            counter.textContent = target % 1 === 0 ? target.toLocaleString() : target.toFixed(1);
        }
    };
    
    updateCounter();
}

// ===== Smooth Scroll for Anchor Links =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#' && href.length > 1) {
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                if (mobileMenu) {
                    mobileMenu.style.display = 'none';
                }
            }
        }
    });
});

// ===== Enter Key Support for URL Input =====
if (urlInput) {
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            shortenBtn.click();
        }
    });
}

// ===== Newsletter Form Handler =====
const newsletterForm = document.querySelector('.newsletter-form');
if (newsletterForm) {
    newsletterForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const emailInput = newsletterForm.querySelector('input[type="email"]');
        const email = emailInput.value.trim();
        const submitBtn = newsletterForm.querySelector('button');
        
        if (!email) {
            showToast('Please enter your email', 'error');
            return;
        }
        
        // Disable button during submission
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        try {
            const response = await fetch('/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: email,turnstile_token: turnstileToken })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Thank you for subscribing!', 'success');
                newsletterForm.reset();
            } else {
                showToast(data.error || 'Subscription failed', 'error');
            }
        } catch (error) {
            showToast('An error occurred. Please try again.', 'error');
            console.error('Error:', error);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    });
}

// ===== Add Animation Classes on Scroll =====
const fadeElements = document.querySelectorAll('.feature-card, .step');
const fadeObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, { threshold: 0.1 });

fadeElements.forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    fadeObserver.observe(el);
});

let turnstileToken = null;

function onTurnstileSuccess(token) {
    turnstileToken = token;
}