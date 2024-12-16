import json

def corrigir_json(json_str):
    try:
        json_str = json_str.replace("'", '"')
        json_str = json_str.replace("False", "false").replace("True", "true").replace("None", "null")
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Erro ao corrigir JSON: {e}")
        print("String JSON problemática:", json_str)
        return []