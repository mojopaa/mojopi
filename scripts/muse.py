import json
from pprint import pprint

import requests
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


if __name__ == "__main__":
    download()
