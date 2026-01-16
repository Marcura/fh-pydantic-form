
// ==== Regex patterns for list path detection ====
// These patterns match both numeric indices [0] and placeholder indices [new_123]
const FHPF_RE = {
  // Full list item: ends with [index] (no trailing content)
  FULL_ITEM: /\[(\d+|new_\d+)\]$/,
  // Subfield: has content after [index] (e.g., [0].field)
  SUBFIELD: /\[(\d+|new_\d+)\]\./,
  // Any index: matches [index] anywhere in path
  ANY_INDEX: /\[(\d+|new_\d+)\]/,
  // Strip index and everything after
  STRIP_INDEX_SUFFIX: /\[(\d+|new_\d+)\].*$/,
  // Pure numeric string
  NUMERIC: /^\d+$/
};

// Helper functions for list item path detection
function isListItemPath(pathPrefix) {
  // Check if path is a full list item: ends with [index] where index is numeric or new_*
  // e.g., "reviews[0]" or "reviews[new_123]" -> true
  // e.g., "reviews[0].rating" or "reviews" -> false
  return FHPF_RE.FULL_ITEM.test(pathPrefix);
}

function isListSubfieldPath(pathPrefix) {
  // Check if path is a subfield of a list item (has content after [index])
  // e.g., "reviews[0].rating" or "reviews[new_123].comment" -> true
  // e.g., "reviews[0]" or "reviews" -> false
  return FHPF_RE.SUBFIELD.test(pathPrefix);
}

function hasListIndex(pathPrefix) {
  // Check if path contains ANY list index (for general list detection)
  return FHPF_RE.ANY_INDEX.test(pathPrefix);
}

function extractListFieldPath(pathPrefix) {
  // Extract the list field path without the index
  // e.g., "addresses[0]" -> "addresses"
  // e.g., "addresses[new_123].street" -> "addresses"
  return pathPrefix.replace(FHPF_RE.STRIP_INDEX_SUFFIX, '');
}

function extractListIndex(pathPrefix) {
  // Extract the index from path
  // e.g., "addresses[0].street" -> 0
  // e.g., "addresses[new_123]" -> "new_123"
  const match = pathPrefix.match(FHPF_RE.ANY_INDEX);
  if (!match) return null;
  const indexStr = match[1];
  // Return numeric index as number, placeholder as string
  return FHPF_RE.NUMERIC.test(indexStr) ? parseInt(indexStr) : indexStr;
}

function fhpfFormNameFromPrefix(prefix) {
  if (!prefix) return null;
  return prefix.replace(/_$/, '');
}

function fhpfResolveComparisonContext(triggerEl, currentPrefix) {
  let grid = null;

  if (triggerEl && triggerEl.closest) {
    grid = triggerEl.closest('[data-fhpf-left-prefix][data-fhpf-right-prefix]');
  }

  if (!grid && currentPrefix) {
    const grids = document.querySelectorAll('[data-fhpf-left-prefix][data-fhpf-right-prefix]');
    for (let i = 0; i < grids.length; i++) {
      const gridLeftPrefix = grids[i].dataset.fhpfLeftPrefix;
      const gridRightPrefix = grids[i].dataset.fhpfRightPrefix;
      if (
        (gridLeftPrefix && currentPrefix.startsWith(gridLeftPrefix)) ||
        (gridRightPrefix && currentPrefix.startsWith(gridRightPrefix))
      ) {
        grid = grids[i];
        break;
      }
    }
  }

  let leftPrefix = null;
  let rightPrefix = null;

  if (grid) {
    leftPrefix = grid.dataset.fhpfLeftPrefix || null;
    rightPrefix = grid.dataset.fhpfRightPrefix || null;
  }

  if ((!leftPrefix || !rightPrefix) && window.__fhpfComparisonPrefixes) {
    const keys = Object.keys(window.__fhpfComparisonPrefixes);
    if (keys.length === 1) {
      const entry = window.__fhpfComparisonPrefixes[keys[0]];
      leftPrefix = leftPrefix || entry.left;
      rightPrefix = rightPrefix || entry.right;
    }
  }

  if (!leftPrefix) leftPrefix = window.__fhpfLeftPrefix;
  if (!rightPrefix) rightPrefix = window.__fhpfRightPrefix;

  return { grid: grid, leftPrefix: leftPrefix, rightPrefix: rightPrefix };
}

// Helper function to copy pill (List[Literal] or List[Enum]) field contents
// This is used by performListCopyByPosition, subfield copy, and performStandardCopy
function copyPillContainer(sourcePillContainer, targetPillContainer, highlightTarget) {
  if (!sourcePillContainer || !targetPillContainer) {
    return false;
  }

  // Get source selected values from pills
  const sourcePillsContainer = sourcePillContainer.querySelector('[id$="_pills"]');
  const sourceValues = [];
  if (sourcePillsContainer) {
    const sourcePills = sourcePillsContainer.querySelectorAll('[data-value]');
    sourcePills.forEach(function(pill) {
      const hiddenInput = pill.querySelector('input[type="hidden"]');
      if (hiddenInput) {
        sourceValues.push({
          value: pill.dataset.value,
          display: pill.querySelector('span.mr-1') ? pill.querySelector('span.mr-1').textContent : pill.dataset.value
        });
      }
    });
  }

  // Clear target pills
  const targetPillsContainer = targetPillContainer.querySelector('[id$="_pills"]');
  const targetDropdown = targetPillContainer.querySelector('select');
  const targetFieldName = targetPillContainer.dataset.fieldName;
  const targetContainerId = targetPillContainer.id;

  if (targetPillsContainer) {
    targetPillsContainer.innerHTML = '';
  }

  // Recreate pills in target with source values
  sourceValues.forEach(function(item, idx) {
    const pillId = targetFieldName + '_' + idx + '_pill';
    const inputName = targetFieldName + '_' + idx;

    // Create hidden input
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = inputName;
    input.value = item.value;

    // Create label span
    const label = document.createElement('span');
    label.className = 'mr-1';
    label.textContent = item.display;

    // Create remove button
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'ml-1 text-xs hover:text-red-600 font-bold cursor-pointer';
    removeBtn.textContent = '×';
    removeBtn.onclick = function() {
      window.fhpfRemoveChoicePill(pillId, item.value, targetContainerId);
    };

    // Create pill span
    const pill = document.createElement('span');
    pill.id = pillId;
    pill.dataset.value = item.value;
    pill.className = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800';
    pill.appendChild(input);
    pill.appendChild(label);
    pill.appendChild(removeBtn);

    targetPillsContainer.appendChild(pill);
  });

  // Rebuild the target dropdown to show remaining options
  if (targetDropdown && typeof fhpfRebuildChoiceDropdown === 'function') {
    // Use internal rebuild function if available
    fhpfRebuildChoiceDropdown(targetContainerId);
  } else if (targetDropdown) {
    // Manual dropdown rebuild
    const allChoicesJson = targetPillContainer.dataset.allChoices || '[]';
    let allChoices = [];
    try {
      allChoices = JSON.parse(allChoicesJson);
    } catch (e) {
      console.error('Failed to parse pill choices:', e);
    }

    const selectedValues = new Set(sourceValues.map(function(v) { return v.value; }));
    const remaining = allChoices.filter(function(choice) {
      return !selectedValues.has(choice.value);
    });

    // Rebuild dropdown options
    targetDropdown.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Add...';
    placeholder.selected = true;
    placeholder.disabled = true;
    targetDropdown.appendChild(placeholder);

    remaining.forEach(function(choice) {
      const opt = document.createElement('option');
      opt.value = choice.value;
      opt.textContent = choice.display;
      opt.dataset.display = choice.display;
      targetDropdown.appendChild(opt);
    });

    targetDropdown.style.display = remaining.length > 0 ? 'inline-block' : 'none';
  }

  // Highlight the target container briefly if requested
  if (highlightTarget !== false) {
    targetPillContainer.style.transition = 'background-color 0.3s';
    targetPillContainer.style.backgroundColor = '#dbeafe';
    setTimeout(function() {
      targetPillContainer.style.backgroundColor = '';
      setTimeout(function() {
        targetPillContainer.style.transition = '';
      }, 300);
    }, 1500);
  }

  return true;
}

