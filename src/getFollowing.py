"""
   Fetch GitHub following users and update README section.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
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

    print = partial(print, flush=True)

    headers = {
        "Authorization": f"token {token}"
    }

    following = []
    cursor = None
    retryCount = 0
    cwnd = 100

    while True:
        query = f'''
query {{
    user(login: "{handle}") {{
        following(first: {cwnd}{f', after: "{cursor}"' if cursor else ''}) {{
            pageInfo {{
                endCursor
                hasNextPage
            }}
            nodes {{
                login
                name
                databaseId
                followers {{
                    totalCount
                }}
            }}
        }}
    }}
}}
'''
        try:
            response = requests.post("https://api.github.com/graphql", json.dumps({"query": query}), headers=headers)
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
                print("Error, retrying")
                sleep(5)
                continue
            print(query)
            print(response.status_code)
            print(response.headers)
            print(response.text)
            exit(1)

        retryCount = 0
        res = response.json()["data"]["user"]["following"]

        for user in res["nodes"]:
            login = user["login"]
            name = user["name"] or login
            user_id = user["databaseId"]
            follower_count = user["followers"]["totalCount"]
            following.append((follower_count, login, user_id, name))
            print((follower_count, login, user_id, name))

        if not res["pageInfo"]["hasNextPage"]:
            break
        cursor = res["pageInfo"]["endCursor"]

    # Sort by follower count descending and take top 21
    following = sorted(set(following), reverse=True)

    html = "<table>\n"

    for i in range(min(len(following), 21)):
        login = following[i][1]
        user_id = following[i][2]
        name = following[i][3]
        if i % 7 == 0:
            if i != 0:
                html += "  </tr>\n"
            html += "  <tr>\n"
        html += f'''    <td align="center">
      <a href="https://github.com/{login}">
        <img src="https://avatars2.githubusercontent.com/u/{user_id}" width="100px;" alt="{login}"/>
      </a>
      <br />
      <a href="https://github.com/{login}">{name}</a>
    </td>
'''

    html += "  </tr>\n</table>"

    with open(readmePath, "r") as readme:
        content = readme.read()

    newContent = re.sub(
        r"(?<=<!\-\-START_SECTION:following\-\->)[\s\S]*(?=<!\-\-END_SECTION:following\-\->)",
        f"\n{html}\n",
        content
    )

    with open(readmePath, "w") as readme:
        readme.write(newContent)
