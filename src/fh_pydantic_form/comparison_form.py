"""
ComparisonForm - Side-by-side form comparison with metrics visualization

This module provides a meta-renderer that displays two PydanticForm instances
side-by-side with visual comparison feedback and synchronized accordion states.
"""

import json
import logging
import re
from copy import deepcopy
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

import fasthtml.common as fh
import monsterui.all as mui
from fastcore.xml import FT
from pydantic import BaseModel

from fh_pydantic_form.constants import (
    ATTR_COMPARE_GRID,
    ATTR_COMPARE_NAME,
    ATTR_LEFT_PREFIX,
    ATTR_RIGHT_PREFIX,
)
from fh_pydantic_form.form_renderer import PydanticForm
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import (
    MetricEntry,
    MetricsDict,
    _is_skip_json_schema_field,
)

logger = logging.getLogger(__name__)

# TypeVar for generic model typing
ModelType = TypeVar("ModelType", bound=BaseModel)


def comparison_form_js():
    """JavaScript for comparison: sync accordions and handle JS-only copy operations."""
    return fh.Script(r"""
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
      constbracketStart = pathPrefix.indexOf('[', listFieldPath.length);
      constbracketEnd = pathPrefix.indexOf(']', bracketStart);
      constrelativePath = (bracketEnd >= 0) ? pathPrefix.substring(bracketEnd + 1) : '';

      // Find source and target list containers to map by position
      constsourceContainerId = sourcePrefix.replace(/_$/, '') + '_' + listFieldPath + '_items_container';
      consttargetContainerId = targetPrefix.replace(/_$/, '') + '_' + listFieldPath + '_items_container';

      constsourceListContainer = resolveById(sourceContainerId);
      consttargetListContainer = resolveById(targetContainerId);

      if (sourceListContainer && targetListContainer) {
        constsourceItems = sourceListContainer.querySelectorAll(':scope > li');
        consttargetItems = targetListContainer.querySelectorAll(':scope > li');

        // Find the position of the source item
        constsourcePosition = -1;
        if (typeof listIndex === 'number') {
          sourcePosition = listIndex;
        } else if (typeof listIndex === 'string' && listIndex.startsWith('new_')) {
          // For placeholder indices, find by searching for the element with this path
          for (let i = 0; i < sourceItems.length; i++) {
            constinputs = sourceItems[i].querySelectorAll('[data-field-path^="' + pathPrefix.replace(/\.[^.]+$/, '') + '"]');
            if (inputs.length > 0) {
              sourcePosition = i;
              break;
            }
          }
        }

        // If we found a valid source position and target has that position, perform the copy
        if (sourcePosition >= 0 && sourcePosition < targetItems.length) {
          constsourceItem = sourceItems[sourcePosition];
          consttargetItem = targetItems[sourcePosition];

          // Find the source input with this exact path
          constsourceInput = sourceItem.querySelector('[data-field-path="' + pathPrefix + '"]');

          // Find the target input with matching relative path
          consttargetInputs = targetItem.querySelectorAll('[data-field-path]');
          consttargetInput = null;

          for (let j = 0; j < targetInputs.length; j++) {
            consttargetFp = targetInputs[j].getAttribute('data-field-path');
            consttBracketStart = targetFp.indexOf('[', listFieldPath.length);
            consttBracketEnd = targetFp.indexOf(']', tBracketStart);
            consttargetRelative = (tBracketEnd >= 0) ? targetFp.substring(tBracketEnd + 1) : '';

            if (targetRelative === relativePath) {
              // Verify it belongs to target form
              constcandidateName = null;
              if (targetInputs[j].tagName === 'UK-SELECT') {
                constnativeSelect = targetInputs[j].querySelector('select');
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
                    constcontent = state.element.querySelector('.uk-accordion-content');
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
            consttag = sourceInput.tagName.toUpperCase();
            consttype = (sourceInput.type || '').toLowerCase();

            if (type === 'checkbox') {
              targetInput.checked = sourceInput.checked;
            } else if (tag === 'SELECT') {
              targetInput.value = sourceInput.value;
              targetInput.dispatchEvent(new Event('change', { bubbles: true }));
            } else if (tag === 'UK-SELECT') {
              constsrcSelect = sourceInput.querySelector('select');
              consttgtSelect = targetInput.querySelector('select');
              if (srcSelect && tgtSelect) {
                constsrcVal = srcSelect.value;
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
                constsrcBtn = sourceInput.querySelector('button');
                consttgtBtn = targetInput.querySelector('button');
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
            constcontent = state.element.querySelector('.uk-accordion-content');
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
      consttargetContainerId = targetPrefix.replace(/_$/, '') + '_' + listFieldPath + '_items_container';
      consttargetContainer = resolveById(targetContainerId);

      if (targetContainer) {
        // Find the "Add Item" button for the target list
        consttargetAddButton = targetContainer.parentElement.querySelector('button[hx-post*="/list/add/"]');

        if (targetAddButton) {
          // Capture the target list items BEFORE adding the new one
          consttargetListItemsBeforeAdd = Array.from(targetContainer.querySelectorAll(':scope > li'));
          consttargetLengthBefore = targetListItemsBeforeAdd.length;

          // Determine the target position: insert after the source item's index, or at end if target is shorter
          constsourceIndex = listIndex;  // The index from the source path (e.g., reviews[2] -> 2)
          constinsertAfterIndex = Math.min(sourceIndex, targetLengthBefore - 1);

          // Get the URL from the add button
          constaddUrl = targetAddButton.getAttribute('hx-post');

          // Determine the insertion point
          constinsertBeforeElement = null;
          if (insertAfterIndex >= 0 && insertAfterIndex < targetLengthBefore - 1) {
            // Insert after insertAfterIndex, which means before insertAfterIndex+1
            insertBeforeElement = targetListItemsBeforeAdd[insertAfterIndex + 1];
          } else if (targetLengthBefore > 0) {
            // Insert at the end: use afterend on the last item
            insertBeforeElement = targetListItemsBeforeAdd[targetLengthBefore - 1];
          }

          // Make the HTMX request with custom swap target
          if (insertBeforeElement) {
            constswapStrategy = (insertAfterIndex >= targetLengthBefore - 1) ? 'afterend' : 'beforebegin';
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
          constcopyCompleted = false;
          consthtmxSettled = false;
          constnewlyAddedElement = null;

          // Listen for HTMX afterSwap event on the container to capture the newly added element
          targetContainer.addEventListener('htmx:afterSwap', function onSwap(evt) {
            // Parse the response to get the new element's ID
            consttempDiv = document.createElement('div');
            tempDiv.innerHTML = evt.detail.xhr.response;
            constnewElement = tempDiv.firstElementChild;
            if (newElement && newElement.id) {
              newlyAddedElement = newElement;
            }
          }, { once: true });

          // Listen for HTMX afterSettle event
          document.body.addEventListener('htmx:afterSettle', function onSettle(evt) {
            htmxSettled = true;
            document.body.removeEventListener('htmx:afterSettle', onSettle);
          }, { once: true });

          constmaxAttempts = 100; // 100 attempts with exponential backoff = ~10 seconds total
          constattempts = 0;

          constcheckAndCopy = function() {
            attempts++;

            // Calculate delay with exponential backoff: 50ms, 50ms, 100ms, 100ms, 200ms, ...
            constdelay = Math.min(50 * Math.pow(2, Math.floor(attempts / 2)), 500);

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
            consttargetItems = targetContainer.querySelectorAll(':scope > li');
            constnewItem = null;
            constnewItemIndex = -1;

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
              constnewItemInputs = newItem.querySelectorAll('[data-field-path]');

              if (newItemInputs.length > 0) {
                // New item is ready, now copy values from source item
                copyCompleted = true;

                // The new item might not contain the textarea with placeholder!
                // Search the entire target container for the newest textarea with "new_" in the name
                constallInputsInContainer = targetContainer.querySelectorAll('[data-field-path^="' + listFieldPath + '["]');

                constfirstInput = null;
                constnewestTimestamp = 0;

                for (let i = 0; i < allInputsInContainer.length; i++) {
                  constinputName = allInputsInContainer[i].name || allInputsInContainer[i].id;
                  if (inputName && inputName.startsWith(targetPrefix.replace(/_$/, '') + '_' + listFieldPath + '_new_')) {
                    // Extract timestamp from name
                    constmatch = inputName.match(/new_(\d+)/);
                    if (match) {
                      consttimestamp = parseInt(match[1]);
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

                constfirstInputPath = firstInput.getAttribute('data-field-path');
                constfirstInputName = firstInput.name || firstInput.id;

                // Extract placeholder from name
                // Pattern: "prefix_listfield_PLACEHOLDER" or "prefix_listfield_PLACEHOLDER_fieldname"
                // For simple list items: "annotated_truth_key_features_new_123"
                // For BaseModel list items: "annotated_truth_reviews_new_123_rating"
                // We want just the placeholder part (new_123)
                constsearchStr = '_' + listFieldPath + '_';
                constidx = firstInputName.indexOf(searchStr);
                constactualPlaceholderIdx = null;

                if (idx >= 0) {
                  constafterListField = firstInputName.substring(idx + searchStr.length);

                  // For BaseModel items with nested fields, the placeholder is between listfield and the next underscore
                  // Check if this looks like a nested field by checking if there's another underscore after "new_"
                  if (afterListField.startsWith('new_')) {
                    // Extract just "new_TIMESTAMP" part - stop at the next underscore after the timestamp
                    constparts = afterListField.split('_');
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
                constnewPathPrefix = listFieldPath + '[' + actualPlaceholderIdx + ']';

                // Now perform the standard copy operation with the new path
                performStandardCopy(pathPrefix, newPathPrefix, sourcePrefix, copyTarget, accordionStates, currentPrefix, leftPrefix, rightPrefix);

                // Wait for copy to complete, then open accordion and highlight
                // Note: We skip automatic refresh because the temporary item ID doesn't persist after refresh
                // User can manually click the refresh button to update counts/summaries if needed
                constwaitForCopyComplete = function() {
                  if (!window.__fhpfCopyInProgress) {
                    // Copy operation is complete, now open and highlight the new item
                    setTimeout(function() {
                      // Re-find the item (it might have been affected by accordion restoration)
                      constcopiedItem = document.getElementById(newItem.id);

                      if (copiedItem && window.UIkit) {
                        // Open the newly created accordion item
                        if (!copiedItem.classList.contains('uk-open')) {
                          constaccordionParent = copiedItem.parentElement;
                          if (accordionParent && accordionParent.hasAttribute('uk-accordion')) {
                            constaccordionComponent = UIkit.accordion(accordionParent);
                            if (accordionComponent) {
                              constitemIndex = Array.from(accordionParent.children).indexOf(copiedItem);
                              accordionComponent.toggle(itemIndex, false);  // false = don't animate
                            }
                          } else {
                            // Manual fallback
                            copiedItem.classList.add('uk-open');
                            constcontent = copiedItem.querySelector('.uk-accordion-content');
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
      constbaseIdPart = pathPrefix; // e.g. "addresses" or "key_features"
      constsourceContainerId = sourcePrefix.replace(/_$/, '') + '_' + baseIdPart + '_items_container';
      consttargetContainerId = targetPrefix.replace(/_$/, '') + '_' + baseIdPart + '_items_container';

      constsourceListContainer = resolveById(sourceContainerId);
      consttargetListContainer = resolveById(targetContainerId);

      // Only do length alignment if BOTH containers exist (i.e., this field is a list on both sides)
      if (sourceListContainer && targetListContainer) {
        constsourceCount = sourceListContainer.querySelectorAll(':scope > li').length;
        consttargetCount = targetListContainer.querySelectorAll(':scope > li').length;

        // If source has more items, add missing ones BEFORE copying values (case 3)
        if (sourceCount > targetCount) {
          constaddBtn = targetListContainer.parentElement.querySelector('button[hx-post*="/list/add/"]');
          if (addBtn) {
            constaddUrl = addBtn.getAttribute('hx-post');
            consttoAdd = sourceCount - targetCount;

            // Queue the required number of additions at the END
            // We'll use htmx.ajax with target=container and swap=beforeend
            // Then wait for HTMX to settle and for the DOM to reflect the new length.
            constadded = 0;
            constaddOne = function(cb) {
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
            constattempts = 0, maxAttempts = 120; // ~6s @ 50ms backoff
            constsettled = false;

            // Capture settle event once
            constonSettle = function onSettleOnce() {
              settled = true;
              document.body.removeEventListener('htmx:afterSettle', onSettleOnce);
            };
            document.body.addEventListener('htmx:afterSettle', onSettle);

            constwaitAndCopy = function() {
              attempts++;
              constdelay = Math.min(50 * Math.pow(1.15, attempts), 250);

              constcurrentCount = targetListContainer.querySelectorAll(':scope > li').length;
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
    constsourceItems = sourceListContainer.querySelectorAll(':scope > li');
    consttargetItems = targetListContainer.querySelectorAll(':scope > li');
    consttargetPrefix = (copyTarget === 'left') ? leftPrefix : rightPrefix;

    // Copy each source item to corresponding target item by position
    for (let i = 0; i < sourceItems.length && i < targetItems.length; i++) {
      constsourceItem = sourceItems[i];
      consttargetItem = targetItems[i];

      // Find all inputs within this source item
      constsourceInputs = sourceItem.querySelectorAll('[data-field-path]');

      Array.from(sourceInputs).forEach(function(sourceInput) {
        constsourceFp = sourceInput.getAttribute('data-field-path');

        // Extract the field path relative to the list item
        // e.g., "addresses[0].street" -> ".street"
        // or "tags[0]" -> ""
        // Find the closing bracket after listFieldPath and extract what comes after
        constbracketStart = sourceFp.indexOf('[', listFieldPath.length);
        constbracketEnd = sourceFp.indexOf(']', bracketStart);
        constrelativePath = (bracketEnd >= 0) ? sourceFp.substring(bracketEnd + 1) : '';

        // Find the corresponding input in the target item by looking for the same relative path
        consttargetInputs = targetItem.querySelectorAll('[data-field-path]');
        consttargetInput = null;

        for (let j = 0; j < targetInputs.length; j++) {
          consttargetFp = targetInputs[j].getAttribute('data-field-path');
          consttBracketStart = targetFp.indexOf('[', listFieldPath.length);
          consttBracketEnd = targetFp.indexOf(']', tBracketStart);
          consttargetRelativePath = (tBracketEnd >= 0) ? targetFp.substring(tBracketEnd + 1) : '';

          if (targetRelativePath === relativePath) {
            // Verify it belongs to the target form
            constcandidateName = null;
            if (targetInputs[j].tagName === 'UK-SELECT') {
              constnativeSelect = targetInputs[j].querySelector('select');
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
        consttag = sourceInput.tagName.toUpperCase();
        consttype = (sourceInput.type || '').toLowerCase();

        if (type === 'checkbox') {
          targetInput.checked = sourceInput.checked;
        } else if (tag === 'SELECT') {
          targetInput.value = sourceInput.value;
        } else if (tag === 'UK-SELECT') {
          constsourceNativeSelect = sourceInput.querySelector('select');
          consttargetNativeSelect = targetInput.querySelector('select');
          if (sourceNativeSelect && targetNativeSelect) {
            constsourceValue = sourceNativeSelect.value;

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
            constsourceButton = sourceInput.querySelector('button');
            consttargetButton = targetInput.querySelector('button');
            if (sourceButton && targetButton) {
              targetButton.innerHTML = sourceButton.innerHTML;
            }
          }
        } else if (tag === 'TEXTAREA') {
          constvalueToSet = sourceInput.value;
          targetInput.value = '';
          targetInput.textContent = '';
          targetInput.innerHTML = '';
          targetInput.value = valueToSet;
          targetInput.textContent = valueToSet;
          targetInput.innerHTML = valueToSet;
          targetInput.setAttribute('value', valueToSet);

          constinputEvent = new Event('input', { bubbles: true });
          constchangeEvent = new Event('change', { bubbles: true });
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
          constaccordionParent = state.element.parentElement;
          if (accordionParent && window.UIkit) {
            constaccordionComponent = UIkit.accordion(accordionParent);
            if (accordionComponent) {
              constitemIndex = Array.from(accordionParent.children).indexOf(state.element);
              accordionComponent.toggle(itemIndex, true);
            } else {
              state.element.classList.add('uk-open');
              constcontent = state.element.querySelector('.uk-accordion-content');
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
      consttargetListFieldWrapper = targetListContainer.closest('[data-path]');
      if (targetListFieldWrapper) {
        constrefreshButton = targetListFieldWrapper.querySelector('button[hx-post*="/refresh"]');
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
      constnormalizedPrefix = normalizePrefix(matchPrefix);
      for (let i = 0; i < candidates.length; i++) {
        constcandidate = candidates[i];
        constdataPrefix = candidate.dataset.inputPrefix;
        if (dataPrefix && dataPrefix === matchPrefix) {
          return candidate;
        }
        constcandidateId = candidate.id;
        if (candidateId && normalizedPrefix && candidateId.startsWith(normalizedPrefix)) {
          return candidate;
        }
      }
      return null;
    }

    consttargetBasePrefix = (copyTarget === 'left') ? leftPrefix : rightPrefix;
    constsourceMatchPrefix = currentPrefix || sourcePrefix;
    consttargetMatchPrefix = targetBasePrefix;
    if (currentPrefix && sourcePrefix && currentPrefix.startsWith(sourcePrefix)) {
      targetMatchPrefix = targetBasePrefix + currentPrefix.substring(sourcePrefix.length);
    }

    constsourcePillCandidates = document.querySelectorAll(
      '[data-field-path="' + sourcePathPrefix + '"][data-pill-field="true"]'
    );
    constsourcePillContainer = findPillContainer(sourcePillCandidates, sourceMatchPrefix);

    if (sourcePillContainer) {
      // Find corresponding target pill container
      consttargetPillContainer = null;

      // Find target by data-field-path that belongs to target form (not source)
      constpillCandidates = document.querySelectorAll('[data-field-path="' + targetPathPrefix + '"][data-pill-field="true"]');
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
              constcontent = state.element.querySelector('.uk-accordion-content');
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
    constallInputs = document.querySelectorAll('[data-field-path]');
    constsourceInputs = Array.from(allInputs).filter(function(el) {
      constfp = el.getAttribute('data-field-path');
      if (!(fp === sourcePathPrefix || fp.startsWith(sourcePathPrefix + '.') || fp.startsWith(sourcePathPrefix + '['))) {
        return false;
      }

      // Check if this element belongs to the source form
      constelementName = null;
      if (el.tagName === 'UK-SELECT') {
        constnativeSelect = el.querySelector('select');
        elementName = nativeSelect ? nativeSelect.name : null;
      } else {
        elementName = el.name;
      }

      return elementName && elementName.startsWith(sourcePrefix);
    });

    // Track updated selects to fire change events later
    constupdatedSelects = [];

    constcopiedCount = 0;
    sourceInputs.forEach(function(sourceInput) {
      constsourceFp = sourceInput.getAttribute('data-field-path');

      // Map source field path to target field path
      // If sourcePathPrefix != targetPathPrefix (list item case), we need to remap
      consttargetFp = sourceFp;
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
      constcandidates = document.querySelectorAll('[data-field-path="' + targetFp + '"]');
      consttargetInput = null;
      for (let i = 0; i < candidates.length; i++) {
        constcandidate = candidates[i];
        constcandidateName = null;
        if (candidate.tagName === 'UK-SELECT') {
          constnativeSelect = candidate.querySelector('select');
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

      consttag = sourceInput.tagName.toUpperCase();
      consttype = (sourceInput.type || '').toLowerCase();

      if (type === 'checkbox') {
        targetInput.checked = sourceInput.checked;
      } else if (tag === 'SELECT') {
        targetInput.value = sourceInput.value;
        updatedSelects.push(targetInput);
      } else if (tag === 'UK-SELECT') {
        constsourceNativeSelect = sourceInput.querySelector('select');
        consttargetNativeSelect = targetInput.querySelector('select');
        if (sourceNativeSelect && targetNativeSelect) {
          constsourceValue = sourceNativeSelect.value;

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
          constsourceButton = sourceInput.querySelector('button');
          consttargetButton = targetInput.querySelector('button');
          if (sourceButton && targetButton) {
            targetButton.innerHTML = sourceButton.innerHTML;
          }

          // Track this select for later event firing
          updatedSelects.push(targetNativeSelect);
        }
      } else if (tag === 'TEXTAREA') {
        // Set value multiple ways to ensure it sticks
        constvalueToSet = sourceInput.value;

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
        constinputEvent = new Event('input', { bubbles: true });
        constchangeEvent = new Event('change', { bubbles: true });
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
      consttargetPrefix = (copyTarget === 'left') ? leftPrefix : rightPrefix;

      // Build container ID patterns - handle both with and without trailing underscore
      constsourceContainerIdPattern = sourcePrefix.replace(/_$/, '') + '_' + sourcePathPrefix + '_items_container';
      consttargetContainerIdPattern = targetPrefix.replace(/_$/, '') + '_' + targetPathPrefix + '_items_container';

      constsourceListContainer = document.getElementById(sourceContainerIdPattern);
      consttargetListContainer = document.getElementById(targetContainerIdPattern);

      if (sourceListContainer && targetListContainer) {
        // Both containers exist, this is a list field
        // Count list items in source and target
        constsourceItemCount = sourceListContainer.querySelectorAll(':scope > li').length;
        consttargetItems = targetListContainer.querySelectorAll(':scope > li');

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
          constaccordionParent = state.element.parentElement;
          if (accordionParent && window.UIkit) {
            constaccordionComponent = UIkit.accordion(accordionParent);
            if (accordionComponent) {
              constitemIndex = Array.from(accordionParent.children).indexOf(state.element);
              accordionComponent.toggle(itemIndex, true);
            } else {
              // Fallback to manual class manipulation
              state.element.classList.add('uk-open');
              constcontent = state.element.querySelector('.uk-accordion-content');
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
    constnativeSelect = ukSelect.querySelector('select');
    if (nativeSelect) {
      constukSelectName = ukSelect.getAttribute('name');
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
    const path = cell.dataset.path;
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
    const path = cell.dataset.path;
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
      const path = cell.dataset.path;
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
""")


