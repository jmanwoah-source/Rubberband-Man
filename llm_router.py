"""
Rubberband Man - Universal LLM Compute Router (ASUS GX10 Qwen 3.8 + Cloud Gemini 2.5)
Bridges Local ASUS GX10 Supercomputer (Qwen 3.8 via Ollama, vLLM, SGLang, LM Studio)
and Cloud Google Gemini 2.5 Flash with intelligent auto-discovery and failover.
100% POSIX / Linux & Windows compatible.
"""

import os
import json
import time
from typing import Dict, Any, Tuple, Optional, List
import requests
from dotenv import load_dotenv

load_dotenv()


def get_active_backend() -> str:
    """Returns 'local' (ASUS GX10 Qwen 3.8) or 'gemini'."""
    return os.getenv("LLM_BACKEND", "gemini").strip().lower()


def normalize_endpoint_url(url: str) -> str:
    """Ensures OpenAI-compatible URL format with /v1, handling raw host/port inputs."""
    if not url:
        return "http://localhost:11434/v1"
    url = url.strip().rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"http://{url}"
    if not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


def get_local_config() -> Dict[str, str]:
    """Returns local ASUS GX10 model server configuration."""
    raw_url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1").strip()
    url = normalize_endpoint_url(raw_url)
    model = os.getenv("LOCAL_LLM_MODEL", "qwen3.8:latest").strip()
    api_key = os.getenv("LOCAL_LLM_API_KEY", "ollama").strip()
    return {"url": url, "model": model, "api_key": api_key}


def fetch_available_models(endpoint_url: str = None) -> List[str]:
    """
    Auto-discovers and queries installed models from local Ollama / vLLM / SGLang / LM Studio.
    Supports both OpenAI /v1/models and native Ollama /api/tags.
    Prioritizes Qwen 3.8 / Qwen models at the top of the list.
    """
    cfg = get_local_config()
    raw_url = (endpoint_url or cfg["url"]).strip().rstrip("/")
    base_url = raw_url[:-3] if raw_url.endswith("/v1") else raw_url
    v1_url = raw_url if raw_url.endswith("/v1") else f"{raw_url}/v1"

    models = []
    # 1. Try Ollama native /api/tags
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=2.5)
        if r.status_code == 200:
            data = r.json()
            if "models" in data and isinstance(data["models"], list):
                for m in data["models"]:
                    name = m.get("name") or m.get("model")
                    if name and name not in models:
                        models.append(name)
    except Exception:
        pass

    # 2. Try OpenAI /v1/models (vLLM, SGLang, LM Studio, Ollama /v1)
    if not models:
        try:
            r = requests.get(f"{v1_url}/models", timeout=2.5)
            if r.status_code == 200:
                data = r.json()
                if "data" in data and isinstance(data["data"], list):
                    for m in data["data"]:
                        mid = m.get("id")
                        if mid and mid not in models:
                            models.append(mid)
        except Exception:
            pass

    def _qwen_sort_key(name: str):
        nl = name.lower()
        if "qwen3.8" in nl or "qwen-3.8" in nl:
            return (0, nl)
        if "qwen3" in nl:
            return (1, nl)
        if "qwen" in nl:
            return (2, nl)
        return (3, nl)

    return sorted(models, key=_qwen_sort_key)


def test_local_connection(endpoint_url: str = None, model_name: str = None) -> Tuple[bool, str, float]:
    """
    Pings local or LAN ASUS GX10 OpenAI-compatible endpoint (Ollama, vLLM, LM Studio)
    to check connectivity and latency.
    """
    cfg = get_local_config()
    url = normalize_endpoint_url(endpoint_url or cfg["url"])

    t0 = time.time()
    try:
        models_url = f"{url}/models"
        resp = requests.get(models_url, timeout=3.0)
        latency_ms = (time.time() - t0) * 1000.0

        if resp.status_code == 200:
            available = fetch_available_models(url)
            model_info = f" ({len(available)} model(s) found: {', '.join(available[:3])})" if available else ""
            return True, f"GX10 Online · {latency_ms:.0f}ms latency{model_info}", latency_ms
        else:
            return False, f"HTTP {resp.status_code} from {url}", 0.0
    except requests.exceptions.ConnectionError:
        return False, f"Connection refused at {url}. Ensure Qwen 3.8 (Ollama/vLLM) is active on GX10.", 0.0
    except requests.exceptions.Timeout:
        return False, f"Timed out connecting to {url} (>3.0s)", 0.0
    except Exception as e:
        return False, f"Error: {str(e)}", 0.0


