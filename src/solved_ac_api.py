import requests
import asyncio

BASE_URL = "https://solved.ac/api/v3"

async def _fetch_api(url: str, params: dict|None, headers: dict|None):
	loop = asyncio.get_running_loop()

	def request_sync():
		response = requests.get(url, headers=headers, params=params)
		response.raise_for_status()
		return response.json()

	json_response = await loop.run_in_executor(None, request_sync)
	return json_response

# 백준 문제 번호로 문제 가져오기
async def get_problem_from_num(problemId: int):
	url = f"{BASE_URL}/problem/show"
	querystring = {"problemId": str(problemId)}
	headers = {
		"x-solvedac-language": "ko",
		"Accept": "application/json"
	}
	return await _fetch_api(url, params=querystring, headers=headers)

# 백준 문제 자동 완성으로 가져오기
async def get_problem_auto_complete(string: str):
	url = f"{BASE_URL}/search/suggestion"
	querystring = {"query": string}
	headers = {
		"x-solvedac-language": "ko",
		"Accept": "application/json"
	}
	return await _fetch_api(url, params=querystring, headers=headers)

# 사용자 검색하기
async def get_user_info(id: str):
	url = f"{BASE_URL}/search/user"
	querystring = {"query": id}
	headers = {
		"x-solvedac-language": "ko",
		"Accept": "application/json"
	}
	return await _fetch_api(url, params=querystring, headers=headers)

# 상위 100 문제 가져오기
async def get_user_top100(handle: str):
	url = f"{BASE_URL}/user/top_100"
	querystring = {"handle": handle}
	headers = {
    "x-solvedac-language": "ko",
    "Accept": "application/json"
  }
	return await _fetch_api(url, params=querystring, headers=headers)