import streamlit as st
import pandas as pd
import io
import zipfile
import numpy as np

# === 网页配置 ===
st.set_page_config(page_title="超级词书工具", page_icon="⚡")

st.title("⚡ 律动词书清洗工具 (多模式 + 分包)")
st.markdown("功能：**灵活删列** -> **清洗** -> **(可选) 均分切割** -> **无表头导出**")

# ================= 侧边栏设置 =================
st.sidebar.header("🛠️ 第一步：删列模式")

# 定义删除模式
mode_options = {
    "A": "保留第3列及之后 (删除前2列)",
    "B": "保留第4列及之后 (删除前3列)",
    "C": "只删除第3列 (保留1,2,4...)",
    "D": "自定义选择删除哪些列",
    "N": "不删除任何列"
}
delete_mode = st.sidebar.radio("请选择删除规则：", list(mode_options.keys()), format_func=lambda x: mode_options[x])

custom_drop_indices = []
if delete_mode == "D":
    st.sidebar.info("请在上传文件后，在下方多选框中选择要删除的列。")

st.sidebar.markdown("---")
st.sidebar.header("📏 第二步：清洗规则")
max_len = st.sidebar.slider("单词/ID 最大长度", 1, 50, 6)

st.sidebar.markdown("---")
st.sidebar.header("📦 第三步：输出设置")
enable_split = st.sidebar.checkbox("开启均分输出 (切分成多个文件)", value=False)
if enable_split:
    split_count = st.sidebar.number_input("切分成几份？", min_value=2, max_value=50, value=2, step=1)
else:
    split_count = 1

# ================= 主程序 =================
uploaded_file = st.file_uploader("上传文件 (xlsx/csv)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        # 1. 读取文件
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, dtype=str, header=None) # 假设无表头或为了通过索引操作，这里先按无header读取防止列名混乱，或者读header
            # 通常用户文件有表头，我们为了索引准确，还是读 header
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, dtype=str)
        else:
            df = pd.read_excel(uploaded_file, dtype=str)
        
        st.success(f"✅ 读取成功！原始数据: {len(df)} 行，{len(df.columns)} 列。")

        # 2. 执行删列逻辑
        cols_count = len(df.columns)
        drop_indices = []

        if delete_mode == "A": # 删 0, 1
            drop_indices = [0, 1]
        elif delete_mode == "B": # 删 0, 1, 2
            drop_indices = [0, 1, 2]
        elif delete_mode == "C": # 删 2
            drop_indices = [2]
        elif delete_mode == "D": # 自定义
            # 让用户选择列名
            cols_to_drop = st.multiselect(
                "请选择要【删除】的列：", 
                df.columns,
                format_func=lambda x: f"{x}" 
            )
            # 找出这些列的索引或名字
            # 为简单起见，直接按名字删
            if cols_to_drop:
                df = df.drop(columns=cols_to_drop)
                st.caption(f"已删除自定义列: {cols_to_drop}")
            
            # 如果是 ABCD 模式中的 A/B/C，我们需要检查索引是否越界
        
        # 执行 A/B/C 的索引删除
        if delete_mode in ["A", "B", "C"]:
            # 过滤掉越界的索引
            valid_indices = [i for i in drop_indices if i < cols_count]
            if len(valid_indices) != len(drop_indices):
                st.warning(f"⚠️ 警告：表格列数不够，部分列无法删除。尝试删除索引: {drop_indices}")
            
            if valid_indices:
                # 使用 iloc 剔除指定索引的列
                # 这里的逻辑是：保留【不在】删除列表里的列
                keep_indices = [i for i in range(cols_count) if i not in valid_indices]
                df = df.iloc[:, keep_indices]
                st.info(f"ℹ️ 已执行模式 {delete_mode}，剩余 {len(df.columns)} 列。")

        # 3. 数据清洗 (空行/重复)
        df = df.dropna(how='any')
        df = df.drop_duplicates()

        # 4. 长度过滤
        if len(df.columns) > 0:
            # 默认检查第一列
            target_col = df.columns[0]
            st.caption(f"正在根据列【{target_col}】进行长度过滤 (≤ {max_len})")
            
            # 执行过滤
            df_final = df[df[target_col].str.strip().str.len() <= max_len]
        else:
            st.error("❌ 所有列都被删完了！请检查你的删列设置。")
            st.stop()
        
        # 统计
        removed_count = len(df) - len(df_final) # 注意这里对比的是“去重后”和“过滤长度后”

        # ================= 结果展示 =================
        st.markdown("---")
        st.subheader("✨ 结果预览")
        st.dataframe(df_final.head())
        st.write(f"最终行数: **{len(df_final)}** (本步骤清洗掉 {removed_count} 行)")

        # ================= 输出下载 (处理均分) =================
        
        # 准备文件名后缀
        file_ext = ".csv" if uploaded_file.name.endswith('.csv') else ".xlsx"
        mime_type = "text/csv" if file_ext == ".csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        if enable_split and split_count > 1:
            # === 分包模式 (ZIP) ===
            st.markdown("### 📦 分包下载")
            
            # 计算切分
            chunks = np.array_split(df_final, split_count)
            
            # 创建内存中的 ZIP 文件
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, chunk in enumerate(chunks):
                    part_filename = f"part_{i+1}{file_ext}"
                    
                    # 将 chunk 转为字节流
                    data_buffer = io.BytesIO()
                    if file_ext == ".csv":
                        chunk.to_csv(data_buffer, index=False, header=False, encoding='utf-8-sig')
                    else:
                        chunk.to_excel(data_buffer, index=False, header=False, engine='openpyxl')
                    
                    # 写入 ZIP
                    zf.writestr(part_filename, data_buffer.getvalue())
            
            zip_buffer.seek(0)
            
            st.download_button(
                label=f"📥 下载 ZIP 压缩包 (内含 {split_count} 个文件)",
                data=zip_buffer,
                file_name="split_result.zip",
                mime="application/zip"
            )
            
            # 显示分包详情
            with st.expander("查看分包详情"):
                for i, chunk in enumerate(chunks):
                    st.text(f"文件 {i+1}: {len(chunk)} 行")

        else:
            # === 单文件模式 ===
            output = io.BytesIO()
            if file_ext == ".csv":
                df_final.to_csv(output, index=False, header=False, encoding='utf-8-sig')
            else:
                df_final.to_excel(output, index=False, header=False, engine='openpyxl')
            
            output.seek(0)
            
            st.download_button(
                label="📥 下载最终结果 (无表头)",
                data=output,
                file_name=f"cleaned_result{file_ext}",
                mime=mime_type
            )

    except Exception as e:
        st.error(f"发生错误: {e}")
