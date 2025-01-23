import json
import math
from collections import Counter
import csv
import os
import datetime



def log_debug(message, debug, log_file=False):
    """Unified management of debugging log output, and saving the logs to a file with timestamps attached"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
    log_message = f"[{timestamp}] {message}" 

    if debug:
        # Write log to file
        print(log_message)
        with open(log_file, "a") as log:
            log.write(log_message + "\n")


def has_minimum_inputs(vin, debug=False, log_file=False):
    """Rule 1: At least 3 inputs required"""
    if len(vin) < 3:
        log_debug("Not CoinJoin: Less than 3 inputs.", debug, log_file)
        return False
    log_debug(f"Rule 1 passed: {len(vin)} inputs.", debug, log_file)
    return True


def has_sufficient_outputs(vin, vout, debug=False, log_file=False):

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


def has_repeated_output_value(vout,vin, transaction_hash, debug=False, log_file=False, top10_file=False):
    """
    Rule 3:
    - At least one output value must reach the threshold frequency.
    - Only the top 5 most frequent values exceeding the threshold are considered, sorted by value in descending order.
    - Write the transaction hash and top 5 values to a CSV file.
    """
    if len(vout) < 3:
        log_debug("Not CoinJoin: Insufficient outputs for meaningful analysis.", debug, log_file)
        return False
        
    target = max(min(int(math.log2(len(vout))), 5), 3)
    # target = 3
    output_values = [out.get("value") for out in vout if out.get("value") is not None]
    value_counts = Counter(output_values)
    vin_count = len(vin)
    vout_count = len(vout)

    # Sort by value in descending order
    sorted_value_counts = sorted(value_counts.items(), key=lambda x: -x[0])
    # Filter by threshold and take top 10
    top10 = [(value, count) for value, count in sorted_value_counts if count >= target][:10]



    if top10:
        log_debug(f"CoinJoin-like detected: Top 10 output values exceeding threshold {target}:", debug, log_file)
        for value, count in top10:
            log_debug(f"Value: {value}, Count: {count}", True, log_file)

        # Write to CSV file
        file_exists = os.path.exists(top10_file)
        with open(top10_file, mode='a', newline='') as csv_file_obj:
            fieldnames = [
                'transaction_hash',
                'number_of_input',
                'number_of_output',
                'total_btc_amount',
                'top10_data'
            ]
            writer = csv.DictWriter(csv_file_obj, fieldnames=fieldnames)

            # If the file does not exist, write the header
            if not file_exists:
                writer.writeheader()

            # Write each top 5 value and count with the transaction hash
            writer.writerow({
                'transaction_hash': transaction_hash,
                'number_of_input': vin_count,
                'number_of_output': vout_count,
                'total_btc_amount': sum(output_values),
                'top10_data': top10,
            })

        return True

    log_debug(f"Not CoinJoin: No output value meets the threshold {target}.", False, log_file)
    return False


def has_unique_output_addresses(vout, debug=False, log_file=None):
    """
    Rule 4: Output addresses must be unique.
    """
    seen_addresses = set()
    for output in vout:
        addresses = output.get("addresses", [])
        for address in addresses:
            if address in seen_addresses:
                log_debug(f"Not CoinJoin: Duplicate address found: {address}.", debug, log_file)
                return False
            seen_addresses.add(address)
    log_debug("Rule passed: All output addresses are unique.", debug, log_file)
    return True


def has_reasonable_output_count(vin, vout, debug=False, log_file=False):
    """Rule 5: The number of outputs must be reasonable"""
    max_output_count = len(vin) * 2
    if len(vout) > max_output_count:
        log_debug(f"Not CoinJoin: Output count ({len(vout)}) exceeds 2x input count ({len(vin)}).", debug, log_file)
        return False
    log_debug(f"Rule 5 passed: Reasonable output count ({len(vout)}).", debug, log_file)
    return True


def has_op_return_output(vout, debug=False, log_file=False):
    """Rule 6: Check for OP_RETURN type outputs"""
    for output in vout:
        if output.get("value") == 0 and output.get("type") == "nonstandard":
            log_debug(f"CoinJoin-like detected: Found OP_RETURN output: {output}", debug, log_file)
            return False
    log_debug("Rule 6 passed: No OP_RETURN outputs found.", debug, log_file)
    return True

def has_not_only_one_input_addresses(vin, debug=False, log_file=False):
    """
    Rule 7: All input addresses must not be the same.
    """
    # Extract all input addresses
    input_addresses = [addr for input_data in vin for addr in input_data.get("addresses", [])]
    unique_addresses = set(input_addresses)

    # If the number of unique addresses is less than or equal to 1, it means that all input addresses are the same
    if len(unique_addresses) <= 1:
        log_debug("Not CoinJoin: All input addresses are the same.", debug, log_file)
        return False
    log_debug("Rule 7 passed: Input addresses are not all the same.", debug, log_file)
    return True

def has_unique_input_addresses_by_value(vin, debug=False, log_file=False):
    """
    Rule 7 (updated): For inputs with the same value, their addresses must be unique.
    """
    # Dictionary to store addresses grouped by value
    value_to_addresses = {}

    for input_data in vin:
        value = input_data.get("value")  # Extract the value of the input
        addresses = input_data.get("addresses", [])  # Extract associated addresses

        if value is not None:
            if value not in value_to_addresses:
                value_to_addresses[value] = set()  # Initialize a set for this value

            for address in addresses:
                if address in value_to_addresses[value]:
                    log_debug(
                        f"Not CoinJoin: Duplicate address '{address}' found for value '{value}'.",
                        debug,
                        log_file,
                    )
                    return False  # Duplicate address found for the same value
                value_to_addresses[value].add(address)  # Add address to the set

    log_debug("Rule passed: All addresses are unique for the same value.", debug, log_file)
    return True



def is_coinjoin_like(tx, debug=False, log_file=False, top10_file=False):
    """
    Check if the transaction has CoinJoin-like characteristics
    """
    transaction_hash = tx.get("hash")
    vin = tx.get("inputs", [])
    vout = tx.get("outputs", [])

    # Check rules
    if not has_minimum_inputs(vin, debug, log_file):
        return False
    if not has_not_only_one_input_addresses(vin, debug, log_file):
        return False
    if not has_sufficient_outputs(vin, vout, debug, log_file):
        return False
    if not has_reasonable_output_count(vin, vout, debug, log_file):
        return False
    if not has_op_return_output(vout, debug, log_file):
        return False
    if not has_unique_output_addresses(vout, debug, log_file):
        return False
    if not has_unique_input_addresses_by_value(vin, debug, log_file):
        return False
    if not has_repeated_output_value(vout,vin,transaction_hash ,debug, log_file,top10_file):
        return False

    # If all rules pass, it is considered possibly CoinJoin-like
    return True

def analyze_transactions(file_path, debug=False, log_file=False, coinjoin_file=False, top10_file=False):
    """
    Read the file and analyze the transaction, and save the input address that matches the CoinJoin feature to a CSV file.
    """
    results = []
    coinjoin_count = 0  # Count transactions that meet CoinJoin characteristics

    # Check if the CSV file exists, open it in append mode if it exists, otherwise create a new file
    file_exists = os.path.exists(coinjoin_file)
    with open(coinjoin_file, mode='a', newline='') as csv_file:
        fieldnames = ['transaction_hash', 'addresses']

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
                        if is_coinjoin_like(transaction, False, log_file, top10_file):
                            result = {
                                "hash": transaction["hash"],
                                "line": line_number,
                                "is_coinjoin_like": True
                            }
                            results.append(result)
                            coinjoin_count += 1  # Every time a CoinJoin transaction is discovered, the count increases by one

                            # Obtain the input address for the CoinJoin transaction
                            addresses = [output.get("addresses", []) for output in transaction.get("outputs", [])]
                            addresses_flat = [address for sublist in addresses for address in sublist]
                            
                            # Write CSV file
                            writer.writerow({
                                'transaction_hash': transaction['hash'],
                                'addresses': ', '.join(addresses_flat)
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

