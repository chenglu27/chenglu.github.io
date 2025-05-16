import streamlit as st
import pandas as pd
import io
from processors import process_order_table
from utils import download_excel, preview_dataframe, highlight_special_items_excel

# 设置页面配置
st.set_page_config(
    page_title="Excel订单表转装箱单工具",
    page_icon="📊",
    layout="wide"
)

# 配置上传文件大小限制 (400MB = 400 * 1024 * 1024 = 419430400 bytes)
st.session_state["MAX_UPLOAD_SIZE"] = 419430400

# 主标题
st.title("Excel订单表转装箱单工具")
st.markdown("---")

# 侧边栏说明
with st.sidebar:
    st.header("使用说明")
    st.markdown("""
    ### 操作步骤:
    1. 上传订单表（必须）
    2. 上传ITEM参考表（必须）
    3. 点击"处理数据"按钮
    4. 预览生成的装箱单表格
    5. 下载转换后的装箱单表格
    
    ### 功能说明:
    - 自动将B列（订单号）按"ITEM-Ord"格式拆分为B列(ITEM)和C列(Ord)
    - 特殊处理含RECS、REL、RER、SW、SWM、TA、WB、WBCS的ITEM项目
    - 根据ITEM匹配No of pkg、Description和单价
    - 特殊处理ITEM：CPGHT、FLG、HT、HTF匹配No of pkg和Description但不匹配单价，ITEM=ORD只匹配No of pkg且不匹配Description和单价
    - 自动计算件数（C列+D列）
    
    ### 输出表格列说明:
    - A列: No of pkg (匹配自参考表)
    - B列: ITEM (从订单表B列提取)
    - C列: Ord (从订单表B列提取)
    - D列: Description (匹配自参考表)
    - E列: 件数 (C列+D列的和)
    - F列: 单价 (匹配自参考表)
    - G列: 总价 (件数*单价)
    """)
    
    st.markdown("---")
    st.markdown("© 2023 Excel转换工具")

# 创建两列布局
col1, col2 = st.columns(2)

# 上传区域
with col1:
    st.header("上传文件")
    
    # 上传订单表格 (添加大小限制提示)
    uploaded_order = st.file_uploader("上传订单表 (Excel格式, 最大400MB)", type=["xlsx", "xls"], key="order_uploader")
    
    # 上传ITEM参考表格 (添加大小限制提示)
    uploaded_item_ref = st.file_uploader("上传ITEM参考表 (Excel格式, 最大400MB)", type=["xlsx", "xls"], key="item_ref_uploader")
    
    # 添加示例数据下载链接
    st.markdown("### 示例说明")
    st.markdown("""
    订单表要求:
    - B列：订单号（格式为"ITEM-Ord"）
    - C列：上（件）数据
    - D列：下（件）数据
    
    特殊处理说明:
    - 对于RECS、REL、RER、SW、SWM、TA、WB、WBCS前缀的ITEM，若D列不为0，会自动复制一行
    - 原行保留C列数据但D列清零，复制行保留D列数据但C列清零
    - 特殊ITEM（CPGHT、FLG、ORD、HT、HTF）在结果中会标红显示
    
    ITEM参考表要求:
    - ITEM列：项目编号
    - No of pkg列：包装数量
    - Description列：描述
    - Unit Price列：单价
    """)
    
    # 处理按钮
    process_button = st.button("处理数据", type="primary", use_container_width=True)

