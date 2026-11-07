"""Check local files and the installed Ollama model; no inference or downloads."""
import sys
from importlib.metadata import version
from core import check_model, load_pages
from settings import load_settings, preferred_model


def main():
    try:
        print(f'Screen capture: mss {version("mss")}')
        print(f'Local OCR: RapidOCR {version("rapidocr-onnxruntime")}')
        pages, _ = load_pages()
        print(f'PDF reference pages: {len(pages)} (notes are optional)')
        if not pages:
            print('No readable notes: the local model can answer from its own knowledge.')
        print(f'Local model: {check_model(preferred_model(load_settings()))}')
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print('Local prerequisites found. Run app.py to start. This is not an accuracy test.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
