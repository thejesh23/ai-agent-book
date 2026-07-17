"""实验 5-1：用代码生成工具提升数学解题能力

对照实验：在同一组 AIME 风格竞赛数学题上，比较
  - 【纯思维链 CoT】：只靠自然语言推理，不能执行代码；
  - 【代码辅助】：把问题形式化为 Python（sympy 符号计算、scipy 数值优化、
     numpy 矩阵），在子进程沙箱执行，返回精确结果。

运行:  python demo.py
环境变量:
  OPENAI_API_KEY   （必填，也支持 MOONSHOT_API_KEY / ARK_API_KEY）
  OPENAI_BASE_URL  （可选，切换到兼容 OpenAI 协议的服务）
  MODEL            （可选，默认 gpt-4o-mini）
"""

import os
import re
import json
import argparse

from openai import OpenAI

from sandbox import run_python

# ---------------------------------------------------------------------------
# 配置：兼容多种可用的 OpenAI 协议 key
# ---------------------------------------------------------------------------

def build_client_and_model():
    """根据环境变量构造 OpenAI 客户端与默认模型名。

    优先级：OPENAI_API_KEY > MOONSHOT_API_KEY > ARK_API_KEY。
    这些服务都兼容 OpenAI 的 chat.completions + function calling 接口。
    """
    model = os.getenv("MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL")

    if os.getenv("OPENAI_API_KEY"):
        api_key = os.getenv("OPENAI_API_KEY")
    elif os.getenv("MOONSHOT_API_KEY"):
        api_key = os.getenv("MOONSHOT_API_KEY")
        base_url = base_url or "https://api.moonshot.cn/v1"
        model = os.getenv("MODEL", "kimi-k2-0905-preview")
    elif os.getenv("ARK_API_KEY"):
        api_key = os.getenv("ARK_API_KEY")
        base_url = base_url or "https://ark.cn-beijing.volces.com/api/v3"
        model = os.getenv("MODEL", "doubao-seed-1-6-250615")
    else:
        raise SystemExit(
            "未找到 API key，请设置 OPENAI_API_KEY（或 MOONSHOT_API_KEY / ARK_API_KEY）"
        )

    # 加上超时与重试：避免个别 API 调用长时间挂起导致整个评测卡死。
    _kw = {"api_key": api_key, "timeout": 60.0, "max_retries": 3}
    if base_url:
        _kw["base_url"] = base_url
    client = OpenAI(**_kw)
    return client, model


# ---------------------------------------------------------------------------
# 工具定义（function calling）
# ---------------------------------------------------------------------------

RUN_PYTHON_TOOL = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "在预装 sympy/numpy/scipy 的 Python 沙箱中执行代码，用于精确的数学计算。"
            "必须用 print() 打印你想看到的结果。适合符号计算、数论枚举、"
            "多项式展开、数值求解等。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 源码，用 print 输出结果。",
                }
            },
            "required": ["code"],
        },
    },
}

FINAL_INSTRUCTION = (
    "题目的答案是一个整数。请在最后单独用一行给出最终答案，格式严格为：\n"
    "FINAL ANSWER: <整数>"
)

COT_SYSTEM = (
    "你是一位数学竞赛高手。请仅用自然语言逐步推理来解题，"
    "不要编写或调用任何代码。\n" + FINAL_INSTRUCTION
)

CODE_SYSTEM = (
    "你是一位擅长用编程解题的数学竞赛高手。遇到需要计算的地方，"
    "请把问题形式化为 Python 代码，并调用 run_python 工具在沙箱中执行，"
    "用精确的计算结果替代心算。可以多次调用工具来验证。\n" + FINAL_INSTRUCTION
)


# ---------------------------------------------------------------------------
# 答案抽取
# ---------------------------------------------------------------------------

def extract_answer(text: str):
    """从模型输出中解析整数答案。优先匹配 FINAL ANSWER，退化到最后一个整数。"""
    if not text:
        return None
    m = list(re.finditer(r"FINAL ANSWER:\s*(-?\d+)", text, re.IGNORECASE))
    if m:
        return int(m[-1].group(1))
    # 退化：抓最后一个 \boxed{...} 或末尾整数
    m = list(re.finditer(r"\\boxed\{\s*(-?\d+)\s*\}", text))
    if m:
        return int(m[-1].group(1))
    nums = re.findall(r"-?\d+", text)
    return int(nums[-1]) if nums else None


