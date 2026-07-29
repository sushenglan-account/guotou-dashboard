# -*- coding: utf-8 -*-
"""国投开发管理一体化平台 - Streamlit 应用
三个页面：系统建设情况看板 / 项目履约情况 / 资金计划情况
"""

import json
import re
import math
from datetime import datetime, timedelta
from collections import OrderedDict, Counter

import streamlit as st
import pandas as pd

# ============================================================
# 数据加载
# ============================================================

@st.cache_data
def load_data():
    with open("data.js", "r", encoding="utf-8") as f:
        js_content = f.read()
    match = re.search(r"const PROJECT_DATA = (\[.*?\]);", js_content, re.DOTALL)
    data = json.loads(match.group(1))
    # 转为 DataFrame
    df = pd.DataFrame(data)
    # 日期列处理
    for col in ["contract_sign_date", "launch_date", "acceptance_date", "deadline"]:
        df[col] = df[col].apply(lambda x: None if (not x or x == "None") else x)
    return df


# ============================================================
# 常量与辅助函数
# ============================================================

COMPLETED_PHASES = ["上线试运行", "交付验收", "运维完成"]

PLATFORM_ORDER = [
    "财务管控与共享服务一体化平台",
    "人力资源与党建文化一体化平台",
    "基础设施",
    "网络安全",
    "专项服务",
]

PLATFORM_SHORT = {
    "财务管控与共享服务一体化平台": "财务管控",
    "人力资源与党建文化一体化平台": "人资党建",
    "基础设施": "基础设施",
    "网络安全": "网络安全",
    "专项服务": "专项服务",
}

PHASE_COLORS = {
    "立项审批": ("#1890ff", "#e6f7ff"),
    "需求分析": ("#1890ff", "#e6f7ff"),
    "需求调研": ("#1890ff", "#e6f7ff"),
    "系统设计": ("#722ed1", "#f9f0ff"),
    "方案设计": ("#722ed1", "#f9f0ff"),
    "开发实施": ("#fa8c16", "#fff7e6"),
    "方案评审": ("#fa8c16", "#fff7e6"),
    "测试验收": ("#52c41a", "#f6ffed"),
    "交付验收": ("#52c41a", "#f6ffed"),
    "上线试运行": ("#13c2c2", "#e6fffb"),
    "运维实施": ("#eb2f96", "#fff0f6"),
    "运维验收": ("#eb2f96", "#fff0f6"),
    "运维完成": ("#f5222d", "#fff1f0"),
}

# 合同阶段名称
STAGE_NAMES = {
    3: ["合同签署", "项目启动", "项目验收"],
    4: ["合同签署", "项目启动", "项目中期", "项目验收"],
    5: ["合同签署", "项目启动", "需求调研", "开发实施", "项目验收"],
    6: ["合同签署", "项目启动", "需求调研", "开发实施", "测试验收", "项目验收"],
}

PAY_RATIOS = {
    3: [0.30, 0.40, 0.30],
    4: [0.20, 0.30, 0.30, 0.20],
    5: [0.20, 0.15, 0.30, 0.25, 0.10],
    6: [0.15, 0.15, 0.20, 0.20, 0.20, 0.10],
}


def format_money(value):
    """格式化金额"""
    if value is None:
        return "¥0"
    value = float(value)
    if value >= 100_000_000:
        return f"¥{value / 100_000_000:.1f}亿"
    elif value >= 10_000:
        return f"¥{value / 10_000:.0f}万"
    return f"¥{value:,.0f}"


def format_money_wan(value):
    """格式化金额（万元）"""
    if value is None:
        return "¥0万"
    return f"¥{value / 10_000:.0f}万"


def format_date(date_str):
    if not date_str or str(date_str) == "None" or pd.isna(date_str):
        return "-"
    return str(date_str).split(" ")[0]


def get_quarter(dt):
    if dt is None or (isinstance(dt, float) and math.isnan(dt)):
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt.split(" ")[0], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    elif not isinstance(dt, datetime):
        return None
    m = dt.month
    if m <= 3:
        return 1
    elif m <= 6:
        return 2
    elif m <= 9:
        return 3
    return 4


