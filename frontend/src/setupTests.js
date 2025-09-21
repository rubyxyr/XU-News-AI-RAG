// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Polyfill for TextEncoder/TextDecoder (required for MSW in Node.js environment)
if (typeof global.TextEncoder === 'undefined') {
  const { TextEncoder, TextDecoder } = require('util');
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

// Setup MSW server for API mocking (conditional import to avoid issues)
let server;
try {
  const mswModule = require('./test-utils/msw-server');
  server = mswModule.server;
  
  // Establish API mocking before all tests
  beforeAll(() => server?.listen({ onUnhandledRequest: 'warn' }));
  
  // Reset any runtime request handlers after each test
  afterEach(() => server?.resetHandlers());
  
  // Clean up after all tests
  afterAll(() => server?.close());
} catch (error) {
  console.warn('MSW server setup failed:', error.message);
}

// Mock window.matchMedia (used by Material-UI)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock ResizeObserver (used by various components)
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock IntersectionObserver (used for infinite scroll)
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.sessionStorage = sessionStorageMock;

// Mock fetch API
global.fetch = jest.fn();

// Mock URL.createObjectURL (used for file uploads)
global.URL.createObjectURL = jest.fn(() => 'mocked-url');
global.URL.revokeObjectURL = jest.fn();

// Mock File and FileReader
global.File = class MockFile {
  constructor(parts, filename, properties) {
    this.parts = parts;
    this.name = filename;
    this.size = properties?.size || parts.join('').length;
    this.type = properties?.type || '';
    this.lastModified = properties?.lastModified || Date.now();
  }
};

global.FileReader = class MockFileReader {
  constructor() {
    this.readyState = 0;
    this.result = null;
    this.error = null;
  }
  
  readAsText(file) {
    this.readyState = 2;
    this.result = file.parts.join('');
    if (this.onload) this.onload({ target: this });
  }
  
  readAsDataURL(file) {
    this.readyState = 2;
    this.result = `data:${file.type};base64,${btoa(file.parts.join(''))}`;
    if (this.onload) this.onload({ target: this });
  }
};

// Mock console methods to reduce noise in tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: ReactDOM.render is deprecated') ||
       args[0].includes('Warning: An invalid form control') ||
       args[0].includes('Warning: componentWillReceiveProps'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Clean up after each test
afterEach(() => {
  jest.clearAllMocks();
  localStorageMock.clear();
  sessionStorageMock.clear();
});
