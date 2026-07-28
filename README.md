# 国投开发管理一体化平台

基于 Streamlit 构建的国投项目数据可视化看板系统。

## 功能

- **系统建设情况看板**：展示项目总体进展、资金情况
- **项目履约情况**：查看合同履约进度、付款计划
- **资金计划情况**：按季度/月度分析资金分布

## 数据源

- `data.js`：包含 42 个项目的完整模拟数据
- `streamlit_app.py`：Streamlit 应用主文件

## 部署方式

### 方式一：Streamlit Cloud（推荐）

1. Fork 本仓库到个人 GitHub 账号
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. 点击 "New app"
4. 选择本仓库、主分支、streamlit_app.py 文件
5. 点击 Deploy

### 方式二：本地运行

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### 方式三：Docker

```bash
docker run -p 8501:8501 \
  -v $(pwd):/app \
  streamlit/streamlit:latest \
  streamlit run /app/streamlit_app.py
```

## 技术栈

- Streamlit 1.58+
- Python 3.10+
- Pandas

## 数据验证

所有 42 行数据通过以下业务规则校验：
- 已付金额 + 待付金额 = 合同金额
- 已付阶段数 + 未付阶段数 = 合同阶段数
- 已付金额 <= 合同金额 × 60%
- 供应商最大占比 16.7%（远低于 30% 上限）
- 项目名称全局唯一
