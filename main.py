from argparse import ArgumentParser
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, timedelta
import os
from typing import List, Optional
from uuid import UUID


from requests import Session


@dataclass
class Arguments:
    budget_id: str
    target_category_id: str
    flag_color: str
    since_date: date


@dataclass
class Category:
    __slots__ = ["name", "id", "hidden", "deleted"]
    name: str
    id: str
    hidden: bool
    deleted: bool


@dataclass
class CategoryGroup:
    __slots__ = ["name", "hidden", "deleted", "categories"]
    name: str
    hidden: bool
    deleted: bool
    categories: List[Category]


@dataclass
class Subtransaction:
    __slots__ = ["amount", "payee_id", "payee_name", "category_id", "memo"]
    amount: float
    payee_id: str
    payee_name: str
    category_id: str
    memo: str


@dataclass
class Transaction:
    __slots__ = [
        "id",
        "date",
        "flag_color",
        "amount",
        "payee_id",
        "payee_name",
        "category_id",
        "subtransactions",
        "transfer_account_id",
    ]
    id: str
    date: date
    flag_color: Optional[str]
    amount: float
    payee_id: str
    payee_name: str
    category_id: str
    subtransactions: List[Subtransaction]
    transfer_account_id: Optional[UUID]


def category_group_from_json(api_json: dict) -> CategoryGroup:
    all_but_categories = {
        s: api_json[s] for s in CategoryGroup.__slots__ if s != "categories"
    }
    categories = [
        Category(**{s: js[s] for s in Category.__slots__})
        for js in api_json["categories"]
    ]
    return CategoryGroup(categories=categories, **all_but_categories)


def transaction_from_json(api_json: dict) -> Transaction:
    all_but_subtransactions = {
        s: api_json[s] for s in Transaction.__slots__ if s != "subtransactions"
    }
    subtransactions = [
        Subtransaction(**{s: subtx[s] for s in Subtransaction.__slots__})
        for subtx in api_json["subtransactions"]
    ]
    return Transaction(subtransactions=subtransactions, **all_but_subtransactions)


def get_session():
    pat = os.getenv("YNAB_PAT")
    if pat is None:
        raise Exception("Token required, please set YNAB_PAT")
    session = Session()
    session.headers.update({"Authorization": f"Bearer {pat}"})
    return session


def split_transaction(tx: Transaction, target_category: str) -> List[Subtransaction]:
    return [
        Subtransaction(
            tx.amount // 2,
            tx.payee_id,
            tx.payee_name,
            tx.category_id,
            "split by ynab_split",
        ),
        Subtransaction(
            tx.amount // 2,
            tx.payee_id,
            tx.payee_name,
            target_category,
            "split by ynab_split",
        ),
    ]


def remove_flag(tx: Transaction) -> Transaction:
    copied = deepcopy(tx)
    copied.flag_color = None
    return copied


def with_subtransactions(subtx: List[Subtransaction], tx: Transaction) -> Transaction:
    copied = deepcopy(tx)
    copied.subtransactions.extend(subtx)
    return copied


def list_transactions(
    budget_id: str, since_date: Optional[date], session: Session
) -> List[Transaction]:
    resp = session.get(
        f"https://api.youneedabudget.com/v1/budgets/{budget_id}/transactions",
        params={
            "since_date": since_date.isoformat() if since_date is not None else None
        },
    )
    resp.raise_for_status()
    return [transaction_from_json(tx) for tx in resp.json()["data"]["transactions"]]


def update_transactions(
    transactions: List[Transaction], budget_id: str, session: Session
) -> None:
    if not transactions:
        raise Exception("No transactions to update. Did you flag some?")
    resp = session.patch(
        f"https://api.youneedabudget.com/v1/budgets/{budget_id}/transactions",
        json={"transactions": [asdict(x) for x in transactions]},
    )
    resp.raise_for_status()


def pretty_print_categories(categories: List[Category]) -> str:
    return "\n".join(
        f"{category.id}: {category.name}"
        for category in categories
        if not (category.hidden or category.deleted)
    )


def pretty_print_category_group_prompt(category_groups: List[CategoryGroup]) -> str:
    return "\n".join(
        f"""{category_group.name}\n{pretty_print_categories(category_group.categories)}\n"""
        for category_group in category_groups
        if not (category_group.hidden or category_group.deleted)
    )


def list_category_groups(budget_id: str, session: Session) -> List[CategoryGroup]:
    categories_resp = session.get(
        f"https://api.youneedabudget.com/v1/budgets/{budget_id}/categories",
    )
    categories_resp.raise_for_status()
    return [
        category_group_from_json(data)
        for data in categories_resp.json()["data"]["category_groups"]
    ]


def choose_category(
    budget_id: str, session: Session, category_groups: Optional[List[CategoryGroup]]
) -> str:
    if category_groups is None:
        groups = list_category_groups(budget_id, session)
    else:
        groups = category_groups
    category_name_map = {
        category.name.lower(): category.id
        for category_group in groups
        for category in category_group.categories
    }
    choices = pretty_print_category_group_prompt(groups)
    name = input(f"{choices}\n\nEnter a category name (case insensitive): ")
    looked_up_id = category_name_map.get(name.lower())
    if looked_up_id is not None:
        print(
            f"Id for category '{name}' is '{looked_up_id}'. You can use this directly in the future"
        )
        return looked_up_id
    else:
        return choose_category(budget_id, session, groups)


def parse_arguments() -> Arguments:
    parser = ArgumentParser()
    budget_help = (
        "Id of the budget you want to split transactions from. Can be found in "
        "the url of your default budget page at "
        "https://app.youneedabudget.com/BUDGET_ID/budget/CURR_MONTH"
    )
    parser.add_argument("budget", type=str, help=budget_help)
    category_help = (
        "Id of the category you want to use to split transactions into. "
        "Enter 'choose' to choose one interactively (kinda) based on the "
        "categories in your budget."
    )
    parser.add_argument("target_category", type=str, help=category_help)
    parser.add_argument(
        "--since-date",
        "-d",
        type=date.fromisoformat,
        help="Split transactions occurring after this date",
        default=date.today() - timedelta(days=30),
    )
    parser.add_argument(
        "--flag-color",
        "-f",
        type=str,
        help="Split transactions flagged with this color",
        default="green",
    )
    args = parser.parse_args()
    return Arguments(
        args.budget, args.target_category, args.flag_color, args.since_date
    )


def prompt_for_category(budget_id: str, category_id: str, session: Session) -> str:
    match category_id.lower():
        case "choose":
            return choose_category(budget_id, session, None)
        case s:
            return s


def main():
    session = get_session()
    arguments = parse_arguments()
    category_id = prompt_for_category(
        arguments.budget_id, arguments.target_category_id, session
    )
    transactions = list_transactions(arguments.budget_id, arguments.since_date, session)
    split_transactions = [
        remove_flag(with_subtransactions(split_transaction(tx, category_id), tx))
        for tx in transactions
        if tx.flag_color == arguments.flag_color
    ]
    print(
        f"Total amount to be split: {sum([transaction.amount for transaction in split_transactions]) / 1000.0}"
    )
    update_transactions(split_transactions, arguments.budget_id, session)


if __name__ == "__main__":
    main()