// Copy function - pure JS implementation
window.fhpfPerformCopy = function(pathPrefix, currentPrefix, copyTarget, triggerEl) {
  try {
    // Set flag to prevent accordion sync
    window.__fhpfCopyInProgress = true;

    // Resolve comparison context (supports multiple comparisons on the page)
    const ctx = fhpfResolveComparisonContext(triggerEl, currentPrefix);
    const leftPrefix = ctx.leftPrefix;
    const rightPrefix = ctx.rightPrefix;
    const grid = ctx.grid;

    if (!leftPrefix || !rightPrefix) {
      console.error('Copy failed: missing comparison prefixes.');
      window.__fhpfCopyInProgress = false;
      return;
    }

    const accordionScope = grid || document;

    // Save all accordion states before copy
    const accordionStates = [];
    accordionScope.querySelectorAll('ul[uk-accordion] > li').forEach(function(li) {
      accordionStates.push({
        element: li,
        isOpen: li.classList.contains('uk-open')
      });
    });

    // Determine source/target prefixes based on copy target
    const sourcePrefix = (copyTarget === 'left') ? rightPrefix : leftPrefix;
    const targetPrefix = (copyTarget === 'left') ? leftPrefix : rightPrefix;
    const targetFormName = fhpfFormNameFromPrefix(targetPrefix);
    const htmxValues = targetFormName ? { fhpf_form_name: targetFormName } : {};

    function resolveById(id) {
      if (!id) return null;
      if (grid && grid.querySelector) {
        return grid.querySelector('[id=\"' + id + '\"]');
      }
      return document.getElementById(id);
    }

    // Determine copy behavior based on path structure:
    // 1. Full list item (e.g., "reviews[0]") -> add new item to target list
    // 2. Subfield of list item (e.g., "reviews[0].rating") -> update existing subfield
    // 3. Regular field (e.g., "name" or "reviews") -> standard copy
    const isFullListItem = isListItemPath(pathPrefix);
    const isSubfield = isListSubfieldPath(pathPrefix);
    let listFieldPath = null;
    let listIndex = null;

    if (isFullListItem || isSubfield) {
      listFieldPath = extractListFieldPath(pathPrefix);
      listIndex = extractListIndex(pathPrefix);
    }

    // CASE 2: Subfield copy - update existing item's subfield (NOT create new item)
    // This is the fix for the bug where copying reviews[0].rating created a new item
    if (isSubfield) {
      // For subfield copies, we need to find the corresponding target field by position
      // and perform a direct value copy (standard copy behavior)
      // Extract the relative path (e.g., ".rating" from "reviews[0].rating")
      // Find the closing bracket after listFieldPath and extract what comes after
      const bracketStart = pathPrefix.indexOf('[', listFieldPath.length);
      const bracketEnd = pathPrefix.indexOf(']', bracketStart);
      const relativePath = (bracketEnd >= 0) ? pathPrefix.substring(bracketEnd + 1) : '';

      // Find source and target list containers to map by position
      const sourceContainerId = sourcePrefix.replace(/_$/, '') + '_' + listFieldPath + '_items_container';
      const targetContainerId = targetPrefix.replace(/_$/, '') + '_' + listFieldPath + '_items_container';

      const sourceListContainer = resolveById(sourceContainerId);
      const targetListContainer = resolveById(targetContainerId);

      if (sourceListContainer && targetListContainer) {
        const sourceItems = sourceListContainer.querySelectorAll(':scope > li');
        const targetItems = targetListContainer.querySelectorAll(':scope > li');

        // Find the position of the source item
        let sourcePosition = -1;
        if (typeof listIndex === 'number') {
          sourcePosition = listIndex;
        } else if (typeof listIndex === 'string' && listIndex.startsWith('new_')) {
          // For placeholder indices, find by searching for the element with this path
          for (let i = 0; i < sourceItems.length; i++) {
            const inputs = sourceItems[i].querySelectorAll('[data-field-path^="' + pathPrefix.replace(/\.[^.]+$/, '') + '"]');
            if (inputs.length > 0) {
              sourcePosition = i;
              break;
            }
          }
        }

        // If we found a valid source position and target has that position, perform the copy
        if (sourcePosition >= 0 && sourcePosition < targetItems.length) {
          const sourceItem = sourceItems[sourcePosition];
          const targetItem = targetItems[sourcePosition];

          // Find the source input with this exact path
          const sourceInput = sourceItem.querySelector('[data-field-path="' + pathPrefix + '"]');

          // Find the target input with matching relative path
          const targetInputs = targetItem.querySelectorAll('[data-field-path]');
          let targetInput = null;

          for (let j = 0; j < targetInputs.length; j++) {
            let targetFp = targetInputs[j].getAttribute('data-field-path');
            const tBracketStart = targetFp.indexOf('[', listFieldPath.length);
            const tBracketEnd = targetFp.indexOf(']', tBracketStart);
            const targetRelative = (tBracketEnd >= 0) ? targetFp.substring(tBracketEnd + 1) : '';

            if (targetRelative === relativePath) {
              // Verify it belongs to target form
              let candidateName = null;
              if (targetInputs[j].tagName === 'UK-SELECT') {
                const nativeSelect = targetInputs[j].querySelector('select');
                candidateName = nativeSelect ? nativeSelect.name : null;
              } else if (targetInputs[j].dataset.pillField === 'true') {
                // Pill containers (DIV elements) don't have a name attribute,
                // use their ID instead which contains the form prefix
                candidateName = targetInputs[j].id;
              } else {
                candidateName = targetInputs[j].name;
              }

              if (candidateName && !candidateName.startsWith(sourcePrefix)) {
                targetInput = targetInputs[j];
                break;
              }
            }
          }

          if (sourceInput && targetInput) {
            // Check if this is a pill field (List[Literal] or List[Enum])
            if (sourceInput.dataset.pillField === 'true' && targetInput.dataset.pillField === 'true') {
              // Use pill-aware copy logic
              copyPillContainer(sourceInput, targetInput, true);

              // Restore accordion states and return
              setTimeout(function() {
                accordionStates.forEach(function(state) {
                  if (state.isOpen && !state.element.classList.contains('uk-open')) {
                    state.element.classList.add('uk-open');
                    const content = state.element.querySelector('.uk-accordion-content');
                    if (content) {
                      content.hidden = false;
                      content.style.height = 'auto';
                    }
                  }
                });
                window.__fhpfCopyInProgress = false;
              }, 100);
              return;
            }

            // Copy the value directly
            const tag = sourceInput.tagName.toUpperCase();
            const type = (sourceInput.type || '').toLowerCase();

            if (type === 'checkbox') {
              targetInput.checked = sourceInput.checked;
            } else if (tag === 'SELECT') {
              targetInput.value = sourceInput.value;
              targetInput.dispatchEvent(new Event('change', { bubbles: true }));
            } else if (tag === 'UK-SELECT') {
              const srcSelect = sourceInput.querySelector('select');
              const tgtSelect = targetInput.querySelector('select');
              if (srcSelect && tgtSelect) {
                const srcVal = srcSelect.value;
                for (let k = 0; k < tgtSelect.options.length; k++) {
                  tgtSelect.options[k].removeAttribute('selected');
                  tgtSelect.options[k].selected = false;
                }
                for (let k = 0; k < tgtSelect.options.length; k++) {
                  if (tgtSelect.options[k].value === srcVal) {
                    tgtSelect.options[k].setAttribute('selected', 'selected');
                    tgtSelect.options[k].selected = true;
                    tgtSelect.selectedIndex = k;
                    tgtSelect.value = srcVal;
                    break;
                  }
                }
                const srcBtn = sourceInput.querySelector('button');
                const tgtBtn = targetInput.querySelector('button');
                if (srcBtn && tgtBtn) {
                  tgtBtn.innerHTML = srcBtn.innerHTML;
                }
                tgtSelect.dispatchEvent(new Event('change', { bubbles: true }));
              }
            } else if (tag === 'TEXTAREA') {
              targetInput.value = sourceInput.value;
              targetInput.textContent = sourceInput.value;
              targetInput.dispatchEvent(new Event('input', { bubbles: true }));
              targetInput.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
              targetInput.value = sourceInput.value;
              targetInput.dispatchEvent(new Event('input', { bubbles: true }));
              targetInput.dispatchEvent(new Event('change', { bubbles: true }));
            }

            // Highlight the target field briefly
            targetInput.style.transition = 'background-color 0.3s';
            targetInput.style.backgroundColor = '#dbeafe';
            setTimeout(function() {
              targetInput.style.backgroundColor = '';
              setTimeout(function() {
                targetInput.style.transition = '';
              }, 300);
            }, 1500);
          }
        }
      }

      // Restore accordion states
      setTimeout(function() {
        accordionStates.forEach(function(state) {
          if (state.isOpen && !state.element.classList.contains('uk-open')) {
            state.element.classList.add('uk-open');
            const content = state.element.querySelector('.uk-accordion-content');
            if (content) {
              content.hidden = false;
              content.style.height = 'auto';
            }
          }
        });
        window.__fhpfCopyInProgress = false;
      }, 100);

      return;  // Exit early - subfield copy is complete
    }

    // CASE 1: Full list item copy - add new item to target list
    if (isFullListItem) {
      // Find target list container
      const targetContainerId = targetPrefix.replace(/_$/, '') + '_' + listFieldPath + '_items_container';
      const targetContainer = resolveById(targetContainerId);

      if (targetContainer) {
        // Find the "Add Item" button for the target list
        const targetAddButton = targetContainer.parentElement.querySelector('button[hx-post*="/list/add/"]');

        if (targetAddButton) {
          // Capture the target list items BEFORE adding the new one
          const targetListItemsBeforeAdd = Array.from(targetContainer.querySelectorAll(':scope > li'));
          const targetLengthBefore = targetListItemsBeforeAdd.length;

          // Determine the target position: insert after the source item's index, or at end if target is shorter
          const sourceIndex = listIndex;  // The index from the source path (e.g., reviews[2] -> 2)
          const insertAfterIndex = Math.min(sourceIndex, targetLengthBefore - 1);

          // Get the URL from the add button
          const addUrl = targetAddButton.getAttribute('hx-post');

          // Determine the insertion point
          let insertBeforeElement = null;
          if (insertAfterIndex >= 0 && insertAfterIndex < targetLengthBefore - 1) {
            // Insert after insertAfterIndex, which means before insertAfterIndex+1
            insertBeforeElement = targetListItemsBeforeAdd[insertAfterIndex + 1];
          } else if (targetLengthBefore > 0) {
            // Insert at the end: use afterend on the last item
            insertBeforeElement = targetListItemsBeforeAdd[targetLengthBefore - 1];
          }

          // Make the HTMX request with custom swap target
          if (insertBeforeElement) {
            const swapStrategy = (insertAfterIndex >= targetLengthBefore - 1) ? 'afterend' : 'beforebegin';
            // Use htmx.ajax to insert at specific position
            htmx.ajax('POST', addUrl, {
              target: '#' + insertBeforeElement.id,
              swap: swapStrategy,
              values: htmxValues
            });
          } else {
            // List is empty, insert into container
            htmx.ajax('POST', addUrl, {
              target: '#' + targetContainerId,
              swap: 'beforeend',
              values: htmxValues
            });
          }

          // Wait for HTMX to complete the swap AND settle, then copy values
          let copyCompleted = false;
          let htmxSettled = false;
          let newlyAddedElement = null;

          // Listen for HTMX afterSwap event on the container to capture the newly added element
          targetContainer.addEventListener('htmx:afterSwap', function onSwap(evt) {
            // Parse the response to get the new element's ID
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = evt.detail.xhr.response;
            const newElement = tempDiv.firstElementChild;
            if (newElement && newElement.id) {
              newlyAddedElement = newElement;
            }
          }, { once: true });

          // Listen for HTMX afterSettle event
          document.body.addEventListener('htmx:afterSettle', function onSettle(evt) {
            htmxSettled = true;
            document.body.removeEventListener('htmx:afterSettle', onSettle);
          }, { once: true });

          let maxAttempts = 100; // 100 attempts with exponential backoff = ~10 seconds total
          let attempts = 0;

          const checkAndCopy = function() {
            attempts++;

            // Calculate delay with exponential backoff: 50ms, 50ms, 100ms, 100ms, 200ms, ...
            const delay = Math.min(50 * Math.pow(2, Math.floor(attempts / 2)), 500);

            // Wait for HTMX to settle before proceeding
            if (!htmxSettled && attempts < maxAttempts) {
              setTimeout(checkAndCopy, delay);
              return;
            }

            // If we timed out waiting for HTMX, give up
            if (!htmxSettled) {
              console.error('Timeout: HTMX did not settle after ' + attempts + ' attempts');
              window.__fhpfCopyInProgress = false;
              return;
            }

            // Find the newly added item using the ID we captured
            const targetItems = targetContainer.querySelectorAll(':scope > li');
            let newItem = null;
            let newItemIndex = -1;

            if (newlyAddedElement && newlyAddedElement.id) {
              // Use the ID we captured from the HTMX response
              newItem = resolveById(newlyAddedElement.id);

              if (newItem) {
                // Find its position in the list
                for (let i = 0; i < targetItems.length; i++) {
                  if (targetItems[i] === newItem) {
                    newItemIndex = i;
                    break;
                  }
                }
              }
            }

            // Check if new item has been added
            if (newItem) {

              // Wait until the new item has input fields (indicating HTMX swap is complete)
              const newItemInputs = newItem.querySelectorAll('[data-field-path]');

              if (newItemInputs.length > 0) {
                // New item is ready, now copy values from source item
                copyCompleted = true;

                // The new item might not contain the textarea with placeholder!
                // Search the entire target container for the newest textarea with "new_" in the name
                const allInputsInContainer = targetContainer.querySelectorAll('[data-field-path^="' + listFieldPath + '["]');

                let firstInput = null;
                let newestTimestamp = 0;

                for (let i = 0; i < allInputsInContainer.length; i++) {
                  const inputName = allInputsInContainer[i].name || allInputsInContainer[i].id;
                  if (inputName && inputName.startsWith(targetPrefix.replace(/_$/, '') + '_' + listFieldPath + '_new_')) {
                    // Extract timestamp from name
                    const match = inputName.match(/new_(\d+)/);
                    if (match) {
                      const timestamp = parseInt(match[1]);
                      if (timestamp > newestTimestamp) {
                        newestTimestamp = timestamp;
                        firstInput = allInputsInContainer[i];
                      }
                    }
                  }
                }

                if (!firstInput) {
                  firstInput = newItemInputs[0];
                }

                const firstInputPath = firstInput.getAttribute('data-field-path');
                const firstInputName = firstInput.name || firstInput.id;

                // Extract placeholder from name
                // Pattern: "prefix_listfield_PLACEHOLDER" or "prefix_listfield_PLACEHOLDER_fieldname"
                // For simple list items: "annotated_truth_key_features_new_123"
                // For BaseModel list items: "annotated_truth_reviews_new_123_rating"
                // We want just the placeholder part (new_123)
                const searchStr = '_' + listFieldPath + '_';
                const idx = firstInputName.indexOf(searchStr);
                let actualPlaceholderIdx = null;

                if (idx >= 0) {
                  const afterListField = firstInputName.substring(idx + searchStr.length);

                  // For BaseModel items with nested fields, the placeholder is between listfield and the next underscore
                  // Check if this looks like a nested field by checking if there's another underscore after "new_"
                  if (afterListField.startsWith('new_')) {
                    // Extract just "new_TIMESTAMP" part - stop at the next underscore after the timestamp
                    const parts = afterListField.split('_');
                    if (parts.length >= 2) {
                      // parts[0] = "new", parts[1] = timestamp, parts[2+] = field names
                      actualPlaceholderIdx = parts[0] + '_' + parts[1];
                    } else {
                      actualPlaceholderIdx = afterListField;
                    }
                  } else {
                    // Numeric index, just use it as-is
                    actualPlaceholderIdx = afterListField.split('_')[0];
                  }
                } else {
                  console.error('Could not find "' + searchStr + '" in name: ' + firstInputName);
                  window.__fhpfCopyInProgress = false;
                  return;
                }

                // Use the actual placeholder index from the name attribute
                const newPathPrefix = listFieldPath + '[' + actualPlaceholderIdx + ']';

                // Now perform the standard copy operation with the new path
                performStandardCopy(pathPrefix, newPathPrefix, sourcePrefix, copyTarget, accordionStates, currentPrefix, leftPrefix, rightPrefix);

                // Wait for copy to complete, then open accordion and highlight
                // Note: We skip automatic refresh because the temporary item ID doesn't persist after refresh
                // User can manually click the refresh button to update counts/summaries if needed
                const waitForCopyComplete = function() {
                  if (!window.__fhpfCopyInProgress) {
                    // Copy operation is complete, now open and highlight the new item
                    setTimeout(function() {
                      // Re-find the item (it might have been affected by accordion restoration)
                      const copiedItem = document.getElementById(newItem.id);

                      if (copiedItem && window.UIkit) {
                        // Open the newly created accordion item
                        if (!copiedItem.classList.contains('uk-open')) {
                          const accordionParent = copiedItem.parentElement;
                          if (accordionParent && accordionParent.hasAttribute('uk-accordion')) {
                            const accordionComponent = UIkit.accordion(accordionParent);
                            if (accordionComponent) {
                              const itemIndex = Array.from(accordionParent.children).indexOf(copiedItem);
                              accordionComponent.toggle(itemIndex, false);  // false = don't animate
                            }
                          } else {
                            // Manual fallback
                            copiedItem.classList.add('uk-open');
                            const content = copiedItem.querySelector('.uk-accordion-content');
                            if (content) {
                              content.hidden = false;
                              content.style.display = '';
                            }
                          }
                        }

                        // Apply visual highlight
                        setTimeout(function() {
                          copiedItem.style.transition = 'all 0.3s ease-in-out';
                          copiedItem.style.backgroundColor = '#dbeafe'; // Light blue background
                          copiedItem.style.borderLeft = '4px solid #3b82f6'; // Blue left border
                          copiedItem.style.borderRadius = '4px';

                          // Scroll into view
                          copiedItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

                          // Fade out the highlight after 3 seconds
                          setTimeout(function() {
                            copiedItem.style.backgroundColor = '';
                            copiedItem.style.borderLeft = '';
                            // Remove inline styles after transition
                            setTimeout(function() {
                              copiedItem.style.transition = '';
                              copiedItem.style.borderRadius = '';
                            }, 300);
                          }, 3000);
                        }, 100);
                      }
                    }, 100);
                  } else {
                    // Still in progress, check again in 50ms
                    setTimeout(waitForCopyComplete, 50);
                  }
                };

                // Start checking after a small delay
                setTimeout(waitForCopyComplete, 100);

              } else if (attempts < maxAttempts) {
                // Not ready yet, try again with exponential backoff
                setTimeout(checkAndCopy, delay);
              } else {
                console.error('Timeout: New list item not ready after ' + attempts + ' attempts');
                window.__fhpfCopyInProgress = false;
              }
            } else if (attempts < maxAttempts) {
              // Item not added yet, try again with exponential backoff
              setTimeout(checkAndCopy, delay);
            } else {
              console.error('Timeout: New list item not found after ' + attempts + ' attempts');
              window.__fhpfCopyInProgress = false;
            }
          };

          // Start checking after a short delay to allow HTMX to initiate
          setTimeout(checkAndCopy, 200);

          // Exit early - the checkAndCopy function will handle the rest
          return;
        } else {
          console.error('Could not find Add Item button for target list');
          window.__fhpfCopyInProgress = false;
          return;
        }
      } else {
        console.error('Could not find target list container');
        window.__fhpfCopyInProgress = false;
        return;
      }
    }

    // Non-list-item copy: standard behavior
    // (Handle full list copy with length alignment before performing copy)
    (function() {
      // Detect if this is a "full list copy" of a list field:
      // we treat it as a list if both sides have containers like "<prefix>_<path>_items_container"
      const baseIdPart = pathPrefix; // e.g. "addresses" or "key_features"
      const sourceContainerId = sourcePrefix.replace(/_$/, '') + '_' + baseIdPart + '_items_container';
      const targetContainerId = targetPrefix.replace(/_$/, '') + '_' + baseIdPart + '_items_container';

      const sourceListContainer = resolveById(sourceContainerId);
      const targetListContainer = resolveById(targetContainerId);

      // Only do length alignment if BOTH containers exist (i.e., this field is a list on both sides)
      if (sourceListContainer && targetListContainer) {
        const sourceCount = sourceListContainer.querySelectorAll(':scope > li').length;
        const targetCount = targetListContainer.querySelectorAll(':scope > li').length;

        // If source has more items, add missing ones BEFORE copying values (case 3)
        if (sourceCount > targetCount) {
          const addBtn = targetListContainer.parentElement.querySelector('button[hx-post*="/list/add/"]');
          if (addBtn) {
            const addUrl = addBtn.getAttribute('hx-post');
            const toAdd = sourceCount - targetCount;

            // Queue the required number of additions at the END
            // We'll use htmx.ajax with target=container and swap=beforeend
            // Then wait for HTMX to settle and for the DOM to reflect the new length.
            let added = 0;
            const addOne = function(cb) {
              htmx.ajax('POST', addUrl, {
                target: '#' + targetContainerId,
                swap: 'beforeend',
                values: htmxValues
              });
              added += 1;
              cb && cb();
            };

            // Fire additions synchronously; HTMX will queue them
            for (let i = 0; i < toAdd; i++) addOne();

            // Wait for afterSettle AND correct length, then perform the copy
            let attempts = 0, maxAttempts = 120; // ~6s @ 50ms backoff
            let settled = false;

            // Capture settle event once
            const onSettle = function onSettleOnce() {
              settled = true;
              document.body.removeEventListener('htmx:afterSettle', onSettleOnce);
            };
            document.body.addEventListener('htmx:afterSettle', onSettle);

            const waitAndCopy = function() {
              attempts++;
              const delay = Math.min(50 * Math.pow(1.15, attempts), 250);

              const currentCount = targetListContainer.querySelectorAll(':scope > li').length;
              if (settled && currentCount >= sourceCount) {
                // Proceed with list copy by DOM position
                performListCopyByPosition(sourceListContainer, targetListContainer, sourcePrefix, copyTarget, accordionStates, pathPrefix, leftPrefix, rightPrefix);
                return;
              }
              if (attempts >= maxAttempts) {
                console.error('Timeout aligning list lengths for full-list copy');
                // Still do a best-effort copy
                performListCopyByPosition(sourceListContainer, targetListContainer, sourcePrefix, copyTarget, accordionStates, pathPrefix, leftPrefix, rightPrefix);
                return;
              }
              setTimeout(waitAndCopy, delay);
            };

            setTimeout(waitAndCopy, 50);
            return; // Defer to waitAndCopy; don't fall through
          } else {
            console.warn('Full-list copy: add button not found on target; proceeding without length alignment.');
          }
        } else {
          // Source has same or fewer items - use position-based copy for lists
          performListCopyByPosition(sourceListContainer, targetListContainer, sourcePrefix, copyTarget, accordionStates, pathPrefix, leftPrefix, rightPrefix);
          return;
        }
      }

      // Default path (non-list fields or already aligned lists)
      performStandardCopy(pathPrefix, pathPrefix, sourcePrefix, copyTarget, accordionStates, currentPrefix, leftPrefix, rightPrefix);
    })();

  } catch (e) {
    window.__fhpfCopyInProgress = false;
    throw e;
  }
};

