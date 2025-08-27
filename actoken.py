import requests

url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

payload={
  'scope': 'GIGACHAT_API_PERS'
}
headers = {
  'Content-Type': 'application/x-www-form-urlencoded',
  'Accept': 'application/json',
  'RqUID': 'be4db953-3054-4679-833d-40d9e0b2479c',
  'Authorization': 'Basic N2NiODY3MzUtMTEwMS00N2M3LWEwYjktNWIzYmY0YTc1NmIxOjFjMjEwNWY0LWU4NTktNGFiMC05NTgyLThiNTdkMWE4OGQ2ZA=='
}

response = requests.request("POST", url, headers=headers, data=payload, verify=False)

print(response.text)