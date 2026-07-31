import os
import urllib.request

logos_dir = r"C:\Users\naman\OneDrive\Desktop\FundersAI\frontend\public\logos"
os.makedirs(logos_dir, exist_ok=True)

amc_domains = {
    "hdfc": "hdfcbank.com",
    "icici": "icicibank.com",
    "axis": "axisbank.com",
    "sbi": "sbi.co.in",
    "ppfas": "amc.ppfas.com",
    "uti": "utimf.com",
    "nippon": "nipponlife.com",
    "kotak": "kotak.com",
    "mirae": "miraeasset.com",
    "dsp": "dspim.com",
    "motilal": "motilaloswal.com",
    "aditya": "adityabirlacapital.com"
}

headers = {'User-Agent': 'Mozilla/5.0'}

for key, domain in amc_domains.items():
    url = f"https://logo.clearbit.com/{domain}"
    file_path = os.path.join(logos_dir, f"{key}.png")
    print(f"Fetching {key} from {url}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            with open(file_path, 'wb') as f:
                f.write(response.read())
        print(f"Saved {key}.png")
    except Exception as e:
        print(f"Failed to fetch {key}: {e}")
