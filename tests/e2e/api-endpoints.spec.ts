import { test, expect } from '@playwright/test';

test.describe('API Endpoints', () => {
  test('should have healthy backend API', async ({ request }) => {
    const response = await request.get('http://localhost:8000/health');
    expect(response.ok()).toBeTruthy();
    
    const health = await response.json();
    expect(health.status).toBe('healthy');
    expect(health.services.kernel_manager).toBe(true);
    expect(health.services.session_manager).toBe(true);
  });

  test('should create and retrieve sessions', async ({ request }) => {
    // Create session
    const createResponse = await request.post('http://localhost:8000/api/sessions/create');
    expect(createResponse.ok()).toBeTruthy();
    
    const session = await createResponse.json();
    expect(session.session_id).toBeTruthy();
    expect(session.active).toBe(true);
    
    // Retrieve session
    const getResponse = await request.get(`http://localhost:8000/api/sessions/${session.session_id}`);
    expect(getResponse.ok()).toBeTruthy();
    
    const retrievedSession = await getResponse.json();
    expect(retrievedSession.session_id).toBe(session.session_id);
  });

  test('should execute code via API', async ({ request }) => {
    // Create session first
    const sessionResponse = await request.post('http://localhost:8000/api/sessions/create');
    const session = await sessionResponse.json();
    
    // Execute code
    const executeResponse = await request.post('http://localhost:8000/api/execute', {
      data: {
        session_id: session.session_id,
        query: 'print("API test")\nresult = 5 * 5\nprint(f"Result: {result}")',
        is_natural_language: false
      }
    });
    
    expect(executeResponse.ok()).toBeTruthy();
    
    const result = await executeResponse.json();
    expect(result.results.stdout).toContain('API test');
    expect(result.results.stdout).toContain('Result: 25');
    expect(result.results.status).toBe('ok');
  });

  test('should handle git operations via API', async ({ request }) => {
    // Create session
    const sessionResponse = await request.post('http://localhost:8000/api/sessions/create');
    const session = await sessionResponse.json();
    
    // Create manual commit
    const commitResponse = await request.post(`http://localhost:8000/api/git/commit/${session.session_id}`, {
      data: {
        message: 'API test commit',
        code: 'print("test commit")',
        branch: 'main',
        description: 'Testing commit creation via API'
      }
    });
    
    expect(commitResponse.ok()).toBeTruthy();
    
    const commit = await commitResponse.json();
    expect(commit.message).toBe('API test commit');
    expect(commit.status).toBe('committed');
    
    // Get commit history
    const historyResponse = await request.get(`http://localhost:8000/api/git/sessions/${session.session_id}/commits?branch=main`);
    expect(historyResponse.ok()).toBeTruthy();
    
    const history = await historyResponse.json();
    expect(Array.isArray(history)).toBeTruthy();
  });

  test('should manage conversation history via API', async ({ request }) => {
    // Create session
    const sessionResponse = await request.post('http://localhost:8000/api/sessions/create');
    const session = await sessionResponse.json();
    
    // Add conversation message
    const messageResponse = await request.post(`http://localhost:8000/api/sessions/${session.session_id}/conversation`, {
      data: {
        role: 'user',
        content: 'Create a simple plot'
      }
    });
    
    expect(messageResponse.ok()).toBeTruthy();
    
    // Get conversation history
    const historyResponse = await request.get(`http://localhost:8000/api/sessions/${session.session_id}/conversation`);
    expect(historyResponse.ok()).toBeTruthy();
    
    const history = await historyResponse.json();
    expect(history.conversation_history).toHaveLength(1);
    expect(history.conversation_history[0].content).toBe('Create a simple plot');
  });

  test('should handle security endpoints', async ({ request }) => {
    // Test security health
    const healthResponse = await request.get('http://localhost:8000/api/security/health');
    expect(healthResponse.ok()).toBeTruthy();
    
    const health = await healthResponse.json();
    expect(health.system_status).toBeTruthy();
    
    // Test container listing
    const containersResponse = await request.get('http://localhost:8000/api/security/containers');
    expect(containersResponse.ok()).toBeTruthy();
    
    const containers = await containersResponse.json();
    expect(Array.isArray(containers.containers)).toBeTruthy();
  });

  test('should handle package management', async ({ request }) => {
    // Create session
    const sessionResponse = await request.post('http://localhost:8000/api/sessions/create');
    const session = await sessionResponse.json();
    
    // List installed packages
    const packagesResponse = await request.get(`http://localhost:8000/api/packages/${session.session_id}/list`);
    expect(packagesResponse.ok()).toBeTruthy();
    
    const packages = await packagesResponse.json();
    expect(Array.isArray(packages.packages)).toBeTruthy();
  });
});
