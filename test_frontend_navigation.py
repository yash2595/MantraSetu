import asyncio
from playwright.async_api import async_playwright
import time
import sys

commands = [
    "Open Kundali",
    "Book a Pandit",
    "Show Muhurat",
    "Open Login",
    "Open Signup",
    "Go Home"
]

async def run_tests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream"
        ])
        
        for command in commands:
            print(f"\\n{'='*50}")
            print(f"TESTING COMMAND: {command}")
            print(f"{'='*50}")
            
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to the React app
            await page.goto("http://localhost:5173/")
            time.sleep(1) # wait for render
            
            url_before = page.url
            print(f"React Router URL Before: {url_before}")
            
            # We will intercept the WebSocket creation and patch the send method
            # so that when the app sends AUDIO_FRAME, we send TEXT frame instead with our command.
            await page.add_init_script(f"""
                const originalSend = WebSocket.prototype.send;
                let textSent = false;
                WebSocket.prototype.send = function(data) {{
                    const msg = JSON.parse(data);
                    if (msg.type === 'AUDIO_FRAME' && !textSent) {{
                        console.log('Intercepted AUDIO_FRAME, injecting TEXT: {command}');
                        originalSend.call(this, JSON.stringify({{
                            type: 'TEXT',
                            payload: {{ text: '{command}' }}
                        }}));
                        textSent = true;
                    }} else if (msg.type !== 'AUDIO_FRAME') {{
                        originalSend.call(this, data);
                    }}
                }};
            """)
            
            await page.reload()
            time.sleep(2)
            
            url_before = page.url
            print(f"React Router URL After Reload: {url_before}")

            # Click the microphone button to start listening
            # The button has an SVG, we can find it by its aria-label or just the button
            try:
                mic_button = page.locator('button').filter(has=page.locator('svg')).first
                await mic_button.click()
                print(f"Frontend WebSocket Message (injected): TEXT -> {command}")
                
                # Wait for navigation to happen (AI response + navigate)
                # We can wait for network idle or just wait a few seconds
                time.sleep(5)
                
                url_after = page.url
                print(f"React Router URL After: {url_after}")
                print(f"Final Browser URL: {url_after}")
                
                if url_after != url_before:
                    print(f"✅ PASS: Navigation successful for '{command}'")
                else:
                    if command == "Go Home" and url_after.endswith("/"):
                        print(f"✅ PASS: Already at home for '{command}'")
                    else:
                        print(f"❌ FAIL: URL did not change for '{command}'")
                        
            except Exception as e:
                print(f"❌ FAIL: Could not test '{command}': {e}")
                
            await context.close()
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
