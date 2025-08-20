import { test, expect } from '@playwright/test';

test.describe('UI Components', () => {
  test('should display all main panels', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Check all main panels are visible
    await expect(page.getByText('Code Editor')).toBeVisible();
    await expect(page.getByText('Output Console')).toBeVisible();
    await expect(page.getByText('AI Assistant')).toBeVisible();
    await expect(page.getByText('Analysis History')).toBeVisible();
    await expect(page.getByText('Packages')).toBeVisible();
    await expect(page.getByText('Version Control')).toBeVisible();
    await expect(page.getByText('Security Status')).toBeVisible();
    await expect(page.getByText('Plots & Tables')).toBeVisible();
  });

  test('should show security status information', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    const securityPanel = page.locator('text=Security Status').locator('..');
    await expect(securityPanel).toBeVisible();
    
    // Check for security status indicators
    await expect(securityPanel.locator('text=/HEALTHY|Active|Yes/i')).toBeVisible({ timeout: 5000 });
    
    // Check for panic button
    await expect(securityPanel.getByRole('button', { name: /panic/i })).toBeVisible();
  });

  test('should display package manager', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    const packagesPanel = page.locator('text=Packages').locator('..');
    await expect(packagesPanel).toBeVisible();
    
    // Check for package installation interface
    await expect(packagesPanel.locator('input[placeholder*="package"], input[placeholder*="Package"]')).toBeVisible();
    await expect(packagesPanel.getByRole('button', { name: /install/i })).toBeVisible();
  });

  test('should show branch manager', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Check for branch indicator
    await expect(page.locator('text=main')).toBeVisible();
    
    // Check session ID is displayed
    await expect(page.locator('text=/Session: .{8}\\.\\.\\./i')).toBeVisible();
  });

  test('should handle responsive layout', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Main panels should still be visible (may be stacked)
    await expect(page.getByText('Code Editor')).toBeVisible();
    await expect(page.getByText('AI Assistant')).toBeVisible();
    
    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    
    await expect(page.getByText('Code Editor')).toBeVisible();
    await expect(page.getByText('AI Assistant')).toBeVisible();
    
    // Reset to desktop
    await page.setViewportSize({ width: 1280, height: 720 });
  });
});
