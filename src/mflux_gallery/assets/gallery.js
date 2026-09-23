
    // Dark mode handling
    function initTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        }
        updateThemeToggleIcon();
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeToggleIcon();
    }

    function updateThemeToggleIcon() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark' ||
                      (!document.documentElement.getAttribute('data-theme') &&
                       window.matchMedia('(prefers-color-scheme: dark)').matches);
        document.documentElement.classList.toggle('dark', isDark);
        const btn = document.querySelector('.theme-toggle');
        if (btn) {
            btn.textContent = isDark ? '☀️' : '🌙';
        }
    }

    // Apply 0build colors before the first paint, then update the button on load.
    initTheme();

    // Initialize theme on load
    document.addEventListener('DOMContentLoaded', initTheme);

    // Metadata expansion state handling
    function initMetadataState() {
        const savedState = localStorage.getItem('metadataExpanded');
        // Only apply saved state if it exists (respecting default collapsed state)
        if (savedState !== null) {
            document.querySelectorAll('details.metadata-section').forEach(details => {
                if (savedState === 'true') {
                    details.setAttribute('open', '');
                } else {
                    details.removeAttribute('open');
                }
            });
        }
    }

    function toggleMetadataState(event) {
        const isOpen = event.target.hasAttribute('open');
        localStorage.setItem('metadataExpanded', isOpen);

        // Sync state across all metadata sections
        document.querySelectorAll('details.metadata-section').forEach(details => {
            if (isOpen) {
                details.setAttribute('open', '');
            } else {
                details.removeAttribute('open');
            }
        });
    }

    // Watch for dynamically loaded metadata sections
    const metadataObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) { // Element node
                    const metadataDetails = node.querySelector('details.metadata-section');
                    if (metadataDetails) {
                        const savedState = localStorage.getItem('metadataExpanded');
                        // Only apply saved state if it exists
                        if (savedState !== null) {
                            if (savedState === 'true') {
                                metadataDetails.setAttribute('open', '');
                            } else {
                                metadataDetails.removeAttribute('open');
                            }
                        }
                        metadataDetails.addEventListener('toggle', toggleMetadataState);
                    }
                }
            });
        });
    });

    // Start observing when DOM is loaded
    document.addEventListener('DOMContentLoaded', () => {
        initMetadataState();
        metadataObserver.observe(document.body, { childList: true, subtree: true });

        // Add event listeners to existing metadata sections
        document.querySelectorAll('details.metadata-section').forEach(details => {
            details.addEventListener('toggle', toggleMetadataState);
        });
    });

    // Swiper owns slide removal. HTMX only applies the out-of-band count update.
    document.addEventListener('delete-successful', function(event) {
        event.target.dataset.deleteSucceeded = 'true';
    });

    function removeDeletedSlide(form) {
        const slide = form.closest('swiper-slide');
        const swiper = document.querySelector('swiper-container')?.swiper;
        if (!slide || !swiper) return;
        const index = Array.from(swiper.slides).indexOf(slide);
        if (index < 0) return;
        swiper.removeSlide(index);
        if (navigator.vibrate) navigator.vibrate(50);
    }

    // Button loading state handling
    function setButtonLoading(button, isLoading) {
        if (isLoading) {
            button.classList.add('loading');
            button.disabled = true;
        } else {
            button.classList.remove('loading');
            button.disabled = false;
        }
    }

    function showButtonFeedback(button, type, duration = 1500) {
        button.classList.remove('loading');
        button.classList.add(type);
        setTimeout(() => {
            button.classList.remove(type);
            button.disabled = false;
        }, duration);
    }

    // Intercept form submissions for loading states
    document.addEventListener('submit', function(event) {
        const form = event.target;
        const button = form.querySelector('button[type="submit"]');

        if (button && (button.classList.contains('delete-image') || button.classList.contains('show-in-finder'))) {
            setButtonLoading(button, true);

            // For delete action, add optimistic animation
            if (button.classList.contains('delete-image')) {
                const slide = button.closest('.swiper-slide');
                if (slide) {
                    slide.classList.add('deleting');
                }
            }
        }
    });

    // Handle successful actions
    document.addEventListener('htmx:afterRequest', function(event) {
        const button = event.detail.elt.querySelector('button[type="submit"]');
        if (button) {
            if (event.detail.successful) {
                if (button.classList.contains('show-in-finder')) {
                    showButtonFeedback(button, 'success');
                } else if (button.classList.contains('delete-image')) {
                    // Delete is successful, but button will be removed with the slide
                    setButtonLoading(button, false);
                    if (event.detail.elt.dataset.deleteSucceeded === 'true') {
                        removeDeletedSlide(event.detail.elt);
                    }
                }
            } else {
                button.closest('swiper-slide')?.classList.remove('deleting');
                showButtonFeedback(button, 'error');
            }
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'f') {
            $(".swiper-slide-active button.show-in-finder")[0]?.click();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'd') {
            $(".swiper-slide-active button.delete-image")[0]?.click();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'n') {
            event.preventDefault();
            $("swiper-container")[0].swiper.slideNext();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'p') {
            event.preventDefault();
            $("swiper-container")[0].swiper.slidePrev();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'j') {
            event.preventDefault();
            const swiper = $("swiper-container")[0].swiper;
            const targetIndex = Math.max(0, swiper.activeIndex - 10);
            swiper.slideTo(targetIndex);
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'k') {
            event.preventDefault();
            const swiper = $("swiper-container")[0].swiper;
            const targetIndex = Math.min(swiper.slides.length - 1, swiper.activeIndex + 10);
            swiper.slideTo(targetIndex);
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'a') {
            event.preventDefault();
            const swiper = $("swiper-container")[0].swiper;
            swiper.slideTo(0);
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'e') {
            event.preventDefault();
            const swiper = $("swiper-container")[0].swiper;
            swiper.slideTo(swiper.slides.length - 1);
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'h') {
            event.preventDefault();
            const keyboardControls = document.getElementById('keyboard-controls');
            if (keyboardControls) {
                keyboardControls.open = !keyboardControls.open;
            }
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'm' || event.key === 'M') {
            event.preventDefault();
            // Toggle the metadata in the active slide
            const activeSlide = document.querySelector('.swiper-slide-active');
            if (activeSlide) {
                const metadataSection = activeSlide.querySelector('details.metadata-section');
                if (metadataSection) {
                    // Simulate a click on the details element to trigger the toggle event
                    metadataSection.open = !metadataSection.open;
                    metadataSection.dispatchEvent(new Event('toggle'));
                }
            }
        }
    });

    // Resolution switching hotkeys (1-4)
    document.addEventListener('keydown', function(event) {
        const resolutionMap = {
            '1': '256',
            '2': '512',
            '3': '768',
            '4': '1024'
        };

        if (resolutionMap[event.key]) {
            event.preventDefault();
            const newResolution = resolutionMap[event.key];
            const currentPath = window.location.pathname;
            const currentSearch = new URLSearchParams(window.location.search);

            // Update the resize_width parameter
            currentSearch.set('resize_width', newResolution);

            // Navigate to the new URL
            window.location.href = currentPath + '?' + currentSearch.toString();
        }
    });

    // Delegation also covers slides inserted after the initial page load.
    document.addEventListener('click', async function(event) {
        const button = event.target.closest('.copy-filename, .copy-prompt');
        if (!button) return;
        const isPrompt = button.classList.contains('copy-prompt');
        const filename = isPrompt ? button.closest('.metadata-section').querySelector('.prompt-text').textContent : button.dataset.filename;
        const hint = isPrompt ? button : button.querySelector('.copy-hint');
        button.disabled = true;
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(filename);
            } else {
                // Local HTTP galleries may not have access to the Clipboard API.
                const field = document.createElement('textarea');
                field.value = filename;
                field.style.cssText = 'position:fixed;left:-9999px;top:0';
                document.body.appendChild(field);
                try {
                    field.select();
                    if (!document.execCommand('copy')) throw new Error('Copy unavailable');
                } finally {
                    field.remove();
                }
            }
            hint.textContent = 'Copied!';
        } catch {
            hint.textContent = 'Copy failed';
        } finally {
            button.classList.add("copy-feedback");
            button.disabled = false;
            button.focus({preventScroll: true});
            clearTimeout(button.copyFeedbackTimer);
            button.copyFeedbackTimer = setTimeout(() => {
                hint.textContent = isPrompt ? 'Copy prompt' : 'Copy filename';
                button.classList.remove('copy-feedback');
            }, 1800);
        }
    });

    function updateNavigation() {
        const swiper = document.querySelector('swiper-container')?.swiper;
        if (!swiper) return;
        const count = swiper.slides.length;
        const position = document.getElementById('slide-position');
        position.textContent = `${count ? swiper.activeIndex + 1 : 0} of ${count}`;
        document.getElementById('empty-gallery').hidden = count > 0;
        document.querySelectorAll('[data-step]').forEach(button => {
            button.disabled = !count || (Number(button.dataset.step) < 0 ? swiper.isBeginning : swiper.isEnd);
        });
        swiper.updateAutoHeight(0);
    }
    document.addEventListener('DOMContentLoaded', () => {
        const container = document.querySelector('swiper-container');
        ['swiperinit', 'swiperslidechange', 'swiperslideslengthchange'].forEach(event => {
            container.addEventListener(event, updateNavigation);
        });
        updateNavigation();
    });
    document.addEventListener('click', event => {
        const button = event.target.closest('[data-step]');
        if (!button) return;
        const swiper = document.querySelector('swiper-container').swiper;
        swiper.slideTo(Math.max(0, Math.min(swiper.slides.length - 1, swiper.activeIndex + Number(button.dataset.step))));
    });
    document.addEventListener('toggle', () => {
        document.querySelector('swiper-container')?.swiper?.updateAutoHeight(0);
    }, true);
    document.addEventListener('htmx:afterSettle', updateNavigation);

    function setFocusMode(enabled) {
        document.documentElement.classList.toggle('focus-mode', enabled);
        const button = document.querySelector('[data-action="focus"]');
        button.setAttribute('aria-pressed', String(enabled));
        button.textContent = enabled ? 'Exit focus' : 'Focus';
        document.querySelector('swiper-container')?.swiper?.update();
    }
    document.addEventListener('click', event => {
        if (event.target.closest('[data-action="focus"]')) {
            setFocusMode(!document.documentElement.classList.contains('focus-mode'));
        }
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') setFocusMode(false);
        if (event.target.closest('input, select, textarea, [contenteditable="true"]') || event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.key === 'v') {
            event.preventDefault();
            setFocusMode(!document.documentElement.classList.contains('focus-mode'));
        }
    });
