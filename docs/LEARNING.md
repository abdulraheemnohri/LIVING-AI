# Learning and evaluation memory (Phase 5 foundation)

`living_ai.learning.LearningStore` keeps local SQLite records of goal outcomes, numeric scores,
feedback, plan summaries, and tags. It retrieves relevant past evaluations using lexical overlap
and reports aggregate statistics.

```python
from living_ai.learning import LearningStore
store = LearningStore("data/learning.sqlite3")
store.record("Build a local Python assistant", score=0.9, outcome="Unit tests passed",
             feedback="Keep dependencies minimal", tags=["python", "offline"])
print(store.retrieve("Python offline assistant"))
print(store.summary())
```

Scores are supplied by a human or external evaluator; the store does not independently verify
success. Retrieval is lexical, not embeddings or semantic search. No network, model dependency,
weight training, source modification, or permission changes are performed.
