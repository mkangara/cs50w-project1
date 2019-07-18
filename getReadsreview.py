import requests
res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":"8qIcqhBcOM7c6YqBYm3g","isbns":"9781632168146"})
print(res.json())
