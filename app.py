import streamlit as st
import pandas as pd
import io

# === 网页配置 ===
st.set_page_config(page_title="数据清洗小工具", page_icon="🧹")

st.title("🧹 自动化数据清洗助手")
st.write("上传你的 Excel 或 CSV 文件，自动删除空行、重复行以及过长的单词。")

# === 侧边栏：设置 ===
st.sidebar.header("⚙️ 设置")
max_len = st.sidebar.slider("最大单词长度限制", min_value=1, max_value=20, value=6)
col_index = st.sidebar.selectbox("单词在哪一列？", [0, 1, 2, 3], format_func=lambda x: f"第 {x+1} 列")

# === 1. 文件上传 ===
uploaded_file = st.file_uploader("请选择文件 (支持 .xlsx, .csv)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    # 读取文件
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, dtype=str)
        else:
            df = pd.read_excel(uploaded_file, dtype=str)
        
        st.success("✅ 文件读取成功！")
        
        # 显示原始数据状态
        st.subheader("📊 原始数据预览")
        col1, col2 = st.columns(2)
        col1.metric("原始行数", len(df))
        st.dataframe(df.head())

        # === 2. 执行清洗逻辑 ===
        # A. 删除空行
        df_clean = df.dropna(how='any')
        # B. 删除重复
        df_clean = df_clean.drop_duplicates()
        
        # C. 过滤长度
        # 获取用户选择的那一列
        target_col_name = df_clean.columns[col_index]
        
        # 确保是字符串并过滤
        df_final = df_clean[df_clean[target_col_name].str.strip().str.len() <= max_len]
        
        # 计算删除了多少
        removed_count = len(df) - len(df_final)

        st.markdown("---")
        st.subheader("✨ 清洗结果")
        
        col3, col4, col5 = st.columns(3)
        col3.metric("剩余行数", len(df_final))
        col4.metric("删除了脏数据", removed_count, delta_color="inverse")
        col5.metric("当前设定长度", f"≤ {max_len}")

        st.dataframe(df_final.head())

        # === 3. 下载按钮 ===
        # 将结果转换为二进制流以便下载
        output = io.BytesIO()
        if uploaded_file.name.endswith('.csv'):
            df_final.to_csv(output, index=False, encoding='utf-8-sig')
            mime_type = "text/csv"
            file_ext = ".csv"
        else:
            df_final.to_excel(output, index=False, engine='openpyxl')
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            file_ext = ".xlsx"
        
        output.seek(0)
        
        st.download_button(
            label="📥 下载清洗后的文件",
            data=output,
            file_name="cleaned_data" + file_ext,
            mime=mime_type
        )

    except Exception as e:
        st.error(f"发生错误：{e}")
        st.info("提示：请检查你的 Excel 文件是否加密，或者格式是否正确。")
