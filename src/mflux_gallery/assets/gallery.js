
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
        const btn = document.querySelector('.theme-toggle');
        if (btn) {
            btn.textContent = isDark ? '☀️' : '🌙';
        }
    }

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

    // Image gallery handlers
    document.addEventListener('delete-successful', function(event) {
        // Haptic feedback for mobile devices
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }

        // Get the current active slide index before removal
        const swiper = $("swiper-container")[0].swiper;
        const activeIndex = swiper.activeIndex;
        const slidesCount = swiper.slides.length;

        // Clear loading state on delete button before slide removal
        const activeSlide = document.querySelector('.swiper-slide-active');
        if (activeSlide) {
            const deleteButton = activeSlide.querySelector('button.delete-image');
            if (deleteButton) {
                setButtonLoading(deleteButton, false);
            }
        }

        // Remove the slide from Swiper after a brief delay to ensure DOM update
        setTimeout(function() {
            // Store whether we're at the last slide before removal
            const isLastSlide = activeIndex === slidesCount - 1;

            // Remove the slide
            swiper.removeSlide(activeIndex);

            // After removing a slide:
            // - If we were at the last slide, we're now at the new last slide (no action needed)
            // - If we weren't at the last slide, we need to stay at the same index (which now shows the next image)
            // Swiper automatically handles this, but we need to ensure the active slide is visible
            if (!isLastSlide) {
                // Force update to ensure the slide is properly displayed
                swiper.slideTo(activeIndex, 0);
            }
        }, 100);
    });

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
                }
            } else {
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
    