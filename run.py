#!/usr/bin/env python3
"""
Expense Manager Application
Run this file to start the Flask web server.
"""

from app import app
import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Expense Manager on http://localhost:{port}")
    print(f"Debug mode: {debug}")
    print("Press CTRL+C to stop the server")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
