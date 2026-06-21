import os
import sys

# Setup Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.services.asset_resolver import AssetResolver

def main():
    resolver = AssetResolver()
    results = resolver.resolve_many(["HDFC Flexi cap", "Parag Flexi Cap"])
    
    for res in results:
        print(f"Input: {res.input}")
        print(f"Resolved Name: {res.resolved_name}")
        print(f"Confidence: {res.confidence}")
        print("Candidates:")
        for cand in res.candidates[:3]:
            print(f"  - {cand.resolved_name} (conf: {cand.confidence})")
        print("-" * 40)

if __name__ == "__main__":
    main()
