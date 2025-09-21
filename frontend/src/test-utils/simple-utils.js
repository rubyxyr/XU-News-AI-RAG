const React = require('react');
const { render } = require('@testing-library/react');

/**
 * Create mock user data for tests
 */
const createMockUser = (overrides = {}) => ({
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  created_at: '2024-01-01T00:00:00Z',
  ...overrides,
});

/**
 * Create mock document data for tests
 */
const createMockDocument = (overrides = {}) => ({
  id: 1,
  title: 'Test Document',
  content: 'This is test content',
  summary: 'Test summary',
  source_url: 'https://example.com',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  tags: ['test', 'document'],
  ...overrides,
});

/**
 * Mock localStorage for tests
 */
const createMockLocalStorage = () => {
  let store = {};
  
  return {
    getItem: jest.fn(key => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn(key => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
};

/**
 * Mock file for upload tests
 */
const createMockFile = (name = 'test.pdf', type = 'application/pdf', size = 1024) => {
  const file = new File(['test content'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

/**
 * Common test data
 */
const testData = {
  validEmail: 'test@example.com',
  invalidEmail: 'invalid-email',
  strongPassword: 'StrongPassword123!',
  weakPassword: '123',
  mockApiResponse: {
    success: true,
    data: {},
    message: 'Success',
  },
  mockApiError: {
    response: {
      status: 400,
      data: {
        error: 'Bad Request',
      },
    },
  },
};

module.exports = {
  createMockUser,
  createMockDocument,
  createMockLocalStorage,
  createMockFile,
  testData,
};
