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
    return fh.Script("""
// Helper functions for list item path detection
function isListItemPath(pathPrefix) {
  // Check if path contains array index pattern like [0], [1], etc.
  return /\[\d+\]/.test(pathPrefix);
}

function extractListFieldPath(pathPrefix) {
  // Extract the list field path without the index
  // e.g., "addresses[0]" -> "addresses"
  return pathPrefix.replace(/\[\d+\].*$/, '');
}

function extractListIndex(pathPrefix) {
  // Extract the index from path
  // e.g., "addresses[0].street" -> 0
  var match = pathPrefix.match(/\[(\d+)\]/);
  return match ? parseInt(match[1]) : null;
}

// Copy function - pure JS implementation
window.fhpfPerformCopy = function(pathPrefix, currentPrefix, copyTarget) {
  try {
    // Set flag to prevent accordion sync
    window.__fhpfCopyInProgress = true;

    // Save all accordion states before copy
    var accordionStates = [];
    document.querySelectorAll('ul[uk-accordion] > li').forEach(function(li) {
      accordionStates.push({
        element: li,
        isOpen: li.classList.contains('uk-open')
      });
    });

    // Determine source prefix based on copy target
    var sourcePrefix = (copyTarget === 'left') ? window.__fhpfRightPrefix : window.__fhpfLeftPrefix;

    // Check if this is a list item copy operation
    var isListItem = isListItemPath(pathPrefix);
    var listFieldPath = null;
    var listIndex = null;

    if (isListItem) {
      listFieldPath = extractListFieldPath(pathPrefix);
      listIndex = extractListIndex(pathPrefix);
    }

    // Special handling for list item copies: add new item instead of overwriting
    if (isListItem) {
      // Find target list container
      var targetPrefix = (copyTarget === 'left') ? window.__fhpfLeftPrefix : window.__fhpfRightPrefix;
      var targetContainerId = targetPrefix.replace(/_$/, '') + '_' + listFieldPath + '_items_container';
      var targetContainer = document.getElementById(targetContainerId);

      if (targetContainer) {
        // Find the "Add Item" button for the target list
        var targetAddButton = targetContainer.parentElement.querySelector('button[hx-post*="/list/add/"]');

        if (targetAddButton) {
          // Capture the target list items BEFORE adding the new one
          var targetListItemsBeforeAdd = Array.from(targetContainer.querySelectorAll(':scope > li'));
          var targetLengthBefore = targetListItemsBeforeAdd.length;

          // Determine the target position: insert after the source item's index, or at end if target is shorter
          var sourceIndex = listIndex;  // The index from the source path (e.g., reviews[2] -> 2)
          var insertAfterIndex = Math.min(sourceIndex, targetLengthBefore - 1);

          // Get the URL from the add button
          var addUrl = targetAddButton.getAttribute('hx-post');

          // Determine the insertion point
          var insertBeforeElement = null;
          if (insertAfterIndex >= 0 && insertAfterIndex < targetLengthBefore - 1) {
            // Insert after insertAfterIndex, which means before insertAfterIndex+1
            insertBeforeElement = targetListItemsBeforeAdd[insertAfterIndex + 1];
          } else if (targetLengthBefore > 0) {
            // Insert at the end: use afterend on the last item
            insertBeforeElement = targetListItemsBeforeAdd[targetLengthBefore - 1];
          }

          // Make the HTMX request with custom swap target
          if (insertBeforeElement) {
            var swapStrategy = (insertAfterIndex >= targetLengthBefore - 1) ? 'afterend' : 'beforebegin';
            // Use htmx.ajax to insert at specific position
            htmx.ajax('POST', addUrl, {
              target: '#' + insertBeforeElement.id,
              swap: swapStrategy
            });
          } else {
            // List is empty, insert into container
            htmx.ajax('POST', addUrl, {
              target: '#' + targetContainerId,
              swap: 'beforeend'
            });
          }

          // Wait for HTMX to complete the swap AND settle, then copy values
          var copyCompleted = false;
          var htmxSettled = false;
          var newlyAddedElement = null;

          // Listen for HTMX afterSwap event on the container to capture the newly added element
          targetContainer.addEventListener('htmx:afterSwap', function onSwap(evt) {
            // Parse the response to get the new element's ID
            var tempDiv = document.createElement('div');
            tempDiv.innerHTML = evt.detail.xhr.response;
            var newElement = tempDiv.firstElementChild;
            if (newElement && newElement.id) {
              newlyAddedElement = newElement;
            }
          }, { once: true });

          // Listen for HTMX afterSettle event
          document.body.addEventListener('htmx:afterSettle', function onSettle(evt) {
            htmxSettled = true;
            document.body.removeEventListener('htmx:afterSettle', onSettle);
          }, { once: true });

          var maxAttempts = 100; // 100 attempts with exponential backoff = ~10 seconds total
          var attempts = 0;

          var checkAndCopy = function() {
            attempts++;

            // Calculate delay with exponential backoff: 50ms, 50ms, 100ms, 100ms, 200ms, ...
            var delay = Math.min(50 * Math.pow(2, Math.floor(attempts / 2)), 500);

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
            var targetItems = targetContainer.querySelectorAll(':scope > li');
            var newItem = null;
            var newItemIndex = -1;

            if (newlyAddedElement && newlyAddedElement.id) {
              // Use the ID we captured from the HTMX response
              newItem = document.getElementById(newlyAddedElement.id);

              if (newItem) {
                // Find its position in the list
                for (var i = 0; i < targetItems.length; i++) {
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
              var newItemInputs = newItem.querySelectorAll('[data-field-path]');

              if (newItemInputs.length > 0) {
                // New item is ready, now copy values from source item
                copyCompleted = true;

                // The new item might not contain the textarea with placeholder!
                // Search the entire target container for the newest textarea with "new_" in the name
                var targetPrefix = (copyTarget === 'left') ? window.__fhpfLeftPrefix : window.__fhpfRightPrefix;
                var allInputsInContainer = targetContainer.querySelectorAll('[data-field-path^="' + listFieldPath + '["]');

                var firstInput = null;
                var newestTimestamp = 0;

                for (var i = 0; i < allInputsInContainer.length; i++) {
                  var inputName = allInputsInContainer[i].name || allInputsInContainer[i].id;
                  if (inputName && inputName.startsWith(targetPrefix.replace(/_$/, '') + '_' + listFieldPath + '_new_')) {
                    // Extract timestamp from name
                    var match = inputName.match(/new_(\d+)/);
                    if (match) {
                      var timestamp = parseInt(match[1]);
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

                var firstInputPath = firstInput.getAttribute('data-field-path');
                var firstInputName = firstInput.name || firstInput.id;

                // Extract placeholder from name
                // Pattern: "prefix_listfield_PLACEHOLDER" or "prefix_listfield_PLACEHOLDER_fieldname"
                // For simple list items: "annotated_truth_key_features_new_123"
                // For BaseModel list items: "annotated_truth_reviews_new_123_rating"
                // We want just the placeholder part (new_123)
                var searchStr = '_' + listFieldPath + '_';
                var idx = firstInputName.indexOf(searchStr);
                var actualPlaceholderIdx = null;

                if (idx >= 0) {
                  var afterListField = firstInputName.substring(idx + searchStr.length);

                  // For BaseModel items with nested fields, the placeholder is between listfield and the next underscore
                  // Check if this looks like a nested field by checking if there's another underscore after "new_"
                  if (afterListField.startsWith('new_')) {
                    // Extract just "new_TIMESTAMP" part - stop at the next underscore after the timestamp
                    var parts = afterListField.split('_');
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
                var newPathPrefix = listFieldPath + '[' + actualPlaceholderIdx + ']';

                // Now perform the standard copy operation with the new path
                performStandardCopy(pathPrefix, newPathPrefix, sourcePrefix, copyTarget, accordionStates);

                // Wait for copy to complete, then open accordion and highlight
                // Note: We skip automatic refresh because the temporary item ID doesn't persist after refresh
                // User can manually click the refresh button to update counts/summaries if needed
                var waitForCopyComplete = function() {
                  if (!window.__fhpfCopyInProgress) {
                    // Copy operation is complete, now open and highlight the new item
                    setTimeout(function() {
                      // Re-find the item (it might have been affected by accordion restoration)
                      var copiedItem = document.getElementById(newItem.id);

                      if (copiedItem && window.UIkit) {
                        // Open the newly created accordion item
                        if (!copiedItem.classList.contains('uk-open')) {
                          var accordionParent = copiedItem.parentElement;
                          if (accordionParent && accordionParent.hasAttribute('uk-accordion')) {
                            var accordionComponent = UIkit.accordion(accordionParent);
                            if (accordionComponent) {
                              var itemIndex = Array.from(accordionParent.children).indexOf(copiedItem);
                              accordionComponent.toggle(itemIndex, false);  // false = don't animate
                            }
                          } else {
                            // Manual fallback
                            copiedItem.classList.add('uk-open');
                            var content = copiedItem.querySelector('.uk-accordion-content');
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
      var targetPrefix = (copyTarget === 'left') ? window.__fhpfLeftPrefix : window.__fhpfRightPrefix;

      var baseIdPart = pathPrefix; // e.g. "addresses" or "key_features"
      var sourceContainerId = sourcePrefix.replace(/_$/, '') + '_' + baseIdPart + '_items_container';
      var targetContainerId = targetPrefix.replace(/_$/, '') + '_' + baseIdPart + '_items_container';

      var sourceListContainer = document.getElementById(sourceContainerId);
      var targetListContainer = document.getElementById(targetContainerId);

      // Only do length alignment if BOTH containers exist (i.e., this field is a list on both sides)
      if (sourceListContainer && targetListContainer) {
        var sourceCount = sourceListContainer.querySelectorAll(':scope > li').length;
        var targetCount = targetListContainer.querySelectorAll(':scope > li').length;

        // If source has more items, add missing ones BEFORE copying values (case 3)
        if (sourceCount > targetCount) {
          var addBtn = targetListContainer.parentElement.querySelector('button[hx-post*="/list/add/"]');
          if (addBtn) {
            var addUrl = addBtn.getAttribute('hx-post');
            var toAdd = sourceCount - targetCount;

            // Queue the required number of additions at the END
            // We'll use htmx.ajax with target=container and swap=beforeend
            // Then wait for HTMX to settle and for the DOM to reflect the new length.
            var added = 0;
            var addOne = function(cb) {
              htmx.ajax('POST', addUrl, {
                target: '#' + targetContainerId,
                swap: 'beforeend',
                values: {} // no-op
              });
              added += 1;
              cb && cb();
            };

            // Fire additions synchronously; HTMX will queue them
            for (var i = 0; i < toAdd; i++) addOne();

            // Wait for afterSettle AND correct length, then perform the copy
            var attempts = 0, maxAttempts = 120; // ~6s @ 50ms backoff
            var settled = false;

            // Capture settle event once
            var onSettle = function onSettleOnce() {
              settled = true;
              document.body.removeEventListener('htmx:afterSettle', onSettleOnce);
            };
            document.body.addEventListener('htmx:afterSettle', onSettle);

            var waitAndCopy = function() {
              attempts++;
              var delay = Math.min(50 * Math.pow(1.15, attempts), 250);

              var currentCount = targetListContainer.querySelectorAll(':scope > li').length;
              if (settled && currentCount >= sourceCount) {
                // Proceed with list copy by DOM position
                performListCopyByPosition(sourceListContainer, targetListContainer, sourcePrefix, copyTarget, accordionStates, pathPrefix);
                return;
              }
              if (attempts >= maxAttempts) {
                console.error('Timeout aligning list lengths for full-list copy');
                // Still do a best-effort copy
                performListCopyByPosition(sourceListContainer, targetListContainer, sourcePrefix, copyTarget, accordionStates, pathPrefix);
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
          performListCopyByPosition(sourceListContainer, targetListContainer, sourcePrefix, copyTarget, accordionStates, pathPrefix);
          return;
        }
      }

      // Default path (non-list fields or already aligned lists)
      performStandardCopy(pathPrefix, pathPrefix, sourcePrefix, copyTarget, accordionStates);
    })();

  } catch (e) {
    window.__fhpfCopyInProgress = false;
    throw e;
  }
};

// Copy list items by DOM position (handles different indices in source/target)
function performListCopyByPosition(sourceListContainer, targetListContainer, sourcePrefix, copyTarget, accordionStates, listFieldPath) {
  try {
    var sourceItems = sourceListContainer.querySelectorAll(':scope > li');
    var targetItems = targetListContainer.querySelectorAll(':scope > li');
    var targetPrefix = (copyTarget === 'left') ? window.__fhpfLeftPrefix : window.__fhpfRightPrefix;

    // Copy each source item to corresponding target item by position
    for (var i = 0; i < sourceItems.length && i < targetItems.length; i++) {
      var sourceItem = sourceItems[i];
      var targetItem = targetItems[i];

      // Find all inputs within this source item
      var sourceInputs = sourceItem.querySelectorAll('[data-field-path]');

      Array.from(sourceInputs).forEach(function(sourceInput) {
        var sourceFp = sourceInput.getAttribute('data-field-path');

        // Extract the field path relative to the list item
        // e.g., "addresses[0].street" -> ".street"
        // or "tags[0]" -> ""
        var listItemPattern = new RegExp('^' + listFieldPath.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\[[^\\\\]]+\\\\]');
        var relativePath = sourceFp.replace(listItemPattern, '');

        // Find the corresponding input in the target item by looking for the same relative path
        var targetInputs = targetItem.querySelectorAll('[data-field-path]');
        var targetInput = null;

        for (var j = 0; j < targetInputs.length; j++) {
          var targetFp = targetInputs[j].getAttribute('data-field-path');
          var targetRelativePath = targetFp.replace(listItemPattern, '');

          if (targetRelativePath === relativePath) {
            // Verify it belongs to the target form
            var candidateName = null;
            if (targetInputs[j].tagName === 'UK-SELECT') {
              var nativeSelect = targetInputs[j].querySelector('select');
              candidateName = nativeSelect ? nativeSelect.name : null;
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

        // Copy the value
        var tag = sourceInput.tagName.toUpperCase();
        var type = (sourceInput.type || '').toLowerCase();

        if (type === 'checkbox') {
          targetInput.checked = sourceInput.checked;
        } else if (tag === 'SELECT') {
          targetInput.value = sourceInput.value;
        } else if (tag === 'UK-SELECT') {
          var sourceNativeSelect = sourceInput.querySelector('select');
          var targetNativeSelect = targetInput.querySelector('select');
          if (sourceNativeSelect && targetNativeSelect) {
            var sourceValue = sourceNativeSelect.value;

            // Clear all selected attributes
            for (var k = 0; k < targetNativeSelect.options.length; k++) {
              targetNativeSelect.options[k].removeAttribute('selected');
              targetNativeSelect.options[k].selected = false;
            }

            // Find and set the matching option
            for (var k = 0; k < targetNativeSelect.options.length; k++) {
              if (targetNativeSelect.options[k].value === sourceValue) {
                targetNativeSelect.options[k].setAttribute('selected', 'selected');
                targetNativeSelect.options[k].selected = true;
                targetNativeSelect.selectedIndex = k;
                targetNativeSelect.value = sourceValue;
                break;
              }
            }

            // Update the button display
            var sourceButton = sourceInput.querySelector('button');
            var targetButton = targetInput.querySelector('button');
            if (sourceButton && targetButton) {
              targetButton.innerHTML = sourceButton.innerHTML;
            }
          }
        } else if (tag === 'TEXTAREA') {
          var valueToSet = sourceInput.value;
          targetInput.value = '';
          targetInput.textContent = '';
          targetInput.innerHTML = '';
          targetInput.value = valueToSet;
          targetInput.textContent = valueToSet;
          targetInput.innerHTML = valueToSet;
          targetInput.setAttribute('value', valueToSet);

          var inputEvent = new Event('input', { bubbles: true });
          var changeEvent = new Event('change', { bubbles: true });
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
    for (var i = targetItems.length - 1; i >= sourceItems.length; i--) {
      targetItems[i].remove();
    }

    // Restore accordion states
    setTimeout(function() {
      accordionStates.forEach(function(state) {
        if (state.isOpen && !state.element.classList.contains('uk-open')) {
          var accordionParent = state.element.parentElement;
          if (accordionParent && window.UIkit) {
            var accordionComponent = UIkit.accordion(accordionParent);
            if (accordionComponent) {
              var itemIndex = Array.from(accordionParent.children).indexOf(state.element);
              accordionComponent.toggle(itemIndex, true);
            } else {
              state.element.classList.add('uk-open');
              var content = state.element.querySelector('.uk-accordion-content');
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
      var targetListFieldWrapper = targetListContainer.closest('[data-path]');
      if (targetListFieldWrapper) {
        var refreshButton = targetListFieldWrapper.querySelector('button[hx-post*="/refresh"]');
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
function performStandardCopy(sourcePathPrefix, targetPathPrefix, sourcePrefix, copyTarget, accordionStates) {
  try {
    // Find all inputs with matching data-field-path from source
    var allInputs = document.querySelectorAll('[data-field-path]');
    var sourceInputs = Array.from(allInputs).filter(function(el) {
      var fp = el.getAttribute('data-field-path');
      if (!(fp === sourcePathPrefix || fp.startsWith(sourcePathPrefix + '.') || fp.startsWith(sourcePathPrefix + '['))) {
        return false;
      }

      // Check if this element belongs to the source form
      var elementName = null;
      if (el.tagName === 'UK-SELECT') {
        var nativeSelect = el.querySelector('select');
        elementName = nativeSelect ? nativeSelect.name : null;
      } else {
        elementName = el.name;
      }

      return elementName && elementName.startsWith(sourcePrefix);
    });

    // Track updated selects to fire change events later
    var updatedSelects = [];

    var copiedCount = 0;
    sourceInputs.forEach(function(sourceInput) {
      var sourceFp = sourceInput.getAttribute('data-field-path');

      // Map source field path to target field path
      // If sourcePathPrefix != targetPathPrefix (list item case), we need to remap
      var targetFp = sourceFp;
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
      var candidates = document.querySelectorAll('[data-field-path="' + targetFp + '"]');
      var targetInput = null;
      for (var i = 0; i < candidates.length; i++) {
        var candidate = candidates[i];
        var candidateName = null;
        if (candidate.tagName === 'UK-SELECT') {
          var nativeSelect = candidate.querySelector('select');
          candidateName = nativeSelect ? nativeSelect.name : null;
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

      var tag = sourceInput.tagName.toUpperCase();
      var type = (sourceInput.type || '').toLowerCase();

      if (type === 'checkbox') {
        targetInput.checked = sourceInput.checked;
      } else if (tag === 'SELECT') {
        targetInput.value = sourceInput.value;
        updatedSelects.push(targetInput);
      } else if (tag === 'UK-SELECT') {
        var sourceNativeSelect = sourceInput.querySelector('select');
        var targetNativeSelect = targetInput.querySelector('select');
        if (sourceNativeSelect && targetNativeSelect) {
          var sourceValue = sourceNativeSelect.value;

          // First, clear all selected attributes
          for (var i = 0; i < targetNativeSelect.options.length; i++) {
            targetNativeSelect.options[i].removeAttribute('selected');
            targetNativeSelect.options[i].selected = false;
          }

          // Find and set the matching option
          for (var i = 0; i < targetNativeSelect.options.length; i++) {
            if (targetNativeSelect.options[i].value === sourceValue) {
              targetNativeSelect.options[i].setAttribute('selected', 'selected');
              targetNativeSelect.options[i].selected = true;
              targetNativeSelect.selectedIndex = i;
              targetNativeSelect.value = sourceValue;
              break;
            }
          }

          // Update the button display
          var sourceButton = sourceInput.querySelector('button');
          var targetButton = targetInput.querySelector('button');
          if (sourceButton && targetButton) {
            targetButton.innerHTML = sourceButton.innerHTML;
          }

          // Track this select for later event firing
          updatedSelects.push(targetNativeSelect);
        }
      } else if (tag === 'TEXTAREA') {
        // Set value multiple ways to ensure it sticks
        var valueToSet = sourceInput.value;

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
        var inputEvent = new Event('input', { bubbles: true });
        var changeEvent = new Event('change', { bubbles: true });
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
      var targetPrefix = (copyTarget === 'left') ? window.__fhpfLeftPrefix : window.__fhpfRightPrefix;

      // Build container ID patterns - handle both with and without trailing underscore
      var sourceContainerIdPattern = sourcePrefix.replace(/_$/, '') + '_' + sourcePathPrefix + '_items_container';
      var targetContainerIdPattern = targetPrefix.replace(/_$/, '') + '_' + targetPathPrefix + '_items_container';

      var sourceListContainer = document.getElementById(sourceContainerIdPattern);
      var targetListContainer = document.getElementById(targetContainerIdPattern);

      if (sourceListContainer && targetListContainer) {
        // Both containers exist, this is a list field
        // Count list items in source and target
        var sourceItemCount = sourceListContainer.querySelectorAll(':scope > li').length;
        var targetItems = targetListContainer.querySelectorAll(':scope > li');

        // Remove excess items from target (from end backwards)
        for (var i = targetItems.length - 1; i >= sourceItemCount; i--) {
          targetItems[i].remove();
        }
      }
    }

    // Restore accordion states after a brief delay
    setTimeout(function() {
      accordionStates.forEach(function(state) {
        if (state.isOpen && !state.element.classList.contains('uk-open')) {
          // Use UIkit's toggle API to properly open the accordion
          var accordionParent = state.element.parentElement;
          if (accordionParent && window.UIkit) {
            var accordionComponent = UIkit.accordion(accordionParent);
            if (accordionComponent) {
              var itemIndex = Array.from(accordionParent.children).indexOf(state.element);
              accordionComponent.toggle(itemIndex, true);
            } else {
              // Fallback to manual class manipulation
              state.element.classList.add('uk-open');
              var content = state.element.querySelector('.uk-accordion-content');
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
    var nativeSelect = ukSelect.querySelector('select');
    if (nativeSelect) {
      var ukSelectName = ukSelect.getAttribute('name');
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

    // Determine index of this <li> inside its <ul>
    const idx     = Array.prototype.indexOf.call(
      sourceLi.parentElement.children,
      sourceLi
    );
    const opening = ev.type === 'show';

    // Mirror on the other side
    document
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

    // Determine index of this <li> within its list container
    const listAccordion = sourceLi.parentElement;
    const idx = Array.prototype.indexOf.call(listAccordion.children, sourceLi);
    const opening = ev.type === 'show';

    // Mirror on the other side
    document
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

      // c) Find the peer's list-container by suffix match
      document
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
        )

        # Emit prefix globals for the copy registry
        prefix_script = fh.Script(f"""
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
