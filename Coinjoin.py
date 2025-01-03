import json
import math
from collections import Counter


def log_debug(message, debug):
    """Unified management of debug log output."""
    if debug:
        print(message)


def has_minimum_inputs(vin, debug=False):
    """Rule 1: At least 3 inputs."""
    if len(vin) < 3:
        log_debug("Not CoinJoin: Less than 3 inputs.", debug)
        return False
    return True


def has_sufficient_outputs(vin, vout, debug=False):
    """Rule 2: The output quantity must be at least half of the input quantity"""
    if int(math.log2(len(vout))) < 6:
        if len(vout) < len(vin):
            log_debug("Not CoinJoin: The output quantity is less than the input quantity.", debug)
            return False
    else:
        if len(vout) < len(vin)/2:
            log_debug("Not CoinJoin: The output quantity is less than half of the input quantity.", debug)
            return False
    
    return True

def has_repeated_output_value(vout, debug=False):
    """
    Rule 3:
    - At least one output value must reach the threshold frequency.
    """
    if len(vout) < 3:
        log_debug("Not CoinJoin: Insufficient outputs for meaningful analysis.", debug)
        return False
        
    target = max(min(int(math.log2(len(vout))) + 1, 5), 3)
    output_values = [out.get("value") for out in vout if out.get("value") is not None]
    value_counts = Counter(output_values)

    log_debug(f"Output Values Frequency: {value_counts}", debug)
    if any(count >= target for count in value_counts.values()):
        log_debug(
            f"CoinJoin-like detected: At least one output value appears {target} or more times.",
            debug,
        )
        return True

    log_debug(f"Not CoinJoin: No output value meets the threshold: {target}.", debug)
    return False

# def has_repeated_output_value(vout, debug=False):
    # """
    # Rule 3:
    # - If there is only one output value, check whether its frequency reaches the threshold.
    # - If there are multiple output values, at least two must reach the threshold.
    # """
#     if len(vout) < 3:
#         log_debug("Not CoinJoin: Insufficient outputs for meaningful analysis.", debug)
#         return False

#     target = max(min(int(math.log2(len(vout))) + 1, 5), 3)
#     output_values = [out.get("value") for out in vout if out.get("value") is not None]
#     value_counts = Counter(output_values)

#     log_debug(f"Output Values Frequency: {value_counts}", debug)

#     unique_value_count = len(value_counts)
#     log_debug(f"Unique output value count: {unique_value_count}", debug)

#     if unique_value_count == 1:
#         single_value = next(iter(value_counts.values()))
#         if single_value >= target:
#             log_debug(f"CoinJoin-like detected: Single value appears {single_value} times (threshold: {target}).", debug)
#             return True
#         log_debug(f"Not CoinJoin: Single value appears {single_value} times (threshold: {target}).", debug)
#         return False

#     elif unique_value_count > 1:
#         significant_values = [count for count in value_counts.values() if count >= target]
#         if len(significant_values) >= 2:
#             log_debug(
#                 f"CoinJoin-like detected: At least two values meet the threshold {target} "
#                 f"(values meeting threshold: {len(significant_values)}).",
#                 debug,
#             )
#             return True
#         log_debug(
#             f"Not CoinJoin: Fewer than two values meet the threshold {target} "
#             f"(values meeting threshold: {len(significant_values)}).",
#             debug,
#         )
#         return False

#     log_debug("Not CoinJoin: Unexpected state in output value analysis.", debug)
#     return False


def has_same_value_different_addresses(vout, debug=False):
    """Rule 4: Same output value must have different addresses."""
    seen_values = {}
    for output in vout:
        value = output.get("value")
        addresses = output.get("scriptPubKey", {}).get("addresses", [])
        if value and addresses:
            for address in addresses:
                if value in seen_values and seen_values[value] == address:
                    log_debug(
                        f"Not CoinJoin: Output with value {value} has the same address {address}.",
                        debug,
                    )
                    return False
                seen_values[value] = address
    return True

def has_reasonable_output_count(vin, vout, debug=False):
    """Rule 5: The number of outputs must be reasonable."""
    max_output_count = len(vin) * 2
    if len(vout) >= max_output_count:
        log_debug(
            f"Not CoinJoin: Output count ({len(vout)}) exceeds 2x input count ({len(vin)}).",
            debug,
        )
        return False
    return True

def has_op_return_output(vout, debug=False):
    """Rule 6: Check for OP_RETURN type outputs."""
    for output in vout:
        if output.get("value") == 0 and output.get("scriptPubKey", {}).get("type") == "nulldata":
            log_debug(f"CoinJoin-like detected: Found OP_RETURN output: {output}", debug)
            return False
    log_debug("Not CoinJoin: No OP_RETURN outputs found.", debug)
    return True


def is_coinjoin_like(tx, debug=False):
    """
    Detect whether a transaction has CoinJoin-like characteristics.
    """
    vin = tx.get("vin", [])
    vout = tx.get("vout", [])

    # Validate rules
    if not has_minimum_inputs(vin, debug):
        return False
    if not has_sufficient_outputs(vin, vout, debug):
        return False
    if not has_reasonable_output_count(vin, vout, debug):
        return False
    if not has_same_value_different_addresses(vout, debug):
        return False
    if not has_op_return_output(vout, debug):
        return False
    if not has_repeated_output_value(vout, debug):
        return False

    # If all rules pass, it is considered possibly CoinJoin-like
    return True


def process_transaction_file(file_path, debug=False):
    """
    Load transaction data from a file and detect whether it is CoinJoin-like.
    """
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return

    if not isinstance(data, (dict, list)):
        print("Invalid transaction format in JSON file.")
        return

    # Process single transaction or list of transactions
    transactions = [data] if isinstance(data, dict) else data
    print(f"Loaded {len(transactions)} transactions for analysis.")

    amount = 0
    # Detect each transaction
    for idx, res in enumerate(transactions, start=1):
        tx = res.get("result", {})
        if is_coinjoin_like(tx, debug=debug):
            txid = tx.get("txid", "Unknown")
            print(f"\nCoinJoin-like transaction detected: TXID = {txid}")
            amount += 1

    print(f"\nTotal CoinJoin-like transactions found: {amount}")



def main():
    # Specify the JSON file path
    file_path = "./txn/block_795550_transactions_details.json"
    process_transaction_file(file_path, debug=False)


if __name__ == "__main__":
    main()
