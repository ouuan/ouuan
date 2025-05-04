"""
   Copyright 2020-2024 Yufan You <https://github.com/ouuan>

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
# Developed by phoenix marie.
import requests
import json
import sys
import re
from time import sleep
from functools import partial
from typing import List, Tuple, Optional
import os
import logging

# --- Constants ---
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
MAX_RETRIES = 5  # Increased max retries
INITIAL_CWND = 1
SLOW_START_THRESHOLD = 20
MIN_ACTIVE_CONTRIBUTIONS = 5
DEFAULT_TOP_FOLLOWERS = 21
AVATAR_WIDTH = "100px"
CACHE_FILE = "github_followers_cache.json"
LOG_FILE = "github_followers.log"

# --- Logging Setup ---
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
def get_github_headers(token: str) -> dict:
    """Constructs the authorization header for GitHub API requests."""
    return {"Authorization": f"token {token}"}

def load_cached_followers() -> Optional[List[Tuple[int, str, int, str]]]:
    """Loads cached follower data from a JSON file if it exists."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logging.warning("Error loading cached followers.")
    return None

def save_cached_followers(followers: List[Tuple[int, str, int, str]]) -> None:
    """Saves the follower data to a JSON file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(followers, f)
        logging.info(f"Follower data saved to cache: {CACHE_FILE}")
    except IOError:
        logging.error(f"Error saving follower data to cache: {CACHE_FILE}")

def fetch_followers_data(handle: str, token: str, cursor: Optional[str] = None, cwnd: int = 1) -> Optional[dict]:
    """
    Fetches follower data from GitHub GraphQL API with rate limiting and error handling.
    """
    headers = get_github_headers(token)
    query = f"""
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
    """
    try:
        response = requests.post(GITHUB_GRAPHQL_URL, json.dumps({"query": query}), headers=headers)
        response.raise_for_status()
        return response.json().get("data", {}).get("user", {}).get("followers")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        return None

def calculate_follower_quota(follower: dict) -> int:
    """Calculates a quota based on follower stats to filter out less engaged users."""
    quota = follower["followers"]["totalCount"]
    for i, repo in enumerate(follower["repositories"]["nodes"]):
        star_count = repo.get("stargazerCount", 0)
        if star_count <= i:
            break
        quota += star_count * (i + 1)
    for i, repo in enumerate(follower["repositoriesContributedTo"]["nodes"]):
        star_count = repo.get("stargazerCount", 0)
        if star_count <= i:
            break
        quota += i * 5
    return quota

def is_active_follower(follower: dict) -> bool:
    """Checks if a follower has been active recently based on contribution count."""
    total_contributions = follower["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return total_contributions > MIN_ACTIVE_CONTRIBUTIONS

def process_follower(follower: dict, excluded_users: Optional[List[str]] = None) -> Optional[Tuple[int, str, int, str]]:
    """Processes a single follower, checks activity and quota, and returns relevant data."""
    login = follower["login"]
    if excluded_users and login in excluded_users:
        logging.info(f"Skipped (excluded): https://github.com/{login}")
        return None

    following_count = follower["following"]["totalCount"]
    name = follower.get("name") or login
    follower_number = follower["followers"]["totalCount"]

    if not is_active_follower(follower):
        logging.info(f"Skipped{'*' if follower_number > 500 else ''} (inactive): https://github.com/{login} with {follower_number} followers and {following_count} following")
        return None

    quota = calculate_follower_quota(follower)
    if following_count > quota:
        logging.info(f"Skipped{'*' if follower_number > 500 else ''} (quota): https://github.com/{login} with {follower_number} followers and {following_count} following")
        return None

    database_id = follower["databaseId"]
    return (follower_number, login, database_id, name)

def generate_top_followers_html(followers: List[Tuple[int, str, int, str]], display_follower_count: bool = False) -> str:
    """Generates the HTML table for the top followers."""
    html = "<table>\n  <tr>\n"
    top_count = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else DEFAULT_TOP_FOLLOWERS
    for i, (follower_number, login, database_id, name) in enumerate(followers):
        if i >= top_count:
            break
        if i > 0 and i % 7 == 0:
            html += "  </tr>\n  <tr>\n"
        follower_count_span = f"<br /><span style='font-size: small;'>({follower_number} followers)</span>" if display_follower_count else ""
        html += f'''    <td align="center">
      <a href="https://github.com/{login}">
        <img src="https://avatars2.githubusercontent.com/u/{database_id}" width="{AVATAR_WIDTH}" alt="{login}"/>
      </a>
      <br />
      <a href="https://github.com/{login}">{name}</a>{follower_count_span}
    </td>
'''
    html += "  </tr>\n</table>"
    return html

def update_readme(readme_path: str, html_content: str) -> None:
    """Updates the top followers section in the README file."""
    try:
        with open(readme_path, "r") as readme:
            content = readme.read()

        new_content = re.sub(
            r"(?<=<!\-\-START_SECTION:top\-followers\-\->)[\s\S]*(?=<!\-\-END_SECTION:top\-followers\-\->)",
            f"\n{html_content}\n",
            content,
        )

        with open(readme_path, "w") as readme:
            readme.write(new_content)
        logging.info(f"README updated successfully at {readme_path}")
        print(f"README updated successfully at {readme_path}")
    except FileNotFoundError:
        logging.error(f"Error: README file not found at {readme_path}")
        print(f"Error: README file not found at {readme_path}")
    except Exception as e:
        logging.error(f"Error updating README: {e}")
        print(f"Error updating README: {e}")

def parse_excluded_users(args: List[str]) -> Optional[List[str]]:
    """Parses excluded users from command-line arguments (if provided)."""
    for arg in args:
        if arg.startswith("--exclude="):
            return [user.strip() for user in arg[len("--exclude="):].split(',')]
    return None

def should_display_follower_count(args: List[str]) -> bool:
    """Checks if the display follower count flag is present in the arguments."""
    return "--show-followers" in args

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python script.py <github_handle> <github_token> <readme_path> [optional: <top_count>] [optional: --exclude=user1,user2,...] [optional: --show-followers]")
        sys.exit(1)

    handle = sys.argv[1]
    token = sys.argv[2]
    readme_path = sys.argv[3]
    top_count = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else DEFAULT_TOP_FOLLOWERS
    excluded_users = parse_excluded_users(sys.argv)
    display_follower_count = should_display_follower_count(sys.argv)

    print = partial(print, flush=True)
    logging.info(f"Starting script for handle: {handle}, README: {readme_path}, Top Count: {top_count}, Excluded: {excluded_users}, Show Followers: {display_follower_count}")

    # --- Attempt to load cached data ---
    cached_followers = load_cached_followers()
    if cached_followers:
        print("Loaded follower data from cache.")
        followers_data = cached_followers
    else:
        followers_data: List[Tuple[int, str, int, str]] = []
        cursor: Optional[str] = None
        retry_count = 0
        cwnd = INITIAL_CWND
        ssthresh = SLOW_START_THRESHOLD

        print(f"Fetching followers for {handle}...")

        while True:
            followers_response = fetch_followers_data(handle, token, cursor, cwnd)

            if followers_response is None:
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    print(f"Retrying in 5 seconds... (Attempt {retry_count}/{MAX_RETRIES})")
                    sleep(5)
                    continue
                else:
                    logging.error("Max retries reached. Exiting follower fetching.")
                    print("Max retries reached. Could not fetch followers.")
                    sys.exit(1)

            nodes = followers_response.get("nodes", [])
            page_info = followers_response.get("pageInfo", {})

            for follower_node in nodes:
                processed_follower = process_follower(follower_node, excluded_users)
                if processed_follower:
                    followers_data.append(processed_follower)
                    print(processed_follower)
                    sys.stdout.flush()

            if not page_info.get("hasNextPage"):
                break

            cursor = page_info.get("endCursor")

            if cwnd < ssthresh:
                cwnd = min(ssthresh, cwnd * 2)
            else:
                cwnd += 1

            sleep(0.1)

        # --- Save fetched data to cache ---
        save_cached_followers(followers_data)

    followers_data.sort(reverse=True)

    html_output = generate_top_followers_html(followers_data, display_follower_count)
    update_readme(readme_path, html_output)

    logging.info("Script finished successfully.")
    print("Script finished.")
 
