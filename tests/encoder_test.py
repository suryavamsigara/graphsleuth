import os
from dotenv import load_dotenv
from engine.embeddings.encoder import EmbeddingEncoder, RemoteEncoder

def main():
    load_dotenv() 
    
    encoder: EmbeddingEncoder = RemoteEncoder("baai/bge-small-en-v1.5")

    text_to_embed = [
        "Testing cloudflare encoder.",
        "This is a random sentence."
    ]
    
    print("Sending request to Cloudflare...")
    result = encoder.encode(text_to_embed)
    
    print(f"Number of vectors returned: {len(result)}")
    if result:
        print(f"Vector dimensions: {len(result[0])}")

if __name__ == "__main__":
    main()