class ComparisonForm(Generic[ModelType]):
    """
    Meta-renderer for side-by-side form comparison with metrics visualization

    This class creates a two-column layout with synchronized accordions and
    visual comparison feedback (colors, tooltips, metric badges).

    The ComparisonForm is a view-only composition helper; state management
    lives in the underlying PydanticForm instances.
    """

    def __init__(
        self,
        name: str,
        left_form: PydanticForm[ModelType],
        right_form: PydanticForm[ModelType],
        *,
        left_label: str = "Reference",
        right_label: str = "Generated",
        copy_left: bool = False,
        copy_right: bool = False,
    ):
        """
        Initialize the comparison form

        Args:
            name: Unique name for this comparison form
            left_form: Pre-constructed PydanticForm for left column
            right_form: Pre-constructed PydanticForm for right column
            left_label: Label for left column
            right_label: Label for right column
            copy_left: If True, show copy buttons in right column to copy to left
            copy_right: If True, show copy buttons in left column to copy to right

        Raises:
            ValueError: If the two forms are not based on the same model class
        """
        # Validate that both forms use the same model
        if left_form.model_class is not right_form.model_class:
            raise ValueError(
                f"Both forms must be based on the same model class. "
                f"Got {left_form.model_class.__name__} and {right_form.model_class.__name__}"
            )

        self.name = name
        self.left_form = left_form
        self.right_form = right_form
        self.model_class = left_form.model_class  # Convenience reference
        self.left_label = left_label
        self.right_label = right_label
        self.copy_left = copy_left
        self.copy_right = copy_right

        # Use spacing from left form (or could add override parameter if needed)
        self.spacing = left_form.spacing

    def _get_field_path_string(self, field_path: List[str]) -> str:
        """Convert field path list to dot-notation string for comparison lookup"""
        return ".".join(field_path)

    def _split_path(self, path: str) -> List[Union[str, int]]:
        """
        Split a dot/bracket path string into segments.

        Examples:
            "author.name" -> ["author", "name"]
            "addresses[0].street" -> ["addresses", 0, "street"]
            "experience[2].company" -> ["experience", 2, "company"]

        Args:
            path: Dot/bracket notation path string

        Returns:
            List of path segments (strings and ints)
        """
        _INDEX = re.compile(r"(.+?)\[(\d+)\]$")
        parts: List[Union[str, int]] = []

        for segment in path.split("."):
            m = _INDEX.match(segment)
            if m:
                # Segment has bracket notation like "name[3]"
                parts.append(m.group(1))
                parts.append(int(m.group(2)))
            else:
                parts.append(segment)

        return parts

    def _get_by_path(self, data: Dict[str, Any], path: str) -> tuple[bool, Any]:
        """
        Get a value from nested dict/list structure by path.

        Args:
            data: The data structure to traverse
            path: Dot/bracket notation path string

        Returns:
            Tuple of (found, value) where found is True if path exists, False otherwise
        """
        cur = data
        for seg in self._split_path(path):
            if isinstance(seg, int):
                if not isinstance(cur, list) or seg >= len(cur):
                    return (False, None)
                cur = cur[seg]
            else:
                if not isinstance(cur, dict) or seg not in cur:
                    return (False, None)
                cur = cur[seg]
        return (True, deepcopy(cur))

    def _set_by_path(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """
        Set a value in nested dict/list structure by path, creating intermediates.

        Args:
            data: The data structure to modify
            path: Dot/bracket notation path string
            value: The value to set
        """
        cur = data
        parts = self._split_path(path)

        for i, seg in enumerate(parts):
            is_last = i == len(parts) - 1

            if is_last:
                # Set the final value
                if isinstance(seg, int):
                    if not isinstance(cur, list):
                        raise ValueError("Cannot set list index on non-list parent")
                    # Extend list if needed
                    while len(cur) <= seg:
                        cur.append(None)
                    cur[seg] = deepcopy(value)
                else:
                    if not isinstance(cur, dict):
                        raise ValueError("Cannot set dict key on non-dict parent")
                    cur[seg] = deepcopy(value)
            else:
                # Navigate or create intermediate containers
                nxt = parts[i + 1]

                if isinstance(seg, int):
                    if not isinstance(cur, list):
                        raise ValueError("Non-list where list expected")
                    # Extend list if needed
                    while len(cur) <= seg:
                        cur.append({} if isinstance(nxt, str) else [])
                    cur = cur[seg]
                else:
                    if seg not in cur or not isinstance(cur[seg], (dict, list)):
                        # Create appropriate container type
                        cur[seg] = {} if isinstance(nxt, str) else []
                    cur = cur[seg]

    def _render_column(
        self,
        *,
        form: PydanticForm[ModelType],
        header_label: str,
        start_order: int,
        wrapper_id: str,
    ) -> FT:
        """
        Render a single column with CSS order values for grid alignment

        Args:
            form: The PydanticForm instance for this column
            header_label: Label for the column header
            start_order: Starting order value (0 for left, 1 for right)
            wrapper_id: ID for the wrapper div

        Returns:
            A div with class="contents" containing ordered grid items
        """
        # Header with order
        cells = [
            fh.Div(
                fh.H3(header_label, cls="text-lg font-semibold text-gray-700"),
                cls="pb-2 border-b",
                style=f"order:{start_order}",
            )
        ]

        # Start at order + 2, increment by 2 for each field
        order_idx = start_order + 2

        # Create renderers for each field
        registry = FieldRendererRegistry()

        for field_name, field_info in self.model_class.model_fields.items():
            # Skip excluded fields
            if field_name in (form.exclude_fields or []):
                continue

            # Skip SkipJsonSchema fields unless explicitly kept
            if _is_skip_json_schema_field(field_info) and not form._is_kept_skip_field(
                [field_name]
            ):
                continue

            # Get value from form
            value = form.values_dict.get(field_name)

            # Get path string for data-path attribute
            path_str = field_name

            # Get renderer class
            renderer_cls = registry.get_renderer(field_name, field_info)
            if not renderer_cls:
                from fh_pydantic_form.field_renderers import StringFieldRenderer

                renderer_cls = StringFieldRenderer

            # Determine comparison-specific refresh endpoint
            comparison_refresh = f"/compare/{self.name}/{'left' if form is self.left_form else 'right'}/refresh"

            # Get label color for this field if specified
            label_color = (
                form.label_colors.get(field_name)
                if hasattr(form, "label_colors")
                else None
            )

            # Determine comparison copy settings
            # Show copy buttons on the SOURCE form (the form you're copying FROM)
            is_left_column = form is self.left_form

            # If copy_left is enabled, show button on RIGHT form to copy TO left
            # If copy_right is enabled, show button on LEFT form to copy TO right
            if is_left_column:
                # This is the left form
                # Show copy button if we want to copy TO the right
                copy_feature_enabled = self.copy_right
                comparison_copy_target = "right" if copy_feature_enabled else None
                target_form = self.right_form
            else:
                # This is the right form
                # Show copy button if we want to copy TO the left
                copy_feature_enabled = self.copy_left
                comparison_copy_target = "left" if copy_feature_enabled else None
                target_form = self.left_form

            # Enable copy button if:
            # 1. The feature is enabled (copy_left or copy_right)
            # 2. The TARGET form is NOT disabled (you can't copy into a disabled/read-only form)
            comparison_copy_enabled = (
                copy_feature_enabled and not target_form.disabled
                if target_form
                else False
            )

            # Create renderer
            renderer = renderer_cls(
                field_name=field_name,
                field_info=field_info,
                value=value,
                prefix=form.base_prefix,
                disabled=form.disabled,
                spacing=form.spacing,
                field_path=[field_name],
                form_name=form.name,
                route_form_name=getattr(form, "template_name", form.name),
                label_color=label_color,  # Pass the label color if specified
                metrics_dict=form.metrics_dict,  # Use form's own metrics
                keep_skip_json_pathset=form._keep_skip_json_pathset,  # Pass keep_skip_json configuration
                refresh_endpoint_override=comparison_refresh,  # Pass comparison-specific refresh endpoint
                comparison_copy_enabled=comparison_copy_enabled,
                comparison_copy_target=comparison_copy_target,
                comparison_name=self.name,
            )

            # Render with data-path and order
            cells.append(
                fh.Div(
                    renderer.render(),
                    cls="",
                    **{"data-path": path_str, "style": f"order:{order_idx}"},
                )
            )

            order_idx += 2

        # Return wrapper with display: contents
        return fh.Div(*cells, id=wrapper_id, cls="contents")

    def render_inputs(self) -> FT:
        """
        Render the comparison form with side-by-side layout

        Returns:
            A FastHTML component with CSS Grid layout
        """
        # Render left column with wrapper
        left_wrapper = self._render_column(
            form=self.left_form,
            header_label=self.left_label,
            start_order=0,
            wrapper_id=f"{self.left_form.name}-inputs-wrapper",
        )

        # Render right column with wrapper
        right_wrapper = self._render_column(
            form=self.right_form,
            header_label=self.right_label,
            start_order=1,
            wrapper_id=f"{self.right_form.name}-inputs-wrapper",
        )

        # Create the grid container with both wrappers
        grid_container = fh.Div(
            left_wrapper,
            right_wrapper,
            cls="fhpf-compare grid grid-cols-2 gap-x-6 gap-y-2 items-start",
            id=f"{self.name}-comparison-grid",
            **{
                ATTR_COMPARE_GRID: "true",
                ATTR_COMPARE_NAME: self.name,
                ATTR_LEFT_PREFIX: self.left_form.base_prefix,
                ATTR_RIGHT_PREFIX: self.right_form.base_prefix,
            },
        )

        # Emit prefix globals for the copy registry
        prefix_script = fh.Script(f"""
window.__fhpfComparisonPrefixes = window.__fhpfComparisonPrefixes || {{}};
window.__fhpfComparisonPrefixes[{json.dumps(self.name)}] = {{
  left: {json.dumps(self.left_form.base_prefix)},
  right: {json.dumps(self.right_form.base_prefix)}
}};
window.__fhpfLeftPrefix = {json.dumps(self.left_form.base_prefix)};
window.__fhpfRightPrefix = {json.dumps(self.right_form.base_prefix)};
""")

        return fh.Div(prefix_script, grid_container, cls="w-full")

    def register_routes(self, app):
        """
        Register HTMX routes for the comparison form

        Args:
            app: FastHTML app instance
        """
        # Register individual form routes (for list manipulation)
        self.left_form.register_routes(app)
        self.right_form.register_routes(app)

        # Register comparison-specific reset/refresh routes
        def create_reset_handler(
            form: PydanticForm[ModelType],
            side: str,
            label: str,
        ):
            """Factory function to create reset handler with proper closure"""

            async def handler(req):
                """Reset one side of the comparison form"""
                # Reset the form state
                await form.handle_reset_request()

                # Render the entire column with proper ordering
                start_order = 0 if side == "left" else 1
                wrapper = self._render_column(
                    form=form,
                    header_label=label,
                    start_order=start_order,
                    wrapper_id=f"{form.name}-inputs-wrapper",
                )
                return wrapper

            return handler

        def create_refresh_handler(
            form: PydanticForm[ModelType],
            side: str,
            label: str,
        ):
            """Factory function to create refresh handler with proper closure"""

            async def handler(req):
                """Refresh one side of the comparison form"""
                # Refresh the form state and capture any warnings
                refresh_result = await form.handle_refresh_request(req)

                # Render the entire column with proper ordering
                start_order = 0 if side == "left" else 1
                wrapper = self._render_column(
                    form=form,
                    header_label=label,
                    start_order=start_order,
                    wrapper_id=f"{form.name}-inputs-wrapper",
                )

                # If refresh returned a warning, include it in the response
                if isinstance(refresh_result, tuple) and len(refresh_result) == 2:
                    alert, _ = refresh_result
                    # Return both the alert and the wrapper
                    return fh.Div(alert, wrapper)
                else:
                    # No warning, just return the wrapper
                    return wrapper

            return handler

        for side, form, label in [
            ("left", self.left_form, self.left_label),
            ("right", self.right_form, self.right_label),
        ]:
            assert form is not None

            # Reset route
            reset_path = f"/compare/{self.name}/{side}/reset"
            reset_handler = create_reset_handler(form, side, label)
            app.route(reset_path, methods=["POST"])(reset_handler)

            # Refresh route
            refresh_path = f"/compare/{self.name}/{side}/refresh"
            refresh_handler = create_refresh_handler(form, side, label)
            app.route(refresh_path, methods=["POST"])(refresh_handler)

        # Note: Copy routes are not needed - copy is handled entirely in JavaScript
        # via window.fhpfPerformCopy() function called directly from onclick handlers

    def form_wrapper(self, content: FT, form_id: Optional[str] = None) -> FT:
        """
        Wrap the comparison content in a form element with proper ID

        Args:
            content: The form content to wrap
            form_id: Optional form ID (defaults to {name}-comparison-form)

        Returns:
            A form element containing the content
        """
        form_id = form_id or f"{self.name}-comparison-form"
        wrapper_id = f"{self.name}-comparison-wrapper"

        # Note: Removed hx_include="closest form" since the wrapper only contains foreign forms
        return mui.Form(
            fh.Div(content, id=wrapper_id),
            id=form_id,
        )

    def _button_helper(self, *, side: str, action: str, text: str, **kwargs) -> FT:
        """
        Helper method to create buttons that target comparison-specific routes

        Args:
            side: "left" or "right"
            action: "reset" or "refresh"
            text: Button text
            **kwargs: Additional button attributes

        Returns:
            A button component
        """
        form = self.left_form if side == "left" else self.right_form

        # Create prefix-based selector
        prefix_selector = f"form [name^='{form.base_prefix}']"

        # Set default attributes
        kwargs.setdefault("hx_post", f"/compare/{self.name}/{side}/{action}")
        kwargs.setdefault("hx_target", f"#{form.name}-inputs-wrapper")
        kwargs.setdefault("hx_swap", "innerHTML")
        kwargs.setdefault("hx_include", prefix_selector)
        kwargs.setdefault("hx_preserve", "scroll")

        # Delegate to the underlying form's button method
        button_method = getattr(form, f"{action}_button")
        return button_method(text, **kwargs)

    def left_reset_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """Create a reset button for the left form"""
        return self._button_helper(
            side="left", action="reset", text=text or "↩️ Reset Left", **kwargs
        )

    def left_refresh_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """Create a refresh button for the left form"""
        return self._button_helper(
            side="left", action="refresh", text=text or "🔄 Refresh Left", **kwargs
        )

    def right_reset_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """Create a reset button for the right form"""
        return self._button_helper(
            side="right", action="reset", text=text or "↩️ Reset Right", **kwargs
        )

    def right_refresh_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """Create a refresh button for the right form"""
        return self._button_helper(
            side="right", action="refresh", text=text or "🔄 Refresh Right", **kwargs
        )


def simple_diff_metrics(
    left_data: BaseModel | Dict[str, Any],
    right_data: BaseModel | Dict[str, Any],
    model_class: Type[BaseModel],
) -> MetricsDict:
    """
    Simple helper to generate metrics based on equality

    Args:
        left_data: Reference data
        right_data: Data to compare
        model_class: Model class for structure

    Returns:
        MetricsDict with simple equality-based metrics
    """
    metrics_dict = {}

    # Convert to dicts if needed
    if hasattr(left_data, "model_dump"):
        left_dict = left_data.model_dump()
    else:
        left_dict = left_data or {}

    if hasattr(right_data, "model_dump"):
        right_dict = right_data.model_dump()
    else:
        right_dict = right_data or {}

    # Compare each field
    for field_name in model_class.model_fields:
        left_val = left_dict.get(field_name)
        right_val = right_dict.get(field_name)

        if left_val == right_val:
            metrics_dict[field_name] = MetricEntry(
                metric=1.0, color="green", comment="Values match exactly"
            )
        elif left_val is None or right_val is None:
            metrics_dict[field_name] = MetricEntry(
                metric=0.0, color="orange", comment="One value is missing"
            )
        else:
            # Try to compute similarity for strings
            if isinstance(left_val, str) and isinstance(right_val, str):
                # Simple character overlap ratio
                common = sum(1 for a, b in zip(left_val, right_val) if a == b)
                max_len = max(len(left_val), len(right_val))
                similarity = common / max_len if max_len > 0 else 0

                metrics_dict[field_name] = MetricEntry(
                    metric=round(similarity, 2),
                    comment=f"String similarity: {similarity:.0%}",
                )
            else:
                metrics_dict[field_name] = MetricEntry(
                    metric=0.0,
                    comment=f"Different values: {left_val} vs {right_val}",
                )

    return metrics_dict
