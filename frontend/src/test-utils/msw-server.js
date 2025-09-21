const { setupServer } = require('msw/node');
const { rest } = require('msw');

// API endpoint mocks
const apiHandlers = [
  // Auth endpoints
  rest.post('/api/auth/register', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        message: 'User registered successfully',
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          created_at: '2024-01-01T00:00:00Z',
        },
        access_token: 'mock-jwt-token',
        refresh_token: 'mock-refresh-token',
      })
    );
  }),

  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        message: 'Login successful',
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          created_at: '2024-01-01T00:00:00Z',
        },
        access_token: 'mock-jwt-token',
        refresh_token: 'mock-refresh-token',
      })
    );
  }),

  rest.post('/api/auth/logout', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ message: 'Logout successful' })
    );
  }),

  rest.get('/api/auth/profile', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          first_name: 'Test',
          last_name: 'User',
          created_at: '2024-01-01T00:00:00Z',
        },
        stats: {
          total_documents: 10,
          recent_activity: [],
        },
      })
    );
  }),

  // Documents endpoints
  rest.get('/api/content/documents', (req, res, ctx) => {
    const page = req.url.searchParams.get('page') || 1;
    const per_page = req.url.searchParams.get('per_page') || 10;
    
    return res(
      ctx.status(200),
      ctx.json({
        documents: [
          {
            id: 1,
            title: 'Test Document 1',
            content: 'This is test content 1',
            summary: 'Summary 1',
            source_url: 'https://example.com/1',
            created_at: '2024-01-01T00:00:00Z',
            tags: ['test', 'document'],
          },
          {
            id: 2,
            title: 'Test Document 2',
            content: 'This is test content 2',
            summary: 'Summary 2',
            source_url: 'https://example.com/2',
            created_at: '2024-01-02T00:00:00Z',
            tags: ['test', 'sample'],
          },
        ],
        pagination: {
          page: parseInt(page),
          per_page: parseInt(per_page),
          total: 2,
          pages: 1,
        },
      })
    );
  }),

  rest.post('/api/content/documents', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        message: 'Document created successfully',
        document: {
          id: 3,
          title: 'New Document',
          content: 'New document content',
          created_at: new Date().toISOString(),
          tags: [],
        },
      })
    );
  }),

  rest.put('/api/content/documents/:id', (req, res, ctx) => {
    const { id } = req.params;
    return res(
      ctx.status(200),
      ctx.json({
        message: 'Document updated successfully',
        document: {
          id: parseInt(id),
          title: 'Updated Document',
          content: 'Updated content',
          updated_at: new Date().toISOString(),
        },
      })
    );
  }),

  rest.delete('/api/content/documents/:id', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ message: 'Document deleted successfully' })
    );
  }),

  // Search endpoints
  rest.post('/api/search/semantic', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        results: [
          {
            id: 1,
            title: 'Search Result 1',
            content: 'Matching content 1',
            similarity_score: 0.95,
            source_url: 'https://example.com/result1',
          },
          {
            id: 2,
            title: 'Search Result 2',
            content: 'Matching content 2',
            similarity_score: 0.87,
            source_url: 'https://example.com/result2',
          },
        ],
        query: 'test query',
        total: 2,
      })
    );
  }),

  rest.get('/api/search/suggestions', (req, res, ctx) => {
    const query = req.url.searchParams.get('query');
    return res(
      ctx.status(200),
      ctx.json({
        suggestions: [
          `${query} suggestion 1`,
          `${query} suggestion 2`,
          `${query} suggestion 3`,
        ],
      })
    );
  }),

  // Sources endpoints
  rest.get('/api/sources', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        sources: [
          {
            id: 1,
            name: 'Test RSS Feed',
            url: 'https://example.com/rss',
            source_type: 'rss',
            is_active: true,
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
      })
    );
  }),

  // Analytics endpoints
  rest.get('/api/analytics/dashboard', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        stats: {
          total_documents: 150,
          total_searches: 45,
          active_sources: 8,
          recent_activity: [
            {
              id: 1,
              action: 'document_created',
              timestamp: '2024-01-01T12:00:00Z',
              details: { title: 'New Document' },
            },
          ],
        },
        charts: {
          documents_over_time: [
            { date: '2024-01-01', count: 5 },
            { date: '2024-01-02', count: 8 },
          ],
        },
      })
    );
  }),
];

// Error handlers for testing error scenarios
const errorHandlers = [
  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(401),
      ctx.json({ error: 'Invalid credentials' })
    );
  }),

  rest.get('/api/content/documents', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({ error: 'Internal server error' })
    );
  }),

  rest.post('/api/content/documents', (req, res, ctx) => {
    return res(
      ctx.status(400),
      ctx.json({ error: 'Validation error' })
    );
  }),
];

// Create the server
const server = setupServer(...apiHandlers);

// Helper function to override handlers for specific tests
const overrideHandlers = (...handlers) => {
  server.use(...handlers);
};

module.exports = {
  server,
  errorHandlers,
  overrideHandlers,
};
