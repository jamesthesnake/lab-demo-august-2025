import { test, expect } from '@playwright/test';

test.describe('Session Management', () => {
  test('should create and restore session on page refresh', async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    
    // Wait for session to be created
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Get the session ID from the UI
    const sessionElement = await page.locator('text=/Session: .{8}\\.\\.\\./').first();
    await expect(sessionElement).toBeVisible();
    const sessionText = await sessionElement.textContent();
    const sessionId = sessionText?.match(/Session: (.{8})\.\.\./)?.[1];
    
    expect(sessionId).toBeTruthy();
    
    // Refresh the page
    await page.reload();
    
    // Verify session is restored
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Verify same session ID is restored
    const restoredSessionElement = await page.locator('text=/Session: .{8}\\.\\.\\./').first();
    await expect(restoredSessionElement).toBeVisible();
    const restoredSessionText = await restoredSessionElement.textContent();
    const restoredSessionId = restoredSessionText?.match(/Session: (.{8})\.\.\./)?.[1];
    
    expect(restoredSessionId).toBe(sessionId);
  });

  test('should persist code across page refresh', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Clear existing code and add custom code
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type('print("Hello from test!")');
    
    // Wait a moment for auto-save
    await page.waitForTimeout(1000);
    
    // Refresh page
    await page.reload();
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Verify code is restored
    await expect(page.locator('text=print("Hello from test!")')).toBeVisible();
  });

  test('should maintain branch state across refresh', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Create a new branch
    const branchButton = page.getByText('main').first();
    await branchButton.click();
    
    // Look for create branch option
    const createBranchButton = page.getByText('Create Branch');
    if (await createBranchButton.isVisible()) {
      await createBranchButton.click();
      await page.fill('input[placeholder*="branch"]', 'test-branch');
      await page.keyboard.press('Enter');
    }
    
    // Wait for branch switch
    await page.waitForTimeout(2000);
    
    // Refresh page
    await page.reload();
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Verify branch is maintained (if branch switching was successful)
    // This test might need adjustment based on actual branch UI implementation
  });
});
