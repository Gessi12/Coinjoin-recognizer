import json
import math
from collections import Counter
import csv
import os
import datetime



def log_debug(message, debug, log_file="coinjoin_analysis.log"):
    """Unified management of debug log output and save logs to a file"""
    """统一管理调试日志输出，并将日志保存到文件，附带时间戳"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 格式化时间
    log_message = f"[{timestamp}] {message}"  # 加上时间戳的日志信息

    if debug:
        # Write log to file
        with open(log_file, "a") as log:
            log.write(log_message + "\n")


def has_minimum_inputs(vin, debug=False, log_file="coinjoin_analysis.log"):
    """Rule 1: At least 3 inputs required"""
    if len(vin) < 3:
        log_debug("Not CoinJoin: Less than 3 inputs.", debug, log_file)
        return False
    log_debug(f"Rule 1 passed: {len(vin)} inputs.", debug, log_file)
    return True


def has_sufficient_outputs(vin, vout, debug=False, log_file="coinjoin_analysis.log"):
    """Rule 2: The output quantity must be at least half of the input quantity"""
    if int(math.log2(len(vout))) + 1 < 5:
        if len(vout) < len(vin):
            log_debug("Not CoinJoin: The output quantity is less than the input quantity.", debug, log_file)
            return False
    else:
        if len(vout) < len(vin) / 2:
            log_debug("Not CoinJoin: The output quantity is less than half of the input quantity.", debug, log_file)
            return False
    log_debug(f"Rule 2 passed: {len(vout)} outputs.", debug, log_file)
    return True


# def has_repeated_output_value(vout, debug=False):
#     """
#     Rule 3:
#     - At least one output value must reach the threshold frequency.
#     - Only the top 5 most frequent values are considered.
#     """
#     if len(vout) < 3:
#         log_debug("Not CoinJoin: Insufficient outputs for meaningful analysis.", debug)
#         return False
        
#     target = max(min(int(math.log2(len(vout))), 5), 3)
#     output_values = [out.get("value") for out in vout if out.get("value") is not None]
#     value_counts = Counter(output_values)

#     # Sort in descending order of occurrence and only take the first five values
#     sorted_value_counts = value_counts.most_common(5)
    
#     # Check the frequent values to see if any of them meet the threshold for occurrence frequency
#     if any(count >= target for count in value_counts.values()):
#         log_debug(
#             f"CoinJoin-like detected: At least one of the top 5 output values appears {target} or more times.",
#             debug,
#         )
#         for value, count in sorted_value_counts:
#             if count >= target:
#                 log_debug(f"Value: {value}, Count: {count}", True)
#         return True

#     log_debug(f"Not CoinJoin: No output value in the top 5 meets the threshold: {target}.", debug)
#     return False


def has_repeated_output_value(vout, debug=False, log_file="coinjoin_analysis.log"):
    """
    Rule 3:
    - At least one output value must reach the threshold frequency.
    """
    if len(vout) < 3:
        log_debug("Not CoinJoin: Insufficient outputs for meaningful analysis.", debug, log_file)
        return False
        
    target = max(min(int(math.log2(len(vout))), 5), 3)
    output_values = [out.get("value") for out in vout if out.get("value") is not None]
    value_counts = Counter(output_values)

    log_debug(f"Output Values Frequency: {value_counts}", debug, log_file)
    
    if any(count >= target for count in value_counts.values()):
        log_debug(f"CoinJoin-like detected: At least one output value appears {target} or more times.", debug, log_file)
        return True

    log_debug(f"Not CoinJoin: No output value meets the threshold: {target}.", debug, log_file)
    return False


def has_same_value_different_addresses(vout, debug=False, log_file="coinjoin_analysis.log"):
    """Rule 4: Same output value must have different addresses"""
    seen_values = {}
    for output in vout:
        value = output.get("value")
        addresses = output.get("addresses", [])
        if value and addresses:
            for address in addresses:
                if value in seen_values and seen_values[value] == address:
                    log_debug(f"Not CoinJoin: Output with value {value} has the same address {address}.", debug, log_file)
                    return False
                seen_values[value] = address
    log_debug("Rule 4 passed: Same value has different addresses.", debug, log_file)
    return True


