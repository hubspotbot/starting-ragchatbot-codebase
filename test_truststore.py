import truststore
truststore.inject_into_ssl()
import requests
try:
    requests.get("https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/adapter_config.json")
    print("Success with truststore")
except Exception as e:
    print("Failed with truststore:", type(e).__name__, e)