# 结果展示区域
with col2:
    st.header("结果预览")
    
    # 初始化session state
    if 'processed_df' not in st.session_state:
        st.session_state.processed_df = None
    
    if 'error_message' not in st.session_state:
        st.session_state.error_message = None
    
    if process_button:
        # 重置错误信息
        st.session_state.error_message = None
        
        if uploaded_order is None or uploaded_item_ref is None:
            st.error("请上传订单表和ITEM参考表!")
        else:
            try:
                # 显示处理中提示
                with st.spinner("正在处理数据..."):
                    # 读取Excel文件
                    order_df = pd.read_excel(uploaded_order)
                    item_ref_df = pd.read_excel(uploaded_item_ref)
                    
                    # 将数字索引转换为字母索引列名
                    if all(isinstance(col, int) for col in order_df.columns) or all(col.isdigit() for col in order_df.columns if isinstance(col, str)):
                        # 创建字母列名映射
                        letter_columns = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F'}
                        # 重命名列
                        order_df.columns = [letter_columns.get(int(col), f"Col_{col}") if isinstance(col, (int, str)) and (isinstance(col, int) or col.isdigit()) else col for col in order_df.columns]
                    
                    # 检查B、C、D列是否存在，如果不存在，尝试使用索引位置
                    if 'B' not in order_df.columns and len(order_df.columns) > 1:
                        st.info("自动重命名列: 第2列 -> B列")
                        new_columns = list(order_df.columns)
                        new_columns[1] = 'B'  # 第2列重命名为B
                        order_df.columns = new_columns
                    
                    if 'C' not in order_df.columns and len(order_df.columns) > 2:
                        st.info("自动重命名列: 第3列 -> C列")
                        new_columns = list(order_df.columns)
                        new_columns[2] = 'C'  # 第3列重命名为C
                        order_df.columns = new_columns
                    
                    if 'D' not in order_df.columns and len(order_df.columns) > 3:
                        st.info("自动重命名列: 第4列 -> D列")
                        new_columns = list(order_df.columns)
                        new_columns[3] = 'D'  # 第4列重命名为D
                        order_df.columns = new_columns
                    
                    # 检查必需的列是否存在
                    required_columns = ['B', 'C', 'D']
                    missing_columns = [col for col in required_columns if col not in order_df.columns]
                    if missing_columns:
                        raise ValueError(f"订单表中缺少以下列: {', '.join(missing_columns)}。请确保Excel表格包含订单号(B列)、上件数(C列)和下件数(D列)。")
                    
                    # 调用处理函数
                    processed_df = process_order_table(order_df, item_ref_df)
                    
                    # 保存到session state
                    st.session_state.processed_df = processed_df
                    
                st.success("数据处理完成!")
            except Exception as e:
                error_msg = str(e)
                st.session_state.error_message = error_msg
                st.error(f"处理过程中出现错误: {error_msg}")
    
    # 显示错误信息
    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        with st.expander("查看错误详情"):
            st.code(st.session_state.error_message)
    
    # 预览处理后的数据
    if st.session_state.processed_df is not None:
        preview_dataframe(st.session_state.processed_df)
        
        # 下载按钮（添加红色标记）
        # 为Excel添加特殊ITEM标红
        excel_output = highlight_special_items_excel(st.session_state.processed_df.copy())
        download_excel(excel_output, "装箱单表格.xlsx")

# 显示详细说明
st.markdown("---")
with st.expander("详细功能说明"):
    st.markdown("""
    ### 订单表处理逻辑:
    1. **B列拆分**: 将B列中的订单号按"ITEM-Ord"格式拆分为ITEM和Ord两个独立的列
    
    2. **特殊ITEM处理**:
       - 对于含有RECS、REL、RER、SW、SWM、TA、WB、WBCS前缀的ITEM
       - 如果D列（下（件））数据不为0，则复制一行数据
       - 在复制行中删除C列数据（设为0），在原行中删除D列数据（设为0）
       - 最终件数 = C列 + D列
       - 特殊处理ITEM（标红显示）：CPGHT、FLG、HT、HTF匹配No of pkg和Description但不匹配单价，ITEM=ORD只匹配No of pkg且不匹配Description和单价
    
    3. **数据匹配**:
       - 根据ITEM编号匹配参考表中的No of pkg、Description和单价
       - 为了兼容性，参考表可以使用不同的列名（例如：包装数量、描述、Price等）
    
    4. **输出格式**:
       - A列: No of pkg (匹配自参考表)
       - B列: ITEM (从订单表B列提取)
       - C列: Ord (从订单表B列提取)
       - D列: Description (匹配自参考表)
       - E列: 件数 (C列+D列的和)
       - F列: 单价 (匹配自参考表)
       - G列: 总价 (件数*单价)
    """)

# 联系信息
st.markdown("---")
st.markdown("""
<div style="text-align: center">
    <p>如有问题请联系管理员</p>
</div>
""", unsafe_allow_html=True)
