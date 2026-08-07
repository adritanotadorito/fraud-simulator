import json
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        try:
            from app.config import get_settings
            self.settings = get_settings()
            self.provider = self.settings.LLM_PROVIDER
            if self.provider == 'gemini':
                self.api_key = self.settings.GEMINI_API_KEY
            else:
                self.api_key = self.settings.OPENAI_API_KEY
        except Exception:
            self.provider = 'gemini'
            self.api_key = None

            
        self.client = None
        if self.api_key:
            if self.provider == 'gemini':
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel('gemini-pro')
            elif self.provider == 'openai':
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate(self, system_prompt: str, user_prompt: str, response_format: str = 'json') -> dict:
        if not self.api_key or not self.client:
            logger.warning("No API key configured or client not initialized. Using fallback.")
            return self._get_fallback_response(system_prompt, user_prompt)

        retries = 3
        backoff = 1
        
        for attempt in range(retries):
            try:
                if self.provider == 'gemini':
                    prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
                    response = await asyncio.to_thread(self.client.generate_content, prompt)
                    text_response = response.text
                elif self.provider == 'openai':
                    response = await self.client.chat.completions.create(
                        model="gpt-4-turbo-preview",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"} if response_format == 'json' else None
                    )
                    text_response = response.choices[0].message.content
                
                # Try parsing as JSON if requested
                if response_format == 'json':
                    try:
                        # Simple cleanup for markdown json blocks
                        cleaned = text_response.strip()
                        if cleaned.startswith("```json"):
                            cleaned = cleaned[7:]
                        if cleaned.endswith("```"):
                            cleaned = cleaned[:-3]
                        return json.loads(cleaned.strip())
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON response: {text_response}")
                        return self._get_fallback_response(system_prompt, user_prompt)
                return {"text": text_response}

            except Exception as e:
                logger.error(f"LLM generate error (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    return self._get_fallback_response(system_prompt, user_prompt)
                await asyncio.sleep(backoff)
                backoff *= 2
                
        return self._get_fallback_response(system_prompt, user_prompt)

    def _get_fallback_response(self, system_prompt: str, user_prompt: str) -> dict:
        # Generate reasonable fallback based on context
        if "FraudGPT" in system_prompt:
            return {
                "target_user_id": "usr_fallback_999",
                "amount": 49.99,
                "merchant_type": "electronics",
                "device_config": {
                    "vpn": True,
                    "tor": False,
                    "emulator": True
                },
                "geo": {
                    "country": "US",
                    "city": "New York"
                },
                "biometrics_manipulation": {
                    "typing_speed_factor": 0.5,
                    "mouse_deviation": 2.0
                },
                "strategy_detail": "Fallback simulated device spoofing attack."
            }
        elif "ShieldGPT" in system_prompt:
            return {
                "explanation": "High risk due to device anomaly and suspicious geolocation mismatch."
            }
        return {"response": "Fallback triggered. Context unhandled."}
