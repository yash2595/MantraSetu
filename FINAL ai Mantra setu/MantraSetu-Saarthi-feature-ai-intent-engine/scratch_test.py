import asyncio
from app.core.app import create_app

app = create_app()

async def main():
    try:
        async with app.router.lifespan_context(app):
            print('Lifespan ok')
    except Exception as e:
        print(f"Exception: {e}")

asyncio.run(main())
