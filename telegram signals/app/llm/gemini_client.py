import json
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.core.config import settings
from app.core.logging import logger
from app.llm.prompts import SYSTEM_PROMPT
from app.llm.schemas import SignalParseSchema

class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key
        self._model = model

    def _get_client_and_model(self, dynamic_key: str | None = None, dynamic_model: str | None = None):
        api_key = dynamic_key or self._api_key or settings.GEMINI_API_KEY
        model = dynamic_model or self._model or settings.GEMINI_MODEL
        
        if not api_key:
            raise ValueError("Gemini API key is not configured.")
            
        client = genai.Client(api_key=api_key)
        return client, model

    async def parse_message(self, message_text: str, dynamic_key: str | None = None, dynamic_model: str | None = None) -> SignalParseSchema:
        """Sends the message text to Gemini and returns structured SignalParseSchema."""
        client, model = self._get_client_and_model(dynamic_key, dynamic_model)
        
        prompt = f"Parse this Telegram message:\n\n{message_text}"
        
        try:
            # Running synchronously inside an async wrapper or using native call.
            # google-genai is synchronous or asynchronous.
            # We can run in an executor if synchronous, or call natively if it has async.
            # Let's run it using loop.run_in_executor or call synchronous method directly.
            import asyncio
            loop = asyncio.get_event_loop()
            
            def call_gemini():
                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=SignalParseSchema,
                    temperature=0.1
                )
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                return response.text

            response_text = await loop.run_in_executor(None, call_gemini)
            logger.debug(f"Gemini API raw response: {response_text}")
            
            # Parse JSON to schema
            parsed_data = json.loads(response_text)
            return SignalParseSchema(**parsed_data)
            
        except APIError as e:
            logger.error(f"Gemini API Error: {e}")
            raise RuntimeError(f"Gemini API returned error: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Gemini: {e}")
            raise RuntimeError(f"Gemini did not return valid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Gemini client: {e}", exc_info=True)
            raise RuntimeError(f"Gemini processing failed: {str(e)}")

# Global client
gemini_client = GeminiClient()
