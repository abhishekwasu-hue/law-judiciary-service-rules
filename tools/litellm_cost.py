"""LiteLLM proxy callback for the engine's gateway runs (other AI providers, Abhi 02.11.2026): appends one JSON line per
answer {"model", "cost", "in", "out"} to $LITELLM_COST_FILE, so the run's real cost (by LiteLLM's price table; free
models = 0) is stored instead of Claude Code's estimate at Claude prices. Loaded by the proxy config
(`litellm_settings.callbacks: litellm_cost.handler`); the workflow copies this file next to the config."""
import json, os

from litellm.integrations.custom_logger import CustomLogger


class CostLog(CustomLogger):
    def _write(self, kwargs, response_obj):
        path = os.environ.get("LITELLM_COST_FILE")
        if not path:
            return
        u = getattr(response_obj, "usage", None)
        tin, tout = int(getattr(u, "prompt_tokens", 0) or 0), int(getattr(u, "completion_tokens", 0) or 0)
        so = kwargs.get("standard_logging_object") or {}
        model = str(so.get("model") or kwargs.get("model") or "?")  # the provider model (e.g. gemini/gemini-2.5-pro), not the claude-* alias
        try:  # price by the provider model; unknown / free model -> 0
            import litellm
            cin, cout = litellm.cost_per_token(model=model, prompt_tokens=tin, completion_tokens=tout)
            cost = float(cin or 0) + float(cout or 0)
        except Exception:
            cost = 0.0
        rec = {"model": model, "cost": round(cost, 6), "in": tin, "out": tout}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._write(kwargs, response_obj)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._write(kwargs, response_obj)


handler = CostLog()
