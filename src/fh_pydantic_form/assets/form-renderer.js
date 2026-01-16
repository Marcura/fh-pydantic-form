  
function moveItem(buttonElement, direction) {
    // Find the accordion item (list item)
    const item = buttonElement.closest('li');
    if (!item) return;

    const container = item.parentElement;
    if (!container) return;

    // Find the sibling in the direction we want to move
    const sibling = direction === 'up' ? item.previousElementSibling : item.nextElementSibling;
    
    if (sibling) {
        if (direction === 'up') {
            container.insertBefore(item, sibling);
        } else {
            // Insert item after the next sibling
            container.insertBefore(item, sibling.nextElementSibling);
        }
        // Update button states after move
        updateMoveButtons(container);
    }
}

function moveItemUp(buttonElement) {
    moveItem(buttonElement, 'up');
}

function moveItemDown(buttonElement) {
    moveItem(buttonElement, 'down');
}

// Function to update button states (disable if at top/bottom)
function updateMoveButtons(container) {
    const items = container.querySelectorAll(':scope > li');
    items.forEach((item, index) => {
        const upButton = item.querySelector('button[onclick^="moveItemUp"]');
        const downButton = item.querySelector('button[onclick^="moveItemDown"]');
        
        if (upButton) upButton.disabled = (index === 0);
        if (downButton) downButton.disabled = (index === items.length - 1);
    });
}

// Snapshot initial form HTML for client-side reset
window.__fhpfInitialFormHtml = window.__fhpfInitialFormHtml || {};

window.fhpfCaptureInitialForms = function(root) {
    const scope = root || document;
    const wrappers = scope.querySelectorAll('[id$="-inputs-wrapper"]');
    wrappers.forEach(wrapper => {
        if (!wrapper.id) return;
        if (window.__fhpfInitialFormHtml[wrapper.id]) return;
        window.__fhpfInitialFormHtml[wrapper.id] = wrapper.innerHTML;
    });
};

window.fhpfResetForm = function(wrapperId, basePrefix, confirmMessage) {
    if (confirmMessage && !window.confirm(confirmMessage)) {
        return false;
    }

    let wrapper = document.getElementById(wrapperId);
    if (!wrapper && basePrefix) {
        const candidate = document.querySelector(`[name^='${basePrefix}']`);
        if (candidate) {
            wrapper = candidate.closest('[id$="-inputs-wrapper"]');
        }
    }

    if (!wrapper) {
        console.warn('Reset target not found:', wrapperId);
        // Show user-facing notification using UIkit if available, otherwise alert
        if (window.UIkit && UIkit.notification) {
            UIkit.notification({message: 'Reset failed: form not found', status: 'warning', pos: 'top-center'});
        } else {
            alert('Reset failed: unable to find the form to reset.');
        }
        return false;
    }

    const initialHtml = window.__fhpfInitialFormHtml
        ? window.__fhpfInitialFormHtml[wrapper.id]
        : null;
    if (!initialHtml) {
        console.warn('No initial snapshot for form:', wrapper.id);
        // Show user-facing notification - initial state was not captured
        if (window.UIkit && UIkit.notification) {
            UIkit.notification({message: 'Reset failed: initial form state not available', status: 'warning', pos: 'top-center'});
        } else {
            alert('Reset failed: the initial form state was not captured. Please refresh the page to reset.');
        }
        return false;
    }

    wrapper.innerHTML = initialHtml;

    // Re-enable move button state for any list containers inside.
    wrapper.querySelectorAll('[id$="_items_container"]').forEach(container => {
        updateMoveButtons(container);
    });

    // Re-process HTMX attributes on the restored subtree.
    if (window.htmx && typeof window.htmx.process === 'function') {
        window.htmx.process(wrapper);
    }

    // Re-initialize UIkit accordions within the restored subtree if available.
    if (window.UIkit && UIkit.accordion) {
        wrapper.querySelectorAll('[uk-accordion]').forEach(el => {
            try {
                UIkit.accordion(el);
            } catch (e) {
                // Ignore UIkit init errors
            }
        });
    }

    return false;
};

