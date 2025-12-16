import streamlit as st
import pandas as pd
import io

# === 网页配置 ===
st.set_page_config(page_title="纯净词书清洗工具", page_icon="🧼")

st.title("🧼 律动词书清洗工具 (去ID + 去表头)")
st.info("💡 自动执行：1. 删除前两列(User ID)  2. 过滤长度  3. 导出时不带表头")

# === 侧边栏：设置 ===
st.sidebar.header("⚙️ 设置")
max_len = st.sidebar.slider("保留的最大单词长度", 1, 50, 6)

# === 1. 文件上传 ===
uploaded_file = st.file_uploader("上传文件 (xlsx/csv)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        # 读取文件
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, dtype=str)
        else:
            df = pd.read_excel(uploaded_file, dtype=str)
        
        st.success(f"✅ 读取成功！原始数据: {len(df)} 行，{len(df.columns)} 列")

        # === 2. 核心清洗逻辑 ===
        if len(df.columns) < 3:
            st.error("❌ 表格列数不足 3 列，无法删除前两列！")
        else:
            # ✂️ A. 删除前两列 (只取第3列及后面的)
            df_clean = df.iloc[:, 2:]
            
            # 🧹 B. 删除空行 & 重复行
            df_clean = df_clean.dropna(how='any')
            df_clean = df_clean.drop_duplicates()

            # 📏 C. 长度过滤 (针对现在的第1列，即原来的第3列)
            target_col = df_clean.columns[0] # 获取列名用于索引
            # 过滤逻辑
            df_final = df_clean[df_clean[target_col].str.strip().str.len() <= max_len]
            
            # 统计
            removed = len(df) - len(df_final)

            # === 3. 结果展示 ===
            st.markdown("---")
            st.subheader("✨ 清洗结果预览 (前5行)")
            st.write("注意：下载的文件将**不包含**下方的灰色表头，只有纯数据。")
            st.dataframe(df_final.head())
            
            col1, col2 = st.columns(2)
            col1.metric("最终行数", len(df_final))
            col2.metric("已清洗掉", removed)

            # === 4. 下载逻辑 (关键修改：header=False) ===
            output = io.BytesIO()
            if uploaded_file.name.endswith('.csv'):
                # header=False 代表不写入表头
                df_final.to_csv(output, index=False, header=False, encoding='utf-8-sig')
                mime_type = "text/csv"
                ext = ".csv"
            else:
                # header=False 代表不写入表头
                df_final.to_excel(output, index=False, header=False, engine='openpyxl')
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ext = ".xlsx"
            
            output.seek(0)
            
            st.download_button(
                label="📥 下载纯净数据 (无表头)",
                data=output,
                file_name="clean_no_header" + ext,
                mime=mime_type
            )

    except Exception as e:
        st.error(f"发生错误: {e}")
