/**
 * Jest tests for comparison-helpers.js
 *
 * These tests validate the JavaScript helper functions used in ComparisonForm
 * for list item path detection and manipulation.
 *
 * Several tests are marked with .failing() to document known bugs that need fixing.
 */

const {
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
} = require('../src/comparison-helpers');

describe('isListItemPath (current buggy implementation)', () => {
  describe('should match numeric indices', () => {
    test.each([
      ['reviews[0]', true],
      ['reviews[1]', true],
      ['reviews[99]', true],
      ['addresses[0].street', true],
      ['items[5].nested.deep', true],
    ])('isListItemPath("%s") should be %s', (path, expected) => {
      expect(isListItemPath(path)).toBe(expected);
    });
  });

  describe('should NOT match non-list paths', () => {
    test.each([
      ['reviews', false],
      ['name', false],
      ['address.street', false],
    ])('isListItemPath("%s") should be %s', (path, expected) => {
      expect(isListItemPath(path)).toBe(expected);
    });
  });

  describe('BUG: fails to match placeholder indices', () => {
    // These tests document the bug - they FAIL with current implementation
    test.failing('should match new_ placeholder index', () => {
      expect(isListItemPath('reviews[new_1234567890]')).toBe(true);
    });

    test.failing('should match placeholder in nested path', () => {
      expect(isListItemPath('addresses[new_123].street')).toBe(true);
    });

    test.failing('should match placeholder with underscore', () => {
      expect(isListItemPath('items[new_999999]')).toBe(true);
    });
  });
});

describe('isListItemPathFixed', () => {
  describe('matches numeric indices (full items only)', () => {
    test.each([
      ['reviews[0]', true],
      ['reviews[1]', true],
      ['items[99]', true],
    ])('isListItemPathFixed("%s") should be %s', (path, expected) => {
      expect(isListItemPathFixed(path)).toBe(expected);
    });
  });

  describe('matches placeholder indices (full items only)', () => {
    test.each([
      ['reviews[new_1234567890]', true],
      ['addresses[new_123]', true],
      ['items[new_0]', true],
    ])('isListItemPathFixed("%s") should be %s', (path, expected) => {
      expect(isListItemPathFixed(path)).toBe(expected);
    });
  });

  describe('does NOT match subfields', () => {
    test.each([
      ['reviews[0].rating', false],
      ['reviews[new_123].comment', false],
      ['addresses[0].street', false],
      ['items[5].nested.deep', false],
    ])('isListItemPathFixed("%s") should be %s', (path, expected) => {
      expect(isListItemPathFixed(path)).toBe(expected);
    });
  });

  describe('does NOT match non-list paths', () => {
    test.each([
      ['reviews', false],
      ['name', false],
      ['address.street', false],
    ])('isListItemPathFixed("%s") should be %s', (path, expected) => {
      expect(isListItemPathFixed(path)).toBe(expected);
    });
  });
});

describe('isListSubfieldPath', () => {
  describe('matches subfields with numeric indices', () => {
    test.each([
      ['reviews[0].rating', true],
      ['reviews[0].comment', true],
      ['addresses[1].street', true],
      ['items[0].nested.deep', true],
    ])('isListSubfieldPath("%s") should be %s', (path, expected) => {
      expect(isListSubfieldPath(path)).toBe(expected);
    });
  });

  describe('matches subfields with placeholder indices', () => {
    test.each([
      ['reviews[new_123].rating', true],
      ['addresses[new_456].street', true],
      ['items[new_0].name', true],
    ])('isListSubfieldPath("%s") should be %s', (path, expected) => {
      expect(isListSubfieldPath(path)).toBe(expected);
    });
  });

  describe('does NOT match full items', () => {
    test.each([
      ['reviews[0]', false],
      ['reviews[new_123]', false],
      ['addresses[1]', false],
    ])('isListSubfieldPath("%s") should be %s', (path, expected) => {
      expect(isListSubfieldPath(path)).toBe(expected);
    });
  });

  describe('does NOT match non-list paths', () => {
    test.each([
      ['reviews', false],
      ['name', false],
      ['address.street', false],
    ])('isListSubfieldPath("%s") should be %s', (path, expected) => {
      expect(isListSubfieldPath(path)).toBe(expected);
    });
  });
});

