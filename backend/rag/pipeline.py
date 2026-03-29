import os
from typing import List, Optional, Tuple

import faiss
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from backend.resilience import ResilientLLMClient
from backend.exceptions import ExternalServiceError, CircuitBreakerOpen
from backend.logging_config import get_logger

load_dotenv()
logger = get_logger()


class RAGPipeline:
	def __init__(self, docs: List[str]):
		self.docs = [d for d in docs if isinstance(d, str) and d.strip()]
		self.model: Optional[SentenceTransformer] = None
		self.index: Optional[faiss.IndexFlatL2] = None
		self.llm_client: Optional[ResilientLLMClient] = None

		if self.docs:
			self.model = SentenceTransformer("all-MiniLM-L6-v2")
			embeddings = self.model.encode(self.docs, convert_to_numpy=True)
			self.index = faiss.IndexFlatL2(embeddings.shape[1])
			self.index.add(embeddings)  # type: ignore[arg-type]
		
		# Initialize resilient LLM client if credentials available
		base_client = self._build_client()
		if base_client:
			self.llm_client = ResilientLLMClient(base_client)

	def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
		if not self.docs or not self.model or not self.index:
			return []

		top_k = max(1, min(top_k, len(self.docs)))
		query_emb = self.model.encode([query], convert_to_numpy=True)
		distances, indices = self.index.search(query_emb, top_k)  # type: ignore[misc]
		results: List[Tuple[str, float]] = []
		for k, doc_index in enumerate(indices[0]):
			if 0 <= doc_index < len(self.docs):
				results.append((self.docs[doc_index], float(distances[0][k])))
		return results

	def _build_client(self) -> Optional[OpenAI]:
		api_key = os.getenv("GROQ_API_KEY")
		base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
		if not api_key:
			return None
		return OpenAI(api_key=api_key, base_url=base_url)

	def _fallback_answer(self, query: str, context: List[str]) -> str:
		q = (query or "").strip().lower()
		is_greeting = q in {"hi", "hello", "hey", "hii", "hola"} or q.startswith("hi ") or q.startswith("hello ")

		if context:
			return (
				"I found relevant context, but LLM mode is not configured yet. "
				f"Top reference: {context[0]}\n\n"
				"To enable full conversational answers, set GROQ_API_KEY in your environment."
			)

		if is_greeting:
			return (
				"Hi! I am ready to help with cost intelligence analysis. "
				"Share invoices, SLA logs, resource usage, or transactions to get anomalies, impact math, and actions. "
				"For full LLM responses, configure GROQ_API_KEY."
			)

		return (
			"I can still run deterministic cost analytics, but LLM mode is not configured and no context documents were provided. "
			"Please provide input data (invoices/SLA/resources/transactions) or set GROQ_API_KEY for richer conversational responses."
		)

	def generate_answer(self, query: str, context: List[str]) -> str:
		"""
		Generate answer using LLM with retrieved context.
		
		Args:
			query: User question
			context: Retrieved documents to use as context
		
		Returns:
			Generated answer string
		"""
		if not self.llm_client:
			return self._fallback_answer(query, context)

		try:
			context_block = "\n".join([f"- {doc}" for doc in context]) if context else "No retrieved documents."
			
			# Use resilient LLM client with circuit breaker
			response = self.llm_client.create_chat_completion(
				model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
				messages=[
					{
						"role": "system",
						"content": "You are an enterprise cost intelligence assistant. Answer using only the provided context when possible, and be explicit about uncertainty."
					},
					{
						"role": "user",
						"content": f"Context:\n{context_block}\n\nQuestion: {query}\n\nProvide concise reasoning and actionable recommendations."
					}
				],
				temperature=0.3,
				max_tokens=300
			)
			
			return response or "No response generated."
		except CircuitBreakerOpen as e:
			logger.warning(f"Circuit breaker open for LLM: {e}. Using fallback.")
			return self._fallback_answer(query, context)
		except ExternalServiceError as e:
			logger.error(f"External service error: {e}. Using fallback.")
			return self._fallback_answer(query, context)
		except Exception as e:
			logger.error(f"Unexpected error in generate_answer: {e}")
			return self._fallback_answer(query, context)

	def run(self, query: str) -> str:
		"""
		Retrieve context and generate answer.
		
		Args:
			query: User question
		
		Returns:
			Generated answer
		"""
		context_docs = [doc for doc, _ in self.retrieve(query)]
		return self.generate_answer(query, context_docs)
