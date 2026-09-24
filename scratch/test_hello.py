import asyncio
from core.eva_core.intent.engine import IntentEngine
from core.eva_core.llm.ollama_provider import OllamaProvider

async def main():
    llm = OllamaProvider("llama3")
    engine = IntentEngine(llm)
    intent = await engine.determine_intent("hello eva")
    print(f"Intent for 'hello eva': {intent.intent}")
    
    intent = await engine.determine_intent("hello eva ")
    print(f"Intent for 'hello eva ': {intent.intent}")
    
    intent = await engine.determine_intent("Hello EVA")
    print(f"Intent for 'Hello EVA': {intent.intent}")

if __name__ == "__main__":
    asyncio.run(main())
