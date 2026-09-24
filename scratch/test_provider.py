import asyncio
import sys
import os
import traceback
import httpx

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.eva_core.main import llm_provider, intent_engine

async def main():
    print("Testing OllamaProvider directly...")
    try:
        # Increase timeout internally for debugging if needed, 
        # but wait, let's just use the provider as is
        res = await llm_provider.generate_json("Say hello in one sentence.")
        print(f"Success! Response: {res}")
    except Exception as e:
        print(f"OllamaProvider Error Type: {type(e)}")
        print(f"OllamaProvider Error Args: {e.args}")
        traceback.print_exc()

    print("\nTesting IntentEngine directly...")
    
    print("\n1. Testing 'hello eva!'")
    res = await intent_engine.determine_intent("hello eva!")
    print(f"Intent: {res.intent}, Confidence: {res.confidence}, Reason: {res.reason}")

    print("\n2. Testing 'open chrome'")
    res = await intent_engine.determine_intent("open chrome")
    print(f"Intent: {res.intent}, Confidence: {res.confidence}, Reason: {res.reason}")

    print("\n3. Testing 'Research AI agents and create a Word report.'")
    res = await intent_engine.determine_intent("Research AI agents and create a Word report.")
    print(f"Intent: {res.intent}, Confidence: {res.confidence}, Reason: {res.reason}")

if __name__ == "__main__":
    asyncio.run(main())
