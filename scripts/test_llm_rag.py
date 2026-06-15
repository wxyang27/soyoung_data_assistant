import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app


DEFAULT_QUESTION = "L0灌券为什么会拖累毛利？"


def main():
    question = " ".join(sys.argv[1:]).strip() or DEFAULT_QUESTION
    app = create_app()
    with app.test_client() as client:
        response = client.post("/api/chat", json={"question": question})
        data = response.get_json()

    print(f"status={response.status_code}")
    print(f"llm_mode={data.get('llm_mode', False)}")
    if data.get("llm"):
        print(f"llm={data['llm'].get('provider')} / {data['llm'].get('model')}")
    print(f"intent={data.get('intent', {}).get('label')}")
    print(f"citations={len(data.get('citations', []))}")
    print("summary=")
    print(data.get("summary", ""))
    print("sections=")
    print(json.dumps(data.get("sections", []), ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()

