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
 * Check if path is a FULL list item.
 *
 * @param {string} pathPrefix - The field path to check
 * @returns {boolean} True if path is a full list item (ends with [index])
 */
function isListItemPath(pathPrefix) {
  // Match both numeric [0] and placeholder [new_123] indices
  // Only match if the path ENDS with the index (full item, not subfield)
  return /\[(\d+|new_\d+)\]$/.test(pathPrefix);
}

/**
 * Backward-compatible alias.
 */
function isListItemPathFixed(pathPrefix) {
  return isListItemPath(pathPrefix);
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
 * @param {string} pathPrefix - The field path
 * @returns {string} The base list field name
 */
function extractListFieldPath(pathPrefix) {
  return pathPrefix.replace(/\[(\d+|new_\d+)\].*$/, '');
}

/**
 * Backward-compatible alias.
 */
function extractListFieldPathFixed(pathPrefix) {
  return extractListFieldPath(pathPrefix);
}

/**
 * Extract the index from path.
 * e.g., "addresses[0].street" -> 0
 * e.g., "addresses[new_123]" -> "new_123"
 *
 * @param {string} pathPrefix - The field path
 * @returns {string|number|null} The index value, or null if not found
 */
function extractListIndex(pathPrefix) {
  const match = pathPrefix.match(/\[(\d+|new_\d+)\]/);
  if (!match) return null;

  const indexStr = match[1];
  // Return numeric for numbers, string for placeholders
  return /^\d+$/.test(indexStr) ? parseInt(indexStr) : indexStr;
}

/**
 * Backward-compatible alias.
 */
function extractListIndexFixed(pathPrefix) {
  return extractListIndex(pathPrefix);
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
  // Escape special regex chars in listFieldPath to match it literally
  const listFieldPathEscaped = listFieldPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // Build pattern to match listFieldPath[anything] (e.g., "reviews[0]" or "reviews[new_123]")
  const listItemPattern = new RegExp('^' + listFieldPathEscaped + '\\[[^\\]]+\\]');
  const match = fullPath.match(listItemPattern);

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
    isListItemPath,
    extractListFieldPath,
    extractListIndex,
    isListItemPathFixed,
    isListSubfieldPath,
    extractListFieldPathFixed,
    extractListIndexFixed,
    extractRelativePath,
    getCopyBehavior,
    remapPathIndex,
  };
}
