import requests
import bs4
import pandas as pd
import json
import os
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Test script for containerization")
    parser.add_argument("--output", "-o", default="test-output.txt")
    args = parser.parse_args()
    
    fake_data = {
        "URL": ["https://example.com/page1", "https://example.com/page2"],
        "Title": ["Example Page 1", "Example Page 2"],
        "Content": ["Sample content from page 1", "Sample content from page 2"]
    }
    df = pd.DataFrame(fake_data)

    
    with open(args.output, "w") as f:
        f.write("\nSimulated data:\n")
        f.write(json.dumps(fake_data, indent=2))

    print(f"\nContainerization successful. Output written to {args.output}")

if __name__ == "__main__":
    main()