def has_reasonable_output_count(vin, vout, debug=False, log_file="coinjoin_analysis.log"):
    """Rule 5: The number of outputs must be reasonable"""
    max_output_count = len(vin) * 2
    if len(vout) > max_output_count:
        log_debug(f"Not CoinJoin: Output count ({len(vout)}) exceeds 2x input count ({len(vin)}).", debug, log_file)
        return False
    log_debug(f"Rule 5 passed: Reasonable output count ({len(vout)}).", debug, log_file)
    return True


def has_op_return_output(vout, debug=False, log_file="coinjoin_analysis.log"):
    """Rule 6: Check for OP_RETURN type outputs"""
    for output in vout:
        if output.get("value") == 0 and output.get("type") == "nonstandard":
            log_debug(f"CoinJoin-like detected: Found OP_RETURN output: {output}", debug, log_file)
            return False
    log_debug("Rule 6 passed: No OP_RETURN outputs found.", debug, log_file)
    return True


def is_coinjoin_like(tx, debug=False, log_file="coinjoin_analysis.log"):
    """
    Check if the transaction has CoinJoin-like characteristics
    """
    vin = tx.get("inputs", [])
    vout = tx.get("outputs", [])

    # Check rules
    if not has_minimum_inputs(vin, debug, log_file):
        return False
    if not has_sufficient_outputs(vin, vout, debug, log_file):
        return False
    if not has_reasonable_output_count(vin, vout, debug, log_file):
        return False
    if not has_op_return_output(vout, debug, log_file):
        return False
    if not has_same_value_different_addresses(vout, debug, log_file):
        return False
    if not has_repeated_output_value(vout, debug, log_file):
        return False

    # If all rules pass, it is considered possibly CoinJoin-like
    return True

def analyze_transactions(file_path, debug=False, log_file=False, coinjoin_file=False):
    """
    Read the file and analyze the transaction, and save the input address that matches the CoinJoin feature to a CSV file.
    """
    results = []
    coinjoin_count = 0  # Count transactions that meet CoinJoin characteristics

    # Check if the CSV file exists, open it in append mode if it exists, otherwise create a new file
    file_exists = os.path.exists(coinjoin_file)
    with open(coinjoin_file, mode='a', newline='') as csv_file:
        fieldnames = ['transaction_hash', 'input_addresses']

        # If the file does not exist, write it to the CSV header
        if not file_exists:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
        else:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        try:
            with open(file_path, "r") as file:
                for line_number, line in enumerate(file, start=1):
                    try:
                        # Parse JSON data
                        transaction = json.loads(line.strip())

                        # Determine whether the transaction meets the CoinJoin characteristics
                        if is_coinjoin_like(transaction, False, log_file):
                            result = {
                                "hash": transaction["hash"],
                                "line": line_number,
                                "is_coinjoin_like": True
                            }
                            results.append(result)
                            coinjoin_count += 1  # Every time a CoinJoin transaction is discovered, the count increases by one

                            # Obtain the input address for the CoinJoin transaction
                            input_addresses = [input.get("addresses", []) for input in transaction.get("inputs", [])]
                            input_addresses_flat = [address for sublist in input_addresses for address in sublist]
                            
                            # Write CSV file
                            writer.writerow({
                                'transaction_hash': transaction['hash'],
                                'input_addresses': ', '.join(input_addresses_flat)
                            })
                            log_debug(f"  -> Transaction {transaction['hash']} is CoinJoin-like.", debug, log_file)
                    except json.JSONDecodeError:
                        log_debug(f"Error decoding JSON on line {line_number}. Skipping...", debug, log_file)
        except FileNotFoundError:
            log_debug(f"Error: File {file_path} not found.", debug, log_file)
        except Exception as e:
            log_debug(f"Unexpected error: {e}", debug, log_file)

    # Print the total number of CoinJoin transactions found
    log_debug(f"\nTotal CoinJoin-like transactions: {coinjoin_count}", debug, log_file)
    
    return True


def main():
    # Specify the JSON file path
    file_path = "./txn/block_795550_transactions_details.json"
    results = analyze_transactions(file_path, debug=True, log_file="coinjoin_analysis.log",coinjoin_file ="coinjoin_input_addresses.csv")  # Set debug to True to enable log printingprocess_transaction_file(file_path, debug=False)


if __name__ == "__main__":
    main()
