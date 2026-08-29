import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("=== 1. Navigation Check ===")
        await page.goto("http://localhost:5173")
        await page.wait_for_timeout(2000)
        try:
            await page.goto("http://localhost:5173/about")
            print("About loaded.")
            await page.goto("http://localhost:5173/services")
            print("Services loaded.")
            print("PASS: Navigation check.")
        except Exception as e:
            print(f"FAIL: Navigation error: {e}")

        print("\n=== 2. Devotee Sign Up (Empty field validation) ===")
        await page.goto("http://localhost:5173/sign-up")
        await page.wait_for_timeout(2000)
        
        await page.click('[data-testid="button-submit-signup"]')
        await page.wait_for_timeout(1000)
        body_text = await page.evaluate("document.body.innerText")
        
        # Check for exact rendered text
        if "Email address is required." in body_text or "Full name is required." in body_text:
            print("PASS: Empty field validations triggered.")
        else:
            print("FAIL: No obvious empty field validation errors seen in DOM.")
            await page.screenshot(path="devotee_empty_validation_fail.png", full_page=True)
            print("Screenshot saved to devotee_empty_validation_fail.png")

        print("\n=== 3. Devotee Sign Up (Mismatched password) ===")
        await page.fill('[data-testid="input-signup-name"]', "Test User")
        await page.fill('[data-testid="input-signup-email"]', "test@example.com")
        await page.fill('[data-testid="input-signup-password"]', "Password123!")
        await page.fill('[data-testid="input-signup-confirm"]', "Password1234!")
        await page.click('[data-testid="button-submit-signup"]')
        await page.wait_for_timeout(1000)
        body_text = await page.evaluate("document.body.innerText")
        if "Passwords do not match" in body_text or "match" in body_text.lower():
            print("PASS: Mismatched password validation triggered.")
        else:
            print("FAIL: No mismatched password error seen in DOM.")
            await page.screenshot(path="devotee_mismatch_validation_fail.png", full_page=True)

        print("\n=== 4. Pandit Sign Up (Client-side validation) ===")
        await page.goto("http://localhost:5173/sign-up?role=pandit")
        await page.wait_for_timeout(2000)
        
        try:
            # Step 1
            await page.get_by_placeholder("Enter your first name").fill("Ram")
            await page.get_by_placeholder("Enter your last name").fill("Sharma")
            await page.get_by_placeholder("Enter your email address").fill("ram@example.com")
            await page.get_by_placeholder("Enter your phone number").fill("9876543210")
            await page.click('[data-testid="pill-pandit-gender-male"]')
            await page.get_by_placeholder("e.g. Varanasi, Haridwar, Delhi").fill("Varanasi")
            await page.get_by_placeholder("e.g. Uttar Pradesh").fill("Uttar Pradesh")
            
            # Click next (Step 1 -> 2)
            await page.locator('button', has_text="Next: Professional Details").click()
            await page.wait_for_timeout(1000)
            
            # Click next (Step 2 -> 3)
            await page.locator('button', has_text="Next: Verification Documents").click()
            await page.wait_for_timeout(1000)
            
            # Step 3
            await page.click('[data-testid="button-submit-pandit-signup"]')
            await page.wait_for_timeout(1000)
            body_text = await page.evaluate("document.body.innerText")
            if "Password is required" in body_text or "must be at least" in body_text or "accept the Terms" in body_text:
                print("PASS: Pandit required field validations triggered.")
            else:
                print("FAIL: No obvious required field validation for Pandit.")
                await page.screenshot(path="pandit_empty_validation_fail.png", full_page=True)
                print("Screenshot saved to pandit_empty_validation_fail.png")
        except Exception as e:
            print(f"FAIL: Could not complete Pandit flow: {e}")
            await page.screenshot(path="pandit_click_fail.png", full_page=True)
            print("Screenshot saved to pandit_click_fail.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