describe('extractListFieldPath (current buggy implementation)', () => {
  describe('works for numeric indices', () => {
    test.each([
      ['reviews[0]', 'reviews'],
      ['reviews[5]', 'reviews'],
      ['addresses[0].street', 'addresses'],
      ['items[99].nested.deep', 'items'],
    ])('extractListFieldPath("%s") should be "%s"', (path, expected) => {
      expect(extractListFieldPath(path)).toBe(expected);
    });
  });

  describe('BUG: fails for placeholder indices', () => {
    test.failing('should extract field path from placeholder index', () => {
      expect(extractListFieldPath('reviews[new_1234567890]')).toBe('reviews');
    });

    test.failing('should extract from nested placeholder path', () => {
      expect(extractListFieldPath('addresses[new_123].street')).toBe('addresses');
    });
  });
});

describe('extractListFieldPathFixed', () => {
  describe('works for numeric indices', () => {
    test.each([
      ['reviews[0]', 'reviews'],
      ['reviews[5]', 'reviews'],
      ['addresses[0].street', 'addresses'],
    ])('extractListFieldPathFixed("%s") should be "%s"', (path, expected) => {
      expect(extractListFieldPathFixed(path)).toBe(expected);
    });
  });

  describe('works for placeholder indices', () => {
    test.each([
      ['reviews[new_1234567890]', 'reviews'],
      ['reviews[new_0]', 'reviews'],
      ['addresses[new_123].street', 'addresses'],
      ['items[new_999].nested.deep', 'items'],
    ])('extractListFieldPathFixed("%s") should be "%s"', (path, expected) => {
      expect(extractListFieldPathFixed(path)).toBe(expected);
    });
  });
});

describe('extractListIndex (current buggy implementation)', () => {
  describe('works for numeric indices', () => {
    test.each([
      ['reviews[0]', 0],
      ['reviews[5]', 5],
      ['reviews[99]', 99],
      ['addresses[0].street', 0],
      ['items[42].nested', 42],
    ])('extractListIndex("%s") should be %s', (path, expected) => {
      expect(extractListIndex(path)).toBe(expected);
    });
  });

  describe('BUG: returns null for placeholder indices', () => {
    test.failing('should extract index from placeholder', () => {
      // The current implementation returns null for placeholders
      // This test documents that it SHOULD return something useful
      const result = extractListIndex('reviews[new_1234567890]');
      expect(result).not.toBeNull();
    });
  });
});

describe('extractListIndexFixed', () => {
  describe('works for numeric indices', () => {
    test.each([
      ['reviews[0]', 0],
      ['reviews[5]', 5],
      ['addresses[0].street', 0],
    ])('extractListIndexFixed("%s") should be %s', (path, expected) => {
      expect(extractListIndexFixed(path)).toBe(expected);
    });
  });

  describe('works for placeholder indices', () => {
    test.each([
      ['reviews[new_1234567890]', 'new_1234567890'],
      ['reviews[new_0]', 'new_0'],
      ['addresses[new_123].street', 'new_123'],
    ])('extractListIndexFixed("%s") should be "%s"', (path, expected) => {
      expect(extractListIndexFixed(path)).toBe(expected);
    });
  });

  test('returns null for non-list paths', () => {
    expect(extractListIndexFixed('reviews')).toBeNull();
    expect(extractListIndexFixed('name')).toBeNull();
  });
});

describe('extractRelativePath', () => {
  describe('extracts relative path from full path', () => {
    test.each([
      ['reviews[0].rating', 'reviews', '.rating'],
      ['reviews[0].comment', 'reviews', '.comment'],
      ['reviews[new_123].rating', 'reviews', '.rating'],
      ['addresses[0].street', 'addresses', '.street'],
      ['addresses[0].tags[0]', 'addresses', '.tags[0]'],
      ['items[0].nested.deep', 'items', '.nested.deep'],
    ])('extractRelativePath("%s", "%s") should be "%s"', (fullPath, listFieldPath, expected) => {
      expect(extractRelativePath(fullPath, listFieldPath)).toBe(expected);
    });
  });

  describe('returns empty string for full items', () => {
    test.each([
      ['reviews[0]', 'reviews', ''],
      ['reviews[new_123]', 'reviews', ''],
      ['addresses[5]', 'addresses', ''],
    ])('extractRelativePath("%s", "%s") should be "%s"', (fullPath, listFieldPath, expected) => {
      expect(extractRelativePath(fullPath, listFieldPath)).toBe(expected);
    });
  });
});

describe('getCopyBehavior', () => {
  describe('returns "add_new_item" for full list items', () => {
    test.each([
      'reviews[0]',
      'reviews[1]',
      'addresses[new_123]',
      'items[new_999999]',
    ])('getCopyBehavior("%s") should be "add_new_item"', (path) => {
      expect(getCopyBehavior(path)).toBe('add_new_item');
    });
  });

  describe('returns "update_existing_subfield" for subfields', () => {
    test.each([
      'reviews[0].rating',
      'reviews[0].comment',
      'reviews[new_123].rating',
      'addresses[0].street',
      'items[5].nested.deep',
    ])('getCopyBehavior("%s") should be "update_existing_subfield"', (path) => {
      expect(getCopyBehavior(path)).toBe('update_existing_subfield');
    });
  });

  describe('returns "standard_copy" for non-list paths', () => {
    test.each([
      'reviews',
      'name',
      'address.street',
      'tags',
    ])('getCopyBehavior("%s") should be "standard_copy"', (path) => {
      expect(getCopyBehavior(path)).toBe('standard_copy');
    });
  });
});

