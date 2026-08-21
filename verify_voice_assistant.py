import asyncio
import sys
from playwright.async_api import async_playwright

async def run_verification():
    print("Starting Playwright Voice Assistant Verification...")
    logs = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            permissions=["microphone"],
            bypass_csp=True
        )
        page = await context.new_page()
        
        # Listen to console logs
        def handle_console(msg):
            log_str = f"[Console - {msg.type}] {msg.text}"
            logs.append(log_str)
            print(log_str)
            
        page.on("console", handle_console)
        page.on("pageerror", lambda err: print(f"[Page Error] {err}"))
        
        print("Navigating to http://localhost:5173...")
        await page.goto("http://localhost:5173")
        
        # Wait for the page load
        await page.wait_for_timeout(2000)
        
        # Click Continue with Saarthi
        btn_selector = '[data-testid="button-continue-saarthi"]'
        try:
            await page.wait_for_selector(btn_selector, timeout=5000)
            print("Found ChoicePopup. Clicking 'Continue with Saarthi'...")
            await page.click(btn_selector)
        except Exception as e:
            print("No ChoicePopup appeared or timed out. Proceeding...")
            
        # Wait 10s for connection and greeting to complete
        print("Waiting 10s for initial greeting to finish...")
        await page.wait_for_timeout(10000)
        
        # Simulate speech: "pandit onboarding page par le chal"
        print("\n>>> Simulating User speech: 'pandit onboarding page par le chal'...")
        await page.evaluate("window.simulateUserSpeech('pandit onboarding page par le chal')")
        
        # Wait for URL to become /signup
        print("Waiting for page URL to change to /signup (timeout 30s)...")
        try:
            await page.wait_for_url("**/signup**", timeout=30000)
            print(f"Successfully transitioned! Current page URL: {page.url}")
        except Exception as e:
            print(f"Failed to transition to /signup: {e}")
            
        # Wait 5s for the sign-up page wizard to mount and focus
        await page.wait_for_timeout(5000)
        
        # Simulate User speech: "skip" for avatar
        print("\n>>> Simulating User speech: 'skip' (for profile photo)...")
        await page.evaluate("window.simulateUserSpeech('skip')")
        await page.wait_for_timeout(5000)
        
        # Simulate User speech: "Ramesh"
        print("\n>>> Simulating User speech: 'Ramesh'...")
        await page.evaluate("window.simulateUserSpeech('Ramesh')")
        
        # Wait 10s for form field auto-fill
        print("Waiting 10s for auto-fill to process...")
        await page.wait_for_timeout(10000)
        
        # Check First Name field value
        input_selector = '[data-testid="input-pandit-first-name"]'
        try:
            val = await page.locator(input_selector).input_value()
            print(f"\n[Verification Result] Pandit First Name input value: '{val}'")
            if val.strip() == "Ramesh":
                print("SUCCESS: Form field auto-fill verified correctly!")
            else:
                print("WARNING: Input value does not match 'Ramesh'. Got:", val)
        except Exception as e:
            print(f"Failed to find or read first name input field: {e}")
            
        # Take a screenshot and save it to the conversation brain directory
        screenshot_path = "C:/Users/hp/.gemini/antigravity-ide/brain/ff5ad215-9344-4149-8063-20cc001e680e/form_screenshot.png"
        try:
            await page.screenshot(path=screenshot_path)
            print(f"Form screenshot saved to {screenshot_path}")
        except Exception as e:
            print(f"Failed to save screenshot: {e}")
            
        await browser.close()
        
    with open("browser_console_trace.log", "w", encoding="utf-8") as f:
        f.write("\n".join(logs))
    print("\nLogs saved to browser_console_trace.log")

if __name__ == "__main__":
    asyncio.run(run_verification())
