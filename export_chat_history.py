#!/usr/bin/env python3
"""
千帆/DuMate 对话记录与任务导出脚本
从 opencode.db SQLite 数据库导出：
1. 每个会话导出为 Markdown 文件（人类可读）
2. 全部数据导出为 JSON 文件（完整保留）
3. 任务清单汇总导出为单独 Markdown
"""

import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta

DB_PATH = "/Users/sushenglan/Library/Application Support/qianfan-desktop-app/qianfan_desk_xdg/d20f9967641d4235ad3d03e9942bf08a/data/opencode/opencode.db"
OUTPUT_DIR = "/Users/sushenglan/.qianfan/workspace/d20f9967641d4235ad3d03e9942bf08a/chat_export"

CST = timezone(timedelta(hours=8))

def ts_to_str(ts):
    """毫级时间戳转可读时间"""
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(ts / 1000, tz=CST).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(ts)

def safe_filename(name):
    """生成安全的文件名"""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return safe[:80] if len(safe) > 80 else safe

def parse_part_data(data_str):
    """解析 part 的 data JSON"""
    try:
        return json.loads(data_str)
    except:
        return {"type": "raw", "text": data_str}

def parse_message_data(data_str):
    """解析 message 的 data JSON"""
    try:
        return json.loads(data_str)
    except:
        return {"role": "unknown"}

