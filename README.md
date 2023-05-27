`ynab-split`
===

Split [YNAB](https://www.ynab.com/) transactions between the category they're assigned to and another category en masse.

For example, to split all the transactions with a green flag since January 1, 2023, if your
budget id is `43f9c4b8-b300-4372-ba61-16620af8b3db`, and without knowing the category you want
to split those transactions with, you'd run:

```bash
python3 main.py \
    --since-date 2023-01-01 \ # January 1, 2023
    --flag-color green \ # flag color green
    43f9c4b8-b300-4372-ba61-16620af8b3db \ # budget id
    choose # you don't know the category id yet, you need help choosing it
```

Or, if you'd rather not have to deal with python environment things locally (hey, I get it,
no one really does), you can use the published container image:

```bash
docker run
    -e YNAB_PAT \ # forward the YNAB_PAT environment variable to the container
    jisantuc/ynab-split:latest \ # name of the container
    --since-date 2023-01-01 \ # January 1, 2023
    --flag-color green \ # flag color green
    43f9c4b8-b300-4372-ba61-16620af8b3db \ # budget id
    choose # you don't know the category id yet, you need help choosing it
```

You must have a YNAB personal access token in the `YNAB_PAT` environment variable to use this script.
You can find all the information you need about personal access tokens [here](https://api.youneedabudget.com/#personal-access-tokens).

The best way to get dependencies for the script is with [`nix`](https://nixos.org/). However,
there's also a `requirements.txt` if that's more your style. The only thing
required is `requests`, so non-reproducibility isn't the biggest risk in the universe.

Full usage:

```
usage: main.py [-h] [--since-date SINCE_DATE] [--flag-color FLAG_COLOR] budget target_category

positional arguments:
  budget                Id of the budget you want to split transactions from. Can be found in the url of your default budget page at
                        https://app.youneedabudget.com/BUDGET_ID/budget/CURR_MONTH
  target_category       Id of the category you want to use to split transactions into. Enter 'choose' to choose one interactively (kinda) based on the categories in your budget.

options:
  -h, --help            show this help message and exit
  --since-date SINCE_DATE, -d SINCE_DATE
                        Split transactions occurring after this date
  --flag-color FLAG_COLOR, -f FLAG_COLOR
                        Split transactions flagged with this color
```
