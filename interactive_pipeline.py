#!/usr/bin/env python3
"""
Interactive terminal script for the GuardrailPipeline.
This allows you to type in custom inputs to test how the pipeline handles them.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from prompt_injection_detector.pipeline import GuardrailPipeline, ToolCall

def main():
    print("=" * 60)
    print("🛡️  Interactive Guardrail Pipeline")
    print("=" * 60)
    print("Initializing...")
    
    # Initialize the pipeline
    pipeline = GuardrailPipeline()
    
    print("Pipeline ready! Type your prompt below. Type 'quit' or 'exit' to stop.")
    print("-" * 60)

    while True:
        try:
            print("\n👤 User Input (Paste multiple lines, then press Enter twice to submit. Type 'quit' to exit):")
            lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    print("\nExiting...")
                    return
                    
                if not line.strip() and lines:
                    break  # Submit on empty line after content
                if not lines and line.strip().lower() in ['quit', 'exit']:
                    print("Exiting...")
                    return
                if not line.strip() and not lines:
                    continue # Skip empty lines before typing anything
                lines.append(line)
                
            user_input = '\n'.join(lines).strip()
            if not user_input:
                continue
                
            # Optional: Let the user mock an LLM response or tool call if they want to test L7-L9,
            # but for simplicity, we'll use a generic safe LLM response
            mock_llm_response = "I am a helpful assistant."
            mock_tools = []
            
            print("\n⚙️  Running through 10-Layer Guardrail...")
            result = pipeline.run(
                text=user_input, 
                mock_llm_response=mock_llm_response, 
                mock_tools=mock_tools
            )
            
            # Print the result formatting based on the status
            if result.status == "ALLOWED":
                print(f"✅ Status: \033[92m{result.status}\033[0m")
                print(f"   Verdict: {result.verdict}")
                print(f"   Final Output: {result.llm_output}")
            else:
                print(f"🚨 Status: \033[91m{result.status}\033[0m")
                print(f"   Verdict: {result.verdict}")
                print(f"   Layer Triggered: {result.layer_triggered}")
                if result.reason:
                    print(f"   Reason: {result.reason}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
