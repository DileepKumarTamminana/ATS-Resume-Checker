"""Pure-Python TF-IDF and cosine similarity — no third-party dependencies.

Kept dependency-free on purpose so the core analyzer runs anywhere, including
locked-down environments where installing scientific packages is not possible.
"""

from __future__ import annotations

import math
import re
from collections import Counter

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}")

# Compact English stop-word list (sufficient for keyword salience).
STOP_WORDS: frozenset[str] = frozenset(
    """
    a an and are as at be by for from has have in into is it its of on or that
    the their they this to was were will with we you your our us he she his her
    i me my am been being do does did done but if then else when where which who
    whom what how why not no nor so than too very can could should would may might
    must shall about above after again against all any because before below between
    both during each few more most other own same some such only up down out over
    under further here there also per via etc using use used within across upon
    """.split()
)

# Recruiting boilerplate that adds noise to keyword extraction without carrying
# real matchable signal.
BOILERPLATE_WORDS: frozenset[str] = frozenset(
    """
    strong hiring plus required require requires looking join ability able role roles
    position positions team teams work working years year candidate candidates ideal
    preferred desired responsibilities responsibility qualifications qualification
    including include includes seeking wanted opportunity opportunities help helping
    """.split()
)

STOP_WORDS = STOP_WORDS | BOILERPLATE_WORDS


def tokenize(text: str, keep_stop_words: bool = False) -> list[str]:
    tokens = (m.group(0).lower() for m in WORD_RE.finditer(text))
    if keep_stop_words:
        return list(tokens)
    return [t for t in tokens if t not in STOP_WORDS and not t.isdigit()]


def _ngrams(tokens: list[str], n: int) -> list[str]:
    if n == 1:
        return tokens
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def cosine_similarity(text_a: str, text_b: str) -> float:
    """TF cosine similarity between two documents. Returns 0.0–1.0."""
    counts_a = Counter(tokenize(text_a))
    counts_b = Counter(tokenize(text_b))
    if not counts_a or not counts_b:
        return 0.0

    shared = set(counts_a) & set(counts_b)
    dot = sum(counts_a[t] * counts_b[t] for t in shared)
    norm_a = math.sqrt(sum(v * v for v in counts_a.values()))
    norm_b = math.sqrt(sum(v * v for v in counts_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_keywords(text: str, top_n: int = 40, ngram_range: tuple[int, int] = (1, 2)) -> list[str]:
    """Rank salient keywords/phrases in ``text`` by TF-IDF over its sentences.

    Documents = sentences of the text. A term that appears in many sentences
    (low IDF) is down-weighted, so generic words fade and distinctive terms rise.
    """
    sentences = [s for s in re.split(r"[.\n!?;]", text) if s.strip()]
    if len(sentences) < 2:
        sentences = [text]

    lo, hi = ngram_range
    # Per-sentence term sets (for document frequency), plus separate global
    # frequencies for unigrams and higher-order n-grams.
    doc_term_sets: list[set[str]] = []
    unigram_tf: Counter[str] = Counter()
    phrase_tf: Counter[str] = Counter()
    for sent in sentences:
        toks = tokenize(sent)
        terms: list[str] = []
        for n in range(lo, hi + 1):
            for gram in _ngrams(toks, n):
                if len(gram) < 2:
                    continue
                terms.append(gram)
                if n == 1:
                    unigram_tf[gram] += 1
                else:
                    phrase_tf[gram] += 1
        doc_term_sets.append(set(terms))

    # Keep every unigram, but only multi-word phrases that actually recur —
    # one-off bigrams are mostly noise ("hiring senior", "aws docker").
    global_tf: Counter[str] = Counter(unigram_tf)
    for phrase, tf in phrase_tf.items():
        if tf > 1:
            global_tf[phrase] = tf

    num_docs = len(sentences)
    df: Counter[str] = Counter()
    for term_set in doc_term_sets:
        df.update(t for t in term_set if t in global_tf)

    scored: list[tuple[str, float]] = []
    for term, tf in global_tf.items():
        idf = math.log((1 + num_docs) / (1 + df[term])) + 1.0
        # Give recurring multi-word phrases a slight edge — they carry more signal.
        phrase_bonus = 1.15 if " " in term else 1.0
        scored.append((term, tf * idf * phrase_bonus))

    scored.sort(key=lambda x: (-x[1], x[0]))
    return [term for term, _ in scored[:top_n]]
