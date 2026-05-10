import requests
try:
    requests.get("https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/adapter_config.json")
    print("Success without verify=False")
except Exception as e:
    print("Failed without verify=False:", type(e).__name__, e)

try:
    requests.get("https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/adapter_config.json", verify=False)
    print("Success with verify=False")
except Exception as e:
    print("Failed with verify=False:", type(e).__name__, e)
