## 部署到 Streamlit Cloud 的步骤

当前环境已准备就绪，由于需要你的 GitHub 账号授权，你需要在本地完成以下步骤：

### 步骤 1：创建 GitHub 仓库

1. 访问 [github.com/new](https://github.com/new)
2. 填写仓库信息：
   - **Repository name**: `guotou-dashboard`
   - **Description**: 国投开发管理一体化平台 - Streamlit 看板
   - 选择 **Public**（或 Private，Streamlit Cloud 支持两种）
   - 不勾选 "Add a README" 和 ".gitignore"
3. 点击 "Create repository"

### 步骤 2：初始化本地仓库并推送

打开终端，运行：

```bash
cd /Users/sushenglan/.qianfan/workspace/d20f9967641d4235ad3d03e9942bf08a

git init
git add streamlit_app.py data.js requirements.txt README.md .streamlit/
git commit -m "Initial commit: Streamlit dashboard for project management"

git branch -M main
git remote add origin https://github.com/你的用户名/guotou-dashboard.git
git push -u origin main
```

### 步骤 3：在 Streamlit Cloud 部署

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 点击 "New app" 按钮
3. 选择你的 GitHub 账号和 `guotou-dashboard` 仓库
4. 确保以下设置正确：
   - **Branch**: main
   - **Main file path**: streamlit_app.py
   - **App URL**: `guotou-dashboard`（可自定义）
5. 点击 "Deploy"

### 步骤 4：验证部署

等待约 2-3 分钟，Streamlit Cloud 会自动构建并部署。部署成功后，你会获得一个类似这样的链接：

```
https://guotou-dashboard-你的用户名.streamlit.app/
```

### 快速验证

部署后，访问应用，检查以下内容是否正常显示：

1. **左侧导航栏**有三个菜单项：系统建设情况看板 / 项目履约情况 / 资金计划情况
2. **首页指标卡**显示：42个项目、已付¥5191万、待付¥8459万、合同总额¥1.4亿
3. **项目表格**可按平台/系统分组展开
4. **筛选功能**正常工作（日期筛选、状态筛选、平台筛选）
5. **资金计划页面**季度概览卡片和月度分解表格显示正常

### 可选：设置自定义域名

如需使用自定义域名：
1. 在 Streamlit Cloud 应用设置中找到 "Custom domain"
2. 添加你的域名（如 `dashboard.yourcompany.com`）
3. 在 DNS 提供商处添加 CNAME 记录指向 Streamlit 提供的地址
4. 等待 DNS 生效（通常 24-48 小时）

### 更新应用

当你修改代码后，推送到 GitHub 仓库，Streamlit Cloud 会自动重新部署：

```bash
git add .
git commit -m "Update: fix data calculation"
git push
```

Streamlit Cloud 会在几分钟内自动更新你的应用。

---

**注意事项**：
- Streamlit Cloud 免费版本对资源有限制（1GB RAM、3GB 存储），但对于此应用足够
- 数据文件 `data.js` 约 27KB，完全在限制范围内
- 无需配置 secrets，应用完全公开
- 如需密码保护，在 Streamlit Cloud 设置中启用 "App visibility" -> "Private"
