"""Collect download statistics.
"""
import re
import datetime
import argparse
import json

import requests
import pandas as pd

PYPI_STATS = "https://pypistats.org/api/packages/{}/recent"
CRAN_STATS = "https://cranlogs.r-pkg.org/downloads/total/last-month/{}"
NPM_STATS = "https://api.npmjs.org/downloads/point/last-month/{}"

REQUEST_TIMEOUT = 10  # Timeout in seconds

if __name__ == '__main__':
    # Initiate the parser
    parser = argparse.ArgumentParser()

    # Add arguments to be parsed
    parser.add_argument(
        "--input",
        help="The file name of the repositories data.",
        default="../collect_variables/results/all_variables.json")
    parser.add_argument("--output",
                        help="The file name to export the data to.",
                        default="results/download_stats.csv")

    # Read arguments from the command line
    args = parser.parse_args()

    with open(args.input) as f:  # pylint: disable=unspecified-encoding

        result = []

        for line in f.readlines():

            repo = json.loads(line)
            name = repo["repository_name"]

            try:
                readme = repo["readme"]
            except KeyError:
                continue

            # python
            matches = re.finditer(r"pip install( -+.*)* (.*?)[\\\s]", str(readme))

            for match in matches:

                if name == match.group(2):
                    print(f"Download stats for Python module '{name}'")
                    try:
                        stats = requests.get(PYPI_STATS.format(name), timeout=REQUEST_TIMEOUT)
                        print(stats.json()["data"]["last_month"])
                        result.append({
                            "repository_name":
                            name,
                            "owner":
                            repo["owner"],
                            "last_month":
                            stats.json()["data"]["last_month"],
                            "date":
                            str(datetime.date.today())
                        })
                    except Exception as err:  # pylint: disable=broad-except
                        pass
                    break
            # R
            matches = re.finditer(r"install\.packages\([\"\'](.*?)[\"\']\)",
                                  str(readme))

            for match in matches:

                if name == match.group(1):
                    print(f"Download stats for R package '{name}'")
                    try:
                        stats = requests.get(CRAN_STATS.format(name), timeout=REQUEST_TIMEOUT)
                        print(stats.json()[0]["downloads"])
                        result.append({
                            "repository_name":
                            name,
                            "owner":
                            repo["owner"],
                            "last_month":
                            stats.json()[0]["downloads"],
                            "date":
                            str(datetime.date.today())
                        })

                    except Exception as err:  # pylint: disable=broad-except
                        raise err
                    break

            # JS
            matches = re.finditer(r"npm (i|install)( -+.*)* (.*)",
                                  str(readme))

            for match in matches:
                if name in match.group(3):
                    print(f"Download stats for npm package '{name}'")
                    try:
                        if "@" in match.group(3):
                            stats = requests.get(NPM_STATS.format(match.group(3)),
                                                 timeout=REQUEST_TIMEOUT)
                        else:
                            stats = requests.get(NPM_STATS.format(name), timeout=REQUEST_TIMEOUT)
                        print(stats.json()["downloads"])
                        result.append({
                            "repository_name":
                            name,
                            "owner":
                            repo["owner"],
                            "last_month":
                            stats.json()["downloads"],
                            "date":
                            str(datetime.date.today())
                        })

                    except Exception as err:  # pylint: disable=broad-except
                        print("Repository does not exist")
                    break

        df_stats = pd.DataFrame(result)
        df_stats.sort_values(["owner", "repository_name"], inplace=True)
        print(df_stats)

        df_stats.to_csv(args.output, index=None)
