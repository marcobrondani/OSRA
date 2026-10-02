"""The OSRA MCP server (ARCHITECTURE section 7, ADR-0005, TR-30 to TR-37).

Local only, over stdio, with no outbound connection of its own. It exposes the
method both as resources and through tools, because some clients never show
resources or prompts to the model (TR-31); the phase interviews are offered
as prompts for clients that surface them, and the same questions come from
the next_questions tool (P-3). There is deliberately no tool that confirms a
register.

Run with ``osra-code mcp WORKSPACE --author NAME``; add ``--writes`` to let
the agent draft into assessments whose agent access is ``draft``.
"""

# No "from __future__ import annotations" here: the tool signatures use
# Literal types built from the method pack at run time, and the SDK reads them
# to publish each tool's allowed values.
import json
from pathlib import Path
from typing import Any, Literal

try:
    from mcp.server.mcpserver import Context, MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError as exc:  # pragma: no cover - the extra is not installed
    raise ImportError("the MCP server needs the 'mcp' extra: pip install 'com.brondani.osra[mcp]'") from exc

from . import __version__
from .agent import AUTHORITY, AgentError, AgentService
from .pack import MethodPack

INSTRUCTIONS = (
    "OSRA (Operational Substrate Risk Audit) finds where an AI system's operational risk converges. "
    "Start with method_overview. To interview the practitioner, call next_questions for the assessment and ask "
    "the questions it returns, then record the answers with the add_ and amend tools. "
    "Use preview to show the practitioner what an answer would produce before writing it. " + AUTHORITY
)


def _client_name(ctx: Context | None) -> str | None:
    """The client's own name from the MCP handshake, where available."""
    try:
        info = ctx.session.client_params.client_info  # type: ignore[union-attr]
        return f"{info.name} {info.version}".strip() if info else None
    except Exception:  # noqa: BLE001 - absent on some transports and in tests
        return None


