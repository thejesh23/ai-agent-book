#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 5-2：用代码生成工具提升逻辑思考能力

对比同一个 LLM 在两种模式下求解「骑士与无赖」(Knights & Knaves) 谜题的准确率：

  1) 纯思考(pure)      —— 仅靠自然语言链式推理直接给出答案；
  2) 代码辅助(code)    —— 配备 Code Interpreter(预装 python-constraint)，
                          把谜题形式化为约束满足问题(CSP)，调用求解器搜索答案。

结论预期：约束求解把逻辑推理外包给确定性求解器，准确率应达 90%+，
且显著高于纯思考模式(纯思考在多人、含计数/自指的谜题上容易出错)。

用法：
    export OPENAI_API_KEY=sk-...
    python demo.py                 # 跑全部 12 题
    python demo.py --limit 4       # 只跑前 4 题(省钱冒烟测试)
    python demo.py --model gpt-4o-mini
"""
import argparse
import json
import os
import re
import sys

from openai import OpenAI

from sandbox import run_python

# ---- 读取 .env(如果存在)。避免额外依赖，手写一个极简解析器。----
def _load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

MODEL = os.environ.get("MODEL", "gpt-4o-mini")

# run_python 工具的 function calling 定义
TOOLS = [{
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "在预装了 python-constraint 库的沙箱中执行 Python 代码，返回 stdout/stderr。"
            "用它把逻辑谜题建模为约束满足问题并求解。记得用 print() 打印结果。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "要执行的完整 Python 代码"}
            },
            "required": ["code"],
        },
    },
}]

ANSWER_HINT = (
    '推理结束后，请在最后单独用一行输出 JSON 形式的最终答案，'
    '键为每个居民的名字，值为 "knight" 或 "knave"，例如：'
    '{"A": "knight", "B": "knave"}'
)

PURE_SYSTEM = (
    "你是逻辑推理专家。在「骑士与无赖」谜题中，骑士永远说真话，无赖永远说假话。"
    "请仅凭自己的推理，逐步分析每位居民的身份，找出满足所有陈述的唯一解。\n" + ANSWER_HINT
)

CODE_SYSTEM = (
    "你是逻辑推理专家，擅长把谜题转化为形式化约束并用代码求解。"
    "在「骑士与无赖」谜题中，骑士永远说真话，无赖永远说假话。\n"
    "请务必使用 run_python 工具，用 python-constraint 库把谜题建模为约束满足问题(CSP)来求解。\n\n"
    "【最关键的建模规则】不要把某人的陈述直接当成事实约束！"
    "正确做法是对每位居民 X 加一条【双条件(等价)约束】：\n"
    "    X 的布尔值  ==  (X 那句话在语义上为真)\n"
    "含义：X 是骑士(True) 当且仅当 他的话为真；X 是无赖(False) 当且仅当 他的话为假。\n"
    "这条规则对每一句话都适用，包括计数类('恰好有两个骑士')和自指类('我和 B 同类')的陈述——"
    "都要写成 `X == (那句话的真值表达式)`，绝不能把 `(那句话的真值表达式)` 单独当作硬约束。\n\n"
    "示例(设 True=骑士)：\n"
    "    from constraint import Problem\n"
    "    p = Problem()\n"
    "    for name in ['A','B','C']:\n"
    "        p.addVariable(name, [True, False])\n"
    "    # A 说'我们中恰好有一个骑士'  ->  A == ( (A+B+C)==1 )\n"
    "    p.addConstraint(lambda a,b,c: a == ((a+b+c)==1), ['A','B','C'])\n"
    "    # B 说'C 是无赖'             ->  B == (not C)\n"
    "    p.addConstraint(lambda b,c: b == (not c), ['B','C'])\n"
    "    # C 说'我和 A 是同一类人'     ->  C == (C == A)\n"
    "    p.addConstraint(lambda a,c: c == (c == a), ['A','C'])\n"
    "    for s in p.getSolutions():\n"
    "        print({k:('knight' if v else 'knave') for k,v in s.items()})\n\n"
    "步骤：1) 每人一个布尔变量；2) 每句话写成上面的双条件约束；"
    "3) 调用 getSolutions() 枚举所有解并 print。\n"
    "最终答案必须严格采用求解器打印出的解，不要用自己的直觉去推翻它。"
    "若求解器输出为空，说明约束建错了(很可能漏了双条件)，请检查并重跑。\n" + ANSWER_HINT
)


def parse_answer(text, names):
    """从模型输出里提取最后一个形如 {name: knight/knave} 的 JSON 答案。"""
    norm = {"knight": "knight", "knave": "knave", "骑士": "knight", "无赖": "knave"}
    # 找出所有 {...} 片段，从后往前尝试解析
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text))):
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        got = {}
        for n in names:
            if n not in obj:
                break
            v = str(obj[n]).strip().lower()
            v = norm.get(v, norm.get(str(obj[n]).strip(), None))
            if v is None:
                break
            got[n] = v
        else:
            return got
    return None


def call_model(client, system, user, use_tools):
    """跑一轮对话(含可能的多次工具调用)，返回 (最终文本, 使用的代码列表)。"""
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    codes = []
    for _ in range(8):  # 最多 8 轮，防止无限循环
        kwargs = dict(model=MODEL, messages=messages, temperature=0)
        if use_tools:
            kwargs.update(tools=TOOLS, tool_choice="auto")
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        if use_tools and msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                try:
                    code = json.loads(tc.function.arguments).get("code", "")
                except json.JSONDecodeError:
                    code = ""
                codes.append(code)
                result = run_python(code)
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": result})
            continue
        return msg.content or "", codes
    return "", codes


def run_mode(client, puzzles, mode):
    """跑一种模式，返回逐题记录列表。"""
    system = CODE_SYSTEM if mode == "code" else PURE_SYSTEM
    records = []
    for p in puzzles:
        text, codes = call_model(client, system, p["description"], mode == "code")
        pred = parse_answer(text, p["names"])
        correct = pred == p["solution"]
        records.append(dict(id=p["id"], num=p["num_people"], pred=pred,
                            gold=p["solution"], correct=correct,
                            codes=codes, text=text))
        mark = "✓" if correct else "✗"
        print(f"  [{mode:4}] {p['id']} ({p['num_people']}人) {mark}  "
              f"预测={pred}")
    return records


def main():
    global MODEL
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 题(0=全部)")
    args = ap.parse_args()
    MODEL = args.model

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("错误：请先设置 OPENAI_API_KEY 环境变量(可写入 .env)。")

    with open("puzzles.json", encoding="utf-8") as f:
        puzzles = json.load(f)
    if args.limit:
        puzzles = puzzles[:args.limit]

    client = OpenAI()
    print(f"模型：{MODEL}    题目数：{len(puzzles)}\n")

    print("== 纯思考(pure) ==")
    pure = run_mode(client, puzzles, "pure")
    print("\n== 代码辅助(code) ==")
    code = run_mode(client, puzzles, "code")

    # ---- 准确率对比表 ----
    pure_acc = sum(r["correct"] for r in pure) / len(pure)
    code_acc = sum(r["correct"] for r in code) / len(code)

    print("\n" + "=" * 60)
    print("准确率对比表")
    print("=" * 60)
    print(f"{'题号':<8}{'人数':<6}{'纯思考':<10}{'代码辅助':<10}")
    print("-" * 60)
    for rp, rc in zip(pure, code):
        print(f"{rp['id']:<8}{rp['num']:<6}"
              f"{('✓' if rp['correct'] else '✗'):<10}"
              f"{('✓' if rc['correct'] else '✗'):<10}")
    print("-" * 60)
    print(f"{'准确率':<8}{'':<6}"
          f"{pure_acc*100:>6.1f}%   {code_acc*100:>6.1f}%")
    print("=" * 60)
    print(f"\n纯思考   准确率: {pure_acc*100:.1f}%  "
          f"({sum(r['correct'] for r in pure)}/{len(pure)})")
    print(f"代码辅助 准确率: {code_acc*100:.1f}%  "
          f"({sum(r['correct'] for r in code)}/{len(code)})")
    print(f"提升: {(code_acc-pure_acc)*100:+.1f} 个百分点")

    # ---- 展示一题的约束建模代码与求解结果 ----
    sample = next((r for r in code if r["correct"] and r["codes"]), None)
    if sample:
        print("\n" + "=" * 60)
        print(f"示例：{sample['id']} 的约束建模代码(模型生成)")
        print("=" * 60)
        print(sample["codes"][0])
        print("-- 求解 & 最终答案 --")
        print(f"预测={sample['pred']}  真值={sample['gold']}")

    # 保存完整记录，便于复盘
    with open("last_run.json", "w", encoding="utf-8") as f:
        json.dump(dict(model=MODEL, pure=pure, code=code,
                       pure_acc=pure_acc, code_acc=code_acc),
                  f, ensure_ascii=False, indent=2)
    print("\n完整逐题记录已保存到 last_run.json")


if __name__ == "__main__":
    main()
