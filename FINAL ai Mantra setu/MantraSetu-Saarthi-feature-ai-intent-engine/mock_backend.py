import http.server
import socketserver
import json

class MockBackendHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    def do_GET(self):
        # Add CORS header to GET responses
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        
        if self.path == '/puja/list':
            self.end_headers()
            data = [{"title": "Ganesh Puja"}, {"title": "Satyanarayan Katha"}]
            self.wfile.write(json.dumps(data).encode('utf-8'))
        elif self.path.startswith('/auth/check-duplicate'):
            self.end_headers()
            import urllib.parse
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            # Mock behavior: "duplicate@example.com" or "9999999999" are duplicates
            is_dup = False
            fields = []
            if 'email' in query and query['email'][0] == 'duplicate@example.com':
                is_dup = True
                fields.append('email')
            if 'phone' in query and query['phone'][0] == '9999999999':
                is_dup = True
                fields.append('phone')
            data = {"is_duplicate": is_dup, "fields": fields}
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

PORT = 8000
with socketserver.TCPServer(("", PORT), MockBackendHandler) as httpd:
    print(f"Mock backend running on port {PORT}")
    httpd.serve_forever()
