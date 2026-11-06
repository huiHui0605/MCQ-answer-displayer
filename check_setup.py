"""Check local files and the installed Ollama model; no inference or downloads."""
import sys
from core import check_model, load_pages


def main():
    try:
        pages, _ = load_pages()
        print(f'PDF text pages: {len(pages)}')
        print(f'Local model: {check_model()}')
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print('Local prerequisites found. Run app.py to start. This is not an accuracy test.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
