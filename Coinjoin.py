import json
import math
from collections import Counter


def log_debug(message, debug):
    """统一管理调试日志输出。"""
    if debug:
        print(message)


def has_minimum_inputs(vin, debug=False):
    """规则 1: 至少 3 个输入。"""
    if len(vin) < 3:
        log_debug("Not CoinJoin: Less than 3 inputs.", debug)
        return False
    return True


# def has_sufficient_outputs(vin, vout, debug=False):
#     """规则 2: 输出数量必须 >= 输入数量。"""
#     if len(vout) < len(vin):
#         log_debug("Not CoinJoin: Outputs are fewer than inputs.", debug)
#         return False
#     return True

def has_repeated_output_value(vout, debug=False):
    """规则 3: 至少一个输出金额出现 'target' 次或更多。"""
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
#     """
#     规则 3 & 7: 
#     1. 如果只有一种输出金额，检查其数量是否达到阈值。
#     2. 如果有多种输出金额，至少有两种金额的数量达到阈值。
#     """
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
    """规则 4: 输出中相同金额必须具有不同的地址。"""
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
    """规则 5: 输出数量必须合理。"""
    max_output_count = len(vin) * 2
    if len(vout) >= max_output_count:
        log_debug(
            f"Not CoinJoin: Output count ({len(vout)}) exceeds 2x input count ({len(vin)}).",
            debug,
        )
        return False
    return True

def has_op_return_output(vout, debug=False):
    """规则 6: 检查是否有 OP_RETURN 类型的输出。"""
    for output in vout:
        if output.get("value") == 0 and output.get("scriptPubKey", {}).get("type") == "nulldata":
            log_debug(f"CoinJoin-like detected: Found OP_RETURN output: {output}", debug)
            return False
    log_debug("Not CoinJoin: No OP_RETURN outputs found.", debug)
    return True


def is_coinjoin_like(tx, debug=False):
    """
    检测交易是否具有 CoinJoin-like 特征。
    """
    vin = tx.get("vin", [])
    vout = tx.get("vout", [])

    # 验证规则
    if not has_minimum_inputs(vin, debug):
        return False
    # if not has_sufficient_outputs(vin, vout, debug):
    #     return False
    if not has_reasonable_output_count(vin, vout, debug):
        return False
    if not has_same_value_different_addresses(vout, debug):
        return False
    if not has_op_return_output(vout, debug):
        return False
    if not has_repeated_output_value(vout, debug):
        return False

    # 如果所有规则都通过，认为可能是 CoinJoin 交易
    return True


def process_transaction_file(file_path, debug=False):
    """
    从文件加载交易数据并检测是否为 CoinJoin-like。
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

    # 处理单笔交易或交易列表
    transactions = [data] if isinstance(data, dict) else data
    print(f"Loaded {len(transactions)} transactions for analysis.")

    amount = 0
    # 检测每笔交易
    for idx, res in enumerate(transactions, start=1):
        tx = res.get("result", {})
        if is_coinjoin_like(tx, debug=debug):
            txid = tx.get("txid", "Unknown")
            print(f"\nCoinJoin-like transaction detected: TXID = {txid}")
            amount += 1

    print(f"\nTotal CoinJoin-like transactions found: {amount}")



def main():
    # 指定 JSON 文件路径
    file_path = "./block_795499_transactions_details.json"
    process_transaction_file(file_path, debug=False)


if __name__ == "__main__":
    main()
