"""
All your implementation code for the bank system simulation goes here.
"""
from collections import deque


class Customer:
    """Level 1: a customer who can own one or more accounts.

    NOTE: nothing in the Level 1-4 API takes a customer_id directly
    (every method operates on account_id). Keep an eye on whether this
    object actually earns its place, or if it's YAGNI.
    """

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self.accounts: list[str] = []  # account_ids owned by this customer


class Account:
    """Level 1: a single bank account."""

    def __init__(self, account_id: str, created_at: int):
        self.account_id = account_id
        self.balance = 0
        self.transaction: list[dict] = []  # raw log of deposits/transfers/payments
        self.outgoing = 0  # Level 2: running total sent out, used for ranking
        self.created_at = created_at
        # Level 4: (timestamp, balance) snapshots for point-in-time lookups.
        # Always kept sorted ascending by timestamp.
        self.balance_history: list[tuple[int, int]] = [(created_at, 0)]


class Payment:
    """Level 3: a scheduled payment = a withdrawal (transfer-like) + a
    pending cashback refund that lands 24h later.
    """

    def __init__(self, payment_id: str, account_id: str, amount: int, timestamp: int, cashback_due_at: int):
        self.payment_id = payment_id
        self.account_id = account_id
        self.amount = amount
        self.timestamp = timestamp
        self.cashback_due_at = cashback_due_at
        self.cashback_amount = amount * 2 // 100  # 2%, rounded down
        self.status = "IN_PROGRESS"


class Simulation:
    CASHBACK_DELAY = 24 * 60 * 60 * 1000  # 24 hours, in milliseconds

    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.payments: dict[str, Payment] = {}
        self.payment_counter = 0
        # strictly ordered by cashback_due_at since pay() timestamps are
        # guaranteed strictly increasing -> safe to pop from the left
        self.pending_cashbacks: deque[Payment] = deque()

    def _process_cashbacks(self, timestamp: int) -> None:
        """Refund any cashback due at or before `timestamp`.

        Must run at the top of every timestamped operation so a due
        cashback is applied before that operation's own logic, per spec.
        """
        while self.pending_cashbacks and self.pending_cashbacks[0].cashback_due_at <= timestamp:
            payment = self.pending_cashbacks.popleft()
            account = self.accounts.get(payment.account_id)
            payment.status = "CASHBACK_RECEIVED"
            if account is not None:
                account.balance += payment.cashback_amount
                account.transaction.append({
                    "timestamp": payment.cashback_due_at,
                    "type": "cashback",
                    "amount": payment.cashback_amount,
                })
                account.balance_history.append((payment.cashback_due_at, account.balance))

    def create_account(self, timestamp: int, account_id: str) -> bool | None:
        self._process_cashbacks(timestamp)
        if account_id in self.accounts:
            return False
        self.accounts[account_id] = Account(account_id, timestamp)
        return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int | None:
        self._process_cashbacks(timestamp)
        account = self.accounts.get(account_id)
        if account is None:
            return None
        account.balance += amount
        account.transaction.append({"timestamp": timestamp, "type": "deposit", "amount": amount})
        account.balance_history.append((timestamp, account.balance))
        return account.balance

    def transfer(self, timestamp: int, source_account_id: str, target_account_id: str, amount: int) -> int | None:
        self._process_cashbacks(timestamp)
        if source_account_id == target_account_id:
            return None
        source = self.accounts.get(source_account_id)
        target = self.accounts.get(target_account_id)
        if source is None or target is None:
            return None
        if source.balance < amount:
            return None

        source.balance -= amount
        source.outgoing += amount
        target.balance += amount
        source.transaction.append({"timestamp": timestamp, "type": "transfer_out", "amount": amount, "counterparty": target_account_id})
        target.transaction.append({"timestamp": timestamp, "type": "transfer_in", "amount": amount, "counterparty": source_account_id})
        source.balance_history.append((timestamp, source.balance))
        target.balance_history.append((timestamp, target.balance))
        return source.balance

    def top_spenders(self, timestamp: int, n: int) -> list[str] | None:
        self._process_cashbacks(timestamp)
        ranked = sorted(
            self.accounts.values(),
            key=lambda account: (-account.outgoing, account.account_id),
        )
        return [f"{account.account_id}({account.outgoing})" for account in ranked[:n]]

    def pay(self, timestamp: int, account_id: str, amount: int) -> str | None:
        self._process_cashbacks(timestamp)
        account = self.accounts.get(account_id)
        if account is None:
            return None
        if account.balance < amount:
            return None

        account.balance -= amount
        account.outgoing += amount
        account.transaction.append({"timestamp": timestamp, "type": "pay", "amount": amount})
        account.balance_history.append((timestamp, account.balance))

        self.payment_counter += 1
        payment_id = f"payment{self.payment_counter}"
        payment = Payment(
            payment_id=payment_id,
            account_id=account_id,
            amount=amount,
            timestamp=timestamp,
            cashback_due_at=timestamp + self.CASHBACK_DELAY,
        )
        self.payments[payment_id] = payment
        self.pending_cashbacks.append(payment)
        return payment_id

    def get_payment_status(self, timestamp: int, account_id: str, payment: str) -> str | None:
        self._process_cashbacks(timestamp)
        if account_id not in self.accounts:
            return None
        found = self.payments.get(payment)
        if found is None or found.account_id != account_id:
            return None
        return found.status

    def merge_accounts(self, timestamp: int, account_id_1: str, account_id_2: str) -> bool | None:
        self._process_cashbacks(timestamp)
        if account_id_1 == account_id_2:
            return False
        survivor = self.accounts.get(account_id_1)
        absorbed = self.accounts.get(account_id_2)
        if survivor is None or absorbed is None:
            return False

        survivor.balance += absorbed.balance
        survivor.outgoing += absorbed.outgoing
        survivor.transaction.extend(absorbed.transaction)
        survivor.created_at = min(survivor.created_at, absorbed.created_at)

        # Inherit absorbed account's balance history so point-in-time
        # lookups through the survivor still work for the old timeline.
        survivor.balance_history.extend(absorbed.balance_history)
        survivor.balance_history.sort(key=lambda entry: entry[0])
        survivor.balance_history.append((timestamp, survivor.balance))

        # Re-point every payment owned by the absorbed account to the
        # survivor. Payment objects are shared references with
        # pending_cashbacks, so this single pass updates both places.
        for payment in self.payments.values():
            if payment.account_id == account_id_2:
                payment.account_id = account_id_1

        del self.accounts[account_id_2]
        return True

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None:
        self._process_cashbacks(timestamp)
        account = self.accounts.get(account_id)
        if account is None:
            return None
        if time_at < account.created_at:
            return None

        result = None
        for ts, balance in account.balance_history:
            if ts <= time_at:
                result = balance
            else:
                break
        return result