// Function to toggle all list items open or closed
function toggleListItems(containerId) {
    const containerElement = document.getElementById(containerId);
    if (!containerElement) {
        console.warn('Accordion container not found:', containerId);
        return;
    }

    // Find all direct li children (the accordion items)
    const items = Array.from(containerElement.children).filter(el => el.tagName === 'LI');
    if (!items.length) {
        return; // No items to toggle
    }

    // Determine if we should open all (if any are closed) or close all (if all are open)
    const shouldOpen = items.some(item => !item.classList.contains('uk-open'));

    // Toggle each item accordingly
    items.forEach(item => {
        if (shouldOpen) {
            // Open the item if it's not already open
            if (!item.classList.contains('uk-open')) {
                item.classList.add('uk-open');
                // Make sure the content is expanded
                const content = item.querySelector('.uk-accordion-content');
                if (content) {
                    content.style.height = 'auto';
                    content.hidden = false;
                }
            }
        } else {
            // Close the item
            item.classList.remove('uk-open');
            // Hide the content
            const content = item.querySelector('.uk-accordion-content');
            if (content) {
                content.hidden = true;
            }
        }
    });

    // Attempt to use UIkit's API if available (more reliable)
    if (window.UIkit && UIkit.accordion) {
        try {
            const accordion = UIkit.accordion(containerElement);
            if (accordion) {
                // In UIkit, indices typically start at 0
                items.forEach((item, index) => {
                    const isOpen = item.classList.contains('uk-open');
                    if (shouldOpen && !isOpen) {
                        accordion.toggle(index, false); // Open item without animation
                    } else if (!shouldOpen && isOpen) {
                        accordion.toggle(index, false); // Close item without animation
                    }
                });
            }
        } catch (e) {
            console.warn('UIkit accordion API failed, falling back to manual toggle', e);
            // The manual toggle above should have handled it
        }
    }
}

// Simple accordion state preservation using item IDs
window.saveAccordionState = function(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const openItemIds = [];
    container.querySelectorAll('li.uk-open').forEach(item => {
        if (item.id) {
            openItemIds.push(item.id);
        }
    });
    
    // Store in sessionStorage with container-specific key
    sessionStorage.setItem(`accordion_state_${containerId}`, JSON.stringify(openItemIds));
};

window.restoreAccordionState = function(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const savedState = sessionStorage.getItem(`accordion_state_${containerId}`);
    if (!savedState) return;
    
    try {
        const openItemIds = JSON.parse(savedState);
        
        // Restore open state for each saved item by ID
        openItemIds.forEach(itemId => {
            const item = document.getElementById(itemId);
            if (item && container.contains(item)) {
                item.classList.add('uk-open');
                const content = item.querySelector('.uk-accordion-content');
                if (content) {
                    content.hidden = false;
                    content.style.height = 'auto';
                }
            }
        });
    } catch (e) {
        console.warn('Failed to restore accordion state:', e);
    }
};

// Save all accordion states in the form (both lists and nested BaseModels)
window.saveAllAccordionStates = function() {
    // Save list container states
    document.querySelectorAll('[id$="_items_container"]').forEach(container => {
        window.saveAccordionState(container.id);
    });

    // Save all UIkit accordion item states (nested BaseModels, etc.)
    document.querySelectorAll('.uk-accordion > li').forEach(item => {
        if (item.id) {
            const isOpen = item.classList.contains('uk-open');
            sessionStorage.setItem('accordion_state_' + item.id, isOpen ? 'open' : 'closed');
        }
    });
};

// Restore all accordion states in the form (both lists and nested BaseModels)
window.restoreAllAccordionStates = function() {
    // Restore list container states
    document.querySelectorAll('[id$="_items_container"]').forEach(container => {
        window.restoreAccordionState(container.id);
    });

    // Use requestAnimationFrame to ensure DOM has fully updated after swap
    requestAnimationFrame(() => {
        setTimeout(() => {
            // Restore ALL UIkit accordion item states in the entire document (not just swapped area)
            document.querySelectorAll('.uk-accordion > li').forEach(item => {
                if (item.id) {
                    const savedState = sessionStorage.getItem('accordion_state_' + item.id);

                    if (savedState === 'open' && !item.classList.contains('uk-open')) {
                        item.classList.add('uk-open');
                    } else if (savedState === 'closed' && item.classList.contains('uk-open')) {
                        item.classList.remove('uk-open');
                    }
                }
            });
        }, 150);
    });
};

// ============================================
// List[Literal] / List[Enum] pill management
// ============================================

