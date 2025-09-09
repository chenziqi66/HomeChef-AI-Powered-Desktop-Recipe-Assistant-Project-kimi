#!/usr/bin/env python3
"""
gpt_client.py
Simple wrapper to call OpenAI GPT. If no API key is found it returns a helpful fallback.
"""
import os, json
from typing import List

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

try:
    import openai
    if OPENAI_KEY:
        openai.api_key = OPENAI_KEY
except Exception:
    openai = None

def _safe_response(prompt: str) -> str:
    # A lightweight fallback if OpenAI key is missing or package not available.
    # Keep it short and useful.
    if "recipe" in prompt.lower() or "with" in prompt.lower():
        return "Try simple dishes like pancakes, omelette, or a tomato pasta. Combine flour, egg and milk for pancakes; eggs and milk for scrambled eggs; pasta with tomatoes and garlic for a quick pasta."
    return "I don't have access to the OpenAI API right now. Please set OPENAI_API_KEY environment variable to enable full AI features."

class GPTClient:
    def __init__(self):
        self.available = (OPENAI_KEY is not None) and (openai is not None)

    def suggest_recipes_with_gpt(self, ingredients: List[str], db_matches: List[dict]) -> str:
        prompt = f"""You are a helpful cooking assistant. The user has the following ingredients: {', '.join(ingredients)}.
First, if any good simple recipes come to mind, list 3 short recipe ideas (title + 1-line description).
Second, if database matches exist, mention them briefly.
Third, give 3 substitution suggestions for common missing items."""
        if not self.available:
            return _safe_response(prompt)
        try:
            messages = [
                {"role":"system", "content":"You are a helpful cooking assistant that gives concise recipe ideas and substitutions."},
                {"role":"user", "content": prompt}
            ]
            resp = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, max_tokens=300)
            return resp['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"(OpenAI error) {e}"

    def chat_with_gpt(self, message: str, context: dict=None) -> str:
        prompt = message
        if context:
            prompt = f"Context: Recipe {context.get('title')} with ingredients {', '.join(context.get('ingredients', []))}.\nUser: {message}"
        if not self.available:
            return _safe_response(prompt)
        try:
            messages = [
                {"role":"system", "content":"You are a helpful, concise cooking assistant."},
                {"role":"user", "content": prompt}
            ]
            resp = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, max_tokens=300)
            return resp['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"(OpenAI error) {e}"
