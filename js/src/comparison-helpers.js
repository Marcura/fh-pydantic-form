/**
 * comparison-helpers.js
 *
 * Helper functions for ComparisonForm list item path detection and manipulation.
 * These functions are extracted from the embedded JavaScript in comparison_form.py
 * to enable proper unit testing.
 *
 * IMPORTANT: Any changes here should be reflected in comparison_form.py
 * (or ideally, comparison_form.py should import this file's content).
 */

/**
 * Check if path contains array index pattern like [0], [1], etc.
 *
 * KNOWN BUG: This pattern only matches numeric indices, not placeholder
 * indices like [new_1234567890] used for newly added items.
 *
 * @param {string} pathPrefix - The field path to check
 * @returns {boolean} True if path contains an array index
 */
function isListItemPath(pathPrefix) {
  // Current (buggy) implementation - only matches numeric indices
  return /\[\d+\]/.test(pathPrefix);
}

/**
 * Fixed version of isListItemPath that handles both numeric and placeholder indices.
 * Also distinguishes between full items and subfields.
 *
 * @param {string} pathPrefix - The field path to check
 * @returns {boolean} True if path is a full list item (ends with [index])
 */
function isListItemPathFixed(pathPrefix) {
  // Match both numeric [0] and placeholder [new_123] indices
  // Only match if the path ENDS with the index (full item, not subfield)
  return /\[(\d+|new_\d+)\]$/.test(pathPrefix);
}

/**
 * Check if path is a subfield within a list item.
 *
 * @param {string} pathPrefix - The field path to check
 * @returns {boolean} True if path is a subfield (has content after [index])
 */
function isListSubfieldPath(pathPrefix) {
  // Match paths like reviews[0].rating (has . after the index)
  return /\[(\d+|new_\d+)\]\./.test(pathPrefix);
}

/**
 * Extract the list field path without the index.
 * e.g., "addresses[0]" -> "addresses"
 * e.g., "addresses[0].street" -> "addresses"
 *
 * KNOWN BUG: Only removes numeric indices, not placeholder indices.
 *
 * @param {string} pathPrefix - The field path
 * @returns {string} The base list field name
 */
function extractListFieldPath(pathPrefix) {
  // Current (buggy) implementation
  return pathPrefix.replace(/\[\d+\].*$/, '');
}

/**
 * Fixed version that handles both numeric and placeholder indices.
 *
 * @param {string} pathPrefix - The field path
 * @returns {string} The base list field name
 */
function extractListFieldPathFixed(pathPrefix) {
  return pathPrefix.replace(/\[(\d+|new_\d+)\].*$/, '');
}

/**
 * Extract the index from path.
 * e.g., "addresses[0].street" -> 0
 * e.g., "addresses[5]" -> 5
 *
 * KNOWN BUG: Only extracts numeric indices, returns null for placeholder indices.
 *
 * @param {string} pathPrefix - The field path
 * @returns {number|null} The numeric index, or null if not found
 */
function extractListIndex(pathPrefix) {
  // Current (buggy) implementation
  var match = pathPrefix.match(/\[(\d+)\]/);
  return match ? parseInt(match[1]) : null;
}

/**
 * Fixed version that handles placeholder indices.
 * Returns the index value (numeric or placeholder string).
 *
 * @param {string} pathPrefix - The field path
 * @returns {string|number|null} The index value, or null if not found
 */
function extractListIndexFixed(pathPrefix) {
  var match = pathPrefix.match(/\[(\d+|new_\d+)\]/);
  if (!match) return null;

  var indexStr = match[1];
  // Return numeric for numbers, string for placeholders
  return /^\d+$/.test(indexStr) ? parseInt(indexStr) : indexStr;
}

/**
 * Extract the relative path (subfield portion) from a full path.
 * e.g., "reviews[0].rating" with listFieldPath="reviews" -> ".rating"
 * e.g., "reviews[0]" with listFieldPath="reviews" -> ""
 *
 * @param {string} fullPath - The full field path
 * @param {string} listFieldPath - The base list field name
 * @returns {string} The relative path after the index
 */
function extractRelativePath(fullPath, listFieldPath) {
  // Build pattern to match listFieldPath[anything]
  var escapedPath = listFieldPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  var pattern = new RegExp('^' + escapedPath + '\\[[^\\]]+\\]');
  var match = fullPath.match(pattern);

  if (!match) return fullPath;
  return fullPath.slice(match[0].length);
}

/**
 * Determine the copy behavior based on path structure.
 *
 * @param {string} pathPrefix - The field path
 * @returns {string} One of: 'add_new_item', 'update_existing_subfield', 'standard_copy'
 */
function getCopyBehavior(pathPrefix) {
  // Full list item (ends with [index]) -> add new item
  if (/\[(\d+|new_\d+)\]$/.test(pathPrefix)) {
    return 'add_new_item';
  }
  // Subfield of list item (has content after [index]) -> update existing
  if (/\[(\d+|new_\d+)\]\./.test(pathPrefix)) {
    return 'update_existing_subfield';
  }
  // Everything else (full list, scalar field) -> standard copy
  return 'standard_copy';
}

/**
 * Remap a source path to target path by replacing the index.
 *
 * @param {string} sourcePath - The source field path
 * @param {string} sourceIndex - The source index (numeric string or placeholder)
 * @param {string} targetIndex - The target index (numeric string or placeholder)
 * @returns {string} The remapped path
 */
function remapPathIndex(sourcePath, sourceIndex, targetIndex) {
  return sourcePath.replace('[' + sourceIndex + ']', '[' + targetIndex + ']');
}

// Export for Node.js/Jest testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    // Current (buggy) implementations
    isListItemPath,
    extractListFieldPath,
    extractListIndex,

    // Fixed implementations
    isListItemPathFixed,
    isListSubfieldPath,
    extractListFieldPathFixed,
    extractListIndexFixed,

    // Additional helpers
    extractRelativePath,
    getCopyBehavior,
    remapPathIndex,
  };
}
