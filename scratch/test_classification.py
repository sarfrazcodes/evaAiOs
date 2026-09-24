import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.eva_core.main import intent_engine

async def run_test(number, text, expected):
    print(f"\n{number}. Testing '{text}'")
    res = await intent_engine.determine_intent(text)
    print(f"Expected: {expected}")
    print(f"Actual Intent: {res.intent}, Confidence: {res.confidence}, Reason: {res.reason}")
    if res.intent != expected:
        print(f"!!! FAIL !!! Expected {expected}, got {res.intent}")
    else:
        print("PASS")

async def main():
    print("Testing IntentEngine Classifications...")
    
    await run_test(1, "hello eva!", "conversation")
    await run_test(2, "open chrome", "application_operation")
    await run_test(3, "create a folder called projects", "file_operation")
    await run_test(4, "What are AI agents?", "information_request")
    await run_test(5, "Research AI agents and create a Word report.", "complex_task")
    await run_test(6, "Research AI operating systems, compare the results, and prepare a report.", "complex_task")
    await run_test(7, "Open Chrome, search for AI operating systems, summarize the results, and save them to a document.", "complex_task")

if __name__ == "__main__":
    asyncio.run(main())