def format_part_for_markdown(part_data, indent=""):
    """将 part 格式化为 Markdown 文本"""
    ptype = part_data.get("type", "")
    text = part_data.get("text", "")
    visibility = part_data.get("visibility", "")

    if ptype == "text" and text:
        return f"{text}"
    
    elif ptype == "reasoning" and text:
        if visibility == "hidden":
            return None  # 跳过隐藏的 reasoning
        return f"> [思考过程]\n> {text}"

    elif ptype == "tool":
        tool_name = part_data.get("tool", "unknown")
        call_id = part_data.get("callID", "")
        state = part_data.get("state", {})
        status = state.get("status", "")
        input_data = state.get("input", {})
        output = state.get("output", "")
        error = state.get("error", "")

        lines = [f"**[工具调用: {tool_name}]** (状态: {status})"]
        
        if input_data:
            # Truncate very long inputs
            input_str = json.dumps(input_data, ensure_ascii=False, indent=2)
            if len(input_str) > 2000:
                input_str = input_str[:2000] + "\n... (已截断)"
            lines.append(f"  输入:\n```\n{input_str}\n```")
        
        if output:
            output_str = str(output)
            if len(output_str) > 2000:
                output_str = output_str[:2000] + "\n... (已截断)"
            lines.append(f"  输出:\n```\n{output_str}\n```")
        
        if error:
            lines.append(f"  错误: {error}")
        
        return "\n".join(lines)

    elif ptype == "step-start":
        return None  # 跳过 step-start 标记
    
    elif ptype == "step-finish":
        return None  # 跳过 step-finish 标记

    elif ptype == "file":
        name = part_data.get("name", "")
        path = part_data.get("path", "")
        return f"[文件: {name}] ({path})"

    elif ptype == "file-export":
        name = part_data.get("name", "")
        path = part_data.get("path", "")
        return f"[导出文件: {name}] ({path})"

    elif ptype == "raw":
        return text if text else None

    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sessions_dir = os.path.join(OUTPUT_DIR, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ============ 1. 导出会话列表 ============
    cursor.execute("""
        SELECT id, title, time_created, time_updated, time_archived, source
        FROM session 
        WHERE time_deleted IS NULL
        ORDER BY time_created ASC
    """)
    sessions = cursor.fetchall()
    print(f"找到 {len(sessions)} 个会话")

    all_data = {
        "export_time": datetime.now(tz=CST).isoformat(),
        "total_sessions": len(sessions),
        "sessions": []
    }
    all_todos = []

    session_index = []

    for i, sess in enumerate(sessions):
        sid = sess["id"]
        title = sess["title"] or "未命名会话"
        created = ts_to_str(sess["time_created"])
        updated = ts_to_str(sess["time_updated"])
        archived = ts_to_str(sess["time_archived"]) if sess["time_archived"] else None
        source = sess["source"]

        print(f"  [{i+1}/{len(sessions)}] {title} ({created})")

        # 获取该会话的所有消息
        cursor.execute("""
            SELECT id, time_created, data
            FROM message
            WHERE session_id = ? AND time_deleted IS NULL
            ORDER BY time_created ASC
        """, (sid,))
        messages = cursor.fetchall()

        # 获取该会话的所有 todo
        cursor.execute("""
            SELECT content, status, priority, position, time_created, time_updated
            FROM todo
            WHERE session_id = ? AND time_deleted IS NULL
            ORDER BY position ASC
        """, (sid,))
        todos = cursor.fetchall()

        session_data = {
            "id": sid,
            "title": title,
            "time_created": created,
            "time_updated": updated,
            "time_archived": archived,
            "source": source,
            "message_count": len(messages),
            "todo_count": len(todos),
            "messages": [],
            "todos": []
        }

        # 构建 Markdown
        md_lines = [
            f"# {title}",
            f"",
            f"- 会话ID: `{sid}`",
            f"- 创建时间: {created}",
            f"- 最后更新: {updated}",
        ]
        if archived:
            md_lines.append(f"- 归档时间: {archived}")
        md_lines.append(f"- 消息数: {len(messages)}")
        if todos:
            md_lines.append(f"- 任务数: {len(todos)}")
        md_lines.append(f"\n---\n")

        # 写入任务清单
        if todos:
            md_lines.append("## 任务清单\n")
            for t in todos:
                status_icon = {"completed": "[x]", "in_progress": "[~]", "pending": "[ ]"}.get(t["status"], "[ ]")
                priority_label = f" ({t['priority']})" if t["priority"] else ""
                md_lines.append(f"- {status_icon} {t['content']}{priority_label}")
                
                session_data["todos"].append({
                    "content": t["content"],
                    "status": t["status"],
                    "priority": t["priority"],
                    "position": t["position"],
                    "time_created": ts_to_str(t["time_created"]),
                    "time_updated": ts_to_str(t["time_updated"]),
                })
                all_todos.append({
                    "session_id": sid,
                    "session_title": title,
                    "content": t["content"],
                    "status": t["status"],
                    "priority": t["priority"],
                    "time_created": ts_to_str(t["time_created"]),
                    "time_updated": ts_to_str(t["time_updated"]),
                })
            md_lines.append(f"\n---\n")

        # 写入对话内容
        md_lines.append("## 对话记录\n")

        for msg in messages:
            mid = msg["id"]
            msg_time = ts_to_str(msg["time_created"])
            msg_data = parse_message_data(msg["data"])
            role = msg_data.get("role", "unknown")
            model = msg_data.get("modelID", "")
            
            role_label = {"user": "用户", "assistant": "DuMate"}.get(role, role)
            
            # 获取该消息的所有 part
            cursor.execute("""
                SELECT id, time_created, data
                FROM part
                WHERE message_id = ? AND time_deleted IS NULL
                ORDER BY time_created ASC
            """, (mid,))
            parts = cursor.fetchall()

            msg_parts_data = []
            content_lines = []

            for part in parts:
                pd = parse_part_data(part["data"])
                msg_parts_data.append(pd)
                formatted = format_part_for_markdown(pd)
                if formatted:
                    content_lines.append(formatted)

            if not content_lines:
                content_lines = ["(无内容)"]

            # 写入消息
            header = f"### {role_label}"
            if model:
                header += f" ({model})"
            header += f" — {msg_time}"
            
            md_lines.append(header)
            md_lines.append("")
            md_lines.append("\n\n".join(content_lines))
            md_lines.append("")

            session_data["messages"].append({
                "id": mid,
                "role": role,
                "time": msg_time,
                "model": model,
                "parts": msg_parts_data,
            })

        # 写入 Markdown 文件
        safe_title = safe_filename(title)
        seq = str(i + 1).zfill(3)
        md_filename = f"{seq}_{safe_title}.md"
        md_path = os.path.join(sessions_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        session_index.append({
            "seq": i + 1,
            "title": title,
            "created": created,
            "messages": len(messages),
            "todos": len(todos),
            "file": md_filename,
        })

        all_data["sessions"].append(session_data)

    # ============ 2. 写入索引文件 ============
    index_path = os.path.join(OUTPUT_DIR, "00_会话索引.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# 对话记录导出索引\n\n")
        f.write(f"- 导出时间: {datetime.now(tz=CST).strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- 会话总数: {len(sessions)}\n")
        f.write(f"- 消息总数: {sum(s['message_count'] for s in all_data['sessions'])}\n")
        f.write(f"- 任务总数: {len(all_todos)}\n")
        f.write(f"\n各会话文件位于 `sessions/` 目录下。\n\n")
        f.write("| # | 会话标题 | 创建时间 | 消息数 | 任务数 |\n")
        f.write("|---|---------|---------|--------|--------|\n")
        for s in session_index:
            f.write(f"| {s['seq']} | {s['title']} | {s['created']} | {s['messages']} | {s['todos']} |\n")

    # ============ 3. 写入任务汇总 ============
    if all_todos:
        todos_path = os.path.join(OUTPUT_DIR, "01_任务汇总.md")
        with open(todos_path, "w", encoding="utf-8") as f:
            f.write("# 任务汇总\n\n")
            f.write(f"- 导出时间: {datetime.now(tz=CST).strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- 任务总数: {len(all_todos)}\n\n")
            
            # 按状态分组
            by_status = {}
            for t in all_todos:
                by_status.setdefault(t["status"], []).append(t)
            
            status_names = {"completed": "已完成", "in_progress": "进行中", "pending": "待处理"}
            
            for status, name in status_names.items():
                if status in by_status:
                    items = by_status[status]
                    f.write(f"## {name} ({len(items)} 条)\n\n")
                    for t in items:
                        priority_label = f" [{t['priority']}]" if t["priority"] else ""
                        f.write(f"- **{t['content']}**{priority_label}\n")
                        f.write(f"  - 所属会话: {t['session_title']}\n")
                        f.write(f"  - 创建: {t['time_created']} | 更新: {t['time_updated']}\n\n")
            
            # 其他状态
            other_statuses = set(by_status.keys()) - set(status_names.keys())
            if other_statuses:
                f.write("## 其他\n\n")
                for status in other_statuses:
                    for t in by_status[status]:
                        f.write(f"- **{t['content']}** (状态: {status})\n")
                        f.write(f"  - 所属会话: {t['session_title']}\n\n")

    # ============ 4. 写入完整 JSON ============
    json_path = os.path.join(OUTPUT_DIR, "full_export.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    conn.close()

    print(f"\n导出完成！")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"  - 00_会话索引.md (索引)")
    if all_todos:
        print(f"  - 01_任务汇总.md (任务汇总)")
    print(f"  - full_export.json (完整JSON数据)")
    print(f"  - sessions/ ({len(sessions)} 个会话 Markdown 文件)")
    print(f"\n总计: {len(sessions)} 个会话, {sum(s['message_count'] for s in all_data['sessions'])} 条消息, {len(all_todos)} 条任务")

if __name__ == "__main__":
    main()
