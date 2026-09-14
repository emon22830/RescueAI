# Agent rules — `app/agents/`

## The graph
- One graph. If you are adding a second `StateGraph`, stop.
- A node is a module with `run(state: AgentState) -> dict`. It returns only the keys it
  changes.
- Parallel nodes may only write to reducer-backed keys. `evidence` is
  `Annotated[list[Evidence], operator.add]`. Writing `findings` from two parallel nodes
  would silently drop one.
- Adding an investigator means: a node module, `graph.add_node`, an edge from
  `supervisor`, and an edge to `risk`.

## LLM use
- Only `risk` calls the LLM, once — it returns the findings, the project state and the
  recovery plan in a single request, because a metered key counts calls, not tokens.
  `recovery.py` owns the plan half of that prompt and the mapping out of it, but it is
  not a node and makes no call of its own. Investigators collect; they do not reason.
- Never call the LLM SDK directly — use `llm.ask_for(Model, system, prompt)`.
- Short-circuit before spending money: no evidence → no findings, no findings → no plan.

## Evidence citation
- `risk` numbers evidence and the model returns `evidence_indexes`. Map indexes back to
  real objects. Never let the model restate evidence in its own words.
- Guard the index: `if 0 <= i < len(evidence)`.

## Prompts
- System prompt states the role, the rules, and what an empty answer looks like.
- Always allow "no findings". A model that must find a problem will invent one.
- Prompts live in the node file as a `SYSTEM` constant, next to the code that uses them.

## Executor
- No LLM. It maps an action to an integration and calls it.
- Never executes anything whose status is not `"approved"`. That guard lives in
  `executor.execute`, the last code before an external workspace is written to.
- An action's life is `pending → approved → executing → completed | failed`, and every
  step of it is written to the database as it happens.
