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
            print(f"\n{'='*50}")
            print(f"TESTING COMMAND: {command}")
            print(f"{'='*50}")
            
            context = await browser.new_context()
            page = await context.new_page()
            page.on('console', lambda msg: print('BROWSER CONSOLE:', msg.text))
            
            # Navigate to the React app
            await page.goto("http://localhost:5173/")
            await asyncio.sleep(1) # wait for render
            
            url_before = page.url
            print(f"React Router URL Before: {url_before}")
            
            # We will intercept the WebSocket creation and patch the send method
            # so that when the app sends CONNECT, we send our TEXT command frame shortly after.
            await page.add_init_script(f"""
                const originalSend = WebSocket.prototype.send;
                let textSent = false;
                WebSocket.prototype.send = function(data) {{
                    originalSend.call(this, data);
                    const msg = JSON.parse(data);
                    if (msg.type === 'CONNECT' && !textSent) {{
                        console.log('Intercepted CONNECT, queueing TEXT injection: {command}');
                        const ws = this;
                        setTimeout(() => {{
                            console.log('Injecting TEXT: {command}');
                            ws.send(JSON.stringify({{
                                type: 'TEXT',
                                payload: {{ text: '{command}' }}
                            }}));
                        }}, 150);
                        textSent = true;
                    }}
                }};
            """)
            
            await page.reload()
            await asyncio.sleep(1)
            
            url_before = page.url
            print(f"React Router URL After Reload: {url_before}")
            
            try:
                # Wait for navigation to happen (AI response + navigate)
                await asyncio.sleep(8)
                
                url_after = page.url
                print(f"React Router URL After: {url_after}")
                print(f"Final Browser URL: {url_after}")
                
                if url_after != url_before:
                    print(f"[PASS]: Navigation successful for '{command}'")
                else:
                    if command == "Go Home" and url_after.endswith("/"):
                        print(f"[PASS]: Already at home for '{command}'")
                    else:
                        print(f"[FAIL]: URL did not change for '{command}'")
                        
            except Exception as e:
                print(f"[FAIL]: Could not test '{command}': {e}")
                
            await context.close()
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
