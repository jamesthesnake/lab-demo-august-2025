import { test, expect } from '@playwright/test';

test.describe('Code Execution', () => {
  test('should execute simple Python code', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Clear existing code and add simple test code
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type('print("Hello World!")\nresult = 2 + 2\nprint(f"2 + 2 = {result}")');
    
    // Execute code
    const executeButton = page.getByRole('button', { name: /run|execute/i });
    await executeButton.click();
    
    // Wait for execution to complete
    await expect(page.getByText('Executing...')).toBeVisible();
    await expect(page.getByText('Executing...')).not.toBeVisible({ timeout: 15000 });
    
    // Verify output
    await expect(page.getByText('Hello World!')).toBeVisible();
    await expect(page.getByText('2 + 2 = 4')).toBeVisible();
  });

  test('should handle code execution errors', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Add code with syntax error
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type('print("Missing quote)');
    
    // Execute code
    const executeButton = page.getByRole('button', { name: /run|execute/i });
    await executeButton.click();
    
    // Wait for execution to complete
    await expect(page.getByText('Executing...')).toBeVisible();
    await expect(page.getByText('Executing...')).not.toBeVisible({ timeout: 15000 });
    
    // Verify error is shown
    await expect(page.locator('text=/error|Error|ERROR/i')).toBeVisible();
  });

  test('should generate and display matplotlib plots', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Add matplotlib code
    const plotCode = `
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('X values')
plt.ylabel('Y values')
plt.show()
`;
    
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type(plotCode);
    
    // Execute code
    const executeButton = page.getByRole('button', { name: /run|execute/i });
    await executeButton.click();
    
    // Wait for execution to complete
    await expect(page.getByText('Executing...')).toBeVisible();
    await expect(page.getByText('Executing...')).not.toBeVisible({ timeout: 20000 });
    
    // Check if plot appears in artifacts panel
    const plotsPanel = page.locator('text=Plots & Tables').locator('..');
    await expect(plotsPanel).toBeVisible();
    
    // Look for plot image or plot indicator
    await expect(page.locator('img[src*=".png"], text=/plot.*png/i')).toBeVisible({ timeout: 5000 });
  });

  test('should generate and display pandas tables', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Add pandas code
    const tableCode = `
import pandas as pd
import numpy as np

# Create sample data
data = {
    'Name': ['Alice', 'Bob', 'Charlie', 'Diana'],
    'Age': [25, 30, 35, 28],
    'Score': [85.5, 92.0, 78.5, 88.0]
}

df = pd.DataFrame(data)
print(df)
df.head()
`;
    
    const codeEditor = page.locator('.monaco-editor textarea').first();
    await codeEditor.click();
    await page.keyboard.press('Control+A');
    await page.keyboard.type(tableCode);
    
    // Execute code
    const executeButton = page.getByRole('button', { name: /run|execute/i });
    await executeButton.click();
    
    // Wait for execution to complete
    await expect(page.getByText('Executing...')).toBeVisible();
    await expect(page.getByText('Executing...')).not.toBeVisible({ timeout: 20000 });
    
    // Check if table appears in output or artifacts
    await expect(page.locator('text=Alice')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Bob')).toBeVisible();
  });
});
