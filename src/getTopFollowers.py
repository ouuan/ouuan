"""
   Copyright 2020-2025 Yufan You <https://github.com/ouuan>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import requests
import json
import sys
import re
from time import sleep
from functools import partial

if __name__ == "__main__":
    assert(len(sys.argv) == 4)
    handle = sys.argv[1]
    token = sys.argv[2]
    readmePath = sys.argv[3]

    print = partial(print, flush = True)

    headers = {
        "Authorization": f"token {token}"
    }

    followers = []
    cursor = None
    retryCount = 0
    cwnd = 1
    ssthresh = 20

    while True:
        query = f'''
query {{
    user(login: "{handle}") {{
        followers(first: {cwnd}{f', after: "{cursor}"' if cursor else ''}) {{
            pageInfo {{
                endCursor
                hasNextPage
            }}
            nodes {{
                login
                name
                databaseId
                following {{
                    totalCount
                }}
                followers {{
                    totalCount
                }}
                repositories(
                    first: 20,
                    orderBy: {{
                        field: STARGAZERS,
                        direction: DESC,
                    }},
                ) {{
                    nodes {{
                        stargazerCount
                    }}
                }}
                repositoriesContributedTo(
                    first: 50,
                    contributionTypes: [COMMIT],
                    orderBy: {{
                        field: STARGAZERS,
                        direction: DESC,
                    }},
                ) {{
                    nodes {{
                        stargazerCount
                    }}
                }}
                contributionsCollection {{
                    contributionCalendar {{
                        totalContributions
                    }}
                }}
            }}
        }}
    }}
}}
'''
        try:
            response = requests.post(f"https://api.github.com/graphql", json.dumps({ "query": query }), headers = headers)
        except Exception as e:
            if retryCount >= 3:
                raise e
            print("Network error, retrying")
            sleep(5)
            retryCount += 1
            continue
        if not response.ok or "data" not in response.json():
            if retryCount < 3:
                retryCount += 1
                if "Retry-After" in response.headers:
                    wait = int(response.headers["Retry-After"])
                    print(f"Rate limit exceeded, retry after {wait} seconds")
                    sleep(wait)
                    continue
                ssthresh = cwnd // 2
                cwnd = 1
                print(f"Error, entering slow start with {ssthresh = }")
                sleep(5)
                continue
            print(query)
            print(response.status_code)
            print(response.headers)
            print(response.text)
            exit(1)
        retryCount = 0
        if cwnd < ssthresh:
            cwnd = min(ssthresh, cwnd * 2)
        else:
            cwnd += 1
        res = response.json()["data"]["user"]["followers"]
        try:
            for follower in res["nodes"]:
                following = follower["following"]["totalCount"]
                login = follower["login"]
                name = follower["name"]
                id = follower["databaseId"]
                followerNumber = follower["followers"]["totalCount"]
                active = follower["contributionsCollection"]["contributionCalendar"]["totalContributions"] > 5
                if not active:
                    print(f"Skipped{'*' if followerNumber > 500 else ''} (inactive): https://github.com/{login} with {followerNumber} followers and {following} following")
                    continue
                quota = followerNumber
                for i, starCount in enumerate([repo["stargazerCount"] for repo in follower["repositories"]["nodes"]]):
                    if starCount <= i:
                        break
                    quota += starCount * (i + 1)
                for i, starCount in enumerate([repo["stargazerCount"] for repo in follower["repositoriesContributedTo"]["nodes"]]):
                    if starCount <= i:
                        break
                    quota += i * 5
                if following > quota:
                    print(f"Skipped{'*' if followerNumber > 500 else ''} (quota): https://github.com/{login} with {followerNumber} followers and {following} following")
                    continue
                followers.append((followerNumber, login, id, name if name else login))
                print(followers[-1])
        except TypeError as e:
            retryCount += 1
            if retryCount >= 3:
                print(res)
                raise e
            print(f'Error: {e}')
            ssthresh = cwnd // 2
            cwnd = 1
            sleep(5)
            continue
        sys.stdout.flush()
        if not res["pageInfo"]["hasNextPage"]:
            break
        cursor = res["pageInfo"]["endCursor"]

    followers = sorted(set(followers), reverse=True)

    html = "<table>\n"

    for i in range(min(len(followers), 21)):
        login = followers[i][1]
        id = followers[i][2]
        name = followers[i][3]
        if i % 7 == 0:
            if i != 0:
                html += "  </tr>\n"
            html += "  <tr>\n"
        html += f'''    <td align="center">
      <a href="https://github.com/{login}">
        <img src="https://avatars2.githubusercontent.com/u/{id}" width="100px;" alt="{login}"/>
      </a>
      <br />
      <a href="https://github.com/{login}">{name}</a>
    </td>
'''

    html += "  </tr>\n</table>"

    with open(readmePath, "r") as readme:
        content = readme.read()

    newContent = re.sub(r"(?<=<!\-\-START_SECTION:top\-followers\-\->)[\s\S]*(?=<!\-\-END_SECTION:top\-followers\-\->)", f"\n{html}\n", content)

    with open(readmePath, "w") as readme:
        readme.write(newContent)
