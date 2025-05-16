import pandas as pd
import numpy as np
import re

def process_order_table(order_df, item_ref_df):
    """
    处理订单表格，将其转换为装箱单格式
    
    参数:
    order_df (DataFrame): 订单表格数据
    item_ref_df (DataFrame): ITEM参考表格数据
    
    返回:
    DataFrame: 处理后的装箱单表格
    """
    # 创建结果DataFrame的副本
    result_df = order_df.copy()
    
    # 列名显示
    print(f"处理表格列: {result_df.columns.tolist()}")
    
    # 确保需要的列存在
    required_cols = ['B', 'C', 'D']
    missing_cols = [col for col in required_cols if col not in result_df.columns]
    if missing_cols:
        # 尝试检查列数是否足够，如果足够则自动重命名
        if len(result_df.columns) >= 4:  # 至少需要4列 (包括A/B/C/D)
            if 'B' not in result_df.columns:
                result_df.rename(columns={result_df.columns[1]: 'B'}, inplace=True)
            if 'C' not in result_df.columns:
                result_df.rename(columns={result_df.columns[2]: 'C'}, inplace=True)
            if 'D' not in result_df.columns:
                result_df.rename(columns={result_df.columns[3]: 'D'}, inplace=True)
            # 重新检查是否还有缺失的列
            missing_cols = [col for col in required_cols if col not in result_df.columns]
            
    if missing_cols:
        raise ValueError(f"订单表格中缺少以下列: {', '.join(missing_cols)}。请确保表格包含订单号(B列)、上件数(C列)和下件数(D列)。")
    
    # 拆分B列为ITEM和Ord列 (按要求2)
    result_df['ITEM'] = result_df['B'].apply(lambda x: extract_item(x) if pd.notna(x) else np.nan)
    result_df['Ord'] = result_df['B'].apply(lambda x: extract_ord(x) if pd.notna(x) else np.nan)
    
    # 处理特殊ITEM (按要求3)
    result_df = handle_special_items(result_df)
    
    # 根据ITEM匹配参考表中的数据 (按要求4)
    result_df = match_reference_data(result_df, item_ref_df)
    
    # 按要求组织列顺序
    result_df = organize_columns(result_df)
    
    return result_df

def extract_item(value):
    """
    从B列值中提取ITEM编号 (按要求2)
    """
    if not isinstance(value, str):
        return value
    
    # 使用正则表达式或分隔符分割ITEM和Ord
    # 假设格式为"ITEM-Ord"
    parts = str(value).split('-', 1)
    if len(parts) > 0:
        return parts[0]
    return np.nan

def extract_ord(value):
    """
    从B列值中提取订单号 (按要求2)
    """
    if not isinstance(value, str):
        return value
    
    # 使用正则表达式或分隔符分割ITEM和Ord
    # 假设格式为"ITEM-Ord"
    parts = str(value).split('-', 1)
    if len(parts) > 1:
        return parts[1]
    return np.nan

