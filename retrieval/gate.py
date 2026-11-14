"""Abstain gate. Lives in code, not in a prompt. Calibrated on the lexical (TF-IDF) score of the top hit."""
GATE = 0.05
def abstain(top_lexical: float, gate: float = GATE) -> bool:
    return top_lexical < gate
