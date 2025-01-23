CoinJoin-like Transaction Analysis Script

概述

该脚本旨在分析比特币交易数据，通过一系列规则判断交易是否具有 CoinJoin 的特征，并将符合条件的交易及相关数据记录到日志和 CSV 文件中。

核心功能

1. 日志管理 (log_debug)

   统一管理调试日志输出，支持在控制台输出日志和将日志保存到文件，日志信息附带时间戳。

2. 交易分析规则

  规则 1：最少输入数量

    函数：has_minimum_inputs(vin, debug=False, log_file=False)规则描述：

      输入数量必须至少为 3。

  规则 2：足够的输出数量

    函数：has_sufficient_outputs(vin, vout, debug=False, log_file=False)规则描述：

      输出数量必须至少是输入数量的一半（或满足特定的对数关系）。

  规则 3：重复输出值

    函数：has_repeated_output_value(vout, transaction_hash, debug=False, log_file=False, top5_file=False)规则描述：

      至少一个输出值达到阈值频率。
  
      仅考虑按值降序排列的前 5 个最频繁的值，并将该些值与交易响应保存到 CSV 文件。

  规则 4：唯一的输出地址

    函数：has_unique_addresses(vout, debug=False, log_file=None)规则描述：

      所有输出地址必须唯一。
  
  规则 5：合理的输出数量

    函数：has_reasonable_output_count(vin, vout, debug=False, log_file=False)规则描述：

      输出数量不能超过输入数量的 2 倍。

  规则 6：检查 OP_RETURN 输出

    函数：has_op_return_output(vout, debug=False, log_file=False)规则描述：

      不允许出现类型为 OP_RETURN且值为 0 的输出。

      规则 7：唯一的输入地址

    函数：has_unique_input_addresses(vin, debug=False, log_file=False)规则描述：

      所有输入地址必须不完全相同。

3. 判断交易是否符合 CoinJoin 特征

  函数：is_coinjoin_like(tx, debug=False, log_file=False, top5_file=False)描述：逐一调用所有规则判断交易是否具有 CoinJoin 特征。如果通过所有规则，则规定为符合 CoinJoin 特征。

4. 交易文件分析

  函数：analyze_transactions(file_path, debug=False, log_file=False, coinjoin_file=False, top5_file=False)描述：

    逐行读取 JSON 文件中的交易记录，检查每笔交易是否具有 CoinJoin 特征。

    如果符合特

