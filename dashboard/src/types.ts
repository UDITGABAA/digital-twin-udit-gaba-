// Mirrors engine/models.py, engine/results.py, rules/evaluate.py, rules/optimize.py (v2.1).

export type Evidence = "observed" | "inventory" | "inferred" | "assumed";

export interface Asset { id: string; name: string; kind: string; zone: string; criticality: number; crown_jewel: boolean }
export interface Identity { id: string; name: string; kind: string; tier: number }
export interface PrivilegeGrant { identity_id: string; asset_id: string; capability: "session" | "login" | "admin"; evidence: Evidence }
export interface Edge { src: string; dst: string; technique: string; evidence: Evidence }
export interface ServiceFlow { id: string; name: string; src: string; dst: string; protocol: string; port: number; identity_id: string; criticality: number; evidence: Evidence }
export interface FlowSelector { techniques: string[]; src_zones: string[]; dst_zones: string[]; src_assets: string[]; dst_assets: string[]; protocols: string[]; ports: number[]; identity_ids: string[]; identity_kinds: string[] }
export interface ControlImpact { deny: FlowSelector; exceptions: FlowSelector[]; efficacy: number; breaks_flows: boolean }
export interface Control { id: string; name: string; cost: number; impacts: ControlImpact[] }
export interface Agent { id: string; name: string; start_zones: string[]; capabilities: string[]; objective: string; target: string; noise_budget: number; skill: number }
export interface Twin { id: string; assets: Asset[]; identities: Identity[]; grants: PrivilegeGrant[]; edges: Edge[]; flows: ServiceFlow[]; controls: Control[]; parent_id: string | null }

export interface CompiledEdge { src: string; dst: string; technique: string; identity_id: string | null; requires: string[]; grants: string[]; p_success: number; cost: number; noise: number; evidence: Evidence }
export type Route = CompiledEdge[];

export interface RouteStat { route: Route; p_select: number; p_route: number; effort_score: number; noise: number; observed_freq: number; observed_success: number }
export interface Result { p_success: number; p_success_ci: [number, number]; effort_distribution: number[]; mean_effort: number | null; p90_effort: number | null; edge_frequency: [string, string, string, number][]; routes: RouteStat[]; weighted_risk: number; n: number; seed: number }
export interface Delta { naive_path_reduction_pct: number; effort_increase_pct: number | null; route_eliminated: boolean; p_success_delta: number; substituted_paths: Route[] }
export interface Confidence { level: "High" | "Medium" | "Low"; score: number; unknowns: string[]; undetermined: boolean }
export interface AgentOutcome { agent_id: string; before: Result; after: Result; naive_before: number; naive_after: number; delta: Delta }
export interface Alternative { control_ids: string[]; cost: number; effort_increase_pct: number | null; route_eliminated: boolean; p_success_delta: number; broken_flows: string[]; recommendation: string }
export interface ChangeVerdict { twin_id: string; after_twin_id: string; control_ids: string[]; delta: Delta; before: Result; after: Result; outcomes: AgentOutcome[]; broken_flows: ServiceFlow[]; cost: number; confidence: Confidence; recommendation: "deploy" | "blocked" | "review"; reasons: string[]; alternatives: Alternative[] }

export interface Portfolio { budget: number; baseline_risk: number; constrained: string[]; constrained_risk_reduction: number; constrained_cost: number; constrained_broken_flows: string[]; naive: string[]; naive_risk_reduction: number; naive_cost: number; naive_broken_flows: string[]; evaluated: number }
export interface Blast { asset_id: string; reachable: string[]; crown_jewels_hit: string[]; upper_bound: string[] }

export interface GraphEdge { src: string; dst: string; technique: string; attck: string; identities: string[]; p_success: number; evidence: Evidence }
export interface Graph { twin_id: string; assets: Asset[]; identities: Identity[]; grants: PrivilegeGrant[]; attack_edges: GraphEdge[]; flows: ServiceFlow[]; controls: Control[] }
