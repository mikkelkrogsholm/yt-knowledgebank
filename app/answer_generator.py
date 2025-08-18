"""
Answer Generator for RAG Pipeline.

This module handles answer generation using OpenAI's GPT models,
including prompt engineering, conversation context, and citation extraction.

Phase 4 Module 3: Answer Generation
"""
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import openai
from app.settings import get_openai_api_key, get_model_config


@dataclass
class GeneratedAnswer:
    """Represents a generated answer with metadata."""
    answer: str
    confidence: float
    citations: List[Dict[str, Any]]
    model_used: str
    token_usage: Optional[Dict[str, int]] = None


class AnswerGenerator:
    """
    Generates answers using OpenAI's GPT models with context and conversation history.
    
    Handles prompt engineering, model selection, and response parsing
    for high-quality question answering.
    """
    
    def __init__(self):
        """Initialize the answer generator."""
        self.api_key = get_openai_api_key()
        self.model_config = get_model_config()
        
        if not self.api_key:
            raise ValueError("OpenAI API key not configured. Please set it in settings.")
        
        # Set up OpenAI client
        openai.api_key = self.api_key
        
        # Model configuration
        self.model = self.model_config["models"]["question_answering"]
        self.fallback_model = self.model_config["models"]["fallback"]
        self.temperature = self.model_config["limits"]["temperature_qa"]
        self.max_tokens = self.model_config["limits"]["max_tokens_qa"]
        
        # Prompt templates
        self.system_prompt = self._build_system_prompt()
    
    def generate_answer(self, question: str, context: str, sources: List[Dict[str, Any]],
                       conversation_history: Optional[List[Dict[str, str]]] = None) -> GeneratedAnswer:
        """
        Generate answer using context and conversation history.
        
        Args:
            question: The question to answer
            context: Assembled context from search results
            sources: Source information for citation
            conversation_history: Previous conversation messages
            
        Returns:
            GeneratedAnswer with answer, confidence, and citations
        """
        try:
            # Build the prompt
            user_prompt = self._build_user_prompt(question, context, sources)
            
            # Prepare messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history[-6:])  # Limit to recent history
            
            # Add current question
            messages.append({"role": "user", "content": user_prompt})
            
            # Generate answer
            response = self._call_openai(messages)
            
            # Parse response
            parsed_response = self._parse_response(response)
            
            return GeneratedAnswer(
                answer=parsed_response["answer"],
                confidence=parsed_response["confidence"],
                citations=parsed_response["citations"],
                model_used=self.model,
                token_usage=response.get("usage")
            )
            
        except Exception as e:
            print(f"Error generating answer: {e}")
            
            # Return fallback answer
            return GeneratedAnswer(
                answer=f"I apologize, but I encountered an error while generating an answer: {str(e)}",
                confidence=0.0,
                citations=[],
                model_used=self.model
            )
    
    def _call_openai(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Call OpenAI API with error handling and fallback."""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            return {
                "content": response.choices[0].message.content,
                "usage": dict(response.usage) if hasattr(response, 'usage') else None
            }
            
        except Exception as e:
            print(f"Primary model {self.model} failed: {e}")
            
            # Try fallback model
            try:
                response = openai.ChatCompletion.create(
                    model=self.fallback_model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"}
                )
                
                return {
                    "content": response.choices[0].message.content,
                    "usage": dict(response.usage) if hasattr(response, 'usage') else None
                }
                
            except Exception as fallback_error:
                print(f"Fallback model {self.fallback_model} also failed: {fallback_error}")
                raise e  # Raise original error
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for answer generation."""
        return """You are an expert AI assistant that answers questions based on provided context from YouTube video transcripts.

Your task is to:
1. Provide accurate, helpful answers based ONLY on the provided context
2. Cite specific sources when making claims
3. Be honest when information is insufficient or missing
4. Maintain conversation context from previous exchanges
5. Structure your response as valid JSON

Response format:
{
  "answer": "Your comprehensive answer here",
  "confidence": 0.0-1.0,
  "citations": [
    {
      "chunk_id": number,
      "relevance": "high|medium|low",
      "quote": "specific relevant quote from source"
    }
  ]
}

Guidelines:
- Base your answer ONLY on the provided context
- If the context doesn't contain sufficient information, say so
- Cite sources for all factual claims
- Use natural, conversational language
- Be concise but comprehensive
- Maintain accuracy over completeness"""
    
    def _build_user_prompt(self, question: str, context: str, sources: List[Dict[str, Any]]) -> str:
        """Build the user prompt with question and context."""
        # Create source reference mapping
        source_refs = {}
        for i, source in enumerate(sources):
            source_refs[source.get("chunk_id", i)] = {
                "video_id": source.get("video_id", "unknown"),
                "start_ms": source.get("start_ms", 0),
                "end_ms": source.get("end_ms", 0)
            }
        
        prompt = f"""Question: {question}

Context from video transcripts:
{context}

Source reference mapping:
{json.dumps(source_refs, indent=2)}

Please answer the question based on the provided context. Include relevant citations in your response."""
        
        return prompt
    
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse OpenAI response and validate structure."""
        try:
            content = response["content"]
            parsed = json.loads(content)
            
            # Validate required fields
            if "answer" not in parsed:
                raise ValueError("Response missing 'answer' field")
            
            # Set defaults for missing fields
            parsed.setdefault("confidence", 0.5)
            parsed.setdefault("citations", [])
            
            # Validate confidence score
            if not isinstance(parsed["confidence"], (int, float)):
                parsed["confidence"] = 0.5
            else:
                parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
            
            # Validate citations structure
            if not isinstance(parsed["citations"], list):
                parsed["citations"] = []
            
            validated_citations = []
            for citation in parsed["citations"]:
                if isinstance(citation, dict):
                    validated_citation = {
                        "chunk_id": citation.get("chunk_id"),
                        "relevance": citation.get("relevance", "medium"),
                        "quote": citation.get("quote", "")
                    }
                    validated_citations.append(validated_citation)
            
            parsed["citations"] = validated_citations
            
            return parsed
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Raw response: {response.get('content', '')}")
            
            # Extract answer from raw text if JSON parsing fails
            raw_content = response.get("content", "")
            return {
                "answer": raw_content if raw_content else "I apologize, but I couldn't generate a proper response.",
                "confidence": 0.3,
                "citations": []
            }
        
        except Exception as e:
            print(f"Error parsing response: {e}")
            return {
                "answer": "I apologize, but I encountered an error while processing the response.",
                "confidence": 0.0,
                "citations": []
            }
    
    def generate_followup_suggestions(self, question: str, answer: str, 
                                    sources: List[Dict[str, Any]]) -> List[str]:
        """
        Generate follow-up question suggestions based on the current Q&A.
        
        Args:
            question: Original question
            answer: Generated answer
            sources: Sources used for the answer
            
        Returns:
            List of suggested follow-up questions
        """
        try:
            prompt = f"""Based on this Q&A exchange, suggest 3 relevant follow-up questions that would help the user learn more:

Question: {question}
Answer: {answer}

Generate 3 natural follow-up questions that:
1. Explore related concepts mentioned in the answer
2. Ask for more details about specific points
3. Connect to broader topics from the available sources

Return as JSON:
{{"suggestions": ["question1", "question2", "question3"]}}"""
            
            response = openai.ChatCompletion.create(
                model=self.fallback_model,  # Use lighter model for suggestions
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates relevant follow-up questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            parsed = json.loads(response.choices[0].message.content)
            return parsed.get("suggestions", [])
            
        except Exception as e:
            print(f"Error generating follow-up suggestions: {e}")
            return []
    
    def estimate_response_quality(self, answer: str, context: str, 
                                 confidence: float) -> Dict[str, Any]:
        """
        Estimate the quality of a generated response.
        
        Args:
            answer: Generated answer
            context: Context used for generation
            confidence: Model's confidence score
            
        Returns:
            Quality metrics dictionary
        """
        # Basic quality metrics
        answer_length = len(answer.split())
        context_length = len(context.split())
        
        # Calculate context utilization
        context_words = set(context.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(context_words.intersection(answer_words))
        
        if len(context_words) > 0:
            context_utilization = overlap / len(context_words)
        else:
            context_utilization = 0.0
        
        # Estimate completeness
        completeness = min(1.0, answer_length / 50)  # Assume 50 words is reasonably complete
        
        # Overall quality score
        quality_score = (confidence * 0.4 + context_utilization * 0.3 + completeness * 0.3)
        
        return {
            "quality_score": round(quality_score, 3),
            "answer_length": answer_length,
            "context_utilization": round(context_utilization, 3),
            "completeness": round(completeness, 3),
            "confidence": confidence
        }