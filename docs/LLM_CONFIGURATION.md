# LLM Provider Configuration Guide

This guide explains how to configure P3-Edge to use different LLM providers (Ollama or Google Gemini).

## Overview

P3-Edge supports two LLM providers:

1. **Ollama** (Local) - Runs models locally on your machine
2. **Google Gemini** (Cloud) - Uses Google's Gemini API

## Quick Start

### Option 1: Ollama (Default - Local)

**Advantages:**
- Free to use
- Complete privacy (runs locally)
- No internet required after model download
- Lower latency

**Requirements:**
- Ollama installed ([ollama.com](https://ollama.com))
- At least 8GB RAM for 4B models
- GPU recommended but not required

**Setup:**
```bash
# 1. Install Ollama
# Visit https://ollama.com and follow installation instructions

# 2. Download the model
ollama pull gemma3n:e2b

# 3. Start Ollama server (if not already running)
ollama serve

# 4. Configure P3-Edge (default configuration)
# Edit config/app_config.json:
{
  "llm": {
    "provider": "ollama",
    "ollama": {
      "model": "gemma3n:e2b-it-q4_K_M",
      "base_url": "http://localhost:11434"
    }
  }
}
```

### Option 2: Google Gemini (Cloud)

**Advantages:**
- No local resources required
- Always up-to-date models
- Potentially better performance
- Access to latest Gemini models

**Requirements:**
- Google API key
- Internet connection
- Google Cloud account (with Gemini API enabled)

**Setup:**
```bash
# 1. Get Google API Key
# Visit https://aistudio.google.com/app/apikey
# Create and copy your API key

# 2. Set environment variable
export GOOGLE_API_KEY="your-api-key-here"

# On Windows:
# set GOOGLE_API_KEY=your-api-key-here

# 3. Install LangChain dependencies
pip install langchain-google-genai

# 4. Configure P3-Edge
# Edit config/app_config.json:
{
  "llm": {
    "provider": "gemini",
    "gemini": {
      "model": "gemini-2.0-flash-exp",
      "temperature": 0.7,
      "api_key_env": "GOOGLE_API_KEY"
    }
  }
}
```

## Configuration Details

### Configuration File Location

The configuration file is located at:
```
p3-edge/config/app_config.json
```

### Configuration Schema

```json
{
  "llm": {
    "provider": "ollama" | "gemini",
    "ollama": {
      "model": "string",
      "base_url": "string"
    },
    "gemini": {
      "model": "string",
      "temperature": number (0.0-1.0),
      "api_key_env": "string"
    }
  }
}
```

### Ollama Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `gemma3n:e2b-it-q4_K_M` | Ollama model name |
| `base_url` | string | `http://localhost:11434` | Ollama server URL |

**Available Models:**
- `gemma3n:e2b` - Gemma 3 2B (smallest, fastest)
- `gemma3n:e2b-it-q4_K_M` - Gemma 3 2B instruction-tuned, quantized
- `llama3.2:3b` - Llama 3.2 3B
- `mistral:7b` - Mistral 7B
- And many more from [ollama.com/library](https://ollama.com/library)

### Gemini Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `gemini-2.0-flash-exp` | Gemini model name |
| `temperature` | number | 0.7 | Sampling temperature (0.0-1.0) |
| `api_key_env` | string | `GOOGLE_API_KEY` | Environment variable for API key |

**Available Models:**
- `gemini-2.0-flash-exp` - Latest Gemini 2.0 Flash (experimental)
- `gemini-1.5-pro` - Gemini 1.5 Pro (most capable)
- `gemini-1.5-flash` - Gemini 1.5 Flash (fast and efficient)
- `gemini-1.0-pro` - Gemini 1.0 Pro (stable)

## Switching Between Providers

You can switch providers at any time by:

1. Editing the configuration file:
   ```bash
   # Change provider to gemini
   "provider": "gemini"

   # Or back to ollama
   "provider": "ollama"
   ```

2. Restarting the application

## Programmatic Configuration

You can also configure the LLM provider programmatically:

```python
from src.services.llm_factory import create_llm_service
from src.tools import ToolExecutor

# Option 1: Ollama
llm_service = create_llm_service(
    provider="ollama",
    model_name="gemma3n:e2b-it-q4_K_M",
    tool_executor=executor
)

# Option 2: Gemini
llm_service = create_llm_service(
    provider="gemini",
    model_name="gemini-2.0-flash-exp",
    api_key="your-api-key",
    tool_executor=executor,
    temperature=0.7
)
```

## Environment Variables

### For Gemini

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Your Google API key for Gemini |

Example:
```bash
# Linux/Mac
export GOOGLE_API_KEY="AIzaSy..."

# Windows
set GOOGLE_API_KEY=AIzaSy...

# Or add to .env file
echo "GOOGLE_API_KEY=AIzaSy..." >> .env
```

### For Ollama

No environment variables required.

## Feature Comparison

| Feature | Ollama | Gemini |
|---------|--------|--------|
| Function Calling | ✅ | ✅ |
| Multimodal (Images) | ✅ | ✅ |
| Streaming | ✅ | ⚠️ (Partial) |
| Offline Mode | ✅ | ❌ |
| Privacy | 🔒 Complete | ⚠️ Cloud-based |
| Cost | Free | Free tier + paid |
| Setup Complexity | Medium | Easy |
| Performance | GPU-dependent | Consistent |

## Troubleshooting

### Ollama Issues

**Issue: "Ollama server not running"**
```bash
# Start Ollama server
ollama serve
```

**Issue: "Model not found"**
```bash
# Download the model
ollama pull gemma3n:e2b-it-q4_K_M
```

**Issue: "Connection refused"**
- Check if Ollama is running: `curl http://localhost:11434/api/version`
- Verify base_url in config matches Ollama server

### Gemini Issues

**Issue: "Google API key not provided"**
```bash
# Set environment variable
export GOOGLE_API_KEY="your-key"
```

**Issue: "LangChain not installed"**
```bash
# Install dependencies
pip install langchain-google-genai
```

**Issue: "API quota exceeded"**
- Check your Google Cloud console for quota limits
- Consider upgrading to paid tier
- Switch to Ollama for unlimited local usage

## Performance Tips

### Ollama
- Use quantized models (q4_K_M, q5_K_M) for better performance
- Enable GPU acceleration if available
- Close other applications to free up RAM
- Consider larger models (7B+) for better quality if you have resources

### Gemini
- Use `gemini-2.0-flash-exp` for fastest responses
- Use `gemini-1.5-pro` for highest quality
- Adjust temperature (0.0-1.0) for creativity vs consistency
- Enable caching for repeated queries (reduces costs)

## Cost Considerations

### Ollama
- **Cost**: Free
- **Resources**: Requires local compute (GPU/CPU + RAM)
- **Operating Cost**: Electricity only

### Gemini
- **Free Tier**: 60 requests per minute
- **Paid**: $0.00025 per 1K characters (input/output)
- **Cost Estimate**: ~$0.10-$0.50 per day for typical usage
- **See**: [Google Gemini Pricing](https://ai.google.dev/pricing)

## Security Best Practices

### API Keys
- Never commit API keys to version control
- Use environment variables or encrypted config
- Rotate keys periodically
- Set up billing alerts

### Local Models
- Keep Ollama updated for security patches
- Use official models from Ollama library
- Monitor disk space for model storage

## Advanced Usage

### Custom Models

**Ollama:**
```bash
# Create custom model from Modelfile
ollama create my-model -f Modelfile
```

**Gemini:**
- Use fine-tuned models via Vertex AI
- Set custom endpoint in config

### Multiple Providers

You can switch providers dynamically:
```python
# In code
from src.services.llm_factory import create_llm_service

# Create both
ollama_service = create_llm_service("ollama")
gemini_service = create_llm_service("gemini", api_key="...")

# Use based on context
service = ollama_service if offline_mode else gemini_service
```

## Support

For issues or questions:
- **Ollama**: https://github.com/ollama/ollama/issues
- **Gemini**: https://ai.google.dev/gemini-api/docs
- **P3-Edge**: https://github.com/esemsc-ss2524/p3-edge/issues

## Updates

Check for updates regularly:
```bash
# Ollama
ollama list  # See installed models
ollama pull model:tag  # Update model

# Gemini
# No manual updates needed - always uses latest API

# P3-Edge
git pull origin main  # Update application
```
