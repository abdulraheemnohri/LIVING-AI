from living_ai.model import CharNGramModel
def test_model_roundtrip(tmp_path):
    m=CharNGramModel(3);m.train_text("the quick brown fox")
    p=tmp_path/"model.json";m.save(p);n=CharNGramModel.load(p)
    assert n.trained_chars==m.trained_chars and n.transitions
