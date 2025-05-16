import streamlit as st
import pandas as pd
import base64
import openpyxl
from openpyxl.styles import Font, PatternFill
from io import BytesIO

def download_excel(excel_buffer, filename):
    """
    创建Excel文件的下载链接
    
    参数:
    excel_buffer (BytesIO): 包含Excel数据的缓冲区
    filename (str): 下载文件的名称
    """
    excel_data = excel_buffer.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">点击下载 {filename}</a>'
    st.markdown(href, unsafe_allow_html=True)

def preview_dataframe(df):
    """
    预览数据框
    
    参数:
    df (DataFrame): 要预览的数据框
    """
    # 检查数据框是否为空
    if df.empty:
        st.warning("生成的表格为空，请检查输入数据")
        return
    
    # 显示数据框的摘要信息
    st.write(f"表格包含 {df.shape[0]} 行 和 {df.shape[1]} 列")
    
    # 预览数据 - 显示前10行
    st.subheader("数据预览 (前10行)")
    
    # 显示原始预览
    preview_df = df.head(10).copy()
    
    # 特殊ITEM列表 (需要标红的ITEM)
    special_items = ['CPGHT', 'FLG', 'ORD', 'HT', 'HTF']
    
    # 为特殊ITEM添加红色标记
    preview_df['ITEM_标记'] = preview_df['ITEM'].apply(
        lambda x: f"🔴 {x}" if str(x) in special_items else x
    )
    
    # 创建一个有序的列列表，把ITEM_标记放在ITEM的位置
    columns = list(preview_df.columns)
    item_index = columns.index('ITEM')
    columns.remove('ITEM_标记')
    columns.insert(item_index, 'ITEM_标记')
    
    # 显示处理后的数据框
    st.dataframe(
        preview_df[columns], 
        use_container_width=True,
        hide_index=True
    )
    
    # 添加特殊ITEM说明
    st.caption("🔴 表示特殊ITEM: CPGHT、FLG、ORD、HT、HTF")
    
    # 显示ITEM列的唯一值数量
    if 'ITEM' in df.columns:
        unique_items = df['ITEM'].nunique()
        st.write(f"共有 {unique_items} 个不同的ITEM")
    
    # 显示提示信息
    st.info("请检查以上预览数据是否符合预期，如果满意请点击下方的下载按钮")

def highlight_special_items_excel(df):
    """
    为Excel中的特殊ITEM添加红色标记
    
    参数:
    df (DataFrame): 要导出的数据框
    
    返回:
    BytesIO: 包含带格式Excel的BytesIO对象
    """
    # 特殊ITEM列表
    special_items = ['CPGHT', 'FLG', 'ORD', 'HT', 'HTF']
    
    try:
        # 创建一个新的Excel文件
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # 写入表头
        for col_idx, col_name in enumerate(df.columns, 1):
            ws.cell(row=1, column=col_idx).value = col_name
        
        # 写入数据并标记特殊ITEM行
        red_font = Font(color="FF0000")
        
        for row_idx, row in enumerate(df.iterrows(), 2):  # 从第2行开始
            row_data = row[1]  # row[0]是索引，row[1]是数据
            
            # 检查是否是特殊ITEM
            is_special = str(row_data.get('ITEM', '')) in special_items
            
            # 写入该行数据
            for col_idx, col_name in enumerate(df.columns, 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.value = row_data.get(col_name, '')
                
                # 如果是特殊ITEM行，设置红色字体
                if is_special:
                    cell.font = red_font
        
        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return output
    
    except Exception as e:
        # 出错时记录错误并返回原始Excel
        print(f"Excel格式化错误: {str(e)}")
        # 简单地直接导出Excel作为备份方案
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        return output
