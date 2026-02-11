#!/usr/bin/env python3
"""
Local File Download Server
Run this script in any folder to share files over WiFi with forced download
"""

import http.server
import socketserver
import os
import urllib.parse
import socket
import zipfile
import io
from pathlib import Path

PORT = 8000

class DownloadHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        # Special route for downloading entire folder as ZIP
        if self.path == '/download-all-zip':
            self.send_zip_of_directory()
            return
        
        # Parse the URL
        parsed_path = urllib.parse.urlparse(self.path)
        request_path = urllib.parse.unquote(parsed_path.path)
        
        # Serve directory listing with custom HTML
        if os.path.isdir('.' + request_path):
            self.send_custom_directory_listing(request_path)
            return
        
        # For files, serve with forced download
        if os.path.isfile('.' + request_path):
            self.send_file_with_download(request_path)
            return
        
        # Otherwise serve normally
        super().do_GET()
    
    def send_file_with_download(self, request_path):
        """Send a file with forced download header"""
        try:
            full_path = '.' + request_path
            with open(full_path, 'rb') as f:
                file_data = f.read()
            
            # Get filename
            filename = os.path.basename(request_path)
            
            self.send_response(200)
            self.send_header("Content-type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(file_data)))
            self.end_headers()
            self.wfile.write(file_data)
        except Exception as e:
            self.send_error(404, "File not found")
    
    def send_custom_directory_listing(self, path):
        """Send a nice HTML directory listing"""
        try:
            full_path = '.' + path
            file_list = os.listdir(full_path)
            file_list.sort(key=lambda x: (not os.path.isdir(os.path.join(full_path, x)), x.lower()))
        except OSError:
            self.send_error(404, "Directory not found")
            return
        
        # Build HTML
        html_parts = []
        html_parts.append('<!DOCTYPE html>')
        html_parts.append('<html><head>')
        html_parts.append('<meta charset="utf-8">')
        html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
        html_parts.append(f'<title>ফাইল লিস্ট: {path}</title>')
        html_parts.append('<style>')
        html_parts.append('''
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 20px; 
                background: #f5f5f5;
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { 
                color: #333; 
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }
            .info {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border-left: 4px solid #2196F3;
            }
            .download-all {
                display: inline-block;
                background: #4CAF50;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 5px;
                margin: 15px 0;
                font-weight: bold;
                transition: background 0.3s;
            }
            .download-all:hover {
                background: #45a049;
            }
            table { 
                width: 100%; 
                border-collapse: collapse;
                margin-top: 20px;
            }
            th {
                background: #4CAF50;
                color: white;
                padding: 12px;
                text-align: left;
            }
            td { 
                padding: 10px; 
                border-bottom: 1px solid #ddd;
            }
            tr:hover {
                background: #f5f5f5;
            }
            a { 
                color: #2196F3; 
                text-decoration: none;
            }
            a:hover { 
                text-decoration: underline;
            }
            .folder { 
                color: #FF9800;
                font-weight: bold;
            }
            .file-icon {
                margin-right: 8px;
            }
            .size {
                color: #666;
                font-size: 0.9em;
            }
        ''')
        html_parts.append('</style></head><body>')
        html_parts.append('<div class="container">')
        html_parts.append(f'<h1>📁 {path if path != "/" else "রুট ফোল্ডার"}</h1>')
        
        # Get local IP
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            html_parts.append(f'<div class="info">')
            html_parts.append(f'<strong>সার্ভার চালু আছে:</strong> http://{local_ip}:{PORT}<br>')
            html_parts.append(f'<strong>মোট ফাইল/ফোল্ডার:</strong> {len(file_list)}')
            html_parts.append(f'</div>')
        except:
            pass
        
        # Download all button
        if path == '/':
            html_parts.append('<a href="/download-all-zip" class="download-all">📦 সব ফাইল ZIP করে ডাউনলোড করুন</a>')
        
        html_parts.append('<table>')
        html_parts.append('<tr><th>নাম</th><th>সাইজ</th></tr>')
        
        # Parent directory link
        if path != '/':
            parent = os.path.dirname(path.rstrip('/'))
            if not parent:
                parent = '/'
            html_parts.append(f'<tr><td colspan="2"><span class="file-icon">⬆️</span><a href="{parent}">.. (উপরে যান)</a></td></tr>')
        
        # List files and folders
        for name in file_list:
            full_item_path = os.path.join(full_path, name)
            display_name = name
            link_name = urllib.parse.quote(name)
            
            if os.path.isdir(full_item_path):
                # Directory
                html_parts.append(f'<tr>')
                html_parts.append(f'<td><span class="file-icon">📁</span><a href="{path}{link_name}/" class="folder">{display_name}/</a></td>')
                html_parts.append(f'<td class="size">-</td>')
                html_parts.append(f'</tr>')
            else:
                # File
                try:
                    size = os.path.getsize(full_item_path)
                    size_str = self.format_size(size)
                except:
                    size_str = "?"
                
                html_parts.append(f'<tr>')
                html_parts.append(f'<td><span class="file-icon">📄</span><a href="{path}{link_name}">{display_name}</a></td>')
                html_parts.append(f'<td class="size">{size_str}</td>')
                html_parts.append(f'</tr>')
        
        html_parts.append('</table>')
        html_parts.append('</div></body></html>')
        
        html_content = '\n'.join(html_parts)
        encoded = html_content.encode('utf-8', 'surrogateescape')
        
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
    
    def send_zip_of_directory(self):
        """Create and send a ZIP file of the entire directory"""
        try:
            # Create ZIP in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Walk through directory
                for root, dirs, files in os.walk('.'):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Skip the script itself
                        if file_path == './download_server.py' or file_path == '.\\download_server.py':
                            continue
                        arcname = file_path[2:]  # Remove './' prefix
                        try:
                            zip_file.write(file_path, arcname)
                        except:
                            pass
            
            zip_buffer.seek(0)
            zip_data = zip_buffer.read()
            
            # Send ZIP file
            self.send_response(200)
            self.send_header("Content-type", "application/zip")
            self.send_header("Content-Disposition", "attachment; filename=all_files.zip")
            self.send_header("Content-Length", str(len(zip_data)))
            self.end_headers()
            self.wfile.write(zip_data)
            
        except Exception as e:
            self.send_error(500, f"ZIP creation failed: {str(e)}")
    
    def format_size(self, size):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

def get_local_ip():
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

if __name__ == "__main__":
    # Get current directory
    current_dir = os.getcwd()
    
    print("=" * 60)
    print("🚀 ফাইল ডাউনলোড সার্ভার চালু হচ্ছে...")
    print("=" * 60)
    print(f"📂 শেয়ার করা ফোল্ডার: {current_dir}")
    print(f"🌐 পোর্ট: {PORT}")
    
    local_ip = get_local_ip()
    print(f"\n✅ সার্ভার চালু হয়েছে!")
    print(f"\n📱 আপনার ফোন/ল্যাপটপ থেকে এই লিংকে যান:")
    print(f"   http://{local_ip}:{PORT}")
    print(f"   অথবা: http://localhost:{PORT}")
    
    print(f"\n💡 টিপস:")
    print(f"   - সব ফাইল একসাথে ZIP করে ডাউনলোড করতে পারবেন")
    print(f"   - যেকোনো ফাইলে ক্লিক করলে সরাসরি ডাউনলোড হবে")
    print(f"   - বন্ধ করতে Ctrl+C চাপুন")
    print("=" * 60)
    print()
    
    # Start server
    with socketserver.TCPServer(("", PORT), DownloadHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 সার্ভার বন্ধ করা হচ্ছে...")
            print("✅ সার্ভার বন্ধ হয়েছে!")