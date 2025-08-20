import { test, expect } from '@playwright/test';

test.describe('Performance Tests', () => {
  test('should load main page within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(10000); // Should load within 10 seconds
  });

  test('should execute code within reasonable time', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Simple code execution
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type('print("Performance test")');
    
    const startTime = Date.now();
    
    const executeButton = page.getByRole('button', { name: /run|execute/i });
    await executeButton.click();
    
    await expect(page.getByText('Performance test')).toBeVisible({ timeout: 15000 });
    
    const executionTime = Date.now() - startTime;
    expect(executionTime).toBeLessThan(15000); // Should execute within 15 seconds
  });

  test('should handle multiple rapid code executions', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    const codeEditor = page.locator('.monaco-editor textarea').first();
    const executeButton = page.getByRole('button', { name: /run|execute/i });
    
    // Execute multiple times rapidly
    for (let i = 0; i < 3; i++) {
      await codeEditor.click();
      await page.keyboard.press('Control+A');
      await page.keyboard.type(`print("Execution ${i + 1}")`);
      
      await executeButton.click();
      await page.waitForTimeout(1000); // Small delay between executions
    }
    
    // Verify all executions completed
    await expect(page.getByText('Execution 3')).toBeVisible({ timeout: 20000 });
  });

  test('should handle large code blocks efficiently', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Large code block
    const largeCode = `
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Generate large dataset
np.random.seed(42)
data = np.random.randn(1000, 5)
df = pd.DataFrame(data, columns=['A', 'B', 'C', 'D', 'E'])

# Perform calculations
df['sum'] = df.sum(axis=1)
df['mean'] = df.mean(axis=1)
df['std'] = df.std(axis=1)

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(df['A'][:100])
plt.title('Sample Data')
plt.show()

print(f"Dataset shape: {df.shape}")
print(f"Mean of column A: {df['A'].mean():.2f}")
`;
    
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type(largeCode);
    
    const startTime = Date.now();
    
    const executeButton = page.getByRole('button', { name: /run|execute/i });
    await executeButton.click();
    
    await expect(page.getByText('Dataset shape:')).toBeVisible({ timeout: 30000 });
    
    const executionTime = Date.now() - startTime;
    expect(executionTime).toBeLessThan(30000); // Should handle large code within 30 seconds
  });
});
