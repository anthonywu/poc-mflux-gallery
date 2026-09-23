
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

    // Delegation also covers slides inserted after the initial page load.
    document.addEventListener('click', async function(event) {
        const button = event.target.closest('.copy-filename');
        if (!button) return;
        const filename = button.dataset.filename;
        const hint = button.querySelector(".copy-hint");
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
                hint.textContent = 'Copy filename';
                button.classList.remove('copy-feedback');
            }, 1800);
        }
    });

    // One viewport-level lens avoids clipping by Swiper's slide containers.
    document.addEventListener('DOMContentLoaded', () => {
        const lens = document.createElement('div');
        lens.className = 'image-zoom-lens';
        lens.hidden = true;
        lens.setAttribute('aria-hidden', 'true');
        const detail = new Image();
        detail.alt = '';
        detail.draggable = false;
        lens.append(detail);
        document.body.append(lens);
        const originals = new WeakMap();
        let activeImage = null;
        let pointer = null;
        let magnification = 2;

        function hideLens() {
            lens.hidden = true;
            activeImage = null;
        }

        function renderLens() {
            if (!activeImage || !activeImage.isConnected) return hideLens();
            const rect = activeImage.getBoundingClientRect();
            const x = pointer.x - rect.left;
            const y = pointer.y - rect.top;
            if (x < 0 || y < 0 || x > rect.width || y > rect.height) return hideLens();
            const original = originals.get(activeImage);
            // Show the preview immediately while the full-resolution image loads.
            const source = original?.complete && original.naturalWidth
                ? original.src : activeImage.currentSrc;
            if (detail.src !== source) detail.src = source;
            lens.hidden = false;
            lens.dataset.zoom = `${magnification}×`;
            const radius = lens.clientWidth / 2;
            lens.style.left = `${pointer.x - radius}px`;
            lens.style.top = `${pointer.y - radius}px`;
            detail.style.width = `${rect.width * magnification}px`;
            detail.style.height = `${rect.height * magnification}px`;
            detail.style.left = `${radius - x * magnification}px`;
            detail.style.top = `${radius - y * magnification}px`;
        }

        document.addEventListener('pointermove', event => {
            const img = event.target.closest('img.swiper-zoom-target');
            if (event.pointerType === 'touch' || event.buttons || !img || !img.naturalWidth) {
                hideLens();
                return;
            }
            magnification = event.altKey || event.metaKey ? 4 : 2;
            activeImage = img;
            pointer = {x: event.clientX, y: event.clientY};
            if (img.dataset.zoomSrc && !originals.has(img)) {
                const original = new Image();
                originals.set(img, original);
                original.onload = () => {
                    if (activeImage === img) renderLens();
                };
                original.src = img.dataset.zoomSrc;
            }
            renderLens();
        });
        document.addEventListener('pointerout', event => {
            if (event.target === activeImage) hideLens();
        });
        for (const type of ['keydown', 'keyup']) {
            document.addEventListener(type, event => {
                magnification = event.altKey || event.metaKey ? 4 : 2;
                if (event.key === 'Alt' || event.key === 'Meta') {
                    renderLens();
                } else if (type === 'keydown') {
                    hideLens();
                }
            });
        }
        for (const event of ['pointerdown', 'pointercancel', 'swiperslidechangetransitionstart', 'swiperzoomchange', 'delete-successful']) {
            document.addEventListener(event, hideLens);
        }
        window.addEventListener('scroll', hideLens, true);
        window.addEventListener('resize', hideLens);
        window.addEventListener('blur', hideLens);
    });
