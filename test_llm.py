#!/usr/bin/env python3
"""
Test script to verify LLM service functionality
"""

import asyncio
import os
import sys
sys.path.append('./backend')

from app.services.llm_service import LLMService, LLMProvider

async def test_llm():
    """Test LLM service functionality"""
    
    print("🧪 Testing LLM Service...")
    
    # Check environment variables
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print(f"📋 Environment Check:")
    print(f"   Anthropic API Key: {'✅ Set' if anthropic_key and anthropic_key != 'your-anthropic-key-here' else '❌ Not set'}")
    print(f"   OpenAI API Key: {'✅ Set' if openai_key and openai_key != 'your-openai-key-here' else '❌ Not set'}")
    
    # Test Anthropic if available
    if anthropic_key and anthropic_key != "your-anthropic-key-here":
        print("\n🤖 Testing Anthropic Claude...")
        try:
            llm = LLMService(
                provider=LLMProvider.ANTHROPIC,
                api_key=anthropic_key,
                model="claude-3-5-sonnet-20241022",
                temperature=0.7,
                max_tokens=100
            )
            
            # Test API status
            status = await llm.check_api_status()
            print(f"   API Status: {'✅ Connected' if status else '❌ Failed'}")
            
            if status:
                # Test simple completion
                response = await llm.generate_response("Say 'Hello from Claude!' and explain what you are in one sentence.")
                print(f"   Response: {response[:100]}...")
                print("   ✅ Anthropic Claude working!")
            
        except Exception as e:
            print(f"   ❌ Anthropic Error: {e}")
    
    # Test OpenAI if available
    if openai_key and openai_key != "your-openai-key-here":
        print("\n🤖 Testing OpenAI...")
        try:
            llm = LLMService(
                provider=LLMProvider.OPENAI,
                api_key=openai_key,
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=100
            )
            
            # Test API status
            status = await llm.check_api_status()
            print(f"   API Status: {'✅ Connected' if status else '❌ Failed'}")
            
            if status:
                # Test simple completion
                response = await llm.generate_response("Say 'Hello from GPT!' and explain what you are in one sentence.")
                print(f"   Response: {response[:100]}...")
                print("   ✅ OpenAI GPT working!")
            
        except Exception as e:
            print(f"   ❌ OpenAI Error: {e}")
    
    # Test tool calling functionality
    print("\n🛠️  Testing Tool Calling...")
    try:
        if anthropic_key and anthropic_key != "your-anthropic-key-here":
            llm = LLMService(provider=LLMProvider.ANTHROPIC)
            
            # Test tool calling
            messages = [{"role": "user", "content": "Generate Python code to print 'Hello World'"}]
            
            response = await llm.client.messages.create(
                model=llm.model,
                system="You are a helpful coding assistant. Generate Python code when requested.",
                messages=messages,
                tools=[{
                    "name": "exec_python",
                    "description": "Execute Python code",
                    "input_schema": {
                        "type": "object",
                        "properties": {"code": {"type": "string"}},
                        "required": ["code"]
                    }
                }],
                tool_choice={"type": "tool", "name": "exec_python"},
                temperature=0.7,
                max_tokens=200
            )
            
            for content_block in response.content:
                if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                    code = content_block.input.get('code', '')
                    print(f"   Generated Code: {code.strip()}")
                    print("   ✅ Tool calling working!")
                    break
            
    except Exception as e:
        print(f"   ❌ Tool Calling Error: {e}")
    
    print("\n🎯 LLM Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_llm())
