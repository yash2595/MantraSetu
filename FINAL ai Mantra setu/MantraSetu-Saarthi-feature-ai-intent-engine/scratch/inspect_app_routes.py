from app.core.app import create_app

app = create_app()

print("\n--- MOUNTED ROUTES IN FASTAPI APP ---")
for route in app.routes:
    methods = getattr(route, "methods", None)
    print(f"Path: {route.path:<40} | Methods: {methods}")
