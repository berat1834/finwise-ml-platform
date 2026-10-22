import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should show login form initially', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Hoş Geldiniz')).toBeVisible();
    await expect(page.locator('input[placeholder="Kullanıcı Adı"]')).toBeVisible();
    await expect(page.locator('input[placeholder="Şifre"]')).toBeVisible();
  });

  test('should show error on invalid login', async ({ page }) => {
    await page.goto('/');
    await page.fill('input[placeholder="Kullanıcı Adı"]', 'invalid');
    await page.fill('input[placeholder="Şifre"]', 'invalid');
    await page.click('button:has-text("Giriş Yap")');
    
    // Expect error message
    const errorMsg = page.locator('.text-red-500, .text-red-600').first();
    await expect(errorMsg).toBeVisible({ timeout: 5000 });
  });
});