def handle_special_items(df):
    """
    处理特殊ITEM项目 (按要求3)
    
    处理规则：对于ITEM完全等于RECS、REL、RER、SW、SWM、TA、WB、WBCS的行，
    如果D列（下（件））数据不为0，则复制一行数据，
    复制行删除C列数据（设为0），并且复制行的ITEM名称后加个数字2，如SW就变成SW2。
    同时删除原行的D列数据（设为0）。
    最终每行的E列（件数）= C列+D列的值。
    """
    # 需要特殊处理的ITEM列表
    special_items = ['RECS', 'REL', 'RER', 'SW', 'SWM', 'TA', 'WB', 'WBCS', 'WM02', 'GWCS', 'WHB']
    
    # 创建结果的副本
    result_df = pd.DataFrame(columns=df.columns)
    
    # 添加件数列
    result_df['件数'] = np.nan
    
    # 处理每一行
    for idx, row in df.iterrows():
        item = str(row['ITEM']) if pd.notna(row['ITEM']) else ""
        
        # 检查是否为特殊ITEM（完全等于）
        is_special = item in special_items
        
        # 特殊处理: 如果D列（下（件））数据不为0且是特殊ITEM
        if is_special and pd.notna(row['D']) and row['D'] != 0:
            # 打印调试信息
            print(f"处理特殊ITEM: {item}, C={row['C']}, D={row['D']}")
            
            # 原行: 保留C列数据，清空D列
            original_row = row.copy()
            original_row['D'] = 0  # 原行的D列清零
            result_df = pd.concat([result_df, pd.DataFrame([original_row])], ignore_index=True)
            
            # 新行: 删除C列数据（设为0），保留D列原始数据，ITEM名称加2
            new_row = row.copy()
            new_row['C'] = 0  # 新行的C列清零
            
            # 修改ITEM名称，在后面加2
            new_row['ITEM'] = f"{item}2"
            print(f"修改ITEM名称: {item} -> {new_row['ITEM']}")
            
            # 将新行添加到结果DataFrame
            result_df = pd.concat([result_df, pd.DataFrame([new_row])], ignore_index=True)
            print(f"新增特殊行: ITEM={new_row['ITEM']}, C={new_row['C']}, D={new_row['D']}")
        else:
            # 对于普通行，直接添加
            result_df = pd.concat([result_df, pd.DataFrame([row])], ignore_index=True)
    
    # 计算件数 (E列) = C列 + D列的值
    result_df['件数'] = result_df.apply(
        lambda row: (pd.to_numeric(row.get('C', 0), errors='coerce') if pd.notna(row.get('C', 0)) else 0) + 
                    (pd.to_numeric(row.get('D', 0), errors='coerce') if pd.notna(row.get('D', 0)) else 0), 
        axis=1
    )
    
    return result_df

def match_reference_data(df, ref_df):
    """
    根据ITEM匹配参考表中的数据 (按要求4)
    """
    # 初始化新列
    df['No of pkg'] = np.nan
    df['Description'] = ''
    df['单价'] = np.nan
    
    # 确保ITEM列在参考表中存在
    if 'ITEM' not in ref_df.columns:
        # 尝试查找可能的ITEM列
        possible_item_cols = ['Item', 'item', '产品']
        for col in possible_item_cols:
            if col in ref_df.columns:
                ref_df.rename(columns={col: 'ITEM'}, inplace=True)
                break
        
        # 如果仍未找到ITEM列，返回原始df
        if 'ITEM' not in ref_df.columns:
            return df
    
    # 标准化参考表中的列名
    column_mapping = {}
    
    # 可能的No of pkg列名
    if 'No of pkg' not in ref_df.columns:
        pkg_cols = ['Pkg', '包装数量', 'Package', '包装']
        for col in pkg_cols:
            if col in ref_df.columns:
                column_mapping[col] = 'No of pkg'
                break
    
    # 可能的Description列名
    if 'Description' not in ref_df.columns:
        desc_cols = ['Desc', '描述', '说明', 'Description']
        for col in desc_cols:
            if col in ref_df.columns and col != 'Description':
                column_mapping[col] = 'Description'
                break
    
    # 可能的Unit Price列名
    if 'Unit Price' not in ref_df.columns:
        price_cols = ['单价', 'Price', 'UnitPrice', '价格']
        for col in price_cols:
            if col in ref_df.columns:
                column_mapping[col] = 'Unit Price'
                break
    
    # 应用列名映射
    if column_mapping:
        ref_df.rename(columns=column_mapping, inplace=True)
    
    # 创建ITEM到参考数据的映射
    item_to_ref = {}
    for _, row in ref_df.iterrows():
        item = str(row['ITEM'])
        no_of_pkg = row.get('No of pkg', np.nan)
        description = row.get('Description', '')
        unit_price = row.get('Unit Price', np.nan)
        
        item_to_ref[item] = {
            'No of pkg': no_of_pkg,
            'Description': description,
            'Unit Price': unit_price
        }
    
    print(f"参考表中的ITEM数量: {len(item_to_ref)}")
    
    # 特殊处理ITEM列表 (CPGHT,FLG,ORD,HT,HTF)
    special_items = ['CPGHT', 'FLG', 'ORD', 'HT', 'HTF']
    print(f"特殊ITEM列表: {special_items}")
    
    # 标记特殊行（添加一个标记列，稍后会删除）
    df['_是特殊ITEM'] = df['ITEM'].apply(lambda x: str(x) in special_items)
    
    # 根据ITEM匹配参考数据
    for idx, row in df.iterrows():
        item = str(row['ITEM'])
        
        # 特殊处理CPGHT、FLG、ORD、HT、HTF这些ITEM
        if any(item == special_item for special_item in special_items):
            print(f"处理特殊ITEM: {item}")
            # 对于所有特殊ITEM，需要匹配No of pkg
            if item in item_to_ref:
                df.at[idx, 'No of pkg'] = item_to_ref[item]['No of pkg']
                
                # 对于ORD，Description字段要清空
                if item == 'ORD':
                    df.at[idx, 'Description'] = ''
                    # 添加这一行确保不会被覆盖
                    print(f"清空ITEM=ORD的Description: {row['ITEM']}")
                else:
                    # 对于其他特殊ITEM，匹配Description
                    df.at[idx, 'Description'] = item_to_ref[item]['Description']
                
                # HT和HTF需要匹配Unit Price
                if item in ['HT', 'HTF']:
                    df.at[idx, '单价'] = item_to_ref[item]['Unit Price']
                    print(f"匹配{item}的单价: {item_to_ref[item]['Unit Price']}")
                    
            # 只有CPGHT、FLG、ORD不匹配单价，其他继续处理
            if item not in ['HT', 'HTF']:
                continue
        
        # 匹配参考数据（其他正常ITEM匹配所有字段）
        if item in item_to_ref:
            df.at[idx, 'No of pkg'] = item_to_ref[item]['No of pkg']
            df.at[idx, 'Description'] = item_to_ref[item]['Description']
            df.at[idx, '单价'] = item_to_ref[item]['Unit Price']
    
    # 确保ORD的Description一定是空的
    df.loc[df['ITEM'] == 'ORD', 'Description'] = ''
    
    # 打印处理后的ORD数据
    for idx, row in df[df['ITEM'] == 'ORD'].iterrows():
        print(f"最终ORD数据: ITEM={row['ITEM']}, Description='{row['Description']}'")
    
    return df

