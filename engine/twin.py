"""clone(): derive a new frozen Twin from an existing one, preserving lineage."""

from engine.models import Twin, Control, Edge, PrivilegeGrant, twin_hash


def clone(
    twin: Twin,
    *,
    add_controls: tuple[Control, ...] = (),
    add_edges: tuple[Edge, ...] = (),
    remove_edges: tuple[Edge, ...] = (),
    add_grants: tuple[PrivilegeGrant, ...] = ()
) -> Twin:
    """Clone a digital twin with incremental updates, preserving lineage.
    
    Never mutates the input.
    New twin's id = twin_hash(new twin).
    parent_id = twin.id.
    """
    # 1. Update controls: replace control if ID matches, else append
    add_ctrl_ids = {c.id for c in add_controls}
    new_controls = tuple(c for c in twin.controls if c.id not in add_ctrl_ids) + tuple(add_controls)
    
    # 2. Update edges: remove edges matching remove_edges (by exact object or (src, dst, technique))
    remove_keys = {(e.src, e.dst, e.technique) for e in remove_edges}
    remaining_edges = tuple(e for e in twin.edges if (e.src, e.dst, e.technique) not in remove_keys)
    add_keys = {(e.src, e.dst, e.technique) for e in add_edges}
    new_edges = tuple(e for e in remaining_edges if (e.src, e.dst, e.technique) not in add_keys) + tuple(add_edges)
    
    # 3. Update grants
    new_grants = tuple(g for g in twin.grants if g not in add_grants) + tuple(add_grants)
    
    # 4. Construct candidate with parent_id = twin.id
    candidate = Twin(
        id="",
        assets=twin.assets,
        identities=twin.identities,
        grants=new_grants,
        edges=new_edges,
        flows=twin.flows,
        controls=new_controls,
        parent_id=twin.id,
    )
    new_id = twin_hash(candidate)
    return candidate.model_copy(update={"id": new_id})


__all__ = ["clone", "twin_hash"]
