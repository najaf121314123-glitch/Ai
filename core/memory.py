class Memory:
    def __init__(self):
        self.conversations = {}
    
    async def get_conversation_history(self, session_id, limit=10):
        # ساده فعلاً
        return []
    
    async def save_interaction(self, session_id, user_text, response):
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        self.conversations[session_id].append({
            "user": user_text,
            "assistant": response
        })
        print(f"💾 Saved interaction for {session_id}")