def map_date_to_year(date_val, target_year):
    """将日期映射到目标年份（保留月日）"""
    if date_val is None or (isinstance(date_val, float) and math.isnan(date_val)):
        return None
    if isinstance(date_val, str):
        try:
            dt = datetime.strptime(date_val.split(" ")[0], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    elif isinstance(date_val, datetime):
        dt = date_val
    else:
        return None
    return datetime(target_year, dt.month, dt.day)


def generate_contract_stages(project_row):
    """生成合同履约阶段数据"""
    stage_count = int(project_row["contract_stages"])
    names = STAGE_NAMES.get(stage_count, STAGE_NAMES[4])
    ratios = PAY_RATIOS.get(stage_count, PAY_RATIOS[4])
    paid_stages = int(project_row["paid_stages"])

    sign_date = project_row["contract_sign_date"]
    if sign_date and not (isinstance(sign_date, float) and math.isnan(sign_date)):
        try:
            base_date = datetime.strptime(str(sign_date).split(" ")[0], "%Y-%m-%d")
        except (ValueError, TypeError):
            base_date = datetime(2024, 1, 1)
    else:
        base_date = datetime(2024, 1, 1)

    launch_date = project_row["launch_date"]
    if launch_date and not (isinstance(launch_date, float) and math.isnan(launch_date)):
        try:
            end_date = datetime.strptime(str(launch_date).split(" ")[0], "%Y-%m-%d")
        except (ValueError, TypeError):
            end_date = base_date + timedelta(days=180)
    else:
        end_date = base_date + timedelta(days=180)

    stages = []
    for i in range(stage_count):
        if i < paid_stages:
            status, status_color = "已完成", "green"
        elif i == paid_stages:
            status, status_color = "进行中", "orange"
        else:
            status, status_color = "未开始", "gray"

        if stage_count > 0:
            stage_date = base_date + (end_date - base_date) * ((i + 1) / stage_count)
        else:
            stage_date = base_date

        stages.append({
            "name": names[i] if i < len(names) else f"阶段{i + 1}",
            "ratio": f"{ratios[i] * 100:.0f}%",
            "date": stage_date.strftime("%Y-%m-%d"),
            "status": status,
            "status_color": status_color,
        })
    return stages


def generate_payment_plan(project_row):
    """生成付款计划数据"""
    stage_count = int(project_row["contract_stages"])
    ratios = PAY_RATIOS.get(stage_count, PAY_RATIOS[4])
    paid_stages = int(project_row["paid_stages"])
    contract_amount = float(project_row["contract_amount"])

    sign_date = project_row["contract_sign_date"]
    if sign_date and not (isinstance(sign_date, float) and math.isnan(sign_date)):
        try:
            base_date = datetime.strptime(str(sign_date).split(" ")[0], "%Y-%m-%d")
        except (ValueError, TypeError):
            base_date = datetime(2024, 1, 1)
    else:
        base_date = datetime(2024, 1, 1)

    launch_date = project_row["launch_date"]
    if launch_date and not (isinstance(launch_date, float) and math.isnan(launch_date)):
        try:
            end_date = datetime.strptime(str(launch_date).split(" ")[0], "%Y-%m-%d")
        except (ValueError, TypeError):
            end_date = base_date + timedelta(days=180)
    else:
        end_date = base_date + timedelta(days=180)

    plans = []
    for i in range(stage_count):
        amount = round(contract_amount * ratios[i])
        if i < paid_stages:
            status, status_color = "已收款", "green"
        elif project_row["project_phase"] == "运维完成" and i == paid_stages:
            status, status_color = "逾期", "red"
        else:
            status, status_color = "未到期", "gray"

        if stage_count > 0:
            stage_date = base_date + (end_date - base_date) * ((i + 1) / stage_count)
        else:
            stage_date = base_date

        plans.append({
            "name": f"第{i + 1}期款项 ({ratios[i] * 100:.0f}%)",
            "amount": amount,
            "date": stage_date.strftime("%Y-%m-%d"),
            "status": status,
            "status_color": status_color,
        })
    return plans


# ============================================================
# 页面 1：系统建设情况看板
# ============================================================

def render_dashboard(df):
    st.markdown("### 系统建设情况看板")

    # --- 筛选区 ---
    with st.container():
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        with col_d1:
            date_start = st.date_input("验收日期起", value=None, key="dash_date_start")
            date_end = st.date_input("验收日期止", value=None, key="dash_date_end")
        with col_d2:
            project_types = sorted(df["project_type"].unique().tolist())
            selected_type = st.selectbox("项目类型", ["全部"] + project_types, key="dash_type")
        with col_d3:
            all_phases = sorted(df["project_phase"].unique().tolist())
            in_progress_phases = [p for p in all_phases if p not in COMPLETED_PHASES]
            status_options = ["进行中（默认）"] + all_phases
            selected_status = st.multiselect("项目状态", status_options, default=["进行中（默认）"], key="dash_status")
        with col_d4:
            st.write("")  # 占位
            if st.button("重置筛选", key="dash_reset"):
                st.rerun()

    # 应用筛选
    filtered = df.copy()

    if date_start or date_end:
        filtered = filtered[filtered["acceptance_date"].notna()]
        if date_start:
            filtered = filtered[filtered["acceptance_date"].apply(
                lambda x: x.split(" ")[0] >= date_start.isoformat() if x else False
            )]
        if date_end:
            filtered = filtered[filtered["acceptance_date"].apply(
                lambda x: x.split(" ")[0] <= date_end.isoformat() if x else False
            )]

    if selected_type != "全部":
        filtered = filtered[filtered["project_type"] == selected_type]

    # 处理"进行中"
    actual_phases = set()
    has_in_progress = any("进行中（默认）" in s for s in selected_status)
    for s in selected_status:
        if s == "进行中（默认）":
            actual_phases.update(in_progress_phases)
        else:
            actual_phases.add(s)

    if actual_phases:
        filtered = filtered[filtered["project_phase"].isin(actual_phases)]

    # --- 汇总指标卡 ---
    total = len(filtered)
    completed = filtered["project_phase"].isin(COMPLETED_PHASES).sum()
    unfinished = total - completed
    contract_total = filtered["contract_amount"].sum()
    paid_total = filtered["paid_amount"].sum()
    unpaid_total = filtered["unpaid_amount"].sum()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("项目总数量", f"{total}")
    with c2:
        st.metric("已完成项目", f"{completed}")
    with c3:
        st.metric("未完成项目", f"{unfinished}")
    with c4:
        st.metric("已付款金额", format_money(paid_total))
    with c5:
        st.metric("待付款金额", format_money(unpaid_total))
    with c6:
        st.metric("合同总金额", format_money(contract_total))

    st.markdown("---")

    # --- 表格区域 ---
    st.markdown("#### 项目明细（按平台/系统分组）")

    for platform in PLATFORM_ORDER:
        plat_df = filtered[filtered["platform"] == platform]
        if plat_df.empty:
            continue

        platform_contract = plat_df["contract_amount"].sum()
        platform_paid = plat_df["paid_amount"].sum()
        platform_unpaid = plat_df["unpaid_amount"].sum()

        with st.expander(
            f"**{platform}** ({len(plat_df)}个项目 | "
            f"合同: {format_money(platform_contract)} | "
            f"已付: {format_money(platform_paid)} | "
            f"待付: {format_money(platform_unpaid)})",
            expanded=True,
        ):
            systems = plat_df["system"].unique()
            for system in systems:
                sys_df = plat_df[plat_df["system"] == system].sort_values("row")
                sys_contract = sys_df["contract_amount"].sum()
                sys_paid = sys_df["paid_amount"].sum()
                sys_unpaid = sys_df["unpaid_amount"].sum()

                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;├ **{system}** "
                    f"({len(sys_df)}个项目 | "
                    f"合同: {format_money(sys_contract)} | "
                    f"已付: {format_money(sys_paid)} | "
                    f"待付: {format_money(sys_unpaid)})"
                )

                # 详情表
                display_df = sys_df[[
                    "project_name", "project_type", "project_phase",
                    "contract_amount", "paid_amount", "unpaid_amount", "supplier"
                ]].copy()
                display_df.columns = [
                    "项目名称", "类型", "阶段", "合同金额", "已付款", "待付款", "供应商"
                ]
                display_df["合同金额"] = display_df["合同金额"].apply(format_money)
                display_df["已付款"] = display_df["已付款"].apply(format_money)
                display_df["待付款"] = display_df["待付款"].apply(format_money)

                st.dataframe(display_df, use_container_width=True, hide_index=True)


