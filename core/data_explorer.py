import asyncio
import logging
import json
from pathlib import Path
from core.data_explorer import DataExplorer
from core.event_bus import EventBus
from core.memory import Memory

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class NovaDataShell:
    """رابط خط فرمان غیرمسدودکننده برای Data Explorer"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.memory = Memory()
        # تزریق وابستگی‌ها به DataExplorer برای اتصال واقعی به حافظه
        self.explorer = DataExplorer(".", memory_manager=self.memory)
        self.running = True
        
    async def start(self):
        """شروع برنامه با بنر و ایندکس‌سازی اولیه"""
        print("""
╔══════════════════════════════════════════════════════╗
║  🔍 Nova Data Explorer v2.1 (Fully Async)           ║
║  [Non-blocking Input | Parallel Deep Search]        ║
╚══════════════════════════════════════════════════════╝
        """)
        
        print("⏳ Building initial index...")
        term_count = await self.explorer.build_index()
        stats = self.explorer.get_stats()
        
        print(f"✅ Indexed {term_count} terms | "
              f"📁 {stats['tracked_files']} files | "
              f"💾 {stats['total_size_mb']} MB\n")
        
        await self.main_loop()
    
    async def main_loop(self):
        """حلقه اصلی با ورودی غیرمسدودکننده"""
        commands_help = (
            "\n📌 Commands:\n"
            "  /search <term>  - جستجوی سریع (ایندکس)\n"
            "  /deep <term>    - جستجوی عمیق موازی\n"
            "  /memory <term>  - جستجو در حافظه Nova\n"
            "  /stats          - آمار ایندکس\n"
            "  /tree [path]    - درخت فایل‌ها\n"
            "  /exit           - خروج\n" + "-"*50
        )
        print(commands_help)
        
        loop = asyncio.get_running_loop()
        
        while self.running:
            try:
                # ✅ کلید اصلی: اجرای input در Thread جداگانه
                cmd = await loop.run_in_executor(None, input, "🚀 nova> ")
                cmd = cmd.strip()
                
                if not cmd:
                    continue
                    
                parts = cmd.split(maxsplit=1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                match command:
                    case "/exit":
                        self.running = False
                        print("👋 خداحافظ!")
                    case "/search":
                        await self._handle_search(arg)
                    case "/deep":
                        await self._handle_deep_search(arg)
                    case "/memory":
                        await self._handle_memory_search(arg)
                    case "/stats":
                        self._handle_stats()
                    case "/tree":
                        await self._handle_tree(arg)
                    case _:
                        print("❌ دستور ناشناخته. /help را امتحان کنید.")
                        
            except KeyboardInterrupt:
                print("\n⚠️ Use /exit to quit safely")
            except Exception as e:
                logger.error(f"Shell error: {e}", exc_info=True)
    
    async def _handle_search(self, query: str):
        if not query:
            print("⚠️ Usage: /search <term>")
            return
            
        result = await self.explorer.search(query, max_results=10)
        print(f"\n📋 {result['count']} results in {result['time_ms']}ms")
        
        for i, item in enumerate(result['results'], 1):
            snippet = item.get('snippet', '').replace('\n', ' ')[:150]
            print(f"{i}. 📄 {item['path']} ({item.get('size', 0)} bytes)")
            print(f"   📝 ...{snippet}...\n")
    
    async def _handle_deep_search(self, query: str):
        """جستجوی عمیق واقعاً موازی"""
        if not query:
            print("⚠️ Usage: /deep <term>")
            return
            
        print(f"🔍 Deep searching '{query}' (parallel)...")
        
        # جمع‌آوری فایل‌های هدف
        files = [
            p for p in Path(".").rglob("*") 
            if p.is_file() and p.suffix in DataExplorer.SUPPORTED_EXTENSIONS
        ]
        
        # جستجوی موازی با محدودیت همزمانی
        sem = asyncio.Semaphore(20)
        
        async def check_file(path: Path):
            async with sem:
                try:
                    async with aiofiles.open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = await f.read()
                        if query.lower() in content.lower():
                            return {"path": str(path), "size": path.stat().st_size}
                except Exception:
                    pass
            return None
        
        # نیاز به ایمپورت aiofiles در بالای فایل
        import aiofiles
        tasks = [check_file(f) for f in files]
        raw_results = await asyncio.gather(*tasks)
        results = [r for r in raw_results if r]
        
        print(f"📋 Found {len(results)} matches")
        for i, item in enumerate(results[:10], 1):
            print(f"{i}. 📄 {item['path']} ({item['size']} bytes)")
    
    async def _handle_memory_search(self, query: str):
        if not query:
            print("⚠️ Usage: /memory <term>")
            return
            
        results = await self.explorer.search_memory(query)
        if results:
            print(f"\n🧠 {len(results)} memory entries:")
            for i, entry in enumerate(results[:5], 1):
                # فرمت‌دهی هوشمند بر اساس نوع خروجی Memory
                text = entry.get('content', str(entry))[:200]
                print(f"{i}. 💭 {text}")
        else:
            print("📭 No memory entries found")
    
    def _handle_stats(self):
        stats = self.explorer.get_stats()
        print("\n📊 Statistics:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    async def _handle_tree(self, path_str: str):
        target = Path(path_str or ".")
        if not target.exists():
            print(f"❌ Path not found: {target}")
            return
            
        print(f"\n📂 Tree: {target}")
        # اجرای عملیات sync فایل‌سیستم در executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._print_tree_sync, target, "", True)
    
    def _print_tree_sync(self, path: Path, prefix: str, is_last: bool):
        """عملیات sync درخت که در Thread Pool اجرا می‌شود"""
        connector = "└── " if is_last else "├── "
        
        if path.is_file():
            size = path.stat().st_size
            print(f"{prefix}{connector}{path.name} ({size}b)")
            return
            
        print(f"{prefix}{connector}{path.name}/")
        children = sorted([p for p in path.iterdir() if not p.name.startswith('.')])
        
        for i, child in enumerate(children):
            new_prefix = prefix + ("    " if is_last else "│   ")
            self._print_tree_sync(child, new_prefix, i == len(children) - 1)

async def main():
    shell = NovaDataShell()
    await shell.start()

if __name__ == "__main__":
    asyncio.run(main())
