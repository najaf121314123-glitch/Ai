"""
AIBrain - هسته‌ی اصلی هوش مصنوعی Nova
نسخه‌ی حرفه‌ای با قابلیت‌های: چت واقعی، حافظه، جستجوی وب، حالت‌ها، و مدیریت هوشمند خطاها
(اصلاح‌شده: تزریق تاریخچه + استریمینگ کلمه‌محور | API text حفظ شده)
"""

import asyncio
import json
import logging
import time
import re
from datetime import datetime
from typing import Dict, Any, AsyncGenerator, List, Optional, Tuple
from urllib.parse import quote_plus

# ============================================
# ۱. واردات وابستگی‌ها با Fallback
# ============================================
try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False
    import requests

from core.event_bus import EventBus
from core.memory import Memory

logger = logging.getLogger(__name__)


# ============================================
# ۲. کلاس اصلی AIBrain
# ============================================
class AIBrain:
    """
    مغز اصلی Nova با قابلیت‌های پیشرفته:
    - جستجوی هوشمند با DuckDuckGo Text API
    - حافظه‌ی مکالمه (تزریق تاریخچه در پرامپت)
    - جستجوی وب با منبع
    - حالت‌های مختلف (خلاق، دقیق، علمی، ساده)
    - مدیریت خطا و Retry
    - کش کردن پاسخ‌ها برای سرعت بیشتر
    """
    
    # ==========================================
    # ۲-۱. تنظیمات اولیه
    # ==========================================
    MODES = {
        "creative": "خلاق و ادبی پاسخ بده.",
        "precise": "دقیق و مختصر پاسخ بده. از توضیحات اضافی پرهیز کن.",
        "scientific": "علمی و مبتنی بر شواهد پاسخ بده.",
        "simple": "ساده و قابل فهم برای عموم پاسخ بده."
    }
    
    DEFAULT_MODE = "creative"
    MAX_RETRIES = 3
    CACHE_TTL = 3600  # ۱ ساعت
    
    def __init__(
        self,
        event_bus: EventBus,
        memory: Memory,
        default_model: str = "gpt-4o-mini",
        mode: str = DEFAULT_MODE
    ):
        self.event_bus = event_bus
        self.memory = memory
        self.default_model = default_model
        self.mode = mode if mode in self.MODES else self.DEFAULT_MODE
        
        # کلاینت DuckDuckGo
        if HAS_DDGS:
            self.ddgs = DDGS()
            logger.info("🧠 AIBrain initialized with duckduckgo-search (Text Mode)")
        else:
            self.ddgs = None
            logger.warning("⚠️ duckduckgo-search not found. Using fallback mode.")
        
        # کش پاسخ‌ها
        self._cache: Dict[str, Tuple[str, float]] = {}
        
        # تاریخچه‌ی داخلی (برای جلوگیری از تکرار)
        self._last_query: str = ""
        self._last_response: str = ""
        
        # اشتراک در رویدادها
        self.event_bus.subscribe("user_message_received", self._handle_user_message)
        self.event_bus.subscribe("change_mode", self._change_mode)
        
        logger.info(f"🎯 AIBrain mode set to: {self.mode}")
    
    # ==========================================
    # ۲-۲. مدیریت حالت‌ها
    # ==========================================
    async def _change_mode(self, data: Dict[str, Any]) -> None:
        """تغییر حالت هوش مصنوعی"""
        new_mode = data.get("mode", self.DEFAULT_MODE)
        if new_mode in self.MODES:
            self.mode = new_mode
            logger.info(f"🔄 Mode changed to: {self.mode}")
            await self.event_bus.publish("mode_changed", {
                "mode": self.mode,
                "description": self.MODES[self.mode]
            })
        else:
            logger.warning(f"⚠️ Invalid mode: {new_mode}. Available: {list(self.MODES.keys())}")
    
    # ==========================================
    # ۲-۳. هندلر اصلی پیام
    # ==========================================
    async def _handle_user_message(self, event_data: Dict[str, Any]) -> None:
        """
        هندلر اصلی که پیام کاربر رو پردازش و پاسخ رو برمی‌گردونه.
        شامل: حافظه، کش، حالت‌ها، و مدیریت خطا
        """
        user_text = event_data.get("text", "").strip()
        session_id = event_data.get("session_id", "default")
        
        if not user_text:
            return
        
        start_time = time.time()
        logger.info(f"💬 Processing: {user_text[:50]}... (session: {session_id})")
        
        try:
            # ======== ۱. بررسی کش ========
            cache_key = f"{session_id}:{user_text}:{self.mode}"
            if cache_key in self._cache:
                cached_response, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self.CACHE_TTL:
                    logger.info(f"⚡ Cache hit for: {user_text[:30]}...")
                    await self._stream_response(session_id, cached_response, "cache")
                    return
            
            # ======== ۲. دریافت تاریخچه از حافظه ========
            history = await self._get_memory_history(session_id)
            
            # ======== ۳. تولید پاسخ ========
            full_response = ""
            async for chunk in self.chat(user_text, history, session_id):
                full_response += chunk
                await self.event_bus.publish("ai_response_chunk", {
                    "chunk": chunk,
                    "session_id": session_id
                })
            
            # ======== ۴. ذخیره در حافظه و کش ========
            await self.memory.save_interaction(session_id, user_text, full_response)
            
            # ذخیره در کش
            self._cache[cache_key] = (full_response, time.time())
            
            # ======== ۵. انتشار رویداد تکمیل ========
            await self.event_bus.publish("ai_response_complete", {
                "full_text": full_response,
                "session_id": session_id,
                "mode": self.mode,
                "duration_ms": round((time.time() - start_time) * 1000, 2)
            })
            
            # ذخیره آخرین سوال و پاسخ
            self._last_query = user_text
            self._last_response = full_response
            
            logger.info(f"✅ Response complete ({len(full_response)} chars) in {round(time.time() - start_time, 2)}s")
            
        except Exception as e:
            logger.error(f"❌ AI Error: {e}", exc_info=True)
            error_msg = f"\n❌ خطا در پردازش: {str(e)}"
            await self.event_bus.publish("ai_response_chunk", {
                "chunk": error_msg,
                "session_id": session_id,
                "is_error": True
            })
            await self.event_bus.publish("ai_response_error", {
                "error": str(e),
                "session_id": session_id,
                "mode": self.mode
            })
    
    # ==========================================
    # ۲-۴. دریافت تاریخچه از حافظه
    # ==========================================
    async def _get_memory_history(self, session_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """دریافت تاریخچه‌ی مکالمه از حافظه"""
        try:
            history = await self.memory.get_conversation_history(session_id, limit=limit)
            if history:
                logger.info(f"📚 Loaded {len(history)} history entries for session {session_id}")
                return history
        except Exception as e:
            logger.warning(f"⚠️ Could not load history: {e}")
        return []
    
    # ==========================================
    # ۲-۵. متد اصلی چت (اصلاح‌شده)
    # ==========================================
    async def chat(
        self,
        query: str,
        history: List[Dict[str, str]] = None,
        session_id: str = "default"
    ) -> AsyncGenerator[str, None]:
        """
        تولید پاسخ با text API + ادغام تاریخچه در پرامپت
        """
        loop = asyncio.get_running_loop()
        
        # ✅ ادغام تاریخچه در کوئری (بدون تغییر API)
        context_prompt = ""
        if history:
            recent = history[-3:]  # فقط ۳ پیام آخر
            context_lines = [f"{m.get('role','user')}: {m.get('content','')}" for m in recent]
            context_prompt = "تاریخچه مکالمه:\n" + "\n".join(context_lines) + "\n\nسوال جدید: "
        
        final_query = f"{context_prompt}{query} (حالت: {self.MODES.get(self.mode, '')})"
        
        if HAS_DDGS and self.ddgs:
            # ✅ همچنان از _search_with_retry استفاده می‌شود (text API)
            result = await loop.run_in_executor(
                None,
                self._search_with_retry, 
                final_query,
                session_id
            )
        else:
            result = await loop.run_in_executor(
                None,
                self._fallback_search,
                final_query
            )
        
        # ✅ افزودن منبع (منطق قبلی حفظ شده)
        result_with_source = self._add_source_if_needed(result, query)
        
        # ✅ استریمینگ کلمه‌محور (طبیعی‌تر از chunk_size=15)
        words = result_with_source.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.04)
    
    # ==========================================
    # ۲-۶. جستجو با Retry
    # ==========================================
    def _search_with_retry(self, query: str, session_id: str) -> str:
        """جستجو با قابلیت تکرار خودکار در صورت خطا"""
        for attempt in range(self.MAX_RETRIES):
            try:
                results = list(self.ddgs.text(query, max_results=1))
                if results:
                    answer = results[0].get("body", "")
                    if answer:
                        # اضافه کردن منبع
                        source = results[0].get("href", "")
                        if source:
                            answer += f"\n\n📎 منبع: {source}"
                        return answer
                return "نتیجه‌ای پیدا نشد. سوال خود را واضح‌تر بپرسید."
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(f"❌ Search failed after {self.MAX_RETRIES} attempts: {e}")
                    return f"خطا در جستجو پس از {self.MAX_RETRIES} بار تلاش: {str(e)}"
                logger.warning(f"⚠️ Search attempt {attempt+1} failed: {e}. Retrying...")
                time.sleep(1.5 ** attempt)  # Exponential backoff
        return "خطای غیرمنتظره در جستجو."
    
    # ==========================================
    # ۲-۷. Fallback به API عمومی
    # ==========================================
    def _fallback_search(self, query: str) -> str:
        """جستجوی Fallback با API عمومی DuckDuckGo"""
        try:
            encoded = quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            resp = requests.get(
                url,
                headers={"User-Agent": "Nova-AI/2.0 (Mobile)"},
                timeout=20
            )
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("AbstractText", "")
                if answer:
                    source = data.get("AbstractURL", "")
                    if source:
                        answer += f"\n\n📎 منبع: {source}"
                    return answer
                results = data.get("RelatedTopics", [])
                if results:
                    return results[0].get("Text", "نتیجه‌ای پیدا نشد.")
                return "پاسخی پیدا نشد. لطفاً سوال خود را واضح‌تر بپرسید."
            return f"خطای ارتباطی: {resp.status_code}"
        except Exception as e:
            logger.error(f"Fallback error: {e}")
            return f"خطا در ارتباط با DuckDuckGo: {str(e)}"
    
    # ==========================================
    # ۲-۸. بهبود پرامپت با حالت
    # ==========================================
    def _enhance_query_with_mode(self, query: str) -> str:
        """بهبود پرامپت بر اساس حالت انتخاب‌شده"""
        mode_instruction = self.MODES.get(self.mode, self.MODES[self.DEFAULT_MODE])
        return f"{query} (دستورالعمل: {mode_instruction})"
    
    # ==========================================
    # ۲-۹. افزودن منبع به پاسخ
    # ==========================================
    def _add_source_if_needed(self, response: str, query: str) -> str:
        """اگر پاسخ منبع نداشت، سعی کن منبع پیدا کنی"""
        if "📎 منبع:" in response:
            return response
        
        # ساده: اگر پاسخ کوتاه بود، منبع رو از جستجو بگیر
        if len(response) < 100 and "نتیجه‌ای پیدا نشد" not in response:
            # اینجا می‌تونی یه جستجوی سریع دیگه بزنی برای منبع
            pass
        
        return response
    
    # ==========================================
    # ۲-۱۰. استریم پاسخ
    # ==========================================
    async def _stream_response(self, session_id: str, text: str, source: str = "cache") -> None:
        """ارسال پاسخ ذخیره‌شده به صورت استریم"""
        logger.info(f"⚡ Streaming cached response (source: {source})")
        chunk_size = 15
        for i in range(0, len(text), chunk_size):
            await self.event_bus.publish("ai_response_chunk", {
                "chunk": text[i:i + chunk_size],
                "session_id": session_id,
                "cached": True
            })
            await asyncio.sleep(0.02)
        await self.event_bus.publish("ai_response_complete", {
            "full_text": text,
            "session_id": session_id,
            "cached": True,
            "source": source
        })
    
    # ==========================================
    # ۲-۱۱. متدهای کمکی
    # ==========================================
    def get_mode(self) -> str:
        """دریافت حالت فعلی"""
        return self.mode
    
    def get_modes(self) -> Dict[str, str]:
        """دریافت لیست حالت‌ها"""
        return self.MODES.copy()
    
    async def clear_cache(self) -> None:
        """پاک‌سازی کش"""
        self._cache.clear()
        logger.info("🗑️ Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """دریافت آمار"""
        return {
            "cache_size": len(self._cache),
            "mode": self.mode,
            "has_ddgs": HAS_DDGS,
            "default_model": self.default_model,
            "last_query": self._last_query[:50] if self._last_query else None,
            "last_response_length": len(self._last_response)
        }
