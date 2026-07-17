# 实验 5-1：用代码生成工具提升数学解题能力

《深入理解 AI Agent》配套实验（★★）。验证一个结论：给 Agent 配上能执行代码的
Python 沙箱后，它在竞赛数学题上的准确率会**显著高于**纯思维链（Chain-of-Thought, CoT）。

## 目的

大模型「心算」大数、枚举、因式分解时极易出错——不是不会方法，而是算错。
本实验让同一个模型（默认 `gpt-4o-mini`）在同一组题上跑两种模式，直接对比：

- **纯 CoT**：只能用自然语言一步步推理，禁止写代码；
- **代码辅助**：把题目形式化为 Python（sympy 符号计算、numpy 矩阵、scipy 数值求解），
  通过 function calling 调用 `run_python` 工具在**子进程沙箱**里执行，用精确结果替代心算。

## 原理

```
题目 ──► 模型
          │  纯 CoT：直接自然语言推理 ─────────────► 最终答案（易算错）
          │
          └─ 代码辅助：生成 Python 代码
                       │  function calling
                       ▼
                 run_python 工具（子进程沙箱，预装 sympy/numpy/scipy，超时保护）
                       │  返回 stdout
                       ▼
                 模型基于精确结果继续推理 ──────────► 最终答案（更准）
```

- 工具用 OpenAI **function calling** 暴露：模型自主决定何时写代码、写什么代码。
- 沙箱是 `sandbox.py` 里的 `run_python()`：把代码写入临时文件，用子进程执行，
  带 20 秒超时，崩溃/死循环不影响主进程。预导入了 `sympy / numpy / scipy`。
- 题目在 `problems.json`：11 道 AIME 风格竞赛题，**答案均为整数、已用暴力枚举离线校验**，
  覆盖数论、模运算、丢番图方程、生成函数、素因子分解、格点计数等。

## 运行

```bash
pip install -r requirements.txt
cp env.example .env   # 或直接 export OPENAI_API_KEY=...
export OPENAI_API_KEY=sk-...      # 也支持 MOONSHOT_API_KEY / ARK_API_KEY

python demo.py                    # 跑完整对照实验
python demo.py --verbose          # 额外打印模型生成的代码与执行结果
python demo.py --limit 3          # 只跑前 3 题（省钱调试）
```

可用环境变量：`OPENAI_API_KEY`（或 `MOONSHOT_API_KEY` / `ARK_API_KEY`）、
`OPENAI_BASE_URL`（切换兼容端点）、`MODEL`（默认 `gpt-4o-mini`）。

## 结论

真实跑 `gpt-4o-mini` 的结果（11 题，`temperature=0`）：

| 模式 | 准确率 |
| --- | --- |
| 纯 CoT | 4/11 ≈ 36% |
| 代码辅助 | 11/11 = 100% |

代码辅助模式准确率**显著更高**。纯 CoT 在需要大量枚举 / 大数运算的题上频繁算错
（如「C(2000,1000) 的最大三位素因子」「1..1000 中恰有 6 个约数的数」「x²+y²<400 的格点数」），
而代码辅助模式把这些交给 sympy/numpy 精确计算，逐题命中。

> 注：竞赛题本就是为了区分算力设计的，纯 CoT 会稳定地在「大计算量」题上翻车，
> 因此本实验的差距是稳定复现的，而非偶然。具体逐题结果见下方运行输出。

## 文件

| 文件 | 说明 |
| --- | --- |
| `demo.py` | 主程序：对照实验 + function calling 循环 + 结果表 |
| `sandbox.py` | 子进程 Python 沙箱（`run_python`，超时保护，预装数学库） |
| `problems.json` | 11 道竞赛题（题面 + 已校验的整数真值 + 考点） |
| `requirements.txt` | 依赖 |
| `env.example` | 环境变量样例 |
