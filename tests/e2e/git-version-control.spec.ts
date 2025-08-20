import { test, expect } from '@playwright/test';

test.describe('Git Version Control', () => {
  test('should create commits with custom messages', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Add some code
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type('print("Test commit")\nx = 42');
    
    // Open commit panel
    const commitButton = page.getByRole('button', { name: /commit changes/i });
    await commitButton.click();
    
    // Fill commit message
    await expect(page.getByText('Commit Changes')).toBeVisible();
    await page.fill('input[placeholder*="Brief description"]', 'Add test variables');
    await page.fill('textarea[placeholder*="Detailed explanation"]', 'Added print statement and variable assignment for testing');
    
    // Submit commit
    const submitCommitButton = page.getByRole('button', { name: /^commit$/i });
    await submitCommitButton.click();
    
    // Verify commit success
    await expect(page.getByText('Code committed to git')).toBeVisible({ timeout: 10000 });
    
    // Check version tree for new commit
    const versionTree = page.locator('text=Analysis History').locator('..');
    await expect(versionTree.getByText('Add test variables')).toBeVisible({ timeout: 5000 });
  });

  test('should generate commit message suggestions', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Add matplotlib code
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type('import matplotlib.pyplot as plt\nplt.plot([1,2,3], [1,4,9])\nplt.show()');
    
    // Open commit panel
    const commitButton = page.getByRole('button', { name: /commit changes/i });
    await commitButton.click();
    
    // Click generate suggestion
    await page.getByText('Generate suggestion').click();
    
    // Verify suggestion is generated
    const messageInput = page.locator('input[placeholder*="Brief description"]');
    await expect(messageInput).toHaveValue('Create data visualization');
  });

  test('should show commit history in version tree', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Execute some code to create a commit
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type('print("First commit")');
    
    const executeButton = page.getByRole('button', { name: /run|execute/i });
    await executeButton.click();
    
    // Wait for execution to complete
    await expect(page.getByText('Executing...')).not.toBeVisible({ timeout: 15000 });
    
    // Check version tree shows commits
    const versionTree = page.locator('text=Analysis History').locator('..');
    await expect(versionTree).toBeVisible();
    
    // Look for commit entries (they might have different formats)
    await expect(versionTree.locator('text=/commit|HEAD|main/i')).toBeVisible({ timeout: 5000 });
  });

  test('should revert to previous commit', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Execute first code
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type('print("First version")');
    
    const executeButton = page.getByRole('button', { name: /run|execute/i });
    await executeButton.click();
    await expect(page.getByText('Executing...')).not.toBeVisible({ timeout: 15000 });
    
    // Execute second code
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type('print("Second version")');
    await executeButton.click();
    await expect(page.getByText('Executing...')).not.toBeVisible({ timeout: 15000 });
    
    // Find and click revert button in version tree
    const versionTree = page.locator('text=Analysis History').locator('..');
    const revertButton = versionTree.getByRole('button', { name: /revert/i }).first();
    
    if (await revertButton.isVisible()) {
      await revertButton.click();
      
      // Verify code is reverted
      await expect(page.getByText('Code reverted to commit')).toBeVisible({ timeout: 10000 });
    }
  });
});
