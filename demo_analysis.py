#!/usr/bin/env python3
"""
Demo script to test AIDO-Lab functionality
"""

import requests
import json
import time

API_URL = "http://localhost:8000"

def test_platform():
    print("🧪 Testing AIDO-Lab Platform...")
    
    # 1. Check health
    print("\n1. Checking API health...")
    response = requests.get(f"{API_URL}/health")
    if response.status_code == 200:
        print("   ✓ API is healthy")
        print(f"   Services: {response.json()['services']}")
    
    # 2. Create session
    print("\n2. Creating new session...")
    response = requests.post(f"{API_URL}/api/sessions/create")
    if response.status_code == 200:
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"   ✓ Session created: {session_id}")
    else:
        print(f"   ✗ Failed to create session: {response.text}")
        return
    
    # 3. Execute natural language query
    print("\n3. Testing natural language to code...")
    queries = [
        "Create a sample dataset with 100 rows of sales data",
        "Show basic statistics of the data",
        "Create a bar chart of sales by category"
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        response = requests.post(f"{API_URL}/api/execute", json={
            "session_id": session_id,
            "query": query,
            "is_natural_language": True,
            "task_type": "data_analysis"
        })
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Generated code:")
            print("   " + "\n   ".join(result["code"].split("\n")[:5]))
            if result.get("results", {}).get("stdout"):
                print(f"   Output: {result['results']['stdout'][:100]}...")
        else:
            print(f"   ✗ Failed: {response.text}")
    
    # 4. Check history
    print("\n4. Checking execution history...")
    response = requests.get(f"{API_URL}/api/history/{session_id}")
    if response.status_code == 200:
        history = response.json()
        print(f"   ✓ Found {len(history['commits'])} commits")
    
    print("\n✅ Demo completed successfully!")
    print(f"\nAccess the platform at:")
    print(f"   Frontend: http://localhost:3000")
    print(f"   API Docs: http://localhost:8000/docs")
    print(f"   Session ID: {session_id}")

if __name__ == "__main__":
    test_platform()
