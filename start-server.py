#!/usr/bin/env python3
"""
HTTP server with live reload for running HTML slides
"""

import webbrowser
import os
import argparse
from livereload import Server


def start_server(port=8080, host='localhost', open_browser=True):
    """Start HTTP server with live reload."""
    server = Server()

    server.watch('*.html')
    server.watch('*.css')
    server.watch('js/**/*.js')
    server.watch('js/**/*.json')
    server.watch('images/**/*')
    server.watch('css/**/*.css')

    display_host = 'localhost' if host in ('localhost', '127.0.0.1') else host
    print(f"Server starting at http://{display_host}:{port}")
    if host == '0.0.0.0':
        print("Listening on all interfaces — reachable from other machines on the LAN.")
    print("Live reload enabled - files will auto-reload when changed")
    print("Press Ctrl+C to stop the server")

    if open_browser:
        webbrowser.open(f"http://{display_host}:{port}")

    try:
        server.serve(port=port, host=host, root='.')
    except KeyboardInterrupt:
        print("\nServer stopped")


def build_parser():
    parser = argparse.ArgumentParser(description="Start HTML slide server with live reload")
    parser.add_argument("-p", "--port", type=int, default=8080,
                        help="Server port (default: 8080)")
    parser.add_argument("--host", default='localhost',
                        help="Bind host (default: localhost). Use 0.0.0.0 to expose on LAN.")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't auto-open the browser")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    start_server(args.port, host=args.host, open_browser=not args.no_browser)
