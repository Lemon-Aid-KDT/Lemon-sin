"""Build a non-private synthetic regularization corpus for PaddleOCR rec training.

The generated labels intentionally use only characters already present in the
target PaddleOCR dictionary. This makes the corpus a conservative regularizer
for domain fine-tuning when a real general Korean recognition corpus is not
available on the A100 host.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dict-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--count", default=70000, type=int)
    parser.add_argument("--seed", default=20260610, type=int)
    parser.add_argument(
        "--font",
        action="append",
        default=[],
        help="Font file to sample from. May be provided multiple times.",
    )
    return parser.parse_args()


def load_dictionary_characters(dict_file: Path) -> list[str]:
    """Load usable single characters from the target recognition dictionary.

    Args:
        dict_file: PaddleOCR recognition dictionary file.

    Returns:
        Ordered list of non-empty characters.

    Raises:
        FileNotFoundError: If the dictionary file does not exist.
        ValueError: If too few usable characters are available.
    """

    chars = [line.rstrip("\n\r") for line in dict_file.read_text(encoding="utf-8").splitlines()]
    usable = [char for char in chars if char and char != "\ufeff"]
    if len(usable) < 20:
        raise ValueError("Dictionary has too few usable characters for synthetic corpus generation.")
    return usable


def split_character_pools(chars: list[str]) -> dict[str, list[str]]:
    """Split dictionary characters into sampling pools.

    Args:
        chars: Characters loaded from the PaddleOCR dictionary.

    Returns:
        Character pools keyed by coarse script type.
    """

    pools = {
        "hangul": [c for c in chars if "\uac00" <= c <= "\ud7a3"],
        "digit": [c for c in chars if c.isdigit()],
        "latin": [c for c in chars if ("A" <= c <= "Z") or ("a" <= c <= "z")],
        "symbol": [c for c in chars if not c.isalnum() and c.strip()],
    }
    pools["all"] = chars
    return pools


def choose_text(rng: random.Random, pools: dict[str, list[str]]) -> str:
    """Sample one synthetic OCR target string.

    Args:
        rng: Deterministic random generator.
        pools: Character pools keyed by script type.

    Returns:
        Synthetic label text.
    """

    pattern = rng.choices(
        ["hangul", "mixed_id", "amount_like", "short_code"],
        weights=[0.55, 0.2, 0.15, 0.1],
        k=1,
    )[0]
    hangul = pools["hangul"] or pools["all"]
    digits = pools["digit"] or pools["all"]
    latin = pools["latin"] or pools["all"]
    symbols = [c for c in pools["symbol"] if c in "-_./()%+:"] or ["-"]

    if pattern == "hangul":
        length = rng.randint(2, 18)
        return "".join(rng.choice(hangul) for _ in range(length))
    if pattern == "mixed_id":
        left = "".join(rng.choice(latin) for _ in range(rng.randint(2, 6)))
        right = "".join(rng.choice(digits) for _ in range(rng.randint(2, 6)))
        return left + rng.choice(symbols) + right
    if pattern == "amount_like":
        number = "".join(rng.choice(digits) for _ in range(rng.randint(1, 4)))
        unit = "".join(rng.choice(hangul) for _ in range(rng.randint(1, 3)))
        return number + unit
    length = rng.randint(2, 10)
    return "".join(rng.choice(pools["all"]) for _ in range(length))


def resolve_fonts(font_args: list[str]) -> list[Path]:
    """Resolve available font paths.

    Args:
        font_args: Explicit font paths supplied by the operator.

    Returns:
        Existing font file paths.

    Raises:
        FileNotFoundError: If no usable font file is found.
    """

    candidates = [Path(value) for value in font_args]
    candidates.extend(
        [
            Path("C:/Windows/Fonts/malgun.ttf"),
            Path("C:/Windows/Fonts/malgunbd.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]
    )
    fonts = [path for path in candidates if path.is_file()]
    if not fonts:
        raise FileNotFoundError("No usable font file found for synthetic OCR image generation.")
    return fonts


def render_text_image(text: str, font_path: Path, rng: random.Random) -> Image.Image:
    """Render one synthetic text image.

    Args:
        text: Label text to render.
        font_path: Font path used for rendering.
        rng: Deterministic random generator.

    Returns:
        Rendered RGB image.
    """

    font_size = rng.randint(24, 42)
    font = ImageFont.truetype(str(font_path), font_size)
    scratch = Image.new("RGB", (16, 16), "white")
    draw = ImageDraw.Draw(scratch)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = max(48, right - left + rng.randint(18, 36))
    height = max(40, bottom - top + rng.randint(14, 28))
    background = rng.randint(238, 255)
    image = Image.new("RGB", (width, height), (background, background, background))
    draw = ImageDraw.Draw(image)
    ink = rng.randint(0, 45)
    x = rng.randint(6, max(6, width - (right - left) - 6))
    y = rng.randint(4, max(4, height - (bottom - top) - 4))
    draw.text((x, y), text, fill=(ink, ink, ink), font=font)
    if rng.random() < 0.25:
        image = image.rotate(rng.uniform(-1.5, 1.5), expand=True, fillcolor=(background, background, background))
    return image


def build_corpus(dict_file: Path, output_dir: Path, count: int, seed: int, fonts: list[Path]) -> None:
    """Generate synthetic OCR image files and a PaddleOCR label file.

    Args:
        dict_file: PaddleOCR dictionary file.
        output_dir: Destination dataset root.
        count: Number of synthetic samples.
        seed: Deterministic random seed.
        fonts: Font files used for rendering.
    """

    rng = random.Random(seed)
    chars = load_dictionary_characters(dict_file)
    pools = split_character_pools(chars)
    image_dir = output_dir / "rec" / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    label_path = output_dir / "rec" / "rec_gt_train.txt"

    with label_path.open("w", encoding="utf-8", newline="\n") as label_file:
        for index in range(count):
            text = choose_text(rng, pools)
            font_path = rng.choice(fonts)
            image = render_text_image(text, font_path, rng)
            relative_image_path = f"rec/images/synthetic_general_{index:06d}.jpg"
            image.save(output_dir / relative_image_path, quality=92)
            label_file.write(f"{relative_image_path}\t{text}\n")


def main() -> None:
    """Run the synthetic corpus generator."""

    args = parse_args()
    fonts = resolve_fonts(args.font)
    build_corpus(
        dict_file=args.dict_file,
        output_dir=args.output_dir,
        count=args.count,
        seed=args.seed,
        fonts=fonts,
    )
    print(f"generated_count={args.count}")
    print(f"output_dir={args.output_dir}")


if __name__ == "__main__":
    main()
