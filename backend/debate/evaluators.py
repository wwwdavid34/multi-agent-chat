"""Evaluator agents for debate quality assessment.

Lightweight AG2 agents using GPT-4o-mini to extract structured data:
- StanceExtractor: Parse positions/confidence from responses
- ArgumentParser: Extract claims/evidence/challenges
- ResponsivenessScorer: Measure @tag usage, argument addressing
- ConcessionDetector: Identify mind-changes and concessions
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple

from config import get_openai_api_key

try:
    import autogen as ag2
except ImportError:
    ag2 = None

logger = logging.getLogger(__name__)


class StanceExtractor:
    """Extract structured stance from panelist responses.
    
    Uses cheap GPT-4o-mini to parse:
    - Position (FOR/AGAINST/CONDITIONAL/NEUTRAL)
    - Core claim
    - Confidence level
    """
    
    EXTRACTION_PROMPT = """Analyze this panelist response and extract their stance.

Panelist: {panelist_name}
Response: {response}

Extract:
1. STANCE: Must be exactly one of: FOR, AGAINST, CONDITIONAL, NEUTRAL
2. CORE_CLAIM: A single sentence summarizing their main position
3. CONFIDENCE: A number 0.0-1.0 indicating confidence in their stance

Respond in JSON format:
{{"stance": "FOR|AGAINST|CONDITIONAL|NEUTRAL", "core_claim": "...", "confidence": 0.0-1.0}}"""

    def __init__(self):
        """Initialize stance extractor with GPT-4o-mini."""
        api_key = get_openai_api_key()
        if not api_key:
            raise RuntimeError("OpenAI API key required for evaluators")
        
        self.llm_config = {
            "model": "gpt-4o-mini",
            "api_key": api_key,
            "temperature": 0.1,  # Low temp for consistent extraction
            "response_format": {"type": "json_object"}
        }
    
    async def extract_stance(self, panelist_name: str, response: str, 
                           previous_stance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract stance from panelist response.
        
        Args:
            panelist_name: Name of panelist
            response: Their response text
            previous_stance: Previous stance data for drift detection
            
        Returns:
            Dict with stance, core_claim, confidence, changed_from_previous, change_explanation
        """
        try:
            # Create one-shot assistant for extraction
            if ag2 is None:
                raise RuntimeError("ag2 not installed")
            
            assistant = ag2.AssistantAgent(
                name="stance_extractor",
                llm_config=self.llm_config,
                system_message="You extract structured stance data from debate responses. Always respond with valid JSON."
            )
            
            user_proxy = ag2.UserProxyAgent(
                name="user",
                human_input_mode="NEVER",
                code_execution_config=False
            )
            
            # Get extraction
            prompt = self.EXTRACTION_PROMPT.format(
                panelist_name=panelist_name,
                response=response
            )
            
            result = user_proxy.initiate_chat(
                assistant,
                message=prompt,
                max_turns=1
            )
            
            # Parse JSON response
            last_message = result.chat_history[-1]["content"]
            stance_data = json.loads(last_message)
            
            # Validate stance
            valid_stances = {"FOR", "AGAINST", "CONDITIONAL", "NEUTRAL"}
            if stance_data.get("stance") not in valid_stances:
                logger.warning(f"Invalid stance '{stance_data.get('stance')}', defaulting to NEUTRAL")
                stance_data["stance"] = "NEUTRAL"
            
            # Clamp confidence
            stance_data["confidence"] = max(0.0, min(1.0, stance_data.get("confidence", 0.5)))
            
            # Check for stance drift
            changed_from_previous = False
            change_explanation = None
            
            if previous_stance and previous_stance.get("stance") != stance_data["stance"]:
                changed_from_previous = True
                # Ask for explanation if stance changed
                change_explanation = await self._get_change_explanation(
                    panelist_name, response, previous_stance["stance"], stance_data["stance"]
                )
            
            return {
                "panelist_name": panelist_name,
                "stance": stance_data["stance"],
                "core_claim": stance_data.get("core_claim", ""),
                "confidence": stance_data["confidence"],
                "changed_from_previous": changed_from_previous,
                "change_explanation": change_explanation
            }
            
        except Exception as e:
            logger.error(f"Error extracting stance for {panelist_name}: {e}")
            # Return neutral stance on error
            return {
                "panelist_name": panelist_name,
                "stance": "NEUTRAL",
                "core_claim": "Unable to extract stance",
                "confidence": 0.0,
                "changed_from_previous": False,
                "change_explanation": None
            }
    
    async def _get_change_explanation(self, panelist_name: str, response: str,
                                     old_stance: str, new_stance: str) -> str:
        """Extract explanation for stance change."""
        try:
            if ag2 is None:
                return "Stance changed"
            
            assistant = ag2.AssistantAgent(
                name="change_detector",
                llm_config=self.llm_config,
                system_message="You identify why a panelist changed their stance."
            )
            
            user_proxy = ag2.UserProxyAgent(
                name="user",
                human_input_mode="NEVER",
                code_execution_config=False
            )
            
            prompt = f"""The panelist {panelist_name} changed stance from {old_stance} to {new_stance}.

Response: {response}

In 1-2 sentences, explain what caused this change (new evidence, counterargument, etc.)."""
            
            result = user_proxy.initiate_chat(
                assistant,
                message=prompt,
                max_turns=1
            )
            
            return result.chat_history[-1]["content"]
            
        except Exception as e:
            logger.error(f"Error getting change explanation: {e}")
            return f"Changed from {old_stance} to {new_stance}"


