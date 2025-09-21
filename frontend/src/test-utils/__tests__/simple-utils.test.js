const {
  createMockUser,
  createMockDocument,
  createMockLocalStorage,
  createMockFile,
  testData,
} = require('../simple-utils');

describe('Test Utilities', () => {
  describe('createMockUser', () => {
    test('should create user with default values', () => {
      const user = createMockUser();
      
      expect(user).toEqual(
        expect.objectContaining({
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          first_name: 'Test',
          last_name: 'User',
        })
      );
    });

    test('should override default values', () => {
      const user = createMockUser({ 
        username: 'customuser',
        email: 'custom@example.com' 
      });
      
      expect(user.username).toBe('customuser');
      expect(user.email).toBe('custom@example.com');
      expect(user.first_name).toBe('Test'); // Should keep default
    });
  });

  describe('createMockDocument', () => {
    test('should create document with default values', () => {
      const doc = createMockDocument();
      
      expect(doc).toEqual(
        expect.objectContaining({
          id: 1,
          title: 'Test Document',
          content: 'This is test content',
          tags: ['test', 'document'],
        })
      );
    });

    test('should override default values', () => {
      const doc = createMockDocument({ 
        title: 'Custom Document',
        tags: ['custom', 'tag'] 
      });
      
      expect(doc.title).toBe('Custom Document');
      expect(doc.tags).toEqual(['custom', 'tag']);
    });
  });

  describe('createMockLocalStorage', () => {
    test('should create localStorage mock', () => {
      const mockStorage = createMockLocalStorage();
      
      expect(mockStorage).toHaveProperty('getItem');
      expect(mockStorage).toHaveProperty('setItem');
      expect(mockStorage).toHaveProperty('removeItem');
      expect(mockStorage).toHaveProperty('clear');
    });

    test('should handle localStorage operations', () => {
      const mockStorage = createMockLocalStorage();
      
      // Test setItem and getItem
      mockStorage.setItem('key1', 'value1');
      expect(mockStorage.getItem('key1')).toBe('value1');
      
      // Test removeItem
      mockStorage.removeItem('key1');
      expect(mockStorage.getItem('key1')).toBeNull();
    });
  });

  describe('createMockFile', () => {
    test('should create file with default values', () => {
      const file = createMockFile();
      
      expect(file.name).toBe('test.pdf');
      expect(file.type).toBe('application/pdf');
      expect(file.size).toBe(1024);
    });

    test('should create file with custom values', () => {
      const file = createMockFile('custom.txt', 'text/plain', 2048);
      
      expect(file.name).toBe('custom.txt');
      expect(file.type).toBe('text/plain');
      expect(file.size).toBe(2048);
    });
  });

  describe('testData', () => {
    test('should export test data constants', () => {
      expect(testData.validEmail).toBe('test@example.com');
      expect(testData.invalidEmail).toBe('invalid-email');
      expect(testData.strongPassword).toBe('StrongPassword123!');
      expect(testData.weakPassword).toBe('123');
    });

    test('should have mock API responses', () => {
      expect(testData.mockApiResponse).toEqual(
        expect.objectContaining({
          success: true,
          data: {},
          message: 'Success',
        })
      );
      
      expect(testData.mockApiError).toEqual(
        expect.objectContaining({
          response: expect.objectContaining({
            status: 400,
            data: expect.objectContaining({
              error: 'Bad Request',
            }),
          }),
        })
      );
    });
  });
});
