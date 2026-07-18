import asyncio

class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event, callback):
        if event not in self.subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append(callback)
        print(f"✅ Subscribed to {event}")

    async def publish(self, event, data):
        if event in self.subscribers:
            for callback in self.subscribers[event]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
        else:
            print(f"⚠️ No subscribers for event: {event}")