// Copy list items by DOM position (handles different indices in source/target)
function performListCopyByPosition(sourceListContainer, targetListContainer, sourcePrefix, copyTarget, accordionStates, listFieldPath, leftPrefix, rightPrefix) {
  try {
    const sourceItems = sourceListContainer.querySelectorAll(':scope > li');
    const targetItems = targetListContainer.querySelectorAll(':scope > li');
    const targetPrefix = (copyTarget === 'left') ? leftPrefix : rightPrefix;

    // Copy each source item to corresponding target item by position
    for (let i = 0; i < sourceItems.length && i < targetItems.length; i++) {
      const sourceItem = sourceItems[i];
      const targetItem = targetItems[i];

      // Find all inputs within this source item
      const sourceInputs = sourceItem.querySelectorAll('[data-field-path]');

      Array.from(sourceInputs).forEach(function(sourceInput) {
        const sourceFp = sourceInput.getAttribute('data-field-path');

        // Extract the field path relative to the list item
        // e.g., "addresses[0].street" -> ".street"
        // or "tags[0]" -> ""
        // Find the closing bracket after listFieldPath and extract what comes after
        const bracketStart = sourceFp.indexOf('[', listFieldPath.length);
        const bracketEnd = sourceFp.indexOf(']', bracketStart);
        const relativePath = (bracketEnd >= 0) ? sourceFp.substring(bracketEnd + 1) : '';

        // Find the corresponding input in the target item by looking for the same relative path
        const targetInputs = targetItem.querySelectorAll('[data-field-path]');
        let targetInput = null;

        for (let j = 0; j < targetInputs.length; j++) {
          let targetFp = targetInputs[j].getAttribute('data-field-path');
          const tBracketStart = targetFp.indexOf('[', listFieldPath.length);
          const tBracketEnd = targetFp.indexOf(']', tBracketStart);
          const targetRelativePath = (tBracketEnd >= 0) ? targetFp.substring(tBracketEnd + 1) : '';

          if (targetRelativePath === relativePath) {
            // Verify it belongs to the target form
            let candidateName = null;
            if (targetInputs[j].tagName === 'UK-SELECT') {
              const nativeSelect = targetInputs[j].querySelector('select');
              candidateName = nativeSelect ? nativeSelect.name : null;
            } else if (targetInputs[j].dataset.pillField === 'true') {
              // Pill containers (DIV elements) don't have a name attribute,
              // use their ID instead which contains the form prefix
              candidateName = targetInputs[j].id;
            } else {
              candidateName = targetInputs[j].name;
            }

            if (candidateName && !candidateName.startsWith(sourcePrefix)) {
              targetInput = targetInputs[j];
              break;
            }
          }
        }

        if (!targetInput) {
          return;
        }

        // Check if this is a pill field (List[Literal] or List[Enum])
        if (sourceInput.dataset.pillField === 'true' && targetInput.dataset.pillField === 'true') {
          // Use pill-aware copy logic (don't highlight each one individually during bulk copy)
          copyPillContainer(sourceInput, targetInput, false);
          return;
        }

        // Copy the value
        const tag = sourceInput.tagName.toUpperCase();
        const type = (sourceInput.type || '').toLowerCase();

        if (type === 'checkbox') {
          targetInput.checked = sourceInput.checked;
        } else if (tag === 'SELECT') {
          targetInput.value = sourceInput.value;
        } else if (tag === 'UK-SELECT') {
          const sourceNativeSelect = sourceInput.querySelector('select');
          const targetNativeSelect = targetInput.querySelector('select');
          if (sourceNativeSelect && targetNativeSelect) {
            const sourceValue = sourceNativeSelect.value;

            // Clear all selected attributes
            for (let k = 0; k < targetNativeSelect.options.length; k++) {
              targetNativeSelect.options[k].removeAttribute('selected');
              targetNativeSelect.options[k].selected = false;
            }

            // Find and set the matching option
            for (let k = 0; k < targetNativeSelect.options.length; k++) {
              if (targetNativeSelect.options[k].value === sourceValue) {
                targetNativeSelect.options[k].setAttribute('selected', 'selected');
                targetNativeSelect.options[k].selected = true;
                targetNativeSelect.selectedIndex = k;
                targetNativeSelect.value = sourceValue;
                break;
              }
            }

            // Update the button display
            const sourceButton = sourceInput.querySelector('button');
            const targetButton = targetInput.querySelector('button');
            if (sourceButton && targetButton) {
              targetButton.innerHTML = sourceButton.innerHTML;
            }
          }
        } else if (tag === 'TEXTAREA') {
          const valueToSet = sourceInput.value;
          targetInput.value = '';
          targetInput.textContent = '';
          targetInput.innerHTML = '';
          targetInput.value = valueToSet;
          targetInput.textContent = valueToSet;
          targetInput.innerHTML = valueToSet;
          targetInput.setAttribute('value', valueToSet);

          const inputEvent = new Event('input', { bubbles: true });
          const changeEvent = new Event('change', { bubbles: true });
          targetInput.dispatchEvent(inputEvent);
          targetInput.dispatchEvent(changeEvent);

          try {
            targetInput.focus();
            targetInput.blur();
          } catch (e) {
            // Ignore errors
          }
        } else {
          targetInput.value = sourceInput.value;
          targetInput.dispatchEvent(new Event('input', { bubbles: true }));
          targetInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    }

    // Remove excess items from target if source has fewer items
    for (let i = targetItems.length - 1; i >= sourceItems.length; i--) {
      targetItems[i].remove();
    }

    // Restore accordion states
    setTimeout(function() {
      accordionStates.forEach(function(state) {
        if (state.isOpen && !state.element.classList.contains('uk-open')) {
          const accordionParent = state.element.parentElement;
          if (accordionParent && window.UIkit) {
            const accordionComponent = UIkit.accordion(accordionParent);
            if (accordionComponent) {
              const itemIndex = Array.from(accordionParent.children).indexOf(state.element);
              accordionComponent.toggle(itemIndex, true);
            } else {
              state.element.classList.add('uk-open');
              const content = state.element.querySelector('.uk-accordion-content');
              if (content) {
                content.hidden = false;
                content.style.height = 'auto';
              }
            }
          }
        }
      });

      window.__fhpfCopyInProgress = false;

      // Trigger a refresh on the target list field to update counts and titles
      // Find the refresh button for the target list field
      const targetListFieldWrapper = targetListContainer.closest('[data-path]');
      if (targetListFieldWrapper) {
        const refreshButton = targetListFieldWrapper.querySelector('button[hx-post*="/refresh"]');
        if (refreshButton && window.htmx) {
          // Trigger the HTMX refresh
          htmx.trigger(refreshButton, 'click');
        }
      }
    }, 150);

  } catch (e) {
    window.__fhpfCopyInProgress = false;
    throw e;
  }
}

// Extracted standard copy logic to allow reuse
function performStandardCopy(sourcePathPrefix, targetPathPrefix, sourcePrefix, copyTarget, accordionStates, currentPrefix, leftPrefix, rightPrefix) {
  try {
    // Check if this is a pill field (List[Literal] or List[Enum])
    // Must find the container that belongs to the SOURCE form (by prefix)
    function normalizePrefix(prefix) {
      if (!prefix) return prefix;
      return prefix.replace(/\\./g, '_').replace(/_$/, '');
    }

    function findPillContainer(candidates, matchPrefix) {
      if (!matchPrefix) return null;
      const normalizedPrefix = normalizePrefix(matchPrefix);
      for (let i = 0; i < candidates.length; i++) {
        const candidate = candidates[i];
        const dataPrefix = candidate.dataset.inputPrefix;
        if (dataPrefix && dataPrefix === matchPrefix) {
          return candidate;
        }
        const candidateId = candidate.id;
        if (candidateId && normalizedPrefix && candidateId.startsWith(normalizedPrefix)) {
          return candidate;
        }
      }
      return null;
    }

    const targetBasePrefix = (copyTarget === 'left') ? leftPrefix : rightPrefix;
    const sourceMatchPrefix = currentPrefix || sourcePrefix;
    let targetMatchPrefix = targetBasePrefix;
    if (currentPrefix && sourcePrefix && currentPrefix.startsWith(sourcePrefix)) {
      targetMatchPrefix = targetBasePrefix + currentPrefix.substring(sourcePrefix.length);
    }

    const sourcePillCandidates = document.querySelectorAll(
      '[data-field-path="' + sourcePathPrefix + '"][data-pill-field="true"]'
    );
    const sourcePillContainer = findPillContainer(sourcePillCandidates, sourceMatchPrefix);

    if (sourcePillContainer) {
      // Find corresponding target pill container
      let targetPillContainer = null;

      // Find target by data-field-path that belongs to target form (not source)
      const pillCandidates = document.querySelectorAll('[data-field-path="' + targetPathPrefix + '"][data-pill-field="true"]');
      targetPillContainer = findPillContainer(pillCandidates, targetMatchPrefix);
      if (!targetPillContainer && sourcePillContainer && pillCandidates.length > 1) {
        for (let i = 0; i < pillCandidates.length; i++) {
          if (pillCandidates[i] !== sourcePillContainer) {
            targetPillContainer = pillCandidates[i];
            break;
          }
        }
      }

      if (targetPillContainer) {
        // Use the shared copyPillContainer helper
        copyPillContainer(sourcePillContainer, targetPillContainer, true);

        // Restore accordion states
        setTimeout(function() {
          accordionStates.forEach(function(state) {
            if (state.isOpen && !state.element.classList.contains('uk-open')) {
              state.element.classList.add('uk-open');
              const content = state.element.querySelector('.uk-accordion-content');
              if (content) {
                content.hidden = false;
                content.style.height = 'auto';
              }
            }
          });
          window.__fhpfCopyInProgress = false;
        }, 100);

        return; // Pill copy complete
      }
    }

    // Find all inputs with matching data-field-path from source
    const allInputs = document.querySelectorAll('[data-field-path]');
    const sourceInputs = Array.from(allInputs).filter(function(el) {
      const fp = el.getAttribute('data-field-path');
      if (!(fp === sourcePathPrefix || fp.startsWith(sourcePathPrefix + '.') || fp.startsWith(sourcePathPrefix + '['))) {
        return false;
      }

      // Check if this element belongs to the source form
      let elementName = null;
      if (el.tagName === 'UK-SELECT') {
        const nativeSelect = el.querySelector('select');
        elementName = nativeSelect ? nativeSelect.name : null;
      } else {
        elementName = el.name;
      }

      return elementName && elementName.startsWith(sourcePrefix);
    });

    // Track updated selects to fire change events later
    const updatedSelects = [];

    let copiedCount = 0;
    sourceInputs.forEach(function(sourceInput) {
      const sourceFp = sourceInput.getAttribute('data-field-path');

      // Map source field path to target field path
      // If sourcePathPrefix != targetPathPrefix (list item case), we need to remap
      let targetFp = sourceFp;
      if (sourcePathPrefix !== targetPathPrefix) {
        // Replace the source path prefix with target path prefix
        if (sourceFp === sourcePathPrefix) {
          targetFp = targetPathPrefix;
        } else if (sourceFp.startsWith(sourcePathPrefix + '.')) {
          targetFp = targetPathPrefix + sourceFp.substring(sourcePathPrefix.length);
        } else if (sourceFp.startsWith(sourcePathPrefix + '[')) {
          targetFp = targetPathPrefix + sourceFp.substring(sourcePathPrefix.length);
        }
      }

      // Find target by data-field-path, then verify it's NOT from the source form
      const candidates = document.querySelectorAll('[data-field-path="' + targetFp + '"]');
      let targetInput = null;
      for (let i = 0; i < candidates.length; i++) {
        const candidate = candidates[i];
        let candidateName = null;
        if (candidate.tagName === 'UK-SELECT') {
          const nativeSelect = candidate.querySelector('select');
          candidateName = nativeSelect ? nativeSelect.name : null;
        } else if (candidate.dataset.pillField === 'true') {
          // Pill containers (DIV elements) don't have a name attribute,
          // use their ID instead which contains the form prefix
          candidateName = candidate.id;
        } else {
          candidateName = candidate.name;
        }
        if (candidateName && !candidateName.startsWith(sourcePrefix)) {
          targetInput = candidate;
          break;
        }
      }

      if (!targetInput) {
        return;
      }

      // Check if this is a pill field (List[Literal] or List[Enum])
      if (sourceInput.dataset.pillField === 'true' && targetInput.dataset.pillField === 'true') {
        // Use pill-aware copy logic
        copyPillContainer(sourceInput, targetInput, true);
        copiedCount++;
        return;
      }

      const tag = sourceInput.tagName.toUpperCase();
      const type = (sourceInput.type || '').toLowerCase();

      if (type === 'checkbox') {
        targetInput.checked = sourceInput.checked;
      } else if (tag === 'SELECT') {
        targetInput.value = sourceInput.value;
        updatedSelects.push(targetInput);
      } else if (tag === 'UK-SELECT') {
        const sourceNativeSelect = sourceInput.querySelector('select');
        const targetNativeSelect = targetInput.querySelector('select');
        if (sourceNativeSelect && targetNativeSelect) {
          const sourceValue = sourceNativeSelect.value;

          // First, clear all selected attributes
          for (let optIdx = 0; optIdx < targetNativeSelect.options.length; optIdx++) {
            targetNativeSelect.options[optIdx].removeAttribute('selected');
            targetNativeSelect.options[optIdx].selected = false;
          }

          // Find and set the matching option
          for (let optIdx = 0; optIdx < targetNativeSelect.options.length; optIdx++) {
            if (targetNativeSelect.options[optIdx].value === sourceValue) {
              targetNativeSelect.options[optIdx].setAttribute('selected', 'selected');
              targetNativeSelect.options[optIdx].selected = true;
              targetNativeSelect.selectedIndex = optIdx;
              targetNativeSelect.value = sourceValue;
              break;
            }
          }

          // Update the button display
          const sourceButton = sourceInput.querySelector('button');
          const targetButton = targetInput.querySelector('button');
          if (sourceButton && targetButton) {
            targetButton.innerHTML = sourceButton.innerHTML;
          }

          // Track this select for later event firing
          updatedSelects.push(targetNativeSelect);
        }
      } else if (tag === 'TEXTAREA') {
        // Set value multiple ways to ensure it sticks
        const valueToSet = sourceInput.value;

        // First, completely clear the textarea
        targetInput.value = '';
        targetInput.textContent = '';
        targetInput.innerHTML = '';

        // Then set the new value
        // Method 1: Set value property
        targetInput.value = valueToSet;

        // Method 2: Set textContent
        targetInput.textContent = valueToSet;

        // Method 3: Set innerHTML
        targetInput.innerHTML = valueToSet;

        // Method 4: Use setAttribute
        targetInput.setAttribute('value', valueToSet);

        // Trigger input and change events to notify any UI components
        const inputEvent = new Event('input', { bubbles: true });
        const changeEvent = new Event('change', { bubbles: true });
        targetInput.dispatchEvent(inputEvent);
        targetInput.dispatchEvent(changeEvent);

        // Force browser to re-render by triggering focus events
        try {
          targetInput.focus();
          targetInput.blur();
        } catch (e) {
          // Ignore errors if focus/blur not supported
        }

        copiedCount++;
      } else {
        targetInput.value = sourceInput.value;
        // Trigger events for any UI framework listening
        targetInput.dispatchEvent(new Event('input', { bubbles: true }));
        targetInput.dispatchEvent(new Event('change', { bubbles: true }));
        copiedCount++;
      }
    });

    // Handle list cleanup - remove excess items from target list
    // Only do this when copying a whole list field (not individual items)
    // Check if this is a list field by looking for a list container
    if (sourcePathPrefix && !sourcePathPrefix.includes('[') && sourcePathPrefix === targetPathPrefix) {
      // This is a top-level field (not a list item), check if it's a list field
      // Try to find list containers for both source and target
      const targetPrefix = (copyTarget === 'left') ? leftPrefix : rightPrefix;

      // Build container ID patterns - handle both with and without trailing underscore
      const sourceContainerIdPattern = sourcePrefix.replace(/_$/, '') + '_' + sourcePathPrefix + '_items_container';
      const targetContainerIdPattern = targetPrefix.replace(/_$/, '') + '_' + targetPathPrefix + '_items_container';

      const sourceListContainer = document.getElementById(sourceContainerIdPattern);
      const targetListContainer = document.getElementById(targetContainerIdPattern);

      if (sourceListContainer && targetListContainer) {
        // Both containers exist, this is a list field
        // Count list items in source and target
        const sourceItemCount = sourceListContainer.querySelectorAll(':scope > li').length;
        const targetItems = targetListContainer.querySelectorAll(':scope > li');

        // Remove excess items from target (from end backwards)
        for (let i = targetItems.length - 1; i >= sourceItemCount; i--) {
          targetItems[i].remove();
        }
      }
    }

    // Restore accordion states after a brief delay
    setTimeout(function() {
      accordionStates.forEach(function(state) {
        if (state.isOpen && !state.element.classList.contains('uk-open')) {
          // Use UIkit's toggle API to properly open the accordion
          const accordionParent = state.element.parentElement;
          if (accordionParent && window.UIkit) {
            const accordionComponent = UIkit.accordion(accordionParent);
            if (accordionComponent) {
              const itemIndex = Array.from(accordionParent.children).indexOf(state.element);
              accordionComponent.toggle(itemIndex, true);
            } else {
              // Fallback to manual class manipulation
              state.element.classList.add('uk-open');
              const content = state.element.querySelector('.uk-accordion-content');
              if (content) {
                content.hidden = false;
                content.style.height = 'auto';
              }
            }
          }
        }
      });

      window.__fhpfCopyInProgress = false;

      // Fire change events on updated selects AFTER accordion restoration
      setTimeout(function() {
        updatedSelects.forEach(function(select) {
          select.dispatchEvent(new Event('change', { bubbles: true }));
        });
      }, 50);
    }, 150);

  } catch (e) {
    window.__fhpfCopyInProgress = false;
    throw e;
  }
}

window.fhpfInitComparisonSync = function initComparisonSync(){
  // 1) Wait until UIkit and its util are available
  if (!window.UIkit || !UIkit.util) {
    return setTimeout(initComparisonSync, 50);
  }

  // Fix native select name attributes (MonsterUI puts name on uk-select, not native select)
  // IMPORTANT: Remove name from uk-select to avoid duplicate form submission
  document.querySelectorAll('uk-select[name]').forEach(function(ukSelect) {
    const nativeSelect = ukSelect.querySelector('select');
    if (nativeSelect) {
      const ukSelectName = ukSelect.getAttribute('name');
      if (!nativeSelect.name && ukSelectName) {
        nativeSelect.name = ukSelectName;
        // Remove name from uk-select to prevent duplicate submission
        ukSelect.removeAttribute('name');
      }
    }
  });


  // 2) Sync top-level accordions (BaseModelFieldRenderer)
  UIkit.util.on(
    document,
    'show hide',                  // UIkit fires plain 'show'/'hide'
    'ul[uk-accordion] > li',      // only the top-level items
    mirrorTopLevel
  );

  function mirrorTopLevel(ev) {
    const sourceLi = ev.target.closest('li');
    if (!sourceLi) return;

    // Skip if copy operation is in progress
    if (window.__fhpfCopyInProgress) {
      return;
    }

    // Skip if this event is from a select/dropdown element
    if (ev.target.closest('uk-select, select, [uk-select]')) {
      return;
    }

    // Skip if this is a nested list item (let mirrorNestedListItems handle it)
    if (sourceLi.closest('[id$="_items_container"]')) {
      return;
    }

    // Find our grid-cell wrapper (both left & right share the same data-path)
    const cell = sourceLi.closest('[data-path]');
    if (!cell) return;
    let path = cell.dataset.path;
    const grid = cell.closest('[data-fhpf-compare-grid="true"]');
    const scope = grid || document;

    // Determine index of this <li> inside its <ul>
    const idx     = Array.prototype.indexOf.call(
      sourceLi.parentElement.children,
      sourceLi
    );
    const opening = ev.type === 'show';

    // Mirror on the other side
    scope
      .querySelectorAll(`[data-path="${path}"]`)
      .forEach(peerCell => {
        if (peerCell === cell) return;

        const peerAcc = peerCell.querySelector('ul[uk-accordion]');
        if (!peerAcc || idx >= peerAcc.children.length) return;

        const peerLi      = peerAcc.children[idx];
        const peerContent = peerLi.querySelector('.uk-accordion-content');

        if (opening) {
          peerLi.classList.add('uk-open');
          if (peerContent) {
            peerContent.hidden = false;
            peerContent.style.height = 'auto';
          }
        } else {
          peerLi.classList.remove('uk-open');
          if (peerContent) {
            peerContent.hidden = true;
          }
        }
      });
  }

  // 3) Sync nested list item accordions (individual items within lists)
  UIkit.util.on(
    document,
    'show hide',
    '[id$="_items_container"] > li',  // only list items within items containers
    mirrorNestedListItems
  );

  function mirrorNestedListItems(ev) {
    const sourceLi = ev.target.closest('li');
    if (!sourceLi) return;

    // Skip if copy operation is in progress
    if (window.__fhpfCopyInProgress) {
      return;
    }

    // Skip if this event is from a select/dropdown element
    if (ev.target.closest('uk-select, select, [uk-select]')) {
      return;
    }

    // Skip if this event was triggered by our own sync
    if (sourceLi.dataset.syncDisabled) {
      return;
    }

    // Find the list container (items_container) that contains this item
    const listContainer = sourceLi.closest('[id$="_items_container"]');
    if (!listContainer) return;

    // Find the grid cell wrapper with data-path
    const cell = listContainer.closest('[data-path]');
    if (!cell) return;
    let path = cell.dataset.path;
    const grid = cell.closest('[data-fhpf-compare-grid="true"]');
    const scope = grid || document;

    // Determine index of this <li> within its list container
    const listAccordion = sourceLi.parentElement;
    const idx = Array.prototype.indexOf.call(listAccordion.children, sourceLi);
    const opening = ev.type === 'show';

    // Mirror on the other side
    scope
      .querySelectorAll(`[data-path="${path}"]`)
      .forEach(peerCell => {
        if (peerCell === cell) return;

        // Find the peer's list container
        const peerListContainer = peerCell.querySelector('[id$="_items_container"]');
        if (!peerListContainer) return;

        // The list container IS the accordion itself (not a wrapper around it)
        let peerListAccordion;
        if (peerListContainer.hasAttribute('uk-accordion') && peerListContainer.tagName === 'UL') {
          peerListAccordion = peerListContainer;
        } else {
          peerListAccordion = peerListContainer.querySelector('ul[uk-accordion]');
        }
        
        if (!peerListAccordion || idx >= peerListAccordion.children.length) return;

        const peerLi = peerListAccordion.children[idx];
        const peerContent = peerLi.querySelector('.uk-accordion-content');

        // Prevent event cascading by temporarily disabling our own event listener
        if (peerLi.dataset.syncDisabled) {
          return;
        }

        // Mark this item as being synced to prevent loops
        peerLi.dataset.syncDisabled = 'true';

        // Check current state and only sync if different
        const currentlyOpen = peerLi.classList.contains('uk-open');
        
        if (currentlyOpen !== opening) {
          if (opening) {
            peerLi.classList.add('uk-open');
            if (peerContent) {
              peerContent.hidden = false;
              peerContent.style.height = 'auto';
            }
          } else {
            peerLi.classList.remove('uk-open');
            if (peerContent) {
              peerContent.hidden = true;
            }
          }
        }

        // Re-enable sync after a short delay
        setTimeout(() => {
          delete peerLi.dataset.syncDisabled;
        }, 100);
      });
  }

  // 4) Wrap the list-toggle so ListFieldRenderer accordions sync too
  if (typeof window.toggleListItems === 'function' && !window.__listSyncWrapped) {
    // guard to only wrap once
    window.__listSyncWrapped = true;
    const originalToggle = window.toggleListItems;

    window.toggleListItems = function(containerId) {
      // a) Toggle this column first
      originalToggle(containerId);

      // b) Find the enclosing data-path
      const container = document.getElementById(containerId);
      if (!container) return;
      const cell = container.closest('[data-path]');
      if (!cell) return;
      let path = cell.dataset.path;
      const grid = cell.closest('[data-fhpf-compare-grid="true"]');
      const scope = grid || document;

      // c) Find the peer's list-container by suffix match
      scope
        .querySelectorAll(`[data-path="${path}"]`)
        .forEach(peerCell => {
          if (peerCell === cell) return;

          // look up any [id$="_items_container"]
          const peerContainer = peerCell.querySelector('[id$="_items_container"]');
          if (peerContainer) {
            originalToggle(peerContainer.id);
          }
        });
    };
  }
};

// Initial run
window.fhpfInitComparisonSync();

// Re-run after HTMX swaps to maintain sync
document.addEventListener('htmx:afterSwap', function(event) {
  window.fhpfInitComparisonSync();
});