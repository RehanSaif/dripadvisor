import requests

url = "https://vinted3.p.rapidapi.com/getSearch"

querystring = {"country":"nl","page":"1","order":"newest_first"}

headers = {
	"X-RapidAPI-Key": "0be6bc26c2mshd31f4439f2941bbp1542cdjsnaf85d783ca3d",
	"X-RapidAPI-Host": "vinted3.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())