def organize_columns(df):
    """
    按要求组织输出表格的列顺序
    """
    # 计算总价（件数*单价）
    # 确保数据类型正确以避免乘法错误
    df['件数'] = pd.to_numeric(df['件数'], errors='coerce')
    df['单价'] = pd.to_numeric(df['单价'], errors='coerce')
    
    # 安全计算总价，处理NA值
    df['总价'] = df['件数'].multiply(df['单价'], fill_value=0)
    
    # 在最终输出前，将带有数字2的特殊ITEM替换回原始ITEM
    special_prefixes_with_2 = ['RECS2', 'REL2', 'RER2', 'SW2', 'SWM2', 'TA2', 'WB2', 'WBCS2', 'WM022', 'GWCS2', 'WHB2']
    special_prefixes = ['RECS', 'REL', 'RER', 'SW', 'SWM', 'TA', 'WB', 'WBCS', 'WM02', 'GWCS', 'WHB']
    
    # 创建前缀映射字典
    prefix_mapping = dict(zip(special_prefixes_with_2, special_prefixes))
    
    # 替换ITEM值
    for idx, row in df.iterrows():
        item = str(row['ITEM'])
        if item in prefix_mapping:
            print(f"替换ITEM名称: {item} -> {prefix_mapping[item]}")
            df.at[idx, 'ITEM'] = prefix_mapping[item]
    
    # 保存_是特殊ITEM标记列（如果存在）
    has_special_mark = '_是特殊ITEM' in df.columns
    if has_special_mark:
        special_item_marks = df['_是特殊ITEM'].copy()
    
    # 删除件数为0的行
    before_count = len(df)
    df = df[df['件数'] != 0]
    after_count = len(df)
    if before_count > after_count:
        print(f"已删除 {before_count - after_count} 行件数为0的数据")
    
    # 创建新的DataFrame，按要求组织列顺序 (A-G列)
    columns_order = [
        'No of pkg',   # A列
        'ITEM',        # B列
        'Ord',         # C列 
        'Description', # D列
        '件数',        # E列
        '单价',        # F列
        '总价'         # G列
    ]
    
    # 确保所有必要的列都存在
    for col in columns_order:
        if col not in df.columns:
            if col in ['No of pkg', '单价', '件数']:
                df[col] = np.nan
            else:
                df[col] = ''
    
    # 按照指定顺序返回列
    return df[columns_order]