# ---------------------------------------------------------------------------
# 单题求解
# ---------------------------------------------------------------------------

def solve(client, model, question, use_code, max_turns=8, verbose=False):
    """求解单题，返回 (预测整数答案, 使用的工具代码列表, 最终文本)。"""
    system = CODE_SYSTEM if use_code else COT_SYSTEM
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    tools = [RUN_PYTHON_TOOL] if use_code else None
    codes = []

    for _ in range(max_turns):
        kwargs = dict(model=model, messages=messages, temperature=0)
        if tools:
            kwargs["tools"] = tools
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            # 必须把 assistant 的 tool_calls 消息原样加回
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                    code = args.get("code", "")
                except json.JSONDecodeError:
                    code = ""
                codes.append(code)
                result = run_python(code) if code else "[错误] 未提供 code"
                if verbose:
                    print("\n--- 模型生成的代码 ---\n" + code)
                    print("--- 执行结果 ---\n" + result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
            continue  # 继续让模型基于工具结果推理

        # 没有工具调用 → 最终回答
        return extract_answer(msg.content), codes, (msg.content or "")

    # 超过最大轮次，做最后一次强制收尾
    messages.append(
        {"role": "user", "content": "请立刻给出：FINAL ANSWER: <整数>"}
    )
    resp = client.chat.completions.create(
        model=model, messages=messages, temperature=0
    )
    content = resp.choices[0].message.content or ""
    return extract_answer(content), codes, content


# ---------------------------------------------------------------------------
# 主流程：对照实验
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="实验 5-1 代码辅助 vs 纯 CoT")
    parser.add_argument("--verbose", action="store_true", help="打印模型代码与执行结果")
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 题（调试用）")
    args = parser.parse_args()

    client, model = build_client_and_model()
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "problems.json"), encoding="utf-8") as f:
        problems = json.load(f)
    if args.limit:
        problems = problems[: args.limit]

    print(f"模型: {model}   题目数: {len(problems)}\n")

    rows = []
    cot_correct = code_correct = 0
    for p in problems:
        q, truth = p["question"], p["answer"]
        print(f"[{p['id']:>2}] {p['topic']}  (真值={truth})")

        cot_pred, _, _ = solve(client, model, q, use_code=False, verbose=args.verbose)
        cot_ok = cot_pred == truth
        cot_correct += cot_ok

        code_pred, codes, _ = solve(
            client, model, q, use_code=True, verbose=args.verbose
        )
        code_ok = code_pred == truth
        code_correct += code_ok

        print(
            f"     纯CoT   预测={cot_pred!s:>8}  {'✓' if cot_ok else '✗'}"
            f"   |  代码辅助 预测={code_pred!s:>8}  {'✓' if code_ok else '✗'}"
            f"   (工具调用 {len(codes)} 次)"
        )
        rows.append((p["id"], p["topic"], truth, cot_pred, cot_ok, code_pred, code_ok))

    # ---- 汇总表 ----
    n = len(problems)
    print("\n" + "=" * 78)
    print("逐题对照结果")
    print("=" * 78)
    print(f"{'题号':<5}{'考点':<26}{'真值':>7}{'CoT预测':>10}{'':>4}{'代码预测':>10}{'':>4}")
    print("-" * 78)
    for pid, topic, truth, cp, co, dp, do in rows:
        print(
            f"{pid:<5}{topic:<26}{truth:>7}{str(cp):>10}{'✓' if co else '✗':>4}"
            f"{str(dp):>10}{'✓' if do else '✗':>4}"
        )
    print("-" * 78)
    print(
        f"{'准确率':<5}{'':<26}{'':>7}"
        f"{cot_correct}/{n} = {cot_correct/n:5.0%}".rjust(14)
        + f"{code_correct}/{n} = {code_correct/n:5.0%}".rjust(18)
    )
    print("=" * 78)
    print(
        f"\n结论：纯 CoT 准确率 {cot_correct/n:.0%}，代码辅助准确率 {code_correct/n:.0%}，"
        f"提升 {(code_correct-cot_correct)/n:+.0%}。"
    )


if __name__ == "__main__":
    main()