# ============================================================
# 页面 2：项目履约情况
# ============================================================

def render_page2(df):
    st.markdown("### 项目履约情况")

    # --- 筛选区 ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        date_start = st.date_input("上线日期起", value=None, key="p2_date_start")
        date_end = st.date_input("上线日期止", value=None, key="p2_date_end")
    with col2:
        project_types = sorted(df["project_type"].unique().tolist())
        selected_type = st.selectbox("项目类型", ["全部"] + project_types, key="p2_type")
    with col3:
        platforms = get_platform_order(df)
        selected_platform = st.selectbox("平台", ["全部"] + platforms, key="p2_platform")
    with col4:
        suppliers = sorted(df["supplier"].unique().tolist())
        selected_supplier = st.selectbox("供应商", ["全部"] + suppliers, key="p2_supplier")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        all_phases = sorted(df["project_phase"].unique().tolist())
        in_progress_phases = [p for p in all_phases if p not in COMPLETED_PHASES]
        status_options = ["进行中（默认）"] + all_phases
        selected_status = st.multiselect("项目状态", status_options, default=["进行中（默认）"], key="p2_status")
    with col_s2:
        if st.button("重置筛选", key="p2_reset"):
            st.rerun()

    # 应用筛选
    filtered = df.copy()

    if date_start or date_end:
        filtered = filtered[filtered["launch_date"].notna()]
        if date_start:
            filtered = filtered[filtered["launch_date"].apply(
                lambda x: x.split(" ")[0] >= date_start.isoformat() if x else False
            )]
        if date_end:
            filtered = filtered[filtered["launch_date"].apply(
                lambda x: x.split(" ")[0] <= date_end.isoformat() if x else False
            )]

    if selected_type != "全部":
        filtered = filtered[filtered["project_type"] == selected_type]
    if selected_platform != "全部":
        filtered = filtered[filtered["platform"] == selected_platform]
    if selected_supplier != "全部":
        filtered = filtered[filtered["supplier"] == selected_supplier]

    actual_phases = set()
    for s in selected_status:
        if s == "进行中（默认）":
            actual_phases.update(in_progress_phases)
        else:
            actual_phases.add(s)

    if actual_phases:
        filtered = filtered[filtered["project_phase"].isin(actual_phases)]

    # --- 汇总指标卡 ---
    contract_total = filtered["contract_amount"].sum()
    paid_total = filtered["paid_amount"].sum()
    payable_total = filtered["stage_payable"].sum()
    unpaid_total = filtered["unpaid_amount"].sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("合同总金额", format_money(contract_total))
    with c2:
        st.metric("已付款金额", format_money(paid_total))
    with c3:
        st.metric("应付款金额", format_money(payable_total))
    with c4:
        st.metric("待付款金额", format_money(unpaid_total))

    st.markdown("---")

    # --- 表格 ---
    st.markdown(f"#### 项目列表（共 {len(filtered)} 条）")

    page_size = st.selectbox("每页显示", [15, 30, 50, 100], index=0, key="p2_page_size")
    total_pages = max(1, math.ceil(len(filtered) / page_size))
    page_num = st.number_input("页码", min_value=1, max_value=total_pages, value=1, key="p2_page_num")

    start_idx = (page_num - 1) * page_size
    end_idx = start_idx + page_size
    page_data = filtered.iloc[start_idx:end_idx]

    # 显示表格
    display_df = page_data[[
        "row", "platform", "system", "project_name", "project_phase",
        "contract_amount", "paid_amount", "stage_payable", "unpaid_amount"
    ]].copy()
    display_df.columns = [
        "编号", "平台", "系统", "项目名称", "阶段",
        "合同金额", "已付", "应付", "待付"
    ]
    display_df["合同金额"] = display_df["合同金额"].apply(format_money)
    display_df["已付"] = display_df["已付"].apply(format_money)
    display_df["应付"] = display_df["应付"].apply(format_money)
    display_df["待付"] = display_df["待付"].apply(format_money)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # --- 项目详情 ---
    st.markdown("---")
    st.markdown("#### 项目详情（选择项目查看履约信息）")

    project_options = page_data.apply(
        lambda r: f"[{int(r['row'])}] {r['project_name']}", axis=1
    ).tolist()

    if project_options:
        selected_idx = st.selectbox("选择项目", range(len(project_options)),
                                    format_func=lambda i: project_options[i],
                                    key="p2_selected_project")
        selected_row = page_data.iloc[selected_idx]

        col_detail1, col_detail2 = st.columns([2, 3])

        with col_detail1:
            st.markdown("##### 项目基本信息")
            info_data = {
                "平台": selected_row["platform"],
                "系统": selected_row["system"],
                "项目名称": selected_row["project_name"],
                "项目类型": selected_row["project_type"],
                "项目阶段": selected_row["project_phase"],
                "供应商": selected_row["supplier"],
                "合同签署日期": format_date(selected_row["contract_sign_date"]),
                "计划上线日期": format_date(selected_row["launch_date"]),
                "合同阶段数": f"{int(selected_row['contract_stages'])}",
                "已付款阶段": f"{int(selected_row['paid_stages'])} / {int(selected_row['contract_stages'])}",
                "合同金额": format_money(selected_row["contract_amount"]),
                "已付款金额": format_money(selected_row["paid_amount"]),
                "待付款金额": format_money(selected_row["unpaid_amount"]),
            }
            for k, v in info_data.items():
                st.text(f"{k}: {v}")

        with col_detail2:
            # 合同履约情况
            st.markdown("##### 合同履约情况")
            contract_stages = generate_contract_stages(selected_row)
            cs_df = pd.DataFrame([
                {
                    "阶段名称": s["name"],
                    "付款比例": s["ratio"],
                    "计划完成时间": s["date"],
                    "状态": s["status"],
                }
                for s in contract_stages
            ])
            st.dataframe(cs_df, use_container_width=True, hide_index=True)

            st.markdown("##### 合同收款情况")
            payment_plans = generate_payment_plan(selected_row)
            pp_df = pd.DataFrame([
                {
                    "款项名称": p["name"],
                    "金额": format_money(p["amount"]),
                    "应收日期": p["date"],
                    "状态": p["status"],
                }
                for p in payment_plans
            ])
            st.dataframe(pp_df, use_container_width=True, hide_index=True)
    else:
        st.info("当前筛选条件下无项目数据")


