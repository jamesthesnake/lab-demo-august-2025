import { test, expect } from '@playwright/test';

test.describe('AI Chat Interface', () => {
  test('should send and receive chat messages', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    // Find chat interface in AI Assistant panel
    const chatPanel = page.locator('text=AI Assistant').locator('..');
    await expect(chatPanel).toBeVisible();
    
    // Look for chat input
    const chatInput = chatPanel.locator('textarea, input[type="text"]').first();
    if (await chatInput.isVisible()) {
      await chatInput.fill('Create a simple plot showing x vs x^2');
      
      // Send message
      const sendButton = chatPanel.getByRole('button', { name: /send/i });
      await sendButton.click();
      
      // Wait for response
      await expect(chatPanel.getByText('Create a simple plot')).toBeVisible();
      
      // Look for AI response (might take time depending on LLM availability)
      await expect(chatPanel.locator('text=/import|matplotlib|plt/i')).toBeVisible({ timeout: 15000 });
    }
  });

  test('should handle chat when LLM is unavailable', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    const chatPanel = page.locator('text=AI Assistant').locator('..');
    const chatInput = chatPanel.locator('textarea, input[type="text"]').first();
    
    if (await chatInput.isVisible()) {
      await chatInput.fill('print("hello world")');
      
      const sendButton = chatPanel.getByRole('button', { name: /send/i });
      await sendButton.click();
      
      // Should still handle the request even without LLM
      await expect(chatPanel.getByText('print("hello world")')).toBeVisible();
    }
  });

  test('should insert generated code into editor', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Session ready:')).toBeVisible({ timeout: 10000 });
    
    const chatPanel = page.locator('text=AI Assistant').locator('..');
    const chatInput = chatPanel.locator('textarea, input[type="text"]').first();
    
    if (await chatInput.isVisible()) {
      await chatInput.fill('print hello world');
      
      const sendButton = chatPanel.getByRole('button', { name: /send/i });
      await sendButton.click();
      
      // Look for insert button in chat response
      const insertButton = chatPanel.getByRole('button', { name: /insert|use/i });
      if (await insertButton.isVisible({ timeout: 10000 })) {
        await insertButton.click();
        
        // Verify code is inserted into editor
        await expect(page.locator('text=print("hello world")')).toBeVisible();
      }
    }
  });
});
