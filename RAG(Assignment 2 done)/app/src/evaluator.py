import json
import logging
import re
from typing import Callable, Dict

from langfuse import observe

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_DEFAULT_SCORES: Dict[str, float] = {
    "faithfulness": 0.0,
    "relevance": 0.0,
    "groundedness": 0.0,
}

@observe(name="Evaluate_Response", as_type="span")
def evaluate_response(
    question: str,
    context: str,
    answer: str,
    llm_sync_fn: Callable[[str], str],
) -> Dict[str, float]:
    """
    Evaluate RAG answer quality using LLM-based scoring.

    Returns:
        {
            "faithfulness": float,
            "relevance": float,
            "groundedness": float
        }
    """

    if not answer.strip() or not context.strip():
        logger.debug("Evaluation skipped (empty answer or context)")
        return _DEFAULT_SCORES.copy()

    prompt = _build_eval_prompt(question, context, answer)

    try:
        raw_response = llm_sync_fn(prompt)
        scores = _parse_eval_json(raw_response)
        logger.info(
            "Evaluation complete | faith=%.3f rel=%.3f ground=%.3f",
            scores["faithfulness"],
            scores["relevance"],
            scores["groundedness"],
        )
        return scores

    except Exception:
        logger.exception("Evaluation LLM call failed")
        return _DEFAULT_SCORES.copy()


def _build_eval_prompt(question: str, context: str, answer: str) -> str:
    """
    Balanced evaluation prompt.
    Penalizes clear violations, allows paraphrasing.
    """

    return f"""
You are evaluating a RAG answer.

Score each metric between 0.0 and 1.0.

SCORING PRINCIPLES:
- Paraphrasing is acceptable.
- Minor wording differences are fine.
- Deduct ONLY for clear factual errors or hallucinations.

METRICS:

1) FAITHFULNESS
Claims must match the context.
Deduct:
-0.2 major factual error
-0.1 minor unsupported detail
-0.05 slight distortion

2) RELEVANCE
Answer must directly address the question.
Deduct:
-0.3 completely off-topic
-0.15 partially relevant
-0.05 minor tangent

3) GROUNDEDNESS (Primary hallucination signal)
Deduct:
-0.3 invented number/statistic
-0.2 invented proper name
-0.15 invented concrete fact
-0.05 vague unsupported generalization

CONTEXT:
{context[:4000]}

QUESTION:
{question}

ANSWER:
{answer}

Return ONLY JSON:
{{"faithfulness": <float>, "relevance": <float>, "groundedness": <float>}}
""".strip()


def _parse_eval_json(raw: str) -> Dict[str, float]:
    """
    Extract evaluation JSON from LLM output.

    Handles:
    - Markdown fences
    - Extra reasoning text
    - Single quotes
    """

    try:
        # Remove markdown fences
        cleaned = re.sub(r"```(?:json)?", "", raw)
        cleaned = cleaned.replace("```", "").strip()

        # Extract last JSON object
        matches = list(re.finditer(r"\{[^{}]+\}", cleaned, re.DOTALL))
        if not matches:
            logger.warning("No JSON found in evaluation response")
            return _DEFAULT_SCORES.copy()

        json_block = matches[-1].group(0).replace("'", '"')
        parsed = json.loads(json_block)

        scores: Dict[str, float] = {}

        for key in _DEFAULT_SCORES.keys():
            value = float(parsed.get(key, 0.0))
            # Clamp to [0, 1]
            value = max(0.0, min(1.0, value))
            scores[key] = round(value, 3)

        return scores

    except Exception:
        logger.warning("Failed to parse evaluation JSON")
        return _DEFAULT_SCORES.copy()