def build_server(service: AgentService) -> MCPServer:
    server = MCPServer(name="osra", title="OSRA", version=__version__, instructions=INSTRUCTIONS)
    pack = service.pack

    def allowed(field: str) -> Any:
        return Literal[tuple(pack.vocabulary(field))]  # type: ignore[valid-type]

    Layer, OwnerType, Visibility, Fallback = allowed("layer"), allowed("owner_type"), allowed("visibility"), allowed("fallback")
    FailureType, Latency, Confidence = allowed("type"), allowed("latency"), allowed("confidence")
    Impact, Horizon = allowed("impact"), allowed("materialisation_horizon")
    TrustCategory, Status, ScopeMatch, Method = (allowed("trust_category"), allowed("verification_status"),
                                                 allowed("scope_match"), allowed("method"))
    AssessmentType = allowed("assessment_type")
    Topic = Literal[tuple(sorted(service._topics()))]  # type: ignore[valid-type]
    Register = Literal["substrate", "failures", "trust", "scoring", "summary"]
    Match = Literal["id", "name"]

    def call(ctx: Context | None, fn, *args: Any, **kwargs: Any) -> Any:
        name = _client_name(ctx)
        if name:
            service.agent = name
        try:
            return fn(*args, **kwargs)
        except AgentError as exc:
            raise ToolError(exc.render()) from None
        except Exception as exc:  # noqa: BLE001 - an agent gets a refusal, never a traceback
            raise ToolError(f"OSRA-CODE could not complete the call ({type(exc).__name__}). Writes are atomic, so "
                            "an assessment is never left half-written; 'osra-code history' shows what was recorded.") from None

    # -- the method -----------------------------------------------------------------

    @server.tool(description="Start here. The four phases, what each records, the topics get_method explains, and "
                             "what an agent may and may not do (it drafts; a person confirms).")
    def method_overview(ctx: Context) -> dict:
        return call(ctx, service.method_overview)

    @server.tool(description="The method itself, as published, on one topic: layers, substrate, failure-types, "
                             "detection, impact-and-severity, horizons, trust-categories, verification, trust-gap, "
                             "conditions, categories, scoring, ranking, actions, regulations, assessment-types, authority. "
                             "Read this before explaining a rule or an anchor to the practitioner.")
    def get_method(ctx: Context, topic: Topic) -> Any:
        return call(ctx, service.get_method, topic)

    @server.tool(description="One rule of the method by its identifier (for example category.critical-convergence or "
                             "severity.tested-fallback), with its citation in the methodology. Results name the rules "
                             "that produced them.")
    def get_rule(ctx: Context, rule_id: str) -> dict:
        return call(ctx, service.get_rule, rule_id)

    # -- assessments --------------------------------------------------------------------

    @server.tool(description="The assessments in the workspace, with each one's agent access.")
    def list_assessments(ctx: Context) -> list:
        return call(ctx, service.list_assessments)

    @server.tool(description="An assessment's description, the state of each register (draft or confirmed) and "
                             "whether current results exist.")
    def get_assessment(ctx: Context, assessment: str) -> dict:
        return call(ctx, service.get_assessment, assessment)

    @server.tool(description="One register in full: substrate, failures, trust, scoring or summary.")
    def get_register(ctx: Context, assessment: str, register: Register) -> Any:
        return call(ctx, service.get_register, assessment, register)

    @server.tool(description="What is missing: empty layers, dependencies without failure modes or trust signals, "
                             "failure modes without detection or propagation, findings without scores or narrative, "
                             "and registers awaiting the practitioner's confirmation.")
    def whats_missing(ctx: Context, assessment: str) -> dict:
        return call(ctx, service.whats_missing, assessment)

    @server.tool(description="The method's own questions for the next gap in the assessment, and the tool to record "
                             "the answers with. Ask these, in the practitioner's words, rather than inventing questions.")
    def next_questions(ctx: Context, assessment: str) -> dict:
        return call(ctx, service.next_questions, assessment)

    @server.tool(description="Validation diagnostics for the assessment: each names the rule, the entity, the field "
                             "and a valid example.")
    def validate(ctx: Context, assessment: str) -> list:
        return call(ctx, service.validate, assessment)

    @server.tool(description="What proposed changes would produce (conditions, categories, flags, clocks, scores, "
                             "ranks), writing nothing. Each change is {op: add, kind: dependency|failure-mode|"
                             "trust-signal, fields: {...}}, {op: set, id: DEP-01, fields: {path: value}}, "
                             "{op: remove, id: ...} or {op: rate, dependency: DEP-01, scores: {factor: 1-5}}.")
    def preview(ctx: Context, assessment: str, changes: list[dict]) -> dict:
        return call(ctx, service.preview, assessment, changes)

    @server.tool(description="The current results: the convergence matrix and the ranked findings, with an explanation "
                             "of every computed value.")
    def get_results(ctx: Context, assessment: str) -> dict:
        return call(ctx, service.get_results, assessment)

    @server.tool(description="Compare two assessments of the same system, matching dependencies by id (a refresh) or "
                             "by name (independent runs).")
    def compare(ctx: Context, a: str, b: str, match: Match = "id") -> dict:
        return call(ctx, service.compare, a, b, match)

    @server.tool(description="Check that this installation reproduces the published reference results.")
    def verify(ctx: Context) -> dict:
        return call(ctx, service.verify)

    # -- drafting (needs --writes and agent access 'draft') ------------------------------

    @server.tool(description="Create an assessment for one AI system. system needs name, owner, "
                             "regulatory_classification and boundary. The agent's access to it is 'draft'.")
    def create_assessment(ctx: Context, assessment: str, system: dict, assessment_type: AssessmentType = "full") -> dict:
        return call(ctx, service.create_assessment, assessment, system, assessment_type)

    @server.tool(description="Change the system description (name, owner, regulatory_classification, boundary, "
                             "primary_function, users, ...). Status, agent access and the declared mode are the "
                             "practitioner's to change.")
    def update_system(ctx: Context, assessment: str, fields: dict) -> dict:
        return call(ctx, service.update_system, assessment, fields)

    @server.tool(description="Record a dependency (Phase 1). Values: layer from get_method('layers'); owner_type "
                             "internal|vendor|third-party|unknown; visibility visible|known-unmonitored|invisible; "
                             "fallback yes|no|partial (fallback_tested needed unless no). The identifier is allocated.")
    def add_dependency(ctx: Context, assessment: str, name: str, layer: Layer, owner_type: OwnerType, single_point: bool, visibility: Visibility,
                       fallback: Fallback, fallback_tested: bool | None = None, provider: str | None = None,
                       location: str | None = None, notes: str | None = None) -> dict:
        fields = {k: v for k, v in dict(name=name, layer=layer, owner_type=owner_type, single_point=single_point,
                                        visibility=visibility, fallback=fallback, fallback_tested=fallback_tested,
                                        provider=provider, location=location, notes=notes).items() if v is not None}
        return call(ctx, service.add, assessment, "dependency", fields)

    @server.tool(description="Record a failure mode of a dependency (Phase 2). type hard|degradation|silent|contractual|"
                             "cascade; detection_latency seconds|minutes|hours|days|never; detection_confidence "
                             "high|medium|low|none; impact critical|high|medium|low (severity is computed from it); "
                             "materialisation_horizon imminent|days|weeks|months|years.")
    def add_failure_mode(ctx: Context, assessment: str, dependency: str, type: FailureType, description: str, detection_latency: Latency,
                         detection_confidence: Confidence, impact: Impact, tested_fallback: bool, materialisation_horizon: Horizon,
                         detection_mechanism: str | None = None, propagation_path: str | None = None,
                         downstream_impact: str | None = None, downstream_detection: str | None = None) -> dict:
        fields: dict[str, Any] = {
            "dependency": dependency, "type": type, "description": description,
            "detection": {"mechanism": detection_mechanism, "latency": detection_latency, "confidence": detection_confidence},
            "impact": impact, "tested_fallback": tested_fallback, "materialisation_horizon": materialisation_horizon,
        }
        propagation = {k: v for k, v in dict(path=propagation_path, downstream_impact=downstream_impact,
                                             downstream_detection=downstream_detection).items() if v is not None}
        if propagation:
            fields["propagation"] = propagation
        return call(ctx, service.add, assessment, "failure-mode", fields)

    @server.tool(description="Record a trust signal (Phase 3) and the dependencies it concerns. category from "
                             "get_method('trust-categories'); verification_status verified|partially-verified|unverified|"
                             "unverifiable; scope_match yes|no|partial (needed when verified). reliance is what decision "
                             "depends on the claim, or null if none does. chain lists the layers of trust behind it: "
                             "[{party, trusts, verified}]. The trust gap is computed.")
    def add_trust_signal(ctx: Context, assessment: str, dependencies: list[str], category: TrustCategory, claim: str, reliance: str | None,
                         verification_status: Status, scope_match: ScopeMatch | None = None, verification_method: Method | None = None,
                         last_verified: str | None = None, consequence_if_false: str | None = None,
                         chain: list[dict] | None = None) -> dict:
        verification = {k: v for k, v in dict(status=verification_status, scope_match=scope_match,
                                              method=verification_method, last_verified=last_verified).items()
                        if v is not None}
        fields: dict[str, Any] = {"dependencies": dependencies, "category": category, "claim": claim,
                                  "reliance": reliance, "verification": verification}
        if consequence_if_false is not None:
            fields["consequence_if_false"] = consequence_if_false
        if chain:
            fields["chain"] = chain
        return call(ctx, service.add, assessment, "trust-signal", fields)

    @server.tool(description="Link a trust signal to further dependencies. Phase 4 reads trust gaps only through these links.")
    def link_trust_signal(ctx: Context, assessment: str, signal: str, dependencies: list[str]) -> dict:
        return call(ctx, service.link_trust_signal, assessment, signal, dependencies)

    @server.tool(description="Change fields of a dependency, failure mode or trust signal: changes maps a field path "
                             "(for example detection.confidence or propagation.path) to its new value. Computed values "
                             "cannot be set. The register returns to draft.")
    def amend(ctx: Context, assessment: str, entity: str, changes: dict) -> dict:
        return call(ctx, service.amend, assessment, entity, changes)

    @server.tool(description="Remove a dependency, failure mode or trust signal. Its identifier is retired.")
    def remove(ctx: Context, assessment: str, entity: str) -> dict:
        return call(ctx, service.remove, assessment, entity)

    @server.tool(description="Score a finding's five entered factors against the anchors (get_method('scoring')): "
                             "regulatory_exposure, detection_deficit, trust_depth, blast_radius, remediation_complexity, "
                             "1 to 5. Where it sits between two anchors, take the lower, list the factor in "
                             "between_anchors and give the reason. Materialisation horizon is computed.")
    def rate_finding(ctx: Context, assessment: str, dependency: str, scores: dict[str, int], reasons: dict[str, str] | None = None,
                     between_anchors: list[str] | None = None) -> dict:
        return call(ctx, service.rate_finding, assessment, dependency, scores, reasons, between_anchors)

    @server.tool(description="Draft the Convergence Risk Summary narrative for a finding, from what the practitioner "
                             "says: what_converges, failure_modes, trust_signals, why_governance_missed, "
                             "regulatory_exposure, clauses (from get_method('regulations')), recommended_action, actions "
                             "(catalogue ids) or action_gap, internal_document, governance_change.")
    def write_summary(ctx: Context, assessment: str, dependency: str, fields: dict) -> dict:
        return call(ctx, service.write_summary, assessment, dependency, fields)

    @server.tool(description="Run the engine. Refused until the practitioner has confirmed every register the "
                             "assessment needs; it cannot be done through this server.")
    def score(ctx: Context, assessment: str) -> dict:
        return call(ctx, service.score, assessment)

    @server.tool(description="Produce reports from the current run (substrate-map, failure-surface-register, "
                             "trust-surface-register, convergence-risk-summary, board, ciso, cto, refresh) as md, html "
                             "and docx. Reports carrying narrative need the summary confirmed by the practitioner.")
    def generate_reports(ctx: Context, assessment: str, reports: list[str] | None = None, formats: list[str] | None = None) -> dict:
        return call(ctx, service.generate_reports, assessment, reports, formats)

    # -- resources and prompts --------------------------------------------------------------

    for topic in sorted(service._topics()):
        def make(topic=topic):
            def read() -> str:
                return json.dumps(service.get_method(topic), indent=2, ensure_ascii=False)
            return read
        server.resource(f"osra://method/{topic}", name=f"method-{topic}", mime_type="application/json",
                        description=f"The OSRA method: {topic}")(make())

    @server.resource("osra://method/overview", name="method-overview", mime_type="application/json",
                     description="The four phases and the authority model")
    def overview() -> str:
        return json.dumps(service.method_overview(), indent=2, ensure_ascii=False)

    for phase in (1, 2, 3, 4):
        def make_prompt(phase=phase):
            def interview(assessment: str) -> str:
                info = service.method_overview()["phases"][phase - 1]
                return (f"Interview the practitioner for OSRA Phase {phase}, {info['name']}: \"{info['question']}\". "
                        f"Call next_questions for assessment '{assessment}' and ask the questions it returns, one "
                        "dependency at a time, in plain language. Record each answer with the tool next_questions "
                        "names, use preview to show what an answer would produce, and remind the practitioner that "
                        "they confirm each register themselves with 'osra-code confirm'.")
            return interview
        server.prompt(name=f"phase-{phase}-interview", description=f"Interview for Phase {phase}")(make_prompt())

    return server


def serve(workspace: Path, pack: MethodPack, author: str, writes: bool) -> None:
    service = AgentService(workspace=workspace, pack=pack, author=author, writes=writes)
    build_server(service).run("stdio")