describe('remapPathIndex', () => {
  test.each([
    ['reviews[0]', '0', 'new_123', 'reviews[new_123]'],
    ['reviews[0].rating', '0', 'new_123', 'reviews[new_123].rating'],
    ['reviews[new_123]', 'new_123', '5', 'reviews[5]'],
    ['addresses[0].street', '0', '1', 'addresses[1].street'],
  ])('remapPathIndex("%s", "%s", "%s") should be "%s"', (source, sourceIdx, targetIdx, expected) => {
    expect(remapPathIndex(source, sourceIdx, targetIdx)).toBe(expected);
  });
});

describe('Integration: Copy behavior decision flow', () => {
  /**
   * This test suite validates the complete flow of deciding how to handle
   * a copy operation based on the path structure.
   */

  test('copying full list should use standard copy', () => {
    const path = 'reviews';
    expect(isListItemPathFixed(path)).toBe(false);
    expect(isListSubfieldPath(path)).toBe(false);
    expect(getCopyBehavior(path)).toBe('standard_copy');
  });

  test('copying full list item should add new item', () => {
    const path = 'reviews[0]';
    expect(isListItemPathFixed(path)).toBe(true);
    expect(isListSubfieldPath(path)).toBe(false);
    expect(getCopyBehavior(path)).toBe('add_new_item');
  });

  test('copying subfield should update existing item', () => {
    const path = 'reviews[0].rating';
    expect(isListItemPathFixed(path)).toBe(false);
    expect(isListSubfieldPath(path)).toBe(true);
    expect(getCopyBehavior(path)).toBe('update_existing_subfield');
  });

  test('copying newly added item should add new item', () => {
    const path = 'reviews[new_1234567890]';
    expect(isListItemPathFixed(path)).toBe(true);
    expect(isListSubfieldPath(path)).toBe(false);
    expect(getCopyBehavior(path)).toBe('add_new_item');
  });

  test('copying subfield of newly added item should update existing', () => {
    const path = 'reviews[new_1234567890].rating';
    expect(isListItemPathFixed(path)).toBe(false);
    expect(isListSubfieldPath(path)).toBe(true);
    expect(getCopyBehavior(path)).toBe('update_existing_subfield');
  });
});

describe('Bug reproduction: Current implementation failures', () => {
  /**
   * These tests demonstrate the exact bugs reported by users.
   */

  describe('Bug 1: Copying newly added items fails', () => {
    test('current isListItemPath fails for new_ placeholders', () => {
      // User adds a new item (not saved yet) with path reviews[new_123]
      // Then tries to copy it to the other side
      // Current implementation doesn't detect it as a list item
      const newItemPath = 'reviews[new_1234567890]';

      // Current buggy behavior
      expect(isListItemPath(newItemPath)).toBe(false); // BUG: should be true

      // Fixed behavior
      expect(isListItemPathFixed(newItemPath)).toBe(true);
    });
  });

  describe('Bug 2: Copying subfield creates new item instead of updating', () => {
    test('current implementation treats subfield same as full item', () => {
      const subfieldPath = 'reviews[0].rating';

      // Current buggy behavior: both full item and subfield match the pattern
      expect(isListItemPath('reviews[0]')).toBe(true);
      expect(isListItemPath(subfieldPath)).toBe(true); // BUG: same result!

      // The code can't distinguish between copying a full item (should add new)
      // and copying a subfield (should update existing)

      // Fixed behavior: clear distinction
      expect(isListItemPathFixed('reviews[0]')).toBe(true);  // Full item
      expect(isListItemPathFixed(subfieldPath)).toBe(false); // Subfield
      expect(isListSubfieldPath(subfieldPath)).toBe(true);   // Detected as subfield
    });
  });

  describe('Bug 3: extractListFieldPath fails for placeholders', () => {
    test('cannot extract field path from newly added items', () => {
      const path = 'reviews[new_1234567890]';

      // Current buggy behavior: returns the full path unchanged
      expect(extractListFieldPath(path)).toBe(path); // BUG: should be "reviews"

      // Fixed behavior
      expect(extractListFieldPathFixed(path)).toBe('reviews');
    });
  });
});
