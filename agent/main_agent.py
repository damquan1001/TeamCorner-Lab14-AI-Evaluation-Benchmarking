import asyncio
from typing import List, Dict

class MainAgent:
    """
    Đây là Agent mẫu sử dụng kiến trúc RAG đơn giản.
    Sinh viên nên thay thế phần này bằng Agent thực tế đã phát triển ở các buổi trước.
    """
    def __init__(self):
        self.name = "SupportAgent-v1"

    async def query(self, question: str) -> Dict:
        """
        Mô phỏng quy trình RAG:
        1. Retrieval: Tìm kiếm context liên quan.
        2. Generation: Gọi LLM để sinh câu trả lời.
        """
        # Giả lập độ trễ mạng/LLM
        await asyncio.sleep(0.01) # Chạy nhanh hơn
        
        # Mô phỏng việc lấy đúng doc_id dựa vào số trong câu hỏi
        sources = ["doc_policy_main"]
        import re
        match = re.search(r"số (\d+)", question)
        if match:
            sources.append(f"doc_{match.group(1)}")
            sources.append(f"doc_{match.group(1)}_v2")
            
        # Giả lập dữ liệu trả về
        return {
            "answer": f"Dựa trên tài liệu hệ thống, tôi xin trả lời câu hỏi '{question}' như sau: [Câu trả lời mẫu].",
            "contexts": [
                "Đoạn văn bản trích dẫn 1 dùng để trả lời...",
                "Đoạn văn bản trích dẫn 2 dùng để trả lời..."
            ],
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": 150,
                "sources": sources
            }
        }

if __name__ == "__main__":
    agent = MainAgent()
    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)
    asyncio.run(test())
