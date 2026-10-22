import argparse
import json
from .neural_training import train_small_transformer


def main():
    parser = argparse.ArgumentParser(description="Train LIVING AI's tiny byte-level Transformer from random initialization.")
    parser.add_argument("--input", default="data/corpus", help="Directory containing UTF-8 .txt/.md files")
    parser.add_argument("--output", default="models/tiny_transformer")
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--block-size", type=int, default=128)
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--layers", type=int, default=2)
    args = parser.parse_args()
    result = train_small_transformer(
        input_dir=args.input, output_dir=args.output, steps=args.steps,
        batch_size=args.batch_size, learning_rate=args.learning_rate, seed=args.seed,
        config_overrides={"block_size": args.block_size, "d_model": args.width,
                          "n_heads": args.heads, "n_layers": args.layers},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
