import { test, expect } from '@playwright/test';

test.describe('Dashboard UI', () => {
  test('should have proper title and layout elements', async ({ page }) => {
    // Note: In a real test, we would mock the API response or login first
    // Since this is just UI skeleton testing, we can check basic elements if any are public
    // or test the loading state.
    await page.goto('/');
    
    // Verify document title
    await expect(page).toHaveTitle(/FinWise/i);
  });
});
