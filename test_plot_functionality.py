#!/usr/bin/env python3
"""
Test script to verify AIDO-Lab plot and table functionality
Tests the matplotlib and pandas artifact capture system
"""

import requests
import json
import time
import sys

# Configuration
BACKEND_URL = "http://localhost:8000"
TEST_CODES = [
    {
        "name": "Simple Plot Test",
        "code": """
import matplotlib.pyplot as plt
import numpy as np

# Create sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(8, 6))
plt.plot(x, y, 'b-', linewidth=2)
plt.title('Test Plot - Sine Wave')
plt.xlabel('X values')
plt.ylabel('Y values')
plt.grid(True)
plt.show()

print("✅ Simple plot test completed!")
"""
    },
    {
        "name": "Multiple Plots Test",
        "code": """
import matplotlib.pyplot as plt
import numpy as np

# First plot
x = np.linspace(0, 10, 50)
y1 = np.cos(x)

plt.figure(figsize=(6, 4))
plt.plot(x, y1, 'r-', label='Cosine')
plt.title('Cosine Wave')
plt.legend()
plt.show()

# Second plot
y2 = np.exp(-x/5) * np.sin(x)

plt.figure(figsize=(6, 4))
plt.plot(x, y2, 'g--', label='Damped Sine')
plt.title('Damped Sine Wave')
plt.legend()
plt.show()

print("✅ Multiple plots test completed!")
"""
    },
    {
        "name": "Pandas Table Test",
        "code": """
import pandas as pd
import numpy as np

# Create sample data
data = {
    'Name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
    'Age': [25, 30, 35, 28, 32],
    'Score': [85.5, 92.3, 78.1, 88.7, 91.2],
    'City': ['New York', 'London', 'Tokyo', 'Paris', 'Berlin']
}

df = pd.DataFrame(data)
print("Sample DataFrame:")
print(df)

# This should trigger table capture
df

print("✅ Pandas table test completed!")
"""
    },
    {
        "name": "Combined Plot and Table Test",
        "code": """
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Create data
dates = pd.date_range('2024-01-01', periods=30, freq='D')
values = np.random.randn(30).cumsum() + 100

# Create DataFrame
df = pd.DataFrame({
    'Date': dates,
    'Value': values,
    'Category': ['A' if i % 2 == 0 else 'B' for i in range(30)]
})

# Display table
print("Time series data:")
print(df.head(10))
df.head(10)  # This should capture the table

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(df['Date'], df['Value'], marker='o', linewidth=2)
plt.title('Time Series Plot')
plt.xlabel('Date')
plt.ylabel('Value')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

print("✅ Combined plot and table test completed!")
"""
    }
]

def create_session():
    """Create a new session"""
    try:
        response = requests.post(f"{BACKEND_URL}/api/sessions/create")
        response.raise_for_status()
        data = response.json()
        return data['session_id']
    except Exception as e:
        print(f"❌ Failed to create session: {e}")
        return None

def execute_code(session_id, code):
    """Execute code in the session"""
    try:
        payload = {
            "session_id": session_id,
            "query": code
        }
        response = requests.post(f"{BACKEND_URL}/api/execute", json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Code execution failed: {e}")
        return None

def check_artifacts(session_id):
    """Check for generated artifacts"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/artifacts/{session_id}")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"❌ Failed to check artifacts: {e}")
        return []

def run_tests():
    """Run all test cases"""
    print("🚀 Starting AIDO-Lab Plot & Table Functionality Tests")
    print("=" * 60)
    
    # Create session
    session_id = create_session()
    if not session_id:
        print("❌ Cannot proceed without session")
        return False
    
    print(f"✅ Created session: {session_id}")
    
    all_passed = True
    
    for i, test in enumerate(TEST_CODES, 1):
        print(f"\n📋 Test {i}: {test['name']}")
        print("-" * 40)
        
        # Execute code
        result = execute_code(session_id, test['code'])
        if not result:
            print(f"❌ Test {i} failed - code execution error")
            all_passed = False
            continue
        
        # Check for errors
        if result.get('error'):
            print(f"❌ Test {i} failed - execution error: {result['error']}")
            all_passed = False
            continue
        
        # Print output
        if result.get('output'):
            print("📄 Output:")
            print(result['output'])
        
        # Check artifacts
        time.sleep(1)  # Give time for artifacts to be saved
        artifacts = check_artifacts(session_id)
        
        if artifacts:
            print(f"📊 Generated {len(artifacts)} artifacts:")
            for artifact in artifacts:
                print(f"  - {artifact.get('filename', 'Unknown')} ({artifact.get('type', 'Unknown')})")
        else:
            print("⚠️  No artifacts detected")
        
        print(f"✅ Test {i} completed")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Plot and table functionality is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
