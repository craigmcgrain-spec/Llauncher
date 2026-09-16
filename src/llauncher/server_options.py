"""llama-server option catalog.

Covers all option groups from `llama-server --help`
(upstream ggml-org/llama.cpp, tools/server/README.md):
common, sampling, server-specific, speculative, logging, multimodal.

Each spec drives one auto-generated form widget. Only non-default
(non-empty) values are emitted to the bash command.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OptionSpec:
    flag: str  # primary long flag, e.g. "--ctx-size"
    kind: str = "str"  # "bool" | "int" | "float" | "str" | "choice"
    default: str = ""  # display default (placeholder); "" = server default
    help: str = ""
    category: str = "Misc"
    short: str = ""  # e.g. "-c"
    choices: tuple[str, ...] = ()
    neg: str = ""  # negative flag when default is True, e.g. "--no-cache-prompt"
    default_on: bool = False  # checkbox starts checked
    env: str = ""


# category order for tabs
CATEGORIES = [
    "Model",
    "Context & Batch",
    "GPU & Offload",
    "Sampling",
    "Server Net",
    "Server Behavior",
    "Multimodal",
    "Speculative",
    "Tools & Agent",
    "Chat Template",
    "Logging",
    "Misc",
]

OPTIONS: list[OptionSpec] = [
    # ---------------- Model ----------------
    OptionSpec("--model", "str", "", "Model .gguf path to load (set via model picker below)", "Model", "-m", env="LLAMA_ARG_MODEL"),
    OptionSpec("--hf-repo", "str", "", "Hugging Face repo <user>/<model>[:quant] (auto-download)", "Model", "-hf", env="LLAMA_ARG_HF_REPO"),
    OptionSpec("--hf-file", "str", "", "Hugging Face model file (overrides quant)", "Model", env="LLAMA_ARG_HF_FILE"),
    OptionSpec("--hf-token", "str", "", "Hugging Face access token (default: $HF_TOKEN)", "Model", env="HF_TOKEN"),
    OptionSpec("--model-url", "str", "", "Model download URL", "Model", "-mu", env="LLAMA_ARG_MODEL_URL"),
    OptionSpec("--alias", "str", "", "Model name alias(es), comma-separated (API)", "Model", "-a", env="LLAMA_ARG_ALIAS"),
    OptionSpec("--tags", "str", "", "Model tags, comma-separated (informational)", "Model", env="LLAMA_ARG_TAGS"),
    OptionSpec("--lora", "str", "", "LoRA adapter path(s), comma-separated", "Model", env=""),
    OptionSpec("--lora-scaled", "str", "", "LoRA adapters with scaling FNAME:SCALE,...", "Model"),
    OptionSpec("--control-vector", "str", "", "Control vector file(s), comma-separated", "Model"),
    OptionSpec("--control-vector-scaled", "str", "", "Control vectors FNAME:SCALE,...", "Model"),
    OptionSpec("--control-vector-layer-range", "str", "", "Layer range 'START END' for control vectors", "Model"),
    OptionSpec("--mmproj", "str", "", "Multimodal projector file", "Model", "-mm", env="LLAMA_ARG_MMPROJ"),
    OptionSpec("--mmproj-url", "str", "", "Multimodal projector URL", "Model", "-mmu", env="LLAMA_ARG_MMPROJ_URL"),
    OptionSpec("--override-kv", "str", "", "Override model metadata KEY=TYPE:VALUE,...", "Model"),
    OptionSpec("--override-tensor", "str", "", "Override tensor buffer type PATTERN=TYPE,...", "Model", "-ot", env="LLAMA_ARG_OVERRIDE_TENSOR"),
    OptionSpec("--check-tensors", "bool", "", "Check tensor data for invalid values", "Model"),
    OptionSpec("--no-mmproj", "bool", "", "Disable multimodal projector (even with -hf)", "Model"),
    # ---------------- Context & Batch ----------------
    OptionSpec("--ctx-size", "int", "0", "Prompt context size (0 = from model)", "Context & Batch", "-c", env="LLAMA_ARG_CTX_SIZE"),
    OptionSpec("--n-predict", "int", "-1", "Tokens to predict (-1 = infinity)", "Context & Batch", "-n", env="LLAMA_ARG_N_PREDICT"),
    OptionSpec("--batch-size", "int", "2048", "Logical max batch size", "Context & Batch", "-b", env="LLAMA_ARG_BATCH"),
    OptionSpec("--ubatch-size", "int", "512", "Physical max batch size", "Context & Batch", "-ub", env="LLAMA_ARG_UBATCH"),
    OptionSpec("--keep", "int", "0", "Tokens to keep from initial prompt (-1 = all)", "Context & Batch"),
    OptionSpec("--swa-full", "bool", "", "Full-size SWA cache", "Context & Batch", env="LLAMA_ARG_SWA_FULL"),
    OptionSpec("--cache-type-k", "choice", "f16", "KV cache dtype for K", "Context & Batch", "-ctk",
               ("f32", "f16", "bf16", "q8_0", "q4_0", "q4_1", "iq4_nl", "q5_0", "q5_1"), env="LLAMA_ARG_CACHE_TYPE_K"),
    OptionSpec("--cache-type-v", "choice", "f16", "KV cache dtype for V", "Context & Batch", "-ctv",
               ("f32", "f16", "bf16", "q8_0", "q4_0", "q4_1", "iq4_nl", "q5_0", "q5_1"), env="LLAMA_ARG_CACHE_TYPE_V"),
    OptionSpec("--kv-offload", "bool", "", "KV cache offloading (default: enabled)", "Context & Batch", "-kvo",
               neg="--no-kv-offload", default_on=True, env="LLAMA_ARG_KV_OFFLOAD"),
    OptionSpec("--rope-scaling", "choice", "", "RoPE scaling: none | linear | yarn", "Context & Batch",
               ("none", "linear", "yarn"), env="LLAMA_ARG_ROPE_SCALING_TYPE"),
    OptionSpec("--rope-scale", "float", "", "RoPE context scaling factor", "Context & Batch", env="LLAMA_ARG_ROPE_SCALE"),
    OptionSpec("--rope-freq-base", "float", "", "RoPE base frequency (0 = from model)", "Context & Batch", env="LLAMA_ARG_ROPE_FREQ_BASE"),
    OptionSpec("--rope-freq-scale", "float", "", "RoPE freq scale factor (1/N)", "Context & Batch", env="LLAMA_ARG_ROPE_FREQ_SCALE"),
    OptionSpec("--yarn-orig-ctx", "int", "0", "YaRN original context size", "Context & Batch", env="LLAMA_ARG_YARN_ORIG_CTX"),
    OptionSpec("--yarn-ext-factor", "float", "-1", "YaRN extrapolation mix factor", "Context & Batch", env="LLAMA_ARG_YARN_EXT_FACTOR"),
    OptionSpec("--yarn-attn-factor", "float", "-1", "YaRN attention magnitude scale", "Context & Batch", env="LLAMA_ARG_YARN_ATTN_FACTOR"),
    OptionSpec("--yarn-beta-slow", "float", "-1", "YaRN high correction dim/alpha", "Context & Batch", env="LLAMA_ARG_YARN_BETA_SLOW"),
    OptionSpec("--yarn-beta-fast", "float", "-1", "YaRN low correction dim/beta", "Context & Batch", env="LLAMA_ARG_YARN_BETA_FAST"),
    OptionSpec("--pooling", "choice", "", "Embedding pooling type", "Context & Batch",
               ("none", "mean", "cls", "last", "rank"), env="LLAMA_ARG_POOLING"),
    OptionSpec("--embedding", "bool", "", "Embedding-only mode (dedicated models)", "Context & Batch", env="LLAMA_ARG_EMBEDDINGS"),
    OptionSpec("--embd-normalize", "int", "2", "Embedding normalisation (-1=none,0=max,1=taxicab,2=euclid)", "Context & Batch"),
    # ---------------- GPU & Offload ----------------
    OptionSpec("--gpu-layers", "str", "auto", "Layers in VRAM: number | auto | all", "GPU & Offload", "-ngl", env="LLAMA_ARG_N_GPU_LAYERS"),
    OptionSpec("--split-mode", "choice", "layer", "Split across GPUs", "GPU & Offload", "-sm",
               ("none", "layer", "row", "tensor"), env="LLAMA_ARG_SPLIT_MODE"),
    OptionSpec("--tensor-split", "str", "", "Per-GPU fractions, e.g. 3,1", "GPU & Offload", "-ts", env="LLAMA_ARG_TENSOR_SPLIT"),
    OptionSpec("--main-gpu", "int", "0", "Main GPU index", "GPU & Offload", "-mg", env="LLAMA_ARG_MAIN_GPU"),
    OptionSpec("--device", "str", "", "Offload devices, comma-separated (none = CPU)", "GPU & Offload", "-dev", env="LLAMA_ARG_DEVICE"),
    OptionSpec("--list-devices", "bool", "", "List devices and exit", "GPU & Offload"),
    OptionSpec("--fit", "choice", "on", "Fit unset args to device memory", "GPU & Offload", "-fit", ("on", "off"), env="LLAMA_ARG_FIT"),
    OptionSpec("--fit-target", "str", "1024", "Target margin MiB per device for --fit", "GPU & Offload", "-fitt", env="LLAMA_ARG_FIT_TARGET"),
    OptionSpec("--fit-ctx", "int", "4096", "Min ctx size settable by --fit", "GPU & Offload", "-fitc", env="LLAMA_ARG_FIT_CTX"),
    OptionSpec("--cpu-moe", "bool", "", "Keep all MoE weights on CPU", "GPU & Offload", "-cmoe", env="LLAMA_ARG_CPU_MOE"),
    OptionSpec("--n-cpu-moe", "int", "", "Keep first N MoE layers on CPU", "GPU & Offload", "-ncmoe", env="LLAMA_ARG_N_CPU_MOE"),
    OptionSpec("--n-cpu-ffn", "int", "", "Keep first N dense FFN layers on CPU", "GPU & Offload", "-ncffn", env="LLAMA_ARG_N_CPU_FFN"),
    OptionSpec("--op-offload", "bool", "", "Offload host tensor ops to device (default: on)", "GPU & Offload",
               neg="--no-op-offload", default_on=True),
    OptionSpec("--repack", "bool", "", "Weight repacking (default: on)", "GPU & Offload", neg="--no-repack", default_on=True, env="LLAMA_ARG_REPACK"),
    OptionSpec("--no-host", "bool", "", "Bypass host buffer (extra buffers)", "GPU & Offload", env="LLAMA_ARG_NO_HOST"),
    OptionSpec("--load-mode", "choice", "auto", "Model loading mode", "GPU & Offload", "-lm",
               ("auto", "none", "mmap", "mlock", "mmap+mlock", "dio"), env="LLAMA_ARG_LOAD_MODE"),
    OptionSpec("--lazy-mode", "choice", "auto", "On-demand tensor reads (needs mmap)", "GPU & Offload", "-lzm",
               ("on", "auto", "off"), env="LLAMA_ARG_LAZY_MODE"),
    OptionSpec("--flash-attn", "choice", "auto", "Flash Attention", "GPU & Offload", "-fa", ("on", "off", "auto"), env="LLAMA_ARG_FLASH_ATTN"),
    OptionSpec("--numa", "choice", "", "NUMA optimisation", "GPU & Offload",
               ("distribute", "isolate", "numactl"), env="LLAMA_ARG_NUMA"),
    OptionSpec("--threads", "int", "-1", "CPU threads for generation (-1 = auto)", "GPU & Offload", "-t", env="LLAMA_ARG_THREADS"),
    OptionSpec("--threads-batch", "int", "", "Threads for batch/prompt processing", "GPU & Offload", "-tb"),
    OptionSpec("--cpu-mask", "str", "", "CPU affinity mask (hex)", "GPU & Offload", "-C"),
    OptionSpec("--cpu-range", "str", "", "CPU affinity range lo-hi", "GPU & Offload", "-Cr"),
    OptionSpec("--cpu-strict", "choice", "0", "Strict CPU placement", "GPU & Offload", ("0", "1")),
    OptionSpec("--prio", "int", "0", "Thread priority -1..3", "GPU & Offload"),
    OptionSpec("--poll", "int", "50", "Polling level 0..100", "GPU & Offload"),
    # ---------------- Sampling ----------------
    OptionSpec("--temperature", "float", "0.8", "Temperature", "Sampling", short="--temp"),
    OptionSpec("--top-k", "int", "40", "Top-k (0 = disabled)", "Sampling", env="LLAMA_ARG_TOP_K"),
    OptionSpec("--top-p", "float", "0.95", "Top-p (1.0 = disabled)", "Sampling"),
    OptionSpec("--min-p", "float", "0.05", "Min-p (0.0 = disabled)", "Sampling"),
    OptionSpec("--top-n-sigma", "float", "-1", "Top-n-sigma (-1 = disabled)", "Sampling", short="--top-nsigma"),
    OptionSpec("--xtc-probability", "float", "0", "XTC probability (0 = disabled)", "Sampling"),
    OptionSpec("--xtc-threshold", "float", "0.1", "XTC threshold", "Sampling"),
    OptionSpec("--typical-p", "float", "1", "Locally typical p (1.0 = disabled)", "Sampling", short="--typical"),
    OptionSpec("--seed", "int", "-1", "RNG seed (-1 = random)", "Sampling", "-s"),
    OptionSpec("--samplers", "str", "", "Sampler order, ';'-separated", "Sampling"),
    OptionSpec("--repeat-last-n", "int", "64", "Last n tokens for penalties (0 = off)", "Sampling"),
    OptionSpec("--repeat-penalty", "float", "1", "Repeat penalty (1.0 = off)", "Sampling"),
    OptionSpec("--presence-penalty", "float", "0", "Presence penalty (0 = off)", "Sampling"),
    OptionSpec("--frequency-penalty", "float", "0", "Frequency penalty (0 = off)", "Sampling"),
    OptionSpec("--dry-multiplier", "float", "0", "DRY multiplier (0 = off)", "Sampling"),
    OptionSpec("--dry-base", "float", "1.75", "DRY base value", "Sampling"),
    OptionSpec("--dry-allowed-length", "int", "2", "DRY allowed length", "Sampling"),
    OptionSpec("--dry-penalty-last-n", "int", "64", "DRY penalty last n (0 = off)", "Sampling"),
    OptionSpec("--dry-sequence-breaker", "str", "", "DRY breaker ('none' = none)", "Sampling"),
    OptionSpec("--dynatemp-range", "float", "0", "Dynamic temp range (0 = off)", "Sampling"),
    OptionSpec("--dynatemp-exp", "float", "1", "Dynamic temp exponent", "Sampling"),
    OptionSpec("--mirostat", "choice", "0", "Mirostat sampling", "Sampling", ("0", "1", "2")),
    OptionSpec("--mirostat-lr", "float", "0.1", "Mirostat eta", "Sampling"),
    OptionSpec("--mirostat-ent", "float", "5", "Mirostat tau", "Sampling"),
    OptionSpec("--ignore-eos", "bool", "", "Ignore EOS token", "Sampling"),
    OptionSpec("--logit-bias", "str", "", "TOKEN_ID(+/-)BIAS, e.g. 15043+1", "Sampling", "-l"),
    OptionSpec("--grammar", "str", "", "Inline BNF grammar", "Sampling"),
    OptionSpec("--grammar-file", "str", "", "Grammar file path", "Sampling"),
    OptionSpec("--json-schema", "str", "", "Inline JSON schema", "Sampling", "-j"),
    OptionSpec("--json-schema-file", "str", "", "JSON schema file", "Sampling", "-jf"),
    # ---------------- Server Net ----------------
    OptionSpec("--host", "str", "127.0.0.1", "Listen IP (.sock = unix socket)", "Server Net", env="LLAMA_ARG_HOST"),
    OptionSpec("--port", "int", "8080", "Listen port", "Server Net", env="LLAMA_ARG_PORT"),
    OptionSpec("--reuse-port", "bool", "", "Allow multiple binds to same port", "Server Net", env="LLAMA_ARG_REUSE_PORT"),
    OptionSpec("--api-key", "str", "", "API key(s), comma-separated", "Server Net", env="LLAMA_API_KEY"),
    OptionSpec("--api-key-file", "str", "", "API keys file (one per line)", "Server Net", env="LLAMA_ARG_API_KEY_FILE"),
    OptionSpec("--ssl-key-file", "str", "", "SSL private key (PEM)", "Server Net", env="LLAMA_ARG_SSL_KEY_FILE"),
    OptionSpec("--ssl-cert-file", "str", "", "SSL certificate (PEM)", "Server Net", env="LLAMA_ARG_SSL_CERT_FILE"),
    OptionSpec("--api-prefix", "str", "", "URL prefix (no trailing slash)", "Server Net", env="LLAMA_ARG_API_PREFIX"),
    OptionSpec("--path", "str", "", "Static files directory", "Server Net", env="LLAMA_ARG_STATIC_PATH"),
    OptionSpec("--cors-origins", "str", "*", "Allowed CORS origins, csv ('localhost' = reflect)", "Server Net", env="LLAMA_ARG_CORS_ORIGINS"),
    OptionSpec("--cors-methods", "str", "", "Allowed CORS methods, csv", "Server Net", env="LLAMA_ARG_CORS_METHODS"),
    OptionSpec("--cors-headers", "str", "", "Allowed CORS headers, csv", "Server Net", env="LLAMA_ARG_CORS_HEADERS"),
    OptionSpec("--cors-credentials", "bool", "", "Allow CORS credentials (default: on)", "Server Net",
               neg="--no-cors-credentials", default_on=True, env="LLAMA_ARG_CORS_CREDENTIALS"),
    OptionSpec("--timeout", "int", "3600", "Read/write timeout seconds", "Server Net", "-to", env="LLAMA_ARG_TIMEOUT"),
    OptionSpec("--sse-ping-interval", "int", "30", "SSE ping seconds (-1 = off)", "Server Net", env="LLAMA_ARG_SSE_PING_INTERVAL"),
    OptionSpec("--threads-http", "int", "-1", "HTTP worker threads", "Server Net", env="LLAMA_ARG_THREADS_HTTP"),
    OptionSpec("--no-webui", "bool", "", "Disable the Web UI", "Server Net", short="--no-ui"),
    # ---------------- Server Behavior ----------------
    OptionSpec("--parallel", "int", "-1", "Server slots (-1 = auto)", "Server Behavior", "-np", env="LLAMA_ARG_N_PARALLEL"),
    OptionSpec("--cont-batching", "bool", "", "Continuous batching (default: on)", "Server Behavior", "-cb",
               neg="--no-cont-batching", default_on=True, env="LLAMA_ARG_CONT_BATCHING"),
    OptionSpec("--cache-prompt", "bool", "", "Prompt caching (default: on)", "Server Behavior",
               neg="--no-cache-prompt", default_on=True, env="LLAMA_ARG_CACHE_PROMPT"),
    OptionSpec("--cache-reuse", "int", "0", "Min chunk to reuse via KV shifting", "Server Behavior", env="LLAMA_ARG_CACHE_REUSE"),
    OptionSpec("--cache-ram", "int", "8192", "Max prompt-cache MiB (-1 = none, 0 = off)", "Server Behavior", "-cram", env="LLAMA_ARG_CACHE_RAM"),
    OptionSpec("--kv-unified", "bool", "", "Unified KV buffer (default: on if slots auto)", "Server Behavior", "-kvu",
               neg="--no-kv-unified", default_on=True, env="LLAMA_ARG_KV_UNIFIED"),
    OptionSpec("--ctx-checkpoints", "int", "32", "Max context checkpoints per slot", "Server Behavior", "-ctxcp", env="LLAMA_ARG_CTX_CHECKPOINTS"),
    OptionSpec("--context-shift", "bool", "", "Context shift on infinite generation", "Server Behavior", neg="--no-context-shift", env="LLAMA_ARG_CONTEXT_SHIFT"),
    OptionSpec("--warmup", "bool", "", "Warmup with empty run (default: on)", "Server Behavior", neg="--no-warmup", default_on=True),
    OptionSpec("--special", "bool", "", "Special tokens output", "Server Behavior", "-sp"),
    OptionSpec("--reverse-prompt", "str", "", "Halt generation at PROMPT", "Server Behavior", "-r"),
    OptionSpec("--spm-infill", "bool", "", "Suffix/Prefix/Middle infill pattern", "Server Behavior"),
    OptionSpec("--slot-save-path", "str", "", "Save slot KV cache path", "Server Behavior"),
    OptionSpec("--media-path", "str", "", "Local media dir (file:// URLs)", "Server Behavior"),
    OptionSpec("--models-dir", "str", "", "Router server models directory", "Server Behavior", env="LLAMA_ARG_MODELS_DIR"),
    OptionSpec("--models-preset", "str", "", "Router server presets INI file", "Server Behavior", env="LLAMA_ARG_MODELS_PRESET"),
    OptionSpec("--models-max", "int", "4", "Router max loaded models (0 = unlimited)", "Server Behavior", env="LLAMA_ARG_MODELS_MAX"),
    OptionSpec("--models-autoload", "bool", "", "Router autoload (default: on)", "Server Behavior",
               neg="--no-models-autoload", default_on=True, env="LLAMA_ARG_MODELS_AUTOLOAD"),
    OptionSpec("--slots", "bool", "", "Slots monitoring endpoint (default: on)", "Server Behavior", neg="--no-slots", default_on=True, env="LLAMA_ARG_ENDPOINT_SLOTS"),
    OptionSpec("--metrics", "bool", "", "Prometheus /metrics endpoint", "Server Behavior", env="LLAMA_ARG_ENDPOINT_METRICS"),
    OptionSpec("--props", "bool", "", "Allow POST /props", "Server Behavior", env="LLAMA_ARG_ENDPOINT_PROPS"),
    OptionSpec("--sleep-idle-seconds", "int", "-1", "Sleep after N idle seconds (-1 = off)", "Server Behavior"),
    OptionSpec("--rerank", "bool", "", "Enable reranking endpoint", "Server Behavior", env="LLAMA_ARG_RERANKING"),
    OptionSpec("--jinja", "bool", "", "Jinja chat templates (default: on)", "Server Behavior", neg="--no-jinja", default_on=True, env="LLAMA_ARG_JINJA"),
    OptionSpec("--lora-init-without-apply", "bool", "", "Load LoRA without applying", "Server Behavior"),
    OptionSpec("--log-prompts-dir", "str", "", "Debug: log prompts to dir", "Server Behavior"),
    # ---------------- Multimodal ----------------
    OptionSpec("--mmproj-offload", "bool", "", "GPU offload mmproj (default: on)", "Multimodal",
               neg="--no-mmproj-offload", default_on=True, env="LLAMA_ARG_MMPROJ_OFFLOAD"),
    OptionSpec("--image-min-tokens", "int", "", "Min tokens per image (vision dynamic-res)", "Multimodal", env="LLAMA_ARG_IMAGE_MIN_TOKENS"),
    OptionSpec("--image-max-tokens", "int", "", "Max tokens per image (vision dynamic-res)", "Multimodal", env="LLAMA_ARG_IMAGE_MAX_TOKENS"),
    OptionSpec("--video-fps", "float", "4", "Target video FPS", "Multimodal", env="LLAMA_ARG_VIDEO_FPS"),
    OptionSpec("--video-ffmpeg-dir", "str", "", "ffmpeg/ffprobe directory", "Multimodal", env="LLAMA_ARG_VIDEO_FFMPEG_DIR"),
    # ---------------- Speculative ----------------
    OptionSpec("--spec-type", "str", "none", "Speculative types, csv (none = off)", "Speculative", env="LLAMA_ARG_SPEC_TYPE"),
    OptionSpec("--spec-draft-model", "str", "", "Draft model for spec. decoding", "Speculative", "-md", env="LLAMA_ARG_SPEC_DRAFT_MODEL"),
    OptionSpec("--spec-draft-n-max", "int", "3", "Draft tokens (max)", "Speculative", env="LLAMA_ARG_SPEC_DRAFT_N_MAX"),
    OptionSpec("--spec-draft-n-min", "int", "0", "Draft tokens (min)", "Speculative", env="LLAMA_ARG_SPEC_DRAFT_N_MIN"),
    OptionSpec("--spec-draft-ngl", "str", "auto", "Draft layers in VRAM (num|auto|all)", "Speculative", "-ngld", env="LLAMA_ARG_N_GPU_LAYERS_DRAFT"),
    OptionSpec("--spec-draft-device", "str", "", "Draft offload devices csv", "Speculative", "-devd"),
    OptionSpec("--spec-draft-hf-repo", "str", "", "Draft model HF repo", "Speculative", "-hfd", env="LLAMA_ARG_SPEC_DRAFT_HF_REPO"),
    OptionSpec("--spec-draft-threads", "int", "", "Draft threads", "Speculative", "-td"),
    OptionSpec("--spec-draft-p-split", "float", "0.1", "Spec split probability", "Speculative", env="LLAMA_ARG_SPEC_DRAFT_P_SPLIT"),
    OptionSpec("--spec-default", "bool", "", "Default speculative config", "Speculative"),
    OptionSpec("--lookup-cache-static", "str", "", "Static lookup cache file", "Speculative", "-lcs"),
    OptionSpec("--lookup-cache-dynamic", "str", "", "Dynamic lookup cache file", "Speculative", "-lcd"),
    # ---------------- Tools & Agent ----------------
    OptionSpec("--tools", "str", "", "Built-in agent tools csv or 'all' (untrusted: off)", "Tools & Agent", env="LLAMA_ARG_TOOLS"),
    OptionSpec("--tools-runtime", "str", "none", "Tool runtime (none|docker:|podman:|ssh:…)", "Tools & Agent", env="LLAMA_ARG_TOOLS_RUNTIME"),
    OptionSpec("--mcp-servers-config", "str", "", "MCP servers JSON file (Cursor format)", "Tools & Agent", env="LLAMA_ARG_MCP_SERVERS_CONFIG"),
    OptionSpec("--mcp-servers-json", "str", "", "Inline MCP servers JSON", "Tools & Agent", env="LLAMA_ARG_MCP_SERVERS_JSON"),
    OptionSpec("--agent", "bool", "", "CORS proxy + all tools (untrusted: off)", "Tools & Agent", "-ag", env="LLAMA_ARG_AGENT"),
    # ---------------- Chat Template ----------------
    OptionSpec("--chat-template", "str", "", "Custom Jinja chat template", "Chat Template", env="LLAMA_ARG_CHAT_TEMPLATE"),
    OptionSpec("--chat-template-file", "str", "", "Custom Jinja template file", "Chat Template", env="LLAMA_ARG_CHAT_TEMPLATE_FILE"),
    OptionSpec("--chat-template-kwargs", "str", "", "Template kwargs JSON object", "Chat Template", env="LLAMA_ARG_CHAT_TEMPLATE_KWARGS"),
    OptionSpec("--reasoning", "choice", "auto", "Reasoning/thinking in chat", "Chat Template", "-rea", ("on", "off", "auto"), env="LLAMA_ARG_REASONING"),
    OptionSpec("--reasoning-format", "choice", "auto", "Thought-tag handling", "Chat Template",
               ("auto", "none", "deepseek", "deepseek-legacy"), env="LLAMA_ARG_THINK"),
    OptionSpec("--reasoning-effort", "choice", "default", "Reasoning effort level", "Chat Template",
               ("default", "minimal", "low", "medium", "high", "xhigh", "max"), env="LLAMA_ARG_REASONING_EFFORT"),
    OptionSpec("--reasoning-budget", "int", "-1", "Thinking token budget (-1 = ∞, 0 = end now)", "Chat Template", env="LLAMA_ARG_THINK_BUDGET"),
    OptionSpec("--reasoning-preserve", "bool", "", "Preserve reasoning in history (default: on)", "Chat Template",
               neg="--no-reasoning-preserve", default_on=True, env="LLAMA_ARG_REASONING_PRESERVE"),
    OptionSpec("--prefill-assistant", "bool", "", "Prefill trailing assistant message (default: on)", "Chat Template",
               neg="--no-prefill-assistant", default_on=True, env="LLAMA_ARG_PREFILL_ASSISTANT"),
    OptionSpec("--slot-prompt-similarity", "float", "0.1", "Slot reuse similarity (0 = off)", "Chat Template", "-sps"),
    # ---------------- Logging ----------------
    OptionSpec("--verbose", "bool", "", "Verbose logging (all messages)", "Logging", "-v"),
    OptionSpec("--verbosity", "int", "3", "Log verbosity 0..5", "Logging", "-lv", env="LLAMA_ARG_LOG_VERBOSITY"),
    OptionSpec("--log-file", "str", "", "Log to file", "Logging", env="LLAMA_ARG_LOG_FILE"),
    OptionSpec("--log-colors", "choice", "auto", "Colored logging", "Logging", ("on", "off", "auto"), env="LLAMA_ARG_LOG_COLORS"),
    OptionSpec("--log-disable", "bool", "", "Disable logging", "Logging"),
    OptionSpec("--offline", "bool", "", "Offline mode (cache only, no network)", "Logging", env="LLAMA_ARG_OFFLINE"),
    OptionSpec("--perf", "bool", "", "libllama perf timings", "Logging", neg="--no-perf", env="LLAMA_ARG_PERF"),
    # ---------------- Misc ----------------
    OptionSpec("--escape", "bool", "", "Process escape sequences (default: on)", "Misc", "-e", neg="--no-escape", default_on=True),
    OptionSpec("--version", "bool", "", "Show version and exit (preview only)", "Misc"),
]

BY_FLAG: dict[str, OptionSpec] = {o.flag: o for o in OPTIONS}


def parse_help_flags(help_text: str) -> list[str]:
    """Extract `--long-flag` tokens from `llama-server --help` output."""
    import re

    found: list[str] = []
    for m in re.finditer(r"--[a-z][a-z0-9][a-z0-9\-]*", help_text):
        fl = m.group(0)
        if fl not in found:
            found.append(fl)
    return found


def uncovered_flags(help_text: str) -> list[str]:
    """Flags present in --help output but missing from the catalog."""
    return [f for f in parse_help_flags(help_text) if f not in BY_FLAG]
