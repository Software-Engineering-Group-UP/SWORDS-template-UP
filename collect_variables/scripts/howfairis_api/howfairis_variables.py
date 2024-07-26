"""
Retrieves howfairis variables for an input file of retrieved Github repositories.
"""
import os
import time
from datetime import datetime
import argparse

from howfairis import Repo, Checker
from ghapi.all import GhApi
import pandas as pd
from dotenv import load_dotenv


def get_howfairis_compliance(url_repo):
    """Retrieve howfairis compliance - see https://github.com/fair-software/howfairis

    Args:
        url_repo (string): repository URL
    Returns:
        repository (bool): Whether repository is publicly accessible with version control
        license (bool): Whether repository has a license
        registry (bool): Whether code is in a registry
        citation (bool): Whether software is citable
        checklist (bool): Whether a software quality checklist is used
    """
    repo = Repo(url_repo)
    checker = Checker(repo, is_quiet=True)
    compliance = checker.check_five_recommendations()

    return (compliance.repository, compliance.license, compliance.registry,
            compliance.citation, compliance.checklist)


def read_input_file(file_path):
    """reads in the input file through Pandas

    Args:
        file_path (string): path to the file

    Returns:
        DataFrame
    """
    if "xlsx" in file_path:
        file = pd.read_excel(file_path, engine='openpyxl')
    else:
        file = pd.read_csv(file_path, delimiter= ';', encoding='latin1')
    return file


def is_supported_repo(url):
    """Check if the repository URL is from a supported domain.

    Args:
        url (str): Repository URL

    Returns:
        bool: True if the repository is supported, False otherwise
    """
    supported_domains = ["github.com", "gitlab.com"]
    return any(domain in url for domain in supported_domains)


def parse_repo(repo_url):
    """Parses a repository for howfairis variables

    Args:
        repo_url (str): Repository that should be parsed

    Returns:
        list: A list with the repository URL and the variables, or None if skipped
    """
    # pylint: disable=redefined-outer-name
    if not is_supported_repo(repo_url):
        print(f"Skipping unsupported repository: {repo_url}")
        return None

    request_successful = False
    while not request_successful:
        try:
            entry = [repo_url]
            compliance = get_howfairis_compliance(repo_url)
            if compliance is not None:
                entry.extend(compliance)
                print(entry)
                time.sleep(1)
                request_successful = True
                return entry

        except Exception as error:  # pylint: disable=broad-except
            print(f"Error occurred for {repo_url} (most likely timeout issue due"
                  f" to API limitation). Sleep for a while. Error message: {error}")
            if "Something went wrong asking the repo for its default branch" in str(error):
                print("Skipping repository...")
                request_successful = True  # skip this repo
                return None
            if "TimeoutError" in str(error):
                time.sleep(5)
            else:
                sleep_time = api.rate_limit.get()["rate"]["reset"] - int(time.time())
                time.sleep(sleep_time + 2)

    return None


# if unauthorized API is used, rate limit is lower,
# leading to a ban and waiting time needs to be increased
# see: https://github.com/fair-software/howfairis/#rate-limit
load_dotenv()
token = os.getenv('GITHUB_TOKEN')
user = os.getenv('GITHUB_USER')

api = GhApi(token=token)
if token is not None and user is not None:
    os.environ['APIKEY_GITHUB'] = user + ":" + token

if __name__ == '__main__':
    # Initiate the parser
    parser = argparse.ArgumentParser()

    # Add arguments to be parsed
    parser.add_argument(
        "--input",
        "-i",
        help="The file name of the retrieved repositories.",
        default="../collect_repositories/results/repositories_filtered.csv")
    parser.add_argument("--output",
                        "-o",
                        help="The file name of the filtered repositories.",
                        default="results/howfairis.csv")

    # Read arguments from the command line
    args = parser.parse_args()
    print(f"Retrieving howfairis variables for the following file: {args.input}")


    df_repos = read_input_file(args.input)
    howfairis_variables = []

    for counter, repo_url in enumerate(df_repos["html_url"]):
        result = parse_repo(repo_url)
        if result is not None: # If repo is deleted it is None
            howfairis_variables.append(result)
        if counter % 10 == 0:
            print(f"Parsed {counter} out of {len(df_repos.index)} repos.")

    df_howfairis = pd.DataFrame(howfairis_variables,
                                columns=[
                                    "html_url", "howfairis_repository",
                                    "howfairis_license", "howfairis_registry",
                                    "howfairis_citation", "howfairis_checklist"
                                ])

    current_date = datetime.today().strftime('%Y-%m-%d')
    df_howfairis["date"] = current_date
    df_howfairis.to_csv(args.output, index=False)

    print(
        f"Successfully retrieved howfairis variables for {len(df_howfairis.index)}"
        f" out of {len(df_repos.index)} repositories. Saved result to {args.output}."
    )
