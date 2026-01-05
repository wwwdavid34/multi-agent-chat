"""Test AG2 provider configuration."""
import os
from autogen import AssistantAgent

# Test configurations
test_configs = {
    "gemini": {
        "config_list": [{
            "model": "gemini-1.5-flash",
            "api_key": os.getenv("GEMINI_API_KEY", "test-key"),
            "api_type": "gemini",
        }]
    },
    "anthropic": {
        "config_list": [{
            "model": "claude-3-5-sonnet-20241022",
            "api_key": os.getenv("ANTHROPIC_API_KEY", "test-key"),
            "api_type": "anthropic",
        }]
    },
}

print("Testing AG2 provider configurations...")
print("\nGemini config:")
print(test_configs["gemini"])

print("\nAnthropic config:")
print(test_configs["anthropic"])

print("\nAttempting to create Gemini agent...")
try:
    gemini_agent = AssistantAgent(
        name="TestGemini",
        llm_config=test_configs["gemini"],
        system_message="You are a test agent.",
    )
    print(f"✓ Gemini agent created: {gemini_agent.name}")
    print(f"  Client class: {type(gemini_agent.client)}")
except Exception as e:
    print(f"✗ Gemini agent failed: {e}")

print("\nAttempting to create Anthropic agent...")
try:
    anthropic_agent = AssistantAgent(
        name="TestClaude",
        llm_config=test_configs["anthropic"],
        system_message="You are a test agent.",
    )
    print(f"✓ Anthropic agent created: {anthropic_agent.name}")
    print(f"  Client class: {type(anthropic_agent.client)}")
except Exception as e:
    print(f"✗ Anthropic agent failed: {e}")
