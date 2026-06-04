# core/agents/base_agent.py

import os
import time
import logging
from groq import Groq
import httpx

logger = logging.getLogger(__name__)

# GROQ MODEL CASCADE (Zero downtime)
GROQ_MODELS_CASCADE = [
    "llama-3.3-70b-versatile",                   # 1. Primary model
    "qwen/qwen3-32b",                            # 2. Very powerful model, large context
    "meta-llama/llama-4-scout-17b-16e-instruct"  # 3. Third backup
]
GEMINI_MODEL = "gemini-2.5-flash"


class BaseAgent:
    def __init__(self, model: str = None, max_tokens: int = 8192):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY missing in .env")
        self.groq_client = Groq(api_key=self.groq_api_key)
        
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
            
        # If a model is forced, use it; otherwise take the first from cascade
        self.model = model or GROQ_MODELS_CASCADE[0]
        self.max_tokens = max_tokens

    def execute_with_fallback(self, messages: list) -> str:
        # If Gemini is explicitly requested
        if "gemini" in self.model.lower():
            return self._execute_gemini_direct(messages)

        # Groq Cascade Attempts
        # Try the specified model, then go down the list on error 429
        models_to_try = [self.model]
        for fallback_model in GROQ_MODELS_CASCADE:
            if fallback_model not in models_to_try:
                models_to_try.append(fallback_model)

        for current_model in models_to_try:
            try:
                logger.info(f"Groq attempt with model: {current_model}...")
                response = self.groq_client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=0.3
                )
                return response.choices[0].message.content

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Rate limit" in error_msg:
                    logger.warning(f"Quota exhausted for {current_model}. Switching to next model...")
                    continue
                else:
                    logger.warning(f"Unexpected error with {current_model}: {e}")
                    continue

        # Ultimate Fallback: Gemini
        logger.warning("All Groq models blocked. Triggering ultimate Gemini fallback...")
        return self._execute_gemini_direct(messages)

    def _execute_gemini_direct(self, messages: list) -> str:
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY missing from .env and Groq failed.")
        
        try:
            logger.info("Gemini anti-spam pause (4s)...")
            time.sleep(4.0)

            logger.info(f"Direct HTTP request to Gemini ({GEMINI_MODEL})...")
            
            gemini_contents = []
            system_instruction = None
            is_json_requested = False

            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                
                if "json" in content.lower():
                    is_json_requested = True

                if role == "system":
                    system_instruction = {"parts": [{"text": content}]}
                else:
                    gemini_role = "user" if role == "user" else "model"
                    gemini_contents.append({
                        "role": gemini_role,
                        "parts": [{"text": content}]
                    })

            if not gemini_contents:
                prompt_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                gemini_contents = [{"role": "user", "parts": [{"text": prompt_text}]}]

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.gemini_api_key
            }
            
            generation_config = {"temperature": 0.4}
            
            # Force JSON structure for Gemini if requested
            if is_json_requested:
                generation_config["responseMimeType"] = "application/json"
            
            payload = {
                "contents": gemini_contents,
                "generationConfig": generation_config
            }
            
            if system_instruction:
                payload["systemInstruction"] = system_instruction

            with httpx.Client() as client:
                response = client.post(url, json=payload, headers=headers, timeout=90.0)
                response.raise_for_status()
                result = response.json()
                
            return result['candidates'][0]['content']['parts'][0]['text']
            
        except Exception as gemini_error:
            logger.critical(f"Ultimate Gemini fallback also failed: {gemini_error}")
            raise RuntimeError(f"Total generation failure (Groq + Gemini): {gemini_error}")

    def run(self, *args, **kwargs):
        raise NotImplementedError(f"{self.__class__.__name__} must implement run()")