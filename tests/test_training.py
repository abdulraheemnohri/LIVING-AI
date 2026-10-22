from living_ai.training import train_directory
from living_ai.model import CharNGramModel
def test_train_directory(tmp_path,monkeypatch):
    monkeypatch.setenv("LIVING_AI_DATA_DIR",str(tmp_path/"data"))
    corpus=tmp_path/"corpus";corpus.mkdir();(corpus/"sample.txt").write_text("local AI learns safely",encoding="utf-8")
    output=tmp_path/"model.json";r=train_directory(str(corpus),str(output))
    assert r["files"]==1 and CharNGramModel.load(output).trained_chars>0
