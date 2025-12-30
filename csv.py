import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="CSV工具", page_icon="🔧", layout="wide")

# 初始化 session state
if 'main_df' not in st.session_state:
    st.session_state.main_df = None
if 'compare_df' not in st.session_state:
    st.session_state.compare_df = None

# 文件上传区域
col_file_left, col_file_right = st.columns(2)

with col_file_left:
    main_file = st.file_uploader("选择第一个CSV文件", type=['csv'], key="main_file")
    
    if main_file is not None:
        try:
            st.session_state.main_df = pd.read_csv(main_file, low_memory=False)
            st.success(f"✅ 文件加载成功！共 {len(st.session_state.main_df)} 行")
            st.write("**预览数据：**")
            st.dataframe(st.session_state.main_df.head(), width='stretch')
            st.write(f"**字段列表：** {', '.join(st.session_state.main_df.columns.tolist())}")
        except Exception as e:
            st.error(f"❌ 文件读取失败: {str(e)}")

with col_file_right:
    compare_file = st.file_uploader("选择第二个CSV文件（用于跨文件去重）", type=['csv'], key="compare_file")
    
    if compare_file is not None:
        try:
            st.session_state.compare_df = pd.read_csv(compare_file, low_memory=False)
            st.success(f"✅ 文件加载成功！共 {len(st.session_state.compare_df)} 行")
            st.write("**预览数据：**")
            st.dataframe(st.session_state.compare_df.head(), width='stretch')
            st.write(f"**字段列表：** {', '.join(st.session_state.compare_df.columns.tolist())}")
        except Exception as e:
            st.error(f"❌ 文件读取失败: {str(e)}")

st.markdown("---")

# 去重配置
if st.session_state.main_df is not None:
    # 去重模式选择
    dedup_mode = st.radio(
        "选择去重模式：",
        ["单文件去重", "双文件去重"],
        help="单文件去重：对第一个文件进行去重; 双文件去重：从第一个文件中删除在第二个文件中出现的记录."
    )
    
    col_dedup_left, col_dedup_right = st.columns(2)
    
    with col_dedup_left:
        st.write("**文件1 去重字段选择：**")
        main_available_columns = st.session_state.main_df.columns.tolist()
        main_selected_column = st.selectbox(
            "选择文件1用于去重的字段（单选）",
            main_available_columns,
            help="选择一个字段进行去重判断"
        )
    
    with col_dedup_right:
        if dedup_mode == "双文件去重" and st.session_state.compare_df is not None:
            st.write("**文件2 去重字段选择：**")
            compare_available_columns = st.session_state.compare_df.columns.tolist()
            compare_selected_columns = st.multiselect(
                "选择文件2用于去重的字段（可多选）",
                compare_available_columns,
                help="多个字段将与文件1的字段进行对比"
            )
        else:
            compare_selected_columns = []
    
    # 输出文件名设置
    st.write("**输出文件配置：**")
    col_output_left, col_output_right = st.columns(2)
    
    with col_output_left:
        output_filename = st.text_input(
            "输出文件名",
            value="result.csv",
            help="去重后的文件名"
        )
    
    with col_output_right:
        keep_option = st.selectbox(
            "保留哪条重复记录",
            ["first", "last", False],
            format_func=lambda x: "保留第一条" if x == "first" else "保留最后一条" if x == "last" else "删除所有重复",
            help="当发现重复记录时的处理方式"
        )
    
    st.markdown("---")
    
    # 执行去重
    if st.button("🚀 开始去重", type="primary", width='stretch'):
        if not main_selected_column:
            st.error("⚠️ 请至少选择文件1的一个去重字段")
        elif dedup_mode == "双文件去重" and st.session_state.compare_df is None:
            st.error("⚠️ 双文件去重模式需要上传第二个CSV文件")
        elif dedup_mode == "双文件去重" and not compare_selected_columns:
            st.error("⚠️ 请至少选择文件2的一个去重字段")
        else:
            with st.spinner("正在处理数据..."):
                try:
                    deduplicated_df = st.session_state.main_df.copy()
                    original_count = len(deduplicated_df)
                    
                    if dedup_mode == "单文件去重":
                        # 单文件去重
                        deduplicated_df = deduplicated_df.drop_duplicates(
                            subset=[main_selected_column],
                            keep=keep_option if keep_option != False else False
                        )
                        
                    else:
                        # 双文件去重
                        compare_df_copy = st.session_state.compare_df.copy()

                        # 为 main_df 创建临时键（单字段）
                        deduplicated_df['__temp_key__'] = deduplicated_df[main_selected_column].astype(str)

                        # 为 compare_df 的每个选中字段分别创建键，然后合并
                        keys_in_compare_df = set()
                        for compare_selected_column in compare_selected_columns:
                            keys_in_compare_df.update(compare_df_copy[compare_selected_column].astype(str).unique())

                        # 过滤掉在 compare_df 任意字段中存在的记录
                        deduplicated_df = deduplicated_df[~deduplicated_df['__temp_key__'].isin(keys_in_compare_df)]

                        # 删除临时列
                        deduplicated_df = deduplicated_df.drop(columns=['__temp_key__'])
                    
                    final_count = len(deduplicated_df)
                    removed_count = original_count - final_count
                    
                    # 显示结果
                    st.success("✅ 去重完成")
                    
                    col_result_left, col_result_middle, col_result_right, col_result_extra = st.columns(4)
                    col_result_left.metric("原始记录数", original_count)
                    col_result_middle.metric("去重后记录数", final_count)
                    col_result_right.metric("删除记录数", removed_count, delta=f"-{removed_count}")
                    col_result_extra.metric("重复方案占比", f"{removed_count/original_count*100:.2f}%")
                    
                    st.write("**数据预览：**")
                    st.dataframe(deduplicated_df.head(20), width='stretch')
                    
                    # 准备下载
                    csv_buffer = BytesIO()
                    deduplicated_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                    csv_buffer.seek(0)
                    
                    st.download_button(
                        label="🗂️ 下载文件",
                        data=csv_buffer,
                        file_name=output_filename,
                        mime="text/csv",
                        type="primary",
                        width='stretch'
                    )
                except Exception as e:
                    st.error(f"❌ 去重过程出错: {str(e)}")

else:
    st.info("👆 请先上传至少一个CSV文件开始使用")