def test_gemini_connection() -> Tuple[bool, str]:
    """Verifies Gemini API Key."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return False, "GEMINI_API_KEY is missing."
    try:
        from google import genai
        client = genai.Client(api_key=key)
        client.models.get(model="gemini-3.5-flash-lite")
        return True, "Online (Google Gemini 3.5 Flash Lite API)"
    except Exception as e:
        err = str(e)
        if "API_KEY_INVALID" in err or "400" in err:
            return False, "Invalid API Key"
        return True, f"Configured (Verification: {err[:50]})"


def generate_text(prompt: str, system_instruction: str = "", temperature: float = 0.2) -> Tuple[str, str]:
    """
    Unified text generation router.
    Targets ASUS GX10 Qwen 3.8 when backend == 'local', with automatic fallback to
    discovered Qwen model or Cloud Gemini 3.5 Flash Lite if local daemon is temporarily unreachable.
    """
    backend = get_active_backend()

    if backend == "local":
        text, err = _generate_local(prompt, system_instruction, temperature)
        if text:
            return text, ""
        # Automatic resilience fallback to Gemini if GEMINI_API_KEY is available and local node is offline
        if os.getenv("GEMINI_API_KEY", "").strip():
            g_text, g_err = _generate_gemini(prompt, system_instruction, temperature)
            if g_text:
                return f"*(⚡ GX10 Local Node Offline — Auto-Routed via Gemini 3.5 Flash Lite Standby)*\n\n{g_text}", ""
        return "", err
    else:
        return _generate_gemini(prompt, system_instruction, temperature)


def _generate_local(prompt: str, system_instruction: str, temperature: float) -> Tuple[str, str]:
    """Calls local ASUS GX10 OpenAI-compatible endpoint (Ollama, vLLM, SGLang) for Qwen 3.8."""
    cfg = get_local_config()
    chat_url = f"{cfg['url']}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}"
    }

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    target_model = cfg["model"]

    for attempt in range(2):
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        try:
            resp = requests.post(chat_url, headers=headers, json=payload, timeout=95.0)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    content = choices[0]["message"].get("content", "")
                    return content.strip(), ""
                return "No content returned by local Qwen 3.8 model.", ""
            elif resp.status_code == 404 and attempt == 0:
                available = fetch_available_models(cfg["url"])
                if available:
                    target_model = available[0]
                    continue
                return "", f"Model '{cfg['model']}' not found at {cfg['url']} (HTTP 404)."
            else:
                return "", f"Local GX10 model error HTTP {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.ConnectionError:
            return "", f"Failed to connect to ASUS GX10 endpoint at {cfg['url']}. Ensure Ollama/vLLM is running with '{cfg['model']}'."
        except requests.exceptions.Timeout:
            return "", f"ASUS GX10 endpoint timed out after 95s at {cfg['url']}."
        except Exception as e:
            return "", f"Local model call exception: {str(e)}"

    return "", "Local model generation failed."


def _generate_gemini(prompt: str, system_instruction: str, temperature: float) -> Tuple[str, str]:
    """Calls Google Gemini API with fallback cascade."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return "", "GEMINI_API_KEY is not configured."

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction if system_instruction else None,
            temperature=temperature
        )

        fallback_models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
        last_err = None

        for model in fallback_models:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config
                    )
                    if response and response.text:
                        return response.text.strip(), ""
                except Exception as e:
                    last_err = e
                    time.sleep(0.5 * (attempt + 1))
                    continue
        return "", f"Gemini API failure across models: {str(last_err)}"
    except Exception as e:
        return "", f"Gemini client initialization error: {str(e)}"
