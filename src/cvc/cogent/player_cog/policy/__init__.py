try:
    from cvc.cogent.player_cog.policy.anthropic_pilot import AnthropicCyborgPolicy
except ImportError:
    AnthropicCyborgPolicy = None  # type: ignore[assignment,misc]

try:
    from cvc.cogent.player_cog.policy.openai_pilot import OpenAICyborgPolicy
except ImportError:
    OpenAICyborgPolicy = None  # type: ignore[assignment,misc]

try:
    from cvc.cogent.player_cog.policy.semantic_cog import MettagridSemanticPolicy
except ImportError:
    MettagridSemanticPolicy = None  # type: ignore[assignment,misc]

__all__ = ["AnthropicCyborgPolicy", "MettagridSemanticPolicy", "OpenAICyborgPolicy"]