// Add a new pill when dropdown selection changes
window.fhpfAddChoicePill = function(fieldName, selectEl, containerId) {
    const formValue = selectEl.value;
    if (!formValue) return;

    // Get display text from selected option's data attribute or text content
    const selectedOption = selectEl.options[selectEl.selectedIndex];
    const displayText = selectedOption.dataset.display || selectedOption.textContent;

    const container = document.getElementById(containerId);
    const pillsContainer = document.getElementById(containerId + '_pills');
    if (!container || !pillsContainer) return;

    // Generate unique index using timestamp
    const idx = 'new_' + Date.now();
    const pillId = fieldName + '_' + idx + '_pill';
    const inputName = fieldName + '_' + idx;

    // Create the pill element
    const pill = document.createElement('span');
    pill.id = pillId;
    pill.dataset.value = formValue;
    pill.className = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800';

    // Create hidden input (stores form value)
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = inputName;
    input.value = formValue;

    // Create label span (shows display text)
    const label = document.createElement('span');
    label.className = 'mr-1';
    label.textContent = displayText;

    // Create remove button
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'ml-1 text-xs hover:text-red-600 font-bold cursor-pointer';
    removeBtn.textContent = '×';
    removeBtn.onclick = function() {
        window.fhpfRemoveChoicePill(pillId, formValue, containerId);
    };

    // Assemble pill
    pill.appendChild(input);
    pill.appendChild(label);
    pill.appendChild(removeBtn);

    // Add to pills container
    pillsContainer.appendChild(pill);

    // Reset and rebuild dropdown
    selectEl.value = '';
    fhpfRebuildChoiceDropdown(containerId);
};

// Remove a pill
window.fhpfRemoveChoicePill = function(pillId, formValue, containerId) {
    const pill = document.getElementById(pillId);
    if (pill) {
        pill.remove();
    }
    // Rebuild dropdown to include the removed value
    fhpfRebuildChoiceDropdown(containerId);
};

// Rebuild dropdown based on current pills
function fhpfRebuildChoiceDropdown(containerId) {
    const container = document.getElementById(containerId);
    const dropdown = document.getElementById(containerId + '_dropdown');
    const pillsContainer = document.getElementById(containerId + '_pills');
    if (!container || !dropdown || !pillsContainer) return;

    // Get all possible choices from JSON data attribute
    const allChoicesJson = container.dataset.allChoices || '[]';
    let allChoices = [];
    try {
        allChoices = JSON.parse(allChoicesJson);
    } catch (e) {
        console.error('Failed to parse allChoices JSON:', e);
        return;
    }

    // Get currently selected values from pills
    const pills = pillsContainer.querySelectorAll('[data-value]');
    const selectedValues = new Set();
    pills.forEach(function(pill) {
        selectedValues.add(pill.dataset.value);
    });

    // Calculate remaining choices
    const remaining = allChoices.filter(function(choice) {
        return !selectedValues.has(choice.value);
    });

    // Rebuild dropdown options
    dropdown.innerHTML = '';

    // Add placeholder option
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Add...';
    placeholder.selected = true;
    placeholder.disabled = true;
    dropdown.appendChild(placeholder);

    // Add remaining choices as options
    remaining.forEach(function(choice) {
        const opt = document.createElement('option');
        opt.value = choice.value;
        opt.textContent = choice.display;
        opt.dataset.display = choice.display;
        dropdown.appendChild(opt);
    });

    // Show/hide dropdown based on remaining options
    dropdown.style.display = remaining.length > 0 ? 'inline-block' : 'none';
}

// ============================================
// Initialization
// ============================================

// Wait for the DOM to be fully loaded before initializing
document.addEventListener('DOMContentLoaded', () => {
    // Initialize button states for elements present on initial load
    document.querySelectorAll('[id$="_items_container"]').forEach(container => {
        updateMoveButtons(container);
    });

    if (window.fhpfCaptureInitialForms) {
        window.fhpfCaptureInitialForms(document);
    }

    // Attach HTMX event listener to document.body for list operations
    document.body.addEventListener('htmx:afterSwap', function(event) {
        // Check if this is an insert (afterend swap)
        const targetElement = event.detail.target;
        const requestElement = event.detail.requestConfig?.elt;
        const swapStrategy = requestElement ? requestElement.getAttribute('hx-swap') : null;
        
        if (swapStrategy === 'afterend') {
            // For insertions, get the parent container of the original target
            const listContainer = targetElement.closest('[id$="_items_container"]');
            if (listContainer) {
                updateMoveButtons(listContainer);
            }
        } else {
            // Original logic for other swap types
            const containers = event.detail.target.querySelectorAll('[id$="_items_container"]');
            containers.forEach(container => {
                updateMoveButtons(container);
            });
            
            // If the target itself is a container
            if (event.detail.target.id && event.detail.target.id.endsWith('_items_container')) {
                updateMoveButtons(event.detail.target);
            }
        }

        if (window.fhpfCaptureInitialForms && event.detail.target) {
            window.fhpfCaptureInitialForms(event.detail.target);
        }
    }); 
});