# ============================================================
# 页面 3：资金计划情况
# ============================================================

def render_page3(df):
    st.markdown("### 资金计划情况")

    # --- 筛选区 ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        dimension = st.radio(
            "时间维度",
            ["月度", "季度", "年中", "年底"],
            index=1,
            horizontal=True,
            key="p3_dimension"
        )
    with col2:
        year = st.selectbox("查询年份", [2026, 2025, 2024, 2023], key="p3_year")
    with col3:
        platforms = ["全部"] + df["platform"].unique().tolist()
        selected_platform = st.selectbox("平台", platforms, key="p3_platform")
    with col4:
        if selected_platform != "全部":
            sys_options = ["全部"] + df[df["platform"] == selected_platform]["system"].unique().tolist()
        else:
            sys_options = ["全部"] + df["system"].unique().tolist()
        selected_system = st.selectbox("系统", sys_options, key="p3_system")

    # 应用筛选
    filtered = df.copy()
    if selected_platform != "全部":
        filtered = filtered[filtered["platform"] == selected_platform]
    if selected_system != "全部":
        filtered = filtered[filtered["system"] == selected_system]

    # 确定选中的季度/月
    if dimension == "年中":
        selected_quarter = 2
    elif dimension == "年底":
        selected_quarter = 4
    else:
        selected_quarter = st.session_state.get("p3_quarter", 2)

    # 统一定义季度映射（避免月度/季度分支作用域问题）
    quarter_names = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
    quarter_ranges = {1: "1-3月", 2: "4-6月", 3: "7-9月", 4: "10-12月"}

    # --- 季度概览卡 ---
    if dimension == "月度":
        st.markdown("#### 月度概览")
        month_stats = calculate_month_stats(year, filtered)
        cols = st.columns(6)
        for i in range(12):
            m = i + 1
            stat = month_stats[m]
            with cols[i % 6]:
                if st.button(
                    f"{m}月\n{stat['count']}个项目\n{format_money(stat['amount'])}",
                    key=f"p3_month_{m}",
                    use_container_width=True,
                    type="primary" if m == st.session_state.get("p3_month", 4) else "secondary",
                ):
                    st.session_state["p3_month"] = m
                    st.session_state["p3_quarter"] = get_quarter(datetime(year, m, 1))
                    st.rerun()
        selected_month = st.session_state.get("p3_month", 4)
        selected_quarter = get_quarter(datetime(year, selected_month, 1))
    else:
        st.markdown("#### 季度概览")
        quarter_stats = calculate_quarter_stats(year, filtered)
        cols = st.columns(4)
        for i, q in enumerate([1, 2, 3, 4]):
            stat = quarter_stats[q]
            with cols[i]:
                if st.button(
                    f"{quarter_names[q]} ({quarter_ranges[q]})\n"
                    f"{stat['count']}个项目\n{format_money(stat['amount'])}",
                    key=f"p3_quarter_{q}",
                    use_container_width=True,
                    type="primary" if q == selected_quarter else "secondary",
                ):
                    st.session_state["p3_quarter"] = q
                    st.rerun()

    st.markdown("---")

    # --- 三栏布局 ---
    if dimension == "月度":
        # 月度视图也需要计算 quarter_stats 用于项目分布展示
        quarter_stats = calculate_quarter_stats(year, filtered)
    st.markdown(f"#### {quarter_names.get(selected_quarter, 'Q2')} 项目分布")
    quarter_stat = quarter_stats.get(selected_quarter, {"launch": [], "acceptance": [], "deadline": []})

    col_left, col_mid, col_right = st.columns(3)

    with col_left:
        st.markdown(f"**🔵 计划上线项目（{len(quarter_stat['launch'])}个）**")
        for item in quarter_stat["launch"]:
            st.markdown(
                f"<div style='border-left:3px solid #1890ff; padding:6px 10px; margin-bottom:6px;'>"
                f"<div style='font-size:12px; color:#1890ff;'>{item['system']}</div>"
                f"<div style='font-size:13px;'>{item['project_name']}</div>"
                f"<div style='font-size:12px; color:#999;'>"
                f"{item['date']} | <span style='color:#f5222d; font-weight:600;'>{format_money_wan(item['stage_payable'])}</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        if not quarter_stat["launch"]:
            st.info("暂无数据")

    with col_mid:
        st.markdown(f"**🟢 计划阶段验收项目（{len(quarter_stat['acceptance'])}个）**")
        for item in quarter_stat["acceptance"]:
            st.markdown(
                f"<div style='border-left:3px solid #52c41a; padding:6px 10px; margin-bottom:6px;'>"
                f"<div style='font-size:12px; color:#52c41a;'>{item['system']}</div>"
                f"<div style='font-size:13px;'>{item['project_name']}</div>"
                f"<div style='font-size:12px; color:#999;'>"
                f"{item['date']} | <span style='color:#f5222d; font-weight:600;'>{format_money_wan(item['stage_payable'])}</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        if not quarter_stat["acceptance"]:
            st.info("暂无数据")

    with col_right:
        st.markdown(f"**🟣 计划竣工验收项目（{len(quarter_stat['deadline'])}个）**")
        for item in quarter_stat["deadline"]:
            st.markdown(
                f"<div style='border-left:3px solid #722ed1; padding:6px 10px; margin-bottom:6px;'>"
                f"<div style='font-size:12px; color:#722ed1;'>{item['system']}</div>"
                f"<div style='font-size:13px;'>{item['project_name']}</div>"
                f"<div style='font-size:12px; color:#999;'>"
                f"{item['date']} | <span style='color:#f5222d; font-weight:600;'>{format_money_wan(item['stage_payable'])}</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        if not quarter_stat["deadline"]:
            st.info("暂无数据")

    st.markdown("---")

    # --- 付款计划汇总表 ---
    st.markdown(f"#### 付款计划汇总表（{quarter_names.get(selected_quarter, 'Q2')} 按月分解）")

    quarter_months_map = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}
    months = quarter_months_map.get(selected_quarter, [4, 5, 6])

    # 计算月度数据
    data_by_type = {"上线": {}, "阶段验收": {}, "竣工验收": {}}
    for m in months:
        data_by_type["上线"][m] = 0
        data_by_type["阶段验收"][m] = 0
        data_by_type["竣工验收"][m] = 0

    for _, row in filtered.iterrows():
        mapped_launch = map_date_to_year(row["launch_date"], year)
        mapped_acceptance = map_date_to_year(row["acceptance_date"], year)
        mapped_deadline = map_date_to_year(row["deadline"], year)
        stage_payable = float(row["stage_payable"]) if row["stage_payable"] else 0

        if mapped_launch and mapped_launch.month in months:
            data_by_type["上线"][mapped_launch.month] += stage_payable
        if mapped_acceptance and mapped_acceptance.month in months:
            data_by_type["阶段验收"][mapped_acceptance.month] += stage_payable
        if mapped_deadline and mapped_deadline.month in months:
            data_by_type["竣工验收"][mapped_deadline.month] += stage_payable

    # 构建表格
    table_data = []
    for event_type, monthly_data in data_by_type.items():
        row_data = {"类型": event_type}
        total = 0
        for m in months:
            val = monthly_data[m]
            row_data[f"{m}月"] = format_money_wan(val)
            total += val
        row_data["季度合计"] = format_money_wan(total)
        table_data.append(row_data)

    # 合计行
    total_row = {"类型": "合计"}
    grand_total = 0
    for m in months:
        month_total = sum(data_by_type[t][m] for t in data_by_type)
        total_row[f"{m}月"] = format_money_wan(month_total)
        grand_total += month_total
    total_row["季度合计"] = format_money_wan(grand_total)
    table_data.append(total_row)

    summary_df = pd.DataFrame(table_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)


def get_platform_order(df):
    """获取数据中实际存在的平台，按预定义顺序排列"""
    existing = set(df["platform"].unique())
    return [p for p in PLATFORM_ORDER if p in existing]


def calculate_quarter_stats(year, df):
    """计算季度统计数据"""
    stats = {
        1: {"count": 0, "amount": 0, "launch": [], "acceptance": [], "deadline": []},
        2: {"count": 0, "amount": 0, "launch": [], "acceptance": [], "deadline": []},
        3: {"count": 0, "amount": 0, "launch": [], "acceptance": [], "deadline": []},
        4: {"count": 0, "amount": 0, "launch": [], "acceptance": [], "deadline": []},
    }

    seen_projects = {1: set(), 2: set(), 3: set(), 4: set()}

    for _, row in df.iterrows():
        stage_payable = float(row["stage_payable"]) if row["stage_payable"] else 0

        for date_col, event_key in [
            ("launch_date", "launch"),
            ("acceptance_date", "acceptance"),
            ("deadline", "deadline"),
        ]:
            mapped = map_date_to_year(row[date_col], year)
            if mapped:
                q = get_quarter(mapped)
                if q:
                    stats[q][event_key].append({
                        "system": row["system"],
                        "project_name": row["project_name"],
                        "date": mapped.strftime("%Y-%m-%d"),
                        "stage_payable": stage_payable,
                        "row": int(row["row"]),
                    })
                    seen_projects[q].add(int(row["row"]))

    for q in [1, 2, 3, 4]:
        stats[q]["count"] = len(seen_projects[q])
        all_items = stats[q]["launch"] + stats[q]["acceptance"] + stats[q]["deadline"]
        unique_rows = set()
        amount = 0
        for item in all_items:
            if item["row"] not in unique_rows:
                unique_rows.add(item["row"])
                amount += item["stage_payable"]
        stats[q]["amount"] = amount

    return stats


def calculate_month_stats(year, df):
    """计算月度统计数据"""
    stats = {}
    for i in range(1, 13):
        stats[i] = {"count": 0, "amount": 0, "launch": [], "acceptance": [], "deadline": []}

    seen_projects = {i: set() for i in range(1, 13)}

    for _, row in df.iterrows():
        stage_payable = float(row["stage_payable"]) if row["stage_payable"] else 0

        for date_col, event_key in [
            ("launch_date", "launch"),
            ("acceptance_date", "acceptance"),
            ("deadline", "deadline"),
        ]:
            mapped = map_date_to_year(row[date_col], year)
            if mapped:
                m = mapped.month
                stats[m][event_key].append({
                    "system": row["system"],
                    "project_name": row["project_name"],
                    "date": mapped.strftime("%Y-%m-%d"),
                    "stage_payable": stage_payable,
                    "row": int(row["row"]),
                })
                seen_projects[m].add(int(row["row"]))

    for m in range(1, 13):
        stats[m]["count"] = len(seen_projects[m])
        all_items = stats[m]["launch"] + stats[m]["acceptance"] + stats[m]["deadline"]
        unique_rows = set()
        amount = 0
        for item in all_items:
            if item["row"] not in unique_rows:
                unique_rows.add(item["row"])
                amount += item["stage_payable"]
        stats[m]["amount"] = amount

    return stats


# ============================================================
# 主应用
# ============================================================

def main():
    st.set_page_config(
        page_title="国投开发管理一体化平台",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 自定义样式
    st.markdown("""
    <style>
    .main-header {
        background-color: #001529;
        color: white;
        padding: 12px 24px;
        border-radius: 4px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .main-header h1 {
        font-size: 18px;
        margin: 0;
    }
    .main-header .logo {
        width: 36px;
        height: 36px;
        background-color: #1890ff;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 16px;
    }
    [data-testid="stMetric"] {
        background-color: #fff;
        padding: 12px 16px;
        border-radius: 4px;
        border-left: 4px solid #1890ff;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    [data-testid="stMetric"]:nth-child(2) { border-left-color: #52c41a; }
    [data-testid="stMetric"]:nth-child(3) { border-left-color: #fa8c16; }
    [data-testid="stMetric"]:nth-child(4) { border-left-color: #f5222d; }
    [data-testid="stMetric"]:nth-child(5) { border-left-color: #722ed1; }
    [data-testid="stMetric"]:nth-child(6) { border-left-color: #262626; }
    </style>
    """, unsafe_allow_html=True)

    # 顶部标题
    st.markdown("""
    <div class="main-header">
        <div class="logo">国</div>
        <h1>国投开发管理一体化平台</h1>
    </div>
    """, unsafe_allow_html=True)

    # 加载数据
    df = load_data()

    # 侧边栏导航
    st.sidebar.markdown("### 导航菜单")
    page = st.sidebar.radio(
        "选择页面",
        ["系统建设情况看板", "项目履约情况", "资金计划情况"],
        key="nav_page"
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 数据概览")
    st.sidebar.metric("项目总数", len(df))
    st.sidebar.metric("合同总额", format_money(df["contract_amount"].sum()))
    st.sidebar.metric("供应商数", df["supplier"].nunique())

    # 页面路由
    if page == "系统建设情况看板":
        render_dashboard(df)
    elif page == "项目履约情况":
        render_page2(df)
    elif page == "资金计划情况":
        render_page3(df)


if __name__ == "__main__":
    main()
