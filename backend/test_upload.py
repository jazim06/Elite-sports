import requests

files = {'file': open('/Users/jazim/Projects/Tennia-iphone-analysis/backend/requirements.txt', 'rb')}
r = requests.post('http://localhost:8000/api/upload', files=files)
print(r.status_code, r.text)
