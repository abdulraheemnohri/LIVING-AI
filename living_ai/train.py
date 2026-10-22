import argparse
from .training import train_directory
def main():
    p=argparse.ArgumentParser(description="Train LIVING AI's original character n-gram model.")
    p.add_argument("--input",default="data/corpus");p.add_argument("--output",default="models/char_ngram.json")
    a=p.parse_args();print(train_directory(a.input,a.output))
if __name__=="__main__":main()