class ArgumentParser:
    """Parse responses into structured argument units.
    
    Extracts:
    - Claims (assertions)
    - Evidence (supporting data)
    - Challenges (rebuttals to opponent claims)
    - Concessions (agreement with opponent)
    """
    
    PARSING_PROMPT = """Parse this debate response into structured argument units.

Panelist: {panelist_name}
Response: {response}

Extract all:
- CLAIMS: Assertions made by the panelist
- EVIDENCE: Supporting data, citations, or facts
- CHALLENGES: Direct rebuttals to opponent arguments
- CONCESSIONS: Acknowledgments of agreement with opponents

For each unit, identify:
- type: claim|evidence|challenge|concession
- content: The actual text
- confidence: 0.0-1.0 (how strongly stated)

Respond in JSON array format:
[{{"type": "claim", "content": "...", "confidence": 0.8}}, ...]"""

    def __init__(self):
        """Initialize argument parser with GPT-4o-mini."""
        api_key = get_openai_api_key()
        if not api_key:
            raise RuntimeError("OpenAI API key required for evaluators")
        
        self.llm_config = {
            "model": "gpt-4o-mini",
            "api_key": api_key,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
    
    async def parse_arguments(self, panelist_name: str, response: str,
                            previous_claims: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Parse response into argument units.
        
        Args:
            panelist_name: Name of panelist
            response: Their response text
            previous_claims: Claims from previous rounds for challenge linking
            
        Returns:
            List of argument units with type, content, confidence
        """
        try:
            if ag2 is None:
                raise RuntimeError("ag2 not installed")
            
            assistant = ag2.AssistantAgent(
                name="argument_parser",
                llm_config=self.llm_config,
                system_message="You parse debate responses into structured argument units. Always respond with valid JSON."
            )
            
            user_proxy = ag2.UserProxyAgent(
                name="user",
                human_input_mode="NEVER",
                code_execution_config=False
            )
            
            prompt = self.PARSING_PROMPT.format(
                panelist_name=panelist_name,
                response=response
            )
            
            result = user_proxy.initiate_chat(
                assistant,
                message=prompt,
                max_turns=1
            )
            
            # Parse JSON response
            last_message = result.chat_history[-1]["content"]
            parsed = json.loads(last_message)
            
            # Handle both array and object with "units" key
            units = parsed if isinstance(parsed, list) else parsed.get("units", [])
            
            # Validate and normalize units
            valid_types = {"claim", "evidence", "challenge", "concession"}
            normalized_units = []
            
            for unit in units:
                unit_type = unit.get("type", "claim").lower()
                if unit_type not in valid_types:
                    unit_type = "claim"
                
                confidence = max(0.0, min(1.0, unit.get("confidence", 0.5)))
                
                normalized_units.append({
                    "panelist_name": panelist_name,
                    "unit_type": unit_type,
                    "content": unit.get("content", ""),
                    "confidence": confidence,
                    "target_claim_id": None  # Will be linked later
                })
            
            return normalized_units
            
        except Exception as e:
            logger.error(f"Error parsing arguments for {panelist_name}: {e}")
            # Return minimal claim on error
            return [{
                "panelist_name": panelist_name,
                "unit_type": "claim",
                "content": response[:500],  # First 500 chars as fallback
                "confidence": 0.5,
                "target_claim_id": None
            }]


class ConcessionDetector:
    """Detect explicit concessions and mind-changes in responses.
    
    Looks for:
    - "I was wrong"
    - "You're right"
    - "I now agree"
    - "Given the evidence, I concede"
    """
    
    CONCESSION_PATTERNS = [
        r"i was wrong",
        r"you(?:'re| are) right",
        r"i (?:now |)agree",
        r"i concede",
        r"(?:that's |that is )a (?:good|fair|valid) point",
        r"i've changed my (?:mind|position|view)",
        r"given (?:the |this |that )evidence",
        r"you've convinced me",
    ]
    
    CONFIRMATION_PROMPT = """Does this response contain a genuine concession or mind-change?

Response: {response}

A concession means:
- Explicitly agreeing with an opponent's point
- Acknowledging a previous position was wrong
- Changing stance based on new evidence

Respond with JSON:
{{"is_concession": true|false, "explanation": "...", "what_was_conceded": "..."}}"""

    def __init__(self):
        """Initialize concession detector with GPT-4o-mini."""
        api_key = get_openai_api_key()
        if not api_key:
            raise RuntimeError("OpenAI API key required for evaluators")
        
        self.llm_config = {
            "model": "gpt-4o-mini",
            "api_key": api_key,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.CONCESSION_PATTERNS]
    
    async def detect_concession(self, panelist_name: str, response: str) -> Optional[Dict[str, Any]]:
        """Detect if response contains a concession.
        
        Args:
            panelist_name: Name of panelist
            response: Their response text
            
        Returns:
            Concession data if detected, None otherwise
        """
        # Quick pattern match first
        has_pattern = any(pattern.search(response) for pattern in self.patterns)
        
        if not has_pattern:
            return None  # Fast path: no concession markers
        
        # Confirm with LLM to avoid false positives
        try:
            if ag2 is None:
                return None
            
            assistant = ag2.AssistantAgent(
                name="concession_confirmer",
                llm_config=self.llm_config,
                system_message="You identify genuine concessions in debate responses."
            )
            
            user_proxy = ag2.UserProxyAgent(
                name="user",
                human_input_mode="NEVER",
                code_execution_config=False
            )
            
            prompt = self.CONFIRMATION_PROMPT.format(response=response)
            
            result = user_proxy.initiate_chat(
                assistant,
                message=prompt,
                max_turns=1
            )
            
            # Parse response
            last_message = result.chat_history[-1]["content"]
            data = json.loads(last_message)
            
            if data.get("is_concession"):
                return {
                    "panelist_name": panelist_name,
                    "explanation": data.get("explanation", ""),
                    "what_was_conceded": data.get("what_was_conceded", ""),
                    "response_excerpt": response[:300]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting concession for {panelist_name}: {e}")
            return None


class ResponsivenessScorer:
    """Score how well panelists address opponent arguments.
    
    Measures:
    - % of opponent claims addressed
    - Use of @Name tags
    - Direct responses vs tangential arguments
    """
    
    SCORING_PROMPT = """Evaluate how well this panelist responded to opponent arguments.

Panelist: {panelist_name}
Response: {response}

Opponent Claims (from previous round):
{opponent_claims}

Score on:
1. How many opponent claims were directly addressed?
2. How many were ignored or avoided?
3. How many @Name tags were used?

Respond with JSON:
{{
  "claims_addressed": <count>,
  "claims_missed": <count>,
  "tags_used": <count>,
  "score": <0.0-1.0>,
  "missed_arguments": [<brief descriptions>]
}}"""

    def __init__(self):
        """Initialize responsiveness scorer with GPT-4o-mini."""
        api_key = get_openai_api_key()
        if not api_key:
            raise RuntimeError("OpenAI API key required for evaluators")
        
        self.llm_config = {
            "model": "gpt-4o-mini",
            "api_key": api_key,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
    
    async def score_responsiveness(self, panelist_name: str, response: str,
                                  opponent_claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Score how well panelist addressed opponent arguments.
        
        Args:
            panelist_name: Name of panelist being scored
            response: Their response text
            opponent_claims: List of claims from opponents to address
            
        Returns:
            Responsiveness metrics
        """
        if not opponent_claims:
            # No opponents to respond to (first round or single panelist)
            return {
                "score": 1.0,
                "claims_addressed": 0,
                "claims_missed": 0,
                "tags_used": 0,
                "missed_arguments": []
            }
        
        try:
            if ag2 is None:
                raise RuntimeError("ag2 not installed")
            
            assistant = ag2.AssistantAgent(
                name="responsiveness_scorer",
                llm_config=self.llm_config,
                system_message="You evaluate how well debaters respond to opponent arguments."
            )
            
            user_proxy = ag2.UserProxyAgent(
                name="user",
                human_input_mode="NEVER",
                code_execution_config=False
            )
            
            # Format opponent claims
            claims_text = "\n".join([
                f"- {claim.get('panelist_name', 'Unknown')}: {claim.get('content', '')}"
                for claim in opponent_claims
            ])
            
            prompt = self.SCORING_PROMPT.format(
                panelist_name=panelist_name,
                response=response,
                opponent_claims=claims_text
            )
            
            result = user_proxy.initiate_chat(
                assistant,
                message=prompt,
                max_turns=1
            )
            
            # Parse response
            last_message = result.chat_history[-1]["content"]
            data = json.loads(last_message)
            
            # Validate and normalize
            score = max(0.0, min(1.0, data.get("score", 0.5)))
            
            return {
                "score": score,
                "claims_addressed": max(0, data.get("claims_addressed", 0)),
                "claims_missed": max(0, data.get("claims_missed", 0)),
                "tags_used": max(0, data.get("tags_used", 0)),
                "missed_arguments": data.get("missed_arguments", [])
            }
            
        except Exception as e:
            logger.error(f"Error scoring responsiveness for {panelist_name}: {e}")
            # Return neutral score on error
            return {
                "score": 0.5,
                "claims_addressed": 0,
                "claims_missed": len(opponent_claims),
                "tags_used": 0,
                "missed_arguments": []
            }
    
    def count_tags(self, response: str) -> int:
        """Count @Name tags in response (simple fallback)."""
        return len(re.findall(r'@\w+', response))
