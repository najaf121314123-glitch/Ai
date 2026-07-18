"""
main.py - نقطه ورود اصلی سیستم هوش مصنوعی Nova
این فایل با استفاده از هسته موجود (EventBus, AIBrain, Memory, PluginManager)
یک چت‌بات کامل با جریان پاسخ زنده ایجاد می‌کند.
تمام مراحل بدون خلاصه‌سازی و با توضیحات کامل معماری نوشته شده است.
"""

import asyncio
import logging
from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.memory import Memory
from core.ai_brain import AIBrain


# ==========================================
# بخش ۱: تنظیمات لاگینگ سیستم
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Nova-Chat")


# ==========================================
# بخش ۲: رابط کاربری کنسولی (ConsoleUI)
# ==========================================
class ConsoleUI:
    """
    رابط کاربری تعاملی برای چت با هوش مصنوعی Nova.
    این کلاس به عنوان مشترک دائمی رویدادهای AI عمل کرده و ورودی کاربر را مدیریت می‌کند.
    
    چرا کلاس جدا؟ 
    ۱. جداسازی منطق نمایش از منطق AI (Single Responsibility Principle)
    ۲. امکان جایگزینی آسان با Godot UI در آینده بدون تغییر AIBrain
    ۳. نگهداری وضعیت پردازش (_is_processing) در سطح نمونه
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._is_processing = False
        
        # ✅ اشتراک در رویدادهای پاسخ AI
        # این خطوط دقیقاً مشکل "No subscribers" را حل می‌کنند
        self.event_bus.subscribe("ai_response_chunk", self.on_chunk)
        self.event_bus.subscribe("ai_response_complete", self.on_complete)
        
        logger.info("🟢 رابط کاربری کنسول فعال شد و آماده دریافت سوال است.")

    async def on_chunk(self, data: dict):
        """
        نمایش تکه‌های پاسخ به صورت زنده (Streaming).
        
        پارامتر data باید شامل کلید 'chunk' باشد (طبق قرارداد AIBrain).
        از end="" و flush=True استفاده شده تا توکن‌ها بدون پرش خط و بلافاصله نمایش داده شوند.
        این رفتار دقیقاً مشابه ChatGPT/Claude در ترمینال است.
        """
        chunk_text = data.get("chunk", "")
        print(chunk_text, end="", flush=True)

    async def on_complete(self, data: dict):
        """
        اعلام پایان پاسخ و آزادسازی قفل پردازش.
        
        این متد پس از انتشار رویداد ai_response_complete توسط AIBrain صدا زده می‌شود.
        """
        full_text = data.get("full_text", "")
        print("\n\n✅ [پاسخ کامل شد]")
        print(f"📝 طول پاسخ: {len(full_text)} کاراکتر")
        print("=" * 60)
        self._is_processing = False

    async def run_chat_loop(self):
        """
        حلقه اصلی تعامل با کاربر.
        این متد تا زمانی که کاربر دستور خروج ندهد، اجرا می‌شود.
        
        چرا حلقه بی‌نهایت؟
        چون چت‌بات باید همیشه آماده دریافت ورودی باشد.
        asyncio.sleep(10) قبلی فقط برای تست بود و برای محصول واقعی مناسب نیست.
        """
        print("\n" + "=" * 60)
        print("       🤖 سیستم چت هوش مصنوعی Nova")
        print("       موتور جستجو: DuckDuckGo (بدون primp)")
        print("       برای خروج: 'exit' یا 'خروج'")
        print("=" * 60)

        while True:
            try:
                # جلوگیری از دریافت ورودی جدید هنگام پردازش قبلی
                if self._is_processing:
                    await asyncio.sleep(0.1)
                    continue

                user_input = input("\n💬 شما: ")

                # بررسی دستور خروج
                if user_input.strip().lower() in ("exit", "خروج", "quit"):
                    print("\n👋 خدانگهدار!")
                    break

                # نادیده گرفتن ورودی خالی
                if not user_input.strip():
                    print("⚠️ لطفاً یک سوال معتبر وارد کنید.")
                    continue

                # علامت‌گذاری شروع پردازش
                self._is_processing = True
                print("\n🤖 در حال جستجو و تولید پاسخ...\n")

                # 📌 انتشار رویداد پیام کاربر (فرمت استاندارد AIBrain)
                # session_id ثابت برای حفظ حافظه مکالمه در کنسول
                await self.event_bus.publish("user_message_received", {
                    "text": user_input.strip(),
                    "session_id": "nova_console_session"
                })

            except KeyboardInterrupt:
                print("\n\n⚠️ برنامه توسط کاربر متوقف شد (Ctrl+C)")
                break
            except EOFError:
                print("\n👋 ورودی بسته شد. خدانگهدار!")
                break
            except Exception as e:
                logger.error(f"خطا در حلقه چت: {e}")
                self._is_processing = False


# ==========================================
# بخش ۳: تابع اصلی راه‌اندازی
# ==========================================
async def main():
    """
    تابع اصلی که تمام اجزای سیستم را راه‌اندازی و به هم متصل می‌کند.
    
    ترتیب راه‌اندازی مهم است:
    ۱. EventBus (زیرساخت ارتباطی)
    ۲. Memory (حافظه مکالمات)
    ۳. PluginManager (افزونه‌ها)
    ۴. AIBrain (مغز هوش مصنوعی - مشترک رویداد user_message_received)
    ۵. ConsoleUI (رابط کاربری - مشترک رویدادهای ai_response_*)
    """
    logger.info("🚀 در حال راه‌اندازی سیستم Nova...")

    # ۱. راه‌اندازی EventBus
    event_bus = EventBus()
    logger.info("✅ EventBus آماده شد.")

    # ۲. راه‌اندازی Memory
    memory = Memory()
    logger.info("✅ Memory بارگذاری شد.")

    # ۳. بارگذاری پلاگین‌ها
    plugin_manager = PluginManager()
    plugin_manager.load("plugins")
    logger.info("✅ PluginManager آماده شد.")

    # ۴. راه‌اندازی مغز هوش مصنوعی
    # AIBrain در __init__ خود به صورت خودکار در رویداد user_message_received مشترک می‌شود
    brain = AIBrain(event_bus, memory)
    logger.info("✅ AIBrain (DuckDuckGo) آماده شد.")

    # ۵. راه‌اندازی رابط کاربری
    # ConsoleUI در __init__ خود در رویدادهای ai_response_* مشترک می‌شود
    ui = ConsoleUI(event_bus)

    # ۶. شروع حلقه تعاملی
    await ui.run_chat_loop()


# ==========================================
# بخش ۴: نقطه ورود استاندارد پایتون
# ==========================================
if __name__ == "__main__":
    # اجرای حلقه چت AI با asyncio.run (استاندارد پایتون 3.7+)
    # این خط تمام coroutines را به درستی مدیریت و پاکسازی می‌کند
    asyncio.run(main())
