#!/usr/bin/env python3
"""
Simple direct test of matplotlib functionality
"""

import requests
import json

def test_simple_execution():
    """Test basic code execution without artifacts"""
    
    # Create session
    response = requests.post("http://localhost:8000/api/sessions/create")
    session_data = response.json()
    session_id = session_data['session_id']
    print(f"Created session: {session_id}")
    
    # Test simple print
    simple_code = "print('Hello from AIDO Lab!')\n2 + 2"
    
    payload = {
        "session_id": session_id,
        "query": simple_code
    }
    
    response = requests.post("http://localhost:8000/api/execute", json=payload)
    result = response.json()
    
    print("Simple test result:")
    print(f"Output: {result.get('output', 'No output')}")
    print(f"Error: {result.get('error', 'No error')}")
    
    return result.get('error') is None

if __name__ == "__main__":
    success = test_simple_execution()
    print(f"Test {'PASSED' if success else 'FAILED'}")
