# Memobase Agent with Kimi K3 for LOCOMO Benchmark

An advanced AI agent implementation featuring sophisticated memory management using the Memobase framework, powered by the Kimi K3 model, and evaluated on the LOCOMO (Long Context and Memory Optimization) benchmark.

## Features

### 🧠 Advanced Memory Management
- **Multiple Memory Types**:
  - **Episodic Memory**: Stores specific task experiences and interactions
  - **Semantic Memory**: Maintains general knowledge and facts
  - **Procedural Memory**: Learns and stores problem-solving patterns
  - **Working Memory**: Manages short-term task context

- **Memory Operations**:
  - Automatic memory compression when thresholds are exceeded
  - Memory consolidation and pattern extraction
  - Importance-based decay and retention
  - Clustering of related memories
  - Efficient retrieval based on relevance and recency

### 🚀 Kimi K3 Model Integration
- Utilizes Kimi K3, a ~2.8-trillion parameter Mixture-of-Experts model
- 32 billion active parameters per forward pass
- Optimized for agentic capabilities including:
  - Advanced tool use
  - Multi-step reasoning
  - Code synthesis
  - Long-context understanding (128k tokens)

### 📊 LOCOMO Benchmark
Comprehensive evaluation across multiple task categories:
- **Multi-turn Reasoning**: Complex problem-solving over multiple interactions
- **Long Context Q&A**: Information extraction from extensive documents
- **Task Planning**: Project and resource planning capabilities
- **Knowledge Integration**: Cross-domain synthesis and analysis
- **Tool Usage**: Effective utilization of external tools and APIs

## Installation

1. Clone the repository:
```bash
cd projects/week2/memobase
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp env.example .env
# Edit .env and add your Kimi API key
```

## Configuration

Edit `config.py` to customize:
- Model parameters (temperature, max tokens, etc.)
- Memory settings (thresholds, retention policies)
- Benchmark configurations
- Logging levels

## Usage

### Interactive Mode
Engage in conversation with the agent while it builds and uses memories:

```bash
python main.py --mode interactive
```

Available commands in interactive mode:
- `/help` - Show available commands
- `/memory` - Display memory statistics
- `/clear` - Clear working memory
- `/reset` - Reset conversation (preserves long-term memories)
- `/learn` - Trigger memory consolidation
- `/exit` - Exit interactive mode

### Benchmark Mode
Run the LOCOMO benchmark evaluation:

```bash
# Run full benchmark
python main.py --mode benchmark

# Run specific category
python main.py --mode benchmark --category multi_turn_reasoning

# Run limited number of tasks
python main.py --mode benchmark --num-tasks 5
```

### Demo Mode
Run pre-configured demonstration scenarios:

```bash
python main.py --mode demo
```

Demonstrations include:
- Memory retention across conversations
- Learning from experience
- Context management in long interactions

### Single Task Mode
Execute a specific task:

```bash
python main.py --mode task --task "Plan a 7-day trip to Japan with a $3000 budget"
```

### Additional Options
- `--api-key KEY` - Override the API key from environment
- `--no-memory` - Start with empty memory store
- `--verbose` - Enable detailed logging

## Architecture

### Memory Store (`agent.py`)
The `MemoryStore` class manages different memory types with:
- Persistent storage using pickle
- Memory compression and clustering
- Importance-based retrieval
- Time-based decay mechanisms

### Agent Core (`agent.py`)
The `MemobaseAgent` class provides:
- Message processing with memory context
- Learning from task outcomes
- Memory-aware response generation
- Performance metrics tracking

### Benchmark System (`locomo_benchmark.py`)
The `LOCOMOBenchmark` class implements:
- Task generation and management
- Response evaluation metrics
- Category-specific scoring
- Results persistence and analysis

## Memory Management Strategies

### Compression
When memory exceeds thresholds:
1. Sort memories by importance and recency
2. Keep high-importance memories
3. Compress low-importance memories into clusters
4. Store cluster summaries as compressed memories

### Consolidation
During idle or triggered consolidation:
1. Apply decay to all memories
2. Remove very low importance memories
3. Extract patterns from episodic memories
4. Create procedural memories from patterns

### Retrieval
When processing queries:
1. Search for relevant memories by content
2. Retrieve recent episodic memories
3. Include applicable procedural knowledge
4. Format memories for context inclusion

## Benchmark Results

Results are saved in `benchmark_results/` with:
- Task-level scores and timings
- Category-wise performance metrics
- Memory usage statistics
- Detailed error logs

## Development

### Adding Custom Tools
Extend the agent with custom tools by modifying the agent class:

```python
def add_tool(self, tool_name, tool_function):
    # Add tool registration logic
    pass
```

### Custom Memory Types
Add new memory types in `config.py`:

```python
MEMOBASE_CONFIG["memory_types"].append("custom_type")
```

### Extending Benchmark
Add custom benchmark tasks in `locomo_benchmark.py`:

```python
self.tasks.append(BenchmarkTask(
    id="custom_001",
    category="custom_category",
    query="Your custom task query",
    expected_capabilities=["capability1", "capability2"]
))
```

## Performance Optimization

### Memory Efficiency
- Batch memory operations for better performance
- Use compression for large memory stores
- Implement periodic consolidation
- Clear working memory after task completion

### Response Latency
- Pre-fetch likely memories
- Cache embedding computations
- Use parallel processing for memory search
- Optimize context window usage

## Troubleshooting

### Common Issues

1. **API Key Error**:
   - Ensure `KIMI_API_KEY` is set in `.env`
   - Verify API key validity

2. **Memory Overflow**:
   - Adjust `MAX_MEMORY_ENTRIES` in config
   - Enable more aggressive compression
   - Trigger manual consolidation

3. **Slow Performance**:
   - Reduce `MODEL_MAX_TOKENS`
   - Enable caching in config
   - Use category-specific benchmarks

## Contributing

Contributions are welcome! Areas for improvement:
- Additional memory compression algorithms
- Enhanced retrieval mechanisms
- New benchmark categories
- Performance optimizations
- Tool integrations

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Kimi K3 model by Moonshot AI
- Memobase framework concepts
- LOCOMO benchmark design inspirations
