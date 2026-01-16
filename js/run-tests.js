#!/usr/bin/env node
/**
 * Simple test runner for comparison-helpers.js
 *
 * This script runs tests without requiring npm/Jest installation.
 * It can be executed directly with Node.js.
 *
 * Usage: node run-tests.js
 */

const helpers = require('./src/comparison-helpers');

// Simple test framework
let passed = 0;
let failed = 0;
let xfailed = 0;
const failures = [];

function test(name, fn, expectFail = false) {
  try {
    fn();
    if (expectFail) {
      // Expected to fail but passed - this is unexpected
      failures.push({ name, error: 'Expected to fail but passed', type: 'unexpected_pass' });
      failed++;
    } else {
      passed++;
    }
  } catch (e) {
    if (expectFail) {
      xfailed++;
    } else {
      failures.push({ name, error: e.message, type: 'fail' });
      failed++;
    }
  }
}

function xfail(name, fn) {
  test(name, fn, true);
}

function expect(actual) {
  return {
    toBe(expected) {
      if (actual !== expected) {
        throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
      }
    },
    toBeNull() {
      if (actual !== null) {
        throw new Error(`Expected null, got ${JSON.stringify(actual)}`);
      }
    },
    not: {
      toBe(expected) {
        if (actual === expected) {
          throw new Error(`Expected NOT ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
        }
      },
      toBeNull() {
        if (actual === null) {
          throw new Error(`Expected NOT null, got null`);
        }
      }
    }
  };
}

console.log('Running JavaScript unit tests for comparison-helpers.js\n');
console.log('=' .repeat(70));

// ============================================================================
// Tests for isListItemPath
// ============================================================================
console.log('\n--- isListItemPath ---');

test('isListItemPath matches numeric full items', () => {
  expect(helpers.isListItemPath('reviews[0]')).toBe(true);
  expect(helpers.isListItemPath('reviews[1]')).toBe(true);
  expect(helpers.isListItemPath('reviews[99]')).toBe(true);
  expect(helpers.isListItemPath('addresses[0]')).toBe(true);
});

test('isListItemPath matches placeholder full items', () => {
  expect(helpers.isListItemPath('reviews[new_1234567890]')).toBe(true);
  expect(helpers.isListItemPath('addresses[new_123]')).toBe(true);
});

test('isListItemPath does NOT match subfields', () => {
  expect(helpers.isListItemPath('reviews[0].rating')).toBe(false);
  expect(helpers.isListItemPath('addresses[new_123].street')).toBe(false);
});

test('isListItemPath does NOT match non-list paths', () => {
  expect(helpers.isListItemPath('reviews')).toBe(false);
  expect(helpers.isListItemPath('name')).toBe(false);
});

// ============================================================================
// Tests for isListItemPathFixed
// ============================================================================
console.log('\n--- isListItemPathFixed ---');

test('isListItemPathFixed matches numeric full items', () => {
  expect(helpers.isListItemPathFixed('reviews[0]')).toBe(true);
  expect(helpers.isListItemPathFixed('reviews[1]')).toBe(true);
});

test('isListItemPathFixed matches placeholder full items', () => {
  expect(helpers.isListItemPathFixed('reviews[new_1234567890]')).toBe(true);
  expect(helpers.isListItemPathFixed('addresses[new_123]')).toBe(true);
});

test('isListItemPathFixed does NOT match subfields', () => {
  expect(helpers.isListItemPathFixed('reviews[0].rating')).toBe(false);
  expect(helpers.isListItemPathFixed('reviews[new_123].comment')).toBe(false);
});

test('isListItemPathFixed does NOT match non-list paths', () => {
  expect(helpers.isListItemPathFixed('reviews')).toBe(false);
  expect(helpers.isListItemPathFixed('name')).toBe(false);
});

// ============================================================================
// Tests for isListSubfieldPath
// ============================================================================
console.log('\n--- isListSubfieldPath ---');

test('isListSubfieldPath matches subfields with numeric indices', () => {
  expect(helpers.isListSubfieldPath('reviews[0].rating')).toBe(true);
  expect(helpers.isListSubfieldPath('addresses[1].street')).toBe(true);
});

test('isListSubfieldPath matches subfields with placeholder indices', () => {
  expect(helpers.isListSubfieldPath('reviews[new_123].rating')).toBe(true);
});

test('isListSubfieldPath does NOT match full items', () => {
  expect(helpers.isListSubfieldPath('reviews[0]')).toBe(false);
  expect(helpers.isListSubfieldPath('reviews[new_123]')).toBe(false);
});

// ============================================================================
// Tests for extractListFieldPath
// ============================================================================
console.log('\n--- extractListFieldPath ---');

test('extractListFieldPath works for numeric indices', () => {
  expect(helpers.extractListFieldPath('reviews[0]')).toBe('reviews');
  expect(helpers.extractListFieldPath('addresses[0].street')).toBe('addresses');
});

test('extractListFieldPath works for placeholders', () => {
  expect(helpers.extractListFieldPath('reviews[new_1234567890]')).toBe('reviews');
  expect(helpers.extractListFieldPath('addresses[new_123].street')).toBe('addresses');
});

// ============================================================================
// Tests for extractListFieldPathFixed
// ============================================================================
console.log('\n--- extractListFieldPathFixed ---');

test('extractListFieldPathFixed works for numeric indices', () => {
  expect(helpers.extractListFieldPathFixed('reviews[0]')).toBe('reviews');
  expect(helpers.extractListFieldPathFixed('addresses[0].street')).toBe('addresses');
});

test('extractListFieldPathFixed works for placeholder indices', () => {
  expect(helpers.extractListFieldPathFixed('reviews[new_1234567890]')).toBe('reviews');
  expect(helpers.extractListFieldPathFixed('addresses[new_123].street')).toBe('addresses');
});

// ============================================================================
// Tests for extractListIndex
// ============================================================================
console.log('\n--- extractListIndex ---');

test('extractListIndex works for numeric indices', () => {
  expect(helpers.extractListIndex('reviews[0]')).toBe(0);
  expect(helpers.extractListIndex('reviews[5]')).toBe(5);
  expect(helpers.extractListIndex('addresses[0].street')).toBe(0);
});

test('extractListIndex works for placeholders', () => {
  expect(helpers.extractListIndex('reviews[new_1234567890]')).toBe('new_1234567890');
  expect(helpers.extractListIndex('reviews[new_0]')).toBe('new_0');
});

// ============================================================================
// Tests for extractListIndexFixed
// ============================================================================
console.log('\n--- extractListIndexFixed ---');

test('extractListIndexFixed works for numeric indices', () => {
  expect(helpers.extractListIndexFixed('reviews[0]')).toBe(0);
  expect(helpers.extractListIndexFixed('reviews[5]')).toBe(5);
});

test('extractListIndexFixed works for placeholder indices', () => {
  expect(helpers.extractListIndexFixed('reviews[new_1234567890]')).toBe('new_1234567890');
  expect(helpers.extractListIndexFixed('reviews[new_0]')).toBe('new_0');
});

// ============================================================================
// Tests for getCopyBehavior
// ============================================================================
console.log('\n--- getCopyBehavior ---');

test('getCopyBehavior returns add_new_item for full list items', () => {
  expect(helpers.getCopyBehavior('reviews[0]')).toBe('add_new_item');
  expect(helpers.getCopyBehavior('reviews[new_123]')).toBe('add_new_item');
});

test('getCopyBehavior returns update_existing_subfield for subfields', () => {
  expect(helpers.getCopyBehavior('reviews[0].rating')).toBe('update_existing_subfield');
  expect(helpers.getCopyBehavior('reviews[new_123].rating')).toBe('update_existing_subfield');
});

test('getCopyBehavior returns standard_copy for non-list paths', () => {
  expect(helpers.getCopyBehavior('reviews')).toBe('standard_copy');
  expect(helpers.getCopyBehavior('name')).toBe('standard_copy');
});

// ============================================================================
// Tests for extractRelativePath
// ============================================================================
console.log('\n--- extractRelativePath ---');

test('extractRelativePath extracts subfield portion', () => {
  expect(helpers.extractRelativePath('reviews[0].rating', 'reviews')).toBe('.rating');
  expect(helpers.extractRelativePath('reviews[new_123].comment', 'reviews')).toBe('.comment');
});

test('extractRelativePath returns empty for full items', () => {
  expect(helpers.extractRelativePath('reviews[0]', 'reviews')).toBe('');
  expect(helpers.extractRelativePath('reviews[new_123]', 'reviews')).toBe('');
});

// ============================================================================
// Tests for remapPathIndex
// ============================================================================
console.log('\n--- remapPathIndex ---');

test('remapPathIndex changes index correctly', () => {
  expect(helpers.remapPathIndex('reviews[0]', '0', 'new_123')).toBe('reviews[new_123]');
  expect(helpers.remapPathIndex('reviews[0].rating', '0', 'new_123')).toBe('reviews[new_123].rating');
  expect(helpers.remapPathIndex('reviews[new_123]', 'new_123', '5')).toBe('reviews[5]');
});

// ============================================================================
// Summary
// ============================================================================
console.log('\n' + '=' .repeat(70));
console.log('\nTest Results:');
console.log(`  Passed:  ${passed}`);
console.log(`  Failed:  ${failed}`);
console.log(`  XFailed: ${xfailed} (expected failures documenting bugs)`);
console.log(`  Total:   ${passed + failed + xfailed}`);

if (failures.length > 0) {
  console.log('\nFailures:');
  failures.forEach(f => {
    console.log(`  - ${f.name}: ${f.error}`);
  });
}

// Output JSON for pytest integration
const result = {
  passed,
  failed,
  xfailed,
  total: passed + failed + xfailed,
  failures: failures.filter(f => f.type === 'fail'),
  unexpected_passes: failures.filter(f => f.type === 'unexpected_pass'),
};

console.log('\n--- JSON Output (for pytest integration) ---');
console.log(JSON.stringify(result));

// Exit with error code if there are unexpected failures
process.exit(failed > 0 ? 1 : 0);
