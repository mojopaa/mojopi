import json
from pathlib import Path
from pprint import pprint

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from resolvelib.resolvers import Resolver

# TODO: def parse_requirement(line: str, editable: bool = False) -> Requirement:
# src/pdm/models/requirements.py L480


def download():
    # a rough demo of downloading the mojo package.

    url = "http://127.0.0.1:5000/files/ring/test"
    r = requests.get(url)
    if r.status_code == 200:
        # print(f"{r.json() = }")  # no good.
        # print(f"{r.content = }")  # Oops.
        # print(f"{r.headers['Content-Disposition'].split('=')[-1] = }")  # Hmm.
        # pprint(r.headers["x-ring-info"])  # OUYA
        # print(f"{json.loads(r.headers['x-ring-info'])['file_name'] = }")
        file_name = r.headers["Content-Disposition"].split("=")[-1]
        with open(file_name, "wb") as f:
            f.write(r.content)
        print("file downloaded")
    else:
        print(f"{r.status_code = }")
        print(f"{r.text =}")


def upload():
    info = {"name": "test"}
    info["version"] = "3"
    info["author"] = "Eric"
    info["author_email"] = "eric@simutech.com.tw"
    info["requires_mojo"] = "0.1"
    info["file_name"] = "test-3.ring"
    info["description"] = "**Hellog mojopi**"
    info["description_content_type"] = "text/markdown"
    info["home_page"] = "http://github.com/drunkwcodes"
    info["keywords"] = "test, mojopi"
    info["license"] = "MIT"
    info["maintainer"] = "drunkwcodes"
    info["maintainer_email"] = "drunkwcodes@gmail.com"
    info["summary"] = "test summary"

    url = "http://127.0.0.1:5000/api/ring/test/3"

    file_path = Path(__file__).with_name("test-3.ring")

    # 使用 MultipartEncoder 來建構 multipart/form-data 的內容
    multipart_data = MultipartEncoder(
        fields={
            "file": (
                info["file_name"],
                open(file_path, "rb"),
                "application/octet-stream",
            ),
            "info": ("info.json", json.dumps(info), "application/json"),
        }
    )

    headers = {
        "x-ring-info": json.dumps(info),
        "Content-Type": multipart_data.content_type,
    }

    response = requests.post(url, data=multipart_data, headers=headers)

    # 檢查回應狀態碼
    if response.status_code == 200:
        print("File upload succeeded!")
        print(response.json())  # 如果 API 回傳 JSON 資料，可以用 .json() 解析回傳內容
    else:
        print(f"File upload failed with status code: {response.status_code}")
        print(response.json())  # 顯示回應內容 (通常會包含錯誤訊息)


if __name__ == "__main__":
    download()
    upload()
