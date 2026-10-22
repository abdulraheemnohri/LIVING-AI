from living_ai.learning import LearningStore

def test_record_retrieve_and_summary(tmp_path):
    store=LearningStore(tmp_path/"learning.sqlite3")
    store.record("Build a local Python assistant",score=0.9,outcome="Tests passed",
                 feedback="Keep implementation offline",tags=["python","offline"])
    store.record("Prepare a gardening schedule",score=0.4,outcome="Missing seasonal details")
    assert store.retrieve("Python offline assistant")[0]["goal"]=="Build a local Python assistant"
    summary=store.summary()
    assert summary["evaluations"]==2 and summary["positive_evaluations"]==1
    assert 0 < summary["average_score"] < 1

def test_invalid_inputs_rejected(tmp_path):
    store=LearningStore(tmp_path/"learning.sqlite3")
    for kwargs in [{"goal":"","score":.5,"outcome":"ok"},{"goal":"goal","score":-0.1,"outcome":"bad"},
                   {"goal":"goal","score":1.1,"outcome":"bad"},{"goal":"goal","score":True,"outcome":"bad"},
                   {"goal":"goal","score":.5,"outcome":""}]:
        try: store.record(**kwargs); assert False,"expected ValueError"
        except ValueError: pass

def test_retrieval_bounded_and_persistent(tmp_path):
    path=tmp_path/"learning.sqlite3"; store=LearningStore(path)
    for i in range(8): store.record(f"Task item {i}",score=.5,outcome="reviewed")
    assert len(store.retrieve("",limit=3))==3
    assert LearningStore(path).summary()["evaluations"]==8
