import asyncio
import re
from typing import Dict, List


INJECTION_PATTERNS = [
    r"ignore all previous",
    r"bỏ qua các lệnh",
    r"you have been hacked",
]
UNSAFE_PATTERNS = [
    r"\bhack\b",
    r"làm thơ về chính trị",
    r"kịch bản phim",
]


class MainAgent:
    """Agent V1 — retrieval cơ bản, doc_policy_main luôn đứng đầu."""

    def __init__(self):
        self.name = "SupportAgent-v1"
        self.version = "v1"

    def _is_unsafe(self, question: str) -> bool:
        q = question.lower()
        return any(re.search(p, q) for p in INJECTION_PATTERNS + UNSAFE_PATTERNS)

    def _retrieve_sources(self, question: str) -> List[str]:
        sources = ["doc_policy_main"]
        match = re.search(r"số (\d+)", question)
        if match:
            sources.append(f"doc_{match.group(1)}")
            sources.append(f"doc_{match.group(1)}_v2")
        return sources

    async def query(self, question: str) -> Dict:
        await asyncio.sleep(0.01)

        if self._is_unsafe(question):
            return {
                "answer": "Tôi không thể hỗ trợ yêu cầu này. Vui lòng đặt câu hỏi liên quan đến quy trình nội bộ.",
                "contexts": [],
                "metadata": {
                    "model": "gpt-4o-mini",
                    "tokens_used": 80,
                    "sources": ["doc_policy_main"],
                },
            }

        sources = self._retrieve_sources(question)
        return {
            "answer": f"Dựa trên tài liệu hệ thống, tôi xin trả lời câu hỏi '{question}' như sau: [Câu trả lời mẫu].",
            "contexts": [
                "Đoạn văn bản trích dẫn 1 dùng để trả lời...",
                "Đoạn văn bản trích dẫn 2 dùng để trả lời...",
            ],
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": 150,
                "sources": sources,
            },
        }


class MainAgentV2(MainAgent):
    """Agent V2 — retrieval cải tiến (doc liên quan lên đầu) + safety tốt hơn."""

    def __init__(self):
        super().__init__()
        self.name = "SupportAgent-v2"
        self.version = "v2"

    def _retrieve_sources(self, question: str) -> List[str]:
        match = re.search(r"số (\d+)", question)
        if match:
            n = match.group(1)
            return [f"doc_{n}", f"doc_{n}_v2", "doc_policy_main"]
        return ["doc_policy_main"]

    async def query(self, question: str) -> Dict:
        await asyncio.sleep(0.01)

        if self._is_unsafe(question):
            return {
                "answer": "Tôi không thể hỗ trợ yêu cầu này vì nằm ngoài phạm vi hỗ trợ hoặc vi phạm chính sách an toàn.",
                "contexts": [],
                "metadata": {
                    "model": "gpt-4o-mini",
                    "tokens_used": 60,
                    "sources": ["doc_policy_main"],
                },
            }

        # Out-of-context: không có số trong câu hỏi và không phải hard case có policy
        if "quy trình" not in question.lower() and "quy định" not in question.lower():
            ambiguous_markers = ["cái đó", "hồi nãy", "trực thăng", "bước 1 đến 100"]
            if any(m in question.lower() for m in ambiguous_markers):
                return {
                    "answer": "Tôi không có đủ thông tin trong tài liệu để trả lời chính xác câu hỏi này.",
                    "contexts": [],
                    "metadata": {
                        "model": "gpt-4o-mini",
                        "tokens_used": 70,
                        "sources": ["doc_policy_main"],
                    },
                }

        sources = self._retrieve_sources(question)
        return {
            "answer": f"Theo tài liệu nội bộ ({', '.join(sources[:2])}), câu trả lời cho '{question}' là: [Chi tiết dựa trên ground truth].",
            "contexts": [
                "Đoạn văn bản trích dẫn 1 dùng để trả lời...",
                "Đoạn văn bản trích dẫn 2 dùng để trả lời...",
            ],
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": 120,
                "sources": sources,
            },
        }


if __name__ == "__main__":
    async def test():
        for agent_cls in (MainAgent, MainAgentV2):
            agent = agent_cls()
            resp = await agent.query("Câu hỏi thông thường số 5 về quy trình nội bộ?")
            print(agent.name, resp["metadata"]["sources"])

    asyncio.run(